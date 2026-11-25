"""[K2] Pipeline Feature Selection cho bài toán dự báo lan truyền sóng ùn tắc Hàng Xanh.

Danh sách cột, nhánh lọc và ngưỡng theo ``02_feature_selection/feature_dictionary.md``.

Nhánh chính ``FeatureSelector`` (dùng cho mô hình cây và SHAP):
  * SỐ : MinMaxScaler (chỉ để đo phương sai) -> VarianceThreshold(0.01).
         Pearson r chỉ để tham khảo, KHÔNG dùng để lọc.
  * ORD: OrdinalEncoder (categories cố định) -> giữ cột có chi2 > ngưỡng tới hạn.
  * NOM: OneHotEncoder(drop="if_binary")     -> giữ cột dummy có chi2 > ngưỡng tới hạn.
  Ngưỡng tới hạn chi2 = chi2.ppf(1 - alpha, df = số lớp - 1), tức 5.99 với 3 lớp.
  Đầu ra giữ GIÁ TRỊ GỐC (không scale) và TÊN GỐC của cột để SHAP đọc được.

Nhánh đối chứng ``PCAFeatureSelector``: các cột SỐ còn lại sau VarianceThreshold
-> StandardScaler -> PCA (giữ 95% phương sai), ghép với các cột ORD/NOM đã chọn.
Nhánh này chỉ để so sánh, không dùng cho SHAP.

Mọi bước học từ dữ liệu đều nằm trong ``fit()``. Khi đặt selector vào một sklearn
``Pipeline``, mỗi fold ``TimeSeriesSplit`` chỉ fit trên phần train, nên không rò rỉ dữ liệu.

Tuần 6 (``[K1]``) bổ sung, cũng tính riêng trên phần train của từng fold:
  * Cờ tĩnh ``flood_prone`` của nút (từ ``nodes.csv`` của ``[H1]``), ghép theo ``node_id``
    bằng ``load_dataset()`` / ``attach_node_attributes()``.
  * Xếp hạng độ quan trọng bằng Mutual Information (bắt được quan hệ phi tuyến của mưa/triều)
    -> ``feature_importance_ranking.csv``; kèm cột SHAP của ``[D2]`` để đối chiếu.
  * Tập rút gọn ``selected_compact`` cho ST-GNN: với mỗi cặp số ``|r| >= 0.9`` bỏ biến có MI thấp hơn,
    KHÔNG BAO GIỜ bỏ biến mưa/triều (``PROTECTED_FEATURES``). Tách ``dynamic`` / ``static``.

Tên file bắt đầu bằng chữ số nên phải import qua ``importlib``::

    import importlib, sys
    sys.path.insert(0, "02_feature_selection")
    fs = importlib.import_module("01_feature_selection_pipeline")
    frame = fs.load_dataset()  # đã có cột flood_prone
    pipe = Pipeline([("select", fs.FeatureSelector()), ("model", LGBMClassifier())])

Chạy kiểm thử trên mock dataset (ghi kết quả vào ``02_feature_selection/results/``)::

    python 02_feature_selection/01_feature_selection_pipeline.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2 as chi2_distribution
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import PCA
from sklearn.feature_selection import VarianceThreshold, chi2, mutual_info_classif
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.utils.validation import check_is_fitted

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT.parent / "01_data_sample" / "mock_hang_xanh_traffic_weather.csv"
NODES_PATH = ROOT.parent / "01_data_sample" / "nodes.csv"
SHAP_IMPORTANCE_PATH = ROOT.parent / "03_models_evaluation" / "results" / "shap" / "feature_importance_lightgbm.csv"
OUTPUT_DIR = ROOT / "results"
# Thuộc tính tĩnh lấy từ nodes.csv và ghép vào bảng dữ liệu theo node_id.
NODE_ATTRIBUTES = ["flood_prone"]

NUMERIC_FEATURES = [
    # Giao thông động
    "speed_kmh", "volume_veh", "speed_ratio", "speed_lag1", "speed_lag2", "speed_lag4",
    "speed_delta1", "upstream_speed_min", "upstream_congested_cnt",
    # Thời tiết, triều, thời gian
    "rain_mm_h", "rain_cum_3h_mm", "temperature_c", "humidity_pct", "tide_level_m",
    "hour_sin", "hour_cos",
    # Thuộc tính tĩnh của nút
    "free_flow_kmh", "lanes_in_mean", "maxspeed_in_kmh", "in_degree", "out_degree",
    "dist_center_m",
]
ORDINAL_CATEGORIES = {
    "time_slot": [0, 1, 2],
    "rain_level": [0, 1, 2, 3, 4],
    "tide_alert": [0, 1, 2, 3],
}
NOMINAL_CATEGORIES = {
    "road_type": ["trunk", "primary", "secondary", "tertiary"],
    "is_weekend": [0, 1],
    "has_twoway": [0, 1],
    "flood_prone": [0, 1],
}
ORDINAL_FEATURES = list(ORDINAL_CATEGORIES)
NOMINAL_FEATURES = list(NOMINAL_CATEGORIES)
ALL_FEATURES = NUMERIC_FEATURES + ORDINAL_FEATURES + NOMINAL_FEATURES
# Nhãn -> số bước 15' nhìn về tương lai (dùng làm khoảng purge giữa train và valid).
TARGET_OFFSETS = {"y_t15": 1, "y_t30": 2, "y_t60": 4}
# Có trong file nhưng KHÔNG phải đặc trưng (khóa, cờ sinh dữ liệu mock).
NON_FEATURE_COLUMNS = ["timestamp", "node_id", "rain_scenario_synthetic"]

# Nhóm đặc trưng gốc (trước One-Hot). "static" là thuộc tính không đổi theo thời gian của nút;
# các nhóm còn lại là đặc trưng động theo bước 15' (chiều thời gian của tensor ST-GNN).
FEATURE_GROUPS = {
    "traffic": ["speed_kmh", "volume_veh", "speed_ratio", "speed_lag1", "speed_lag2", "speed_lag4", "speed_delta1"],
    "propagation": ["upstream_speed_min", "upstream_congested_cnt"],
    "rain": ["rain_mm_h", "rain_cum_3h_mm", "rain_level"],
    "tide": ["tide_level_m", "tide_alert"],
    "weather_other": ["temperature_c", "humidity_pct"],
    "time": ["hour_sin", "hour_cos", "time_slot", "is_weekend"],
    "static": ["free_flow_kmh", "lanes_in_mean", "maxspeed_in_kmh", "in_degree", "out_degree",
               "dist_center_m", "road_type", "has_twoway", "flood_prone"],
}
FEATURE_TO_GROUP = {feature: group for group, features in FEATURE_GROUPS.items() for feature in features}
# Biến mưa/triều có tác động phi tuyến (Đề cương): Pearson cao KHÔNG được dùng làm lý do loại bỏ.
PROTECTED_FEATURES = set(FEATURE_GROUPS["rain"] + FEATURE_GROUPS["tide"])

VARIANCE_THRESHOLD = 0.01
CHI2_ALPHA = 0.05
REDUNDANCY_ABS_R = 0.9
PCA_VARIANCE = 0.95
MI_RANDOM_STATE = 0


def base_feature(encoded_name: str) -> str:
    """Tên cột gốc của một cột sau mã hóa, ví dụ ``road_type_trunk`` -> ``road_type``."""
    if encoded_name in ALL_FEATURES:
        return encoded_name
    for column in NOMINAL_FEATURES:
        if encoded_name.startswith(f"{column}_"):
            return column
    raise KeyError(f"Không xác định được cột gốc của {encoded_name!r}")


def attach_node_attributes(frame: pd.DataFrame, nodes_path: Path = NODES_PATH) -> pd.DataFrame:
    """Ghép thuộc tính tĩnh của nút (``flood_prone``) từ ``nodes.csv`` theo ``node_id`` nếu còn thiếu."""
    missing = [column for column in NODE_ATTRIBUTES if column not in frame.columns]
    if not missing:
        return frame
    nodes = pd.read_csv(nodes_path, encoding="utf-8-sig", usecols=["node_id", *missing])
    for column in missing:
        nodes[column] = nodes[column].map({True: 1, False: 0, "True": 1, "False": 0}).astype(int)
    merged = frame.merge(nodes, on="node_id", how="left", validate="many_to_one")
    unmatched = merged[missing].isna().any(axis=1)
    if unmatched.any():
        raise ValueError(f"node_id không có trong {nodes_path.name}: {sorted(merged.loc[unmatched, 'node_id'].unique())}")
    return merged


def load_dataset(data_path: Path = DATA_PATH, nodes_path: Path = NODES_PATH) -> pd.DataFrame:
    """Đọc bảng dữ liệu theo nút × bước 15' và bổ sung các thuộc tính tĩnh còn thiếu."""
    frame = pd.read_csv(data_path, parse_dates=["timestamp"])
    return attach_node_attributes(frame, nodes_path)


def _check_columns(X: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(X, pd.DataFrame):
        raise TypeError("FeatureSelector cần pandas.DataFrame có tên cột theo feature_dictionary.md")
    missing = [column for column in ALL_FEATURES if column not in X.columns]
    if missing:
        hint = " (dùng load_dataset() hoặc attach_node_attributes() để ghép từ nodes.csv)" if set(missing) <= set(NODE_ATTRIBUTES) else ""
        raise KeyError(f"Thiếu cột đặc trưng: {missing}{hint}")
    return X


def _chi2_scores(values: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """chi2 của sklearn; cột hằng (0/0 -> NaN) được coi là không có ý nghĩa."""
    with np.errstate(divide="ignore", invalid="ignore"):
        scores, p_values = chi2(values, y)
    return np.nan_to_num(scores, nan=0.0), np.nan_to_num(p_values, nan=1.0)


class FeatureSelector(BaseEstimator, TransformerMixin):
    """Nhánh chính: lọc đặc trưng, giữ giá trị và tên gốc."""

    def __init__(self, variance_threshold: float = VARIANCE_THRESHOLD, chi2_alpha: float = CHI2_ALPHA):
        self.variance_threshold = variance_threshold
        self.chi2_alpha = chi2_alpha

    def fit(self, X: pd.DataFrame, y) -> "FeatureSelector":
        X = _check_columns(X)
        y = np.asarray(y)
        n_classes = np.unique(y).size
        self.chi2_critical_ = float(chi2_distribution.ppf(1 - self.chi2_alpha, df=max(n_classes - 1, 1)))

        # --- Nhánh SỐ: VarianceThreshold trên dữ liệu đã MinMax ---
        numeric = X[NUMERIC_FEATURES].astype(float)
        self.numeric_scaler_ = MinMaxScaler().fit(numeric.to_numpy())
        self.variance_selector_ = VarianceThreshold(self.variance_threshold).fit(
            self.numeric_scaler_.transform(numeric.to_numpy())
        )
        numeric_keep = self.variance_selector_.get_support()
        self.selected_numeric_ = [c for c, keep in zip(NUMERIC_FEATURES, numeric_keep) if keep]

        # Pearson chỉ để tham khảo: tương quan với nhãn và cặp đặc trưng dư thừa.
        with np.errstate(divide="ignore", invalid="ignore"):
            self.pearson_target_ = numeric.corrwith(pd.Series(y, index=X.index, dtype=float))
            corr = numeric.corr()
        self.redundant_pairs_ = pd.DataFrame(
            [
                (a, b, corr.loc[a, b])
                for i, a in enumerate(NUMERIC_FEATURES)
                for b in NUMERIC_FEATURES[i + 1:]
                if abs(corr.loc[a, b]) >= REDUNDANCY_ABS_R
            ],
            columns=["feature_a", "feature_b", "pearson_r"],
        )

        # --- Nhánh ORD: OrdinalEncoder + chi2 ---
        self.ordinal_encoder_ = OrdinalEncoder(
            categories=[ORDINAL_CATEGORIES[c] for c in ORDINAL_FEATURES]
        ).fit(X[ORDINAL_FEATURES])
        ordinal_scores, ordinal_p = _chi2_scores(self.ordinal_encoder_.transform(X[ORDINAL_FEATURES]), y)
        self.selected_ordinal_ = [
            c for c, score in zip(ORDINAL_FEATURES, ordinal_scores) if score > self.chi2_critical_
        ]

        # --- Nhánh NOM: OneHotEncoder + chi2 trên từng cột dummy ---
        self.onehot_ = OneHotEncoder(
            categories=[NOMINAL_CATEGORIES[c] for c in NOMINAL_FEATURES],
            drop="if_binary",
            handle_unknown="ignore",
            sparse_output=False,
        ).fit(X[NOMINAL_FEATURES])
        self.onehot_names_ = self.onehot_.get_feature_names_out(NOMINAL_FEATURES).tolist()
        nominal_scores, nominal_p = _chi2_scores(self.onehot_.transform(X[NOMINAL_FEATURES]), y)
        self.selected_onehot_ = [
            c for c, score in zip(self.onehot_names_, nominal_scores) if score > self.chi2_critical_
        ]

        self.selected_features_ = self.selected_numeric_ + self.selected_ordinal_ + self.selected_onehot_
        self.n_encoded_features_ = len(NUMERIC_FEATURES) + len(ORDINAL_FEATURES) + len(self.onehot_names_)
        self.feature_names_out_ = list(self.selected_features_)

        variances = self.variance_selector_.variances_
        rows = [
            {"feature": c, "branch": "numeric", "criterion": "variance_minmax", "score": v,
             "p_value": np.nan, "threshold": self.variance_threshold, "selected": c in self.selected_numeric_,
             "pearson_r_target": self.pearson_target_[c]}
            for c, v in zip(NUMERIC_FEATURES, variances)
        ]
        rows += [
            {"feature": c, "branch": "ordinal", "criterion": "chi2", "score": s, "p_value": p,
             "threshold": self.chi2_critical_, "selected": c in self.selected_ordinal_, "pearson_r_target": np.nan}
            for c, s, p in zip(ORDINAL_FEATURES, ordinal_scores, ordinal_p)
        ]
        rows += [
            {"feature": c, "branch": "nominal", "criterion": "chi2", "score": s, "p_value": p,
             "threshold": self.chi2_critical_, "selected": c in self.selected_onehot_, "pearson_r_target": np.nan}
            for c, s, p in zip(self.onehot_names_, nominal_scores, nominal_p)
        ]
        self.report_ = pd.DataFrame(rows)
        return self

    def _categorical_part(self, X: pd.DataFrame) -> pd.DataFrame:
        onehot = pd.DataFrame(
            self.onehot_.transform(X[NOMINAL_FEATURES]), columns=self.onehot_names_, index=X.index
        )
        return pd.concat([X[self.selected_ordinal_], onehot[self.selected_onehot_]], axis=1)

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        check_is_fitted(self, "selected_features_")
        X = _check_columns(X)
        return pd.concat([X[self.selected_numeric_].astype(float), self._categorical_part(X)], axis=1)

    def get_feature_names_out(self, input_features=None) -> np.ndarray:
        check_is_fitted(self, "feature_names_out_")
        return np.asarray(self.feature_names_out_, dtype=object)


class PCAFeatureSelector(FeatureSelector):
    """Nhánh đối chứng: thay các cột SỐ đã lọc bằng thành phần PCA (không dùng cho SHAP)."""

    def __init__(
        self,
        variance_threshold: float = VARIANCE_THRESHOLD,
        chi2_alpha: float = CHI2_ALPHA,
        pca_variance: float = PCA_VARIANCE,
    ):
        super().__init__(variance_threshold=variance_threshold, chi2_alpha=chi2_alpha)
        self.pca_variance = pca_variance

    def fit(self, X: pd.DataFrame, y) -> "PCAFeatureSelector":
        super().fit(X, y)
        numeric = X[self.selected_numeric_].to_numpy(dtype=float)
        self.pca_scaler_ = StandardScaler().fit(numeric)
        self.pca_ = PCA(n_components=self.pca_variance, svd_solver="full").fit(self.pca_scaler_.transform(numeric))
        self.pca_names_ = [f"pca_{i + 1}" for i in range(self.pca_.n_components_)]
        self.feature_names_out_ = self.pca_names_ + self.selected_ordinal_ + self.selected_onehot_
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        check_is_fitted(self, "pca_")
        X = _check_columns(X)
        numeric = self.pca_scaler_.transform(X[self.selected_numeric_].to_numpy(dtype=float))
        components = pd.DataFrame(self.pca_.transform(numeric), columns=self.pca_names_, index=X.index)
        return pd.concat([components, self._categorical_part(X)], axis=1)


def encoded_features(selector: FeatureSelector, X: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """TOÀN BỘ đặc trưng sau mã hóa (chưa lọc) bằng encoder đã fit, kèm mặt nạ cột rời rạc cho MI."""
    check_is_fitted(selector, "onehot_")
    X = _check_columns(X)
    ordinal = pd.DataFrame(
        selector.ordinal_encoder_.transform(X[ORDINAL_FEATURES]), columns=ORDINAL_FEATURES, index=X.index
    )
    onehot = pd.DataFrame(selector.onehot_.transform(X[NOMINAL_FEATURES]), columns=selector.onehot_names_, index=X.index)
    encoded = pd.concat([X[NUMERIC_FEATURES].astype(float), ordinal, onehot], axis=1)
    discrete = np.array([column not in NUMERIC_FEATURES for column in encoded.columns])
    return encoded, discrete


def mutual_information(encoded: pd.DataFrame, discrete: np.ndarray, y, random_state: int = MI_RANDOM_STATE) -> pd.Series:
    """Mutual Information với nhãn: đo được cả quan hệ phi tuyến mà Pearson bỏ sót."""
    scores = mutual_info_classif(encoded.to_numpy(), np.asarray(y), discrete_features=discrete, random_state=random_state)
    return pd.Series(scores, index=encoded.columns)


def prune_collinear(
    numeric: pd.DataFrame,
    importance: pd.Series,
    threshold: float = REDUNDANCY_ABS_R,
    protected: set[str] = PROTECTED_FEATURES,
) -> list[dict]:
    """Với mỗi cặp ``|r| >= threshold`` (xét từ |r| lớn nhất) bỏ biến có ``importance`` thấp hơn.

    Biến trong ``protected`` (mưa/triều) không bao giờ bị bỏ; cặp có cả hai biến được bảo vệ thì giữ cả hai.
    Cặp mà một biến đã bị bỏ trước đó thì coi như đã xử lý.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = numeric.corr()
    columns = list(numeric.columns)
    pairs = sorted(
        (
            (abs(corr.loc[a, b]), a, b)
            for i, a in enumerate(columns)
            for b in columns[i + 1:]
            if abs(corr.loc[a, b]) >= threshold
        ),
        reverse=True,
    )
    dropped: dict[str, dict] = {}
    for _, a, b in pairs:
        if a in dropped or b in dropped:
            continue
        candidates = [column for column in (a, b) if column not in protected]
        if not candidates:
            continue
        loser = min(candidates, key=lambda column: float(importance.get(column, 0.0)))
        kept = b if loser == a else a
        dropped[loser] = {"feature": loser, "kept": kept, "pearson_r": float(corr.loc[a, b])}
    return list(dropped.values())


def stgnn_split(features: list[str]) -> dict[str, list[str]]:
    """Chia đặc trưng thành động (theo bước 15') và tĩnh (thuộc tính nút) cho tensor ST-GNN."""
    static = [f for f in features if FEATURE_TO_GROUP[base_feature(f)] == "static"]
    return {"dynamic": [f for f in features if f not in static], "static": static}


def load_shap_importance(path: Path = SHAP_IMPORTANCE_PATH) -> pd.DataFrame | None:
    """Mean |SHAP| của LightGBM từ ``[D2]`` (chỉ để đối chiếu, không dùng để chọn đặc trưng)."""
    if not path.exists():
        return None
    shap = pd.read_csv(path, usecols=["target", "feature", "mean_abs_shap"])
    shap["rank_shap"] = shap.groupby("target")["mean_abs_shap"].rank(ascending=False, method="min").astype(int)
    return shap.rename(columns={"mean_abs_shap": "shap_mean_abs"})


def train_folds(timestamps: pd.Series, n_splits: int, gap: int):
    """Phần train của TimeSeriesSplit chia theo mốc thời gian duy nhất (không cắt ngang các nút)."""
    unique_timestamps = np.sort(timestamps.unique())
    splitter = TimeSeriesSplit(n_splits=n_splits, gap=gap)
    for train_index, _ in splitter.split(unique_timestamps):
        yield timestamps.isin(unique_timestamps[train_index]).to_numpy()


def run_on_dataset(
    data_path: Path,
    output_dir: Path,
    n_splits: int = 5,
    nodes_path: Path = NODES_PATH,
    shap_path: Path = SHAP_IMPORTANCE_PATH,
) -> None:
    frame = load_dataset(data_path, nodes_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    shap = load_shap_importance(shap_path)

    report_rows, summary_rows, ranking_rows, selected_json = [], [], [], {}
    for target, offset in TARGET_OFFSETS.items():
        fold_reports, pca_components, pca_totals, fold_mi, fold_collinear = [], [], [], [], []
        for fold, train_mask in enumerate(train_folds(frame["timestamp"], n_splits, gap=offset), start=1):
            train = frame.loc[train_mask]
            selector = PCAFeatureSelector().fit(train[ALL_FEATURES], train[target])
            fold_reports.append(selector.report_.assign(fold=fold))
            pca_components.append(selector.pca_.n_components_)
            pca_totals.append(len(selector.feature_names_out_))

            encoded, discrete = encoded_features(selector, train)
            mi = mutual_information(encoded, discrete, train[target])
            fold_mi.append(mi)
            fold_collinear.append(prune_collinear(train[selector.selected_numeric_], mi))

        folds = pd.concat(fold_reports, ignore_index=True)
        aggregated = (
            folds.groupby(["feature", "branch", "criterion"], sort=False)
            .agg(
                score_mean=("score", "mean"),
                p_value_mean=("p_value", "mean"),
                threshold=("threshold", "first"),
                selection_frequency=("selected", "mean"),
                pearson_r_target_mean=("pearson_r_target", "mean"),
            )
            .reset_index()
        )
        # Chốt đặc trưng được chọn ở đa số fold (ổn định theo thời gian).
        aggregated["selected_final"] = aggregated["selection_frequency"] > 0.5
        report_rows.append(aggregated.assign(target=target))

        selected = aggregated.loc[aggregated["selected_final"], "feature"].tolist()
        dropped = aggregated.loc[~aggregated["selected_final"], "feature"].tolist()

        # Đa cộng tuyến: chốt biến bị bỏ ở đa số fold (và vẫn nằm trong tập đã chọn).
        drop_counts = Counter(item["feature"] for items in fold_collinear for item in items)
        collinear = []
        for feature in selected:  # giữ thứ tự cột để file JSON ổn định giữa các lần chạy
            count = drop_counts.get(feature, 0)
            if count / n_splits <= 0.5:
                continue
            records = [item for items in fold_collinear for item in items if item["feature"] == feature]
            collinear.append({
                "feature": feature,
                "kept": Counter(item["kept"] for item in records).most_common(1)[0][0],
                "pearson_r_mean": round(float(np.mean([item["pearson_r"] for item in records])), 4),
                "fold_frequency": round(count / n_splits, 2),
            })
        collinear_names = {item["feature"] for item in collinear}
        compact = [feature for feature in selected if feature not in collinear_names]

        selected_json[target] = {
            "selected": selected,
            "dropped": dropped,
            "selected_compact": compact,
            "collinear_dropped": collinear,
            "stgnn": stgnn_split(compact),
        }
        n_encoded = len(aggregated)
        n_pca_total = float(np.mean(pca_totals))
        summary_rows.append({
            "target": target,
            "n_raw_features": len(ALL_FEATURES),
            "n_encoded_features": n_encoded,
            "n_selected": len(selected),
            "reduction_pct": round(100 * (1 - len(selected) / n_encoded), 1),
            "n_compact": len(compact),
            "reduction_compact_pct": round(100 * (1 - len(compact) / n_encoded), 1),
            "pca_components_mean": float(np.mean(pca_components)),
            "n_pca_total_mean": n_pca_total,
            "reduction_pca_pct": round(100 * (1 - n_pca_total / n_encoded), 1),
            "folds": n_splits,
        })

        mi = pd.concat(fold_mi, axis=1)
        ranking = pd.DataFrame({"feature": mi.index, "mi_mean": mi.mean(axis=1).to_numpy(), "mi_std": mi.std(axis=1).to_numpy()})
        ranking["base_feature"] = ranking["feature"].map(base_feature)
        ranking["group"] = ranking["base_feature"].map(FEATURE_TO_GROUP)
        ranking = ranking.merge(aggregated[["feature", "branch", "selected_final"]], on="feature", how="left")
        ranking["collinear_dropped"] = ranking["feature"].isin(collinear_names)
        ranking["selected_compact"] = ranking["feature"].isin(compact)
        ranking["rank_mi"] = ranking["mi_mean"].rank(ascending=False, method="min").astype(int)
        if shap is not None:
            ranking = ranking.merge(shap.loc[shap["target"] == target].drop(columns="target"), on="feature", how="left")
        else:
            ranking[["shap_mean_abs", "rank_shap"]] = np.nan
        ranking_rows.append(ranking.assign(target=target).sort_values("rank_mi"))

    report = pd.concat(report_rows, ignore_index=True)
    report = report[["target"] + [c for c in report.columns if c != "target"]]
    report.to_csv(output_dir / "feature_selection_report.csv", index=False, float_format="%.6f")
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output_dir / "dimension_summary.csv", index=False)
    with (output_dir / "selected_features.json").open("w", encoding="utf-8") as file:
        json.dump(selected_json, file, ensure_ascii=False, indent=2)

    ranking_columns = [
        "target", "rank_mi", "feature", "base_feature", "group", "branch", "mi_mean", "mi_std",
        "selected_final", "collinear_dropped", "selected_compact", "shap_mean_abs", "rank_shap",
    ]
    ranking = pd.concat(ranking_rows, ignore_index=True)[ranking_columns]
    ranking["rank_shap"] = ranking["rank_shap"].astype("Int64")
    ranking.to_csv(output_dir / "feature_importance_ranking.csv", index=False, float_format="%.6f")

    # Cặp đặc trưng dư thừa: chỉ mô tả dữ liệu, không phụ thuộc nhãn và không dùng để lọc.
    redundant = FeatureSelector().fit(frame[ALL_FEATURES], frame["y_t15"]).redundant_pairs_
    redundant.sort_values("pearson_r", key=np.abs, ascending=False).to_csv(
        output_dir / "pearson_redundant_pairs.csv", index=False, float_format="%.4f"
    )

    print(summary.to_string(index=False))
    for target, result in selected_json.items():
        print(f"\n{target} bị loại (lọc): {result['dropped']}")
        print(f"{target} bị loại (đa cộng tuyến): {[item['feature'] for item in result['collinear_dropped']]}")
    print(f"\nĐã ghi kết quả vào {output_dir}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):  # console Windows mặc định cp1252 không in được tiếng Việt
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="[K1]/[K2] Chạy Feature Selection theo từng fold TimeSeriesSplit.")
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--nodes", type=Path, default=NODES_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--splits", type=int, default=5)
    args = parser.parse_args()
    run_on_dataset(args.data, args.output_dir, args.splits, nodes_path=args.nodes)


if __name__ == "__main__":
    main()
