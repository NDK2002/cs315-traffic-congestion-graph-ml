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

Tên file bắt đầu bằng chữ số nên phải import qua ``importlib``::

    import importlib, sys
    sys.path.insert(0, "02_feature_selection")
    fs = importlib.import_module("01_feature_selection_pipeline")
    pipe = Pipeline([("select", fs.FeatureSelector()), ("model", LGBMClassifier())])

Chạy kiểm thử trên mock dataset (ghi kết quả vào ``02_feature_selection/results/``)::

    python 02_feature_selection/01_feature_selection_pipeline.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2 as chi2_distribution
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import PCA
from sklearn.feature_selection import VarianceThreshold, chi2
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.utils.validation import check_is_fitted

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT.parent / "01_data_sample" / "mock_hang_xanh_traffic_weather.csv"
OUTPUT_DIR = ROOT / "results"

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
}
ORDINAL_FEATURES = list(ORDINAL_CATEGORIES)
NOMINAL_FEATURES = list(NOMINAL_CATEGORIES)
ALL_FEATURES = NUMERIC_FEATURES + ORDINAL_FEATURES + NOMINAL_FEATURES
# Nhãn -> số bước 15' nhìn về tương lai (dùng làm khoảng purge giữa train và valid).
TARGET_OFFSETS = {"y_t15": 1, "y_t30": 2, "y_t60": 4}
# Có trong file nhưng KHÔNG phải đặc trưng (khóa, cờ sinh dữ liệu mock).
NON_FEATURE_COLUMNS = ["timestamp", "node_id", "rain_scenario_synthetic"]

VARIANCE_THRESHOLD = 0.01
CHI2_ALPHA = 0.05
REDUNDANCY_ABS_R = 0.9
PCA_VARIANCE = 0.95


def _check_columns(X: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(X, pd.DataFrame):
        raise TypeError("FeatureSelector cần pandas.DataFrame có tên cột theo feature_dictionary.md")
    missing = [column for column in ALL_FEATURES if column not in X.columns]
    if missing:
        raise KeyError(f"Thiếu cột đặc trưng: {missing}")
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


def train_folds(timestamps: pd.Series, n_splits: int, gap: int):
    """Phần train của TimeSeriesSplit chia theo mốc thời gian duy nhất (không cắt ngang các nút)."""
    unique_timestamps = np.sort(timestamps.unique())
    splitter = TimeSeriesSplit(n_splits=n_splits, gap=gap)
    for train_index, _ in splitter.split(unique_timestamps):
        yield timestamps.isin(unique_timestamps[train_index]).to_numpy()


def run_on_dataset(data_path: Path, output_dir: Path, n_splits: int = 5) -> None:
    frame = pd.read_csv(data_path, parse_dates=["timestamp"])
    output_dir.mkdir(parents=True, exist_ok=True)

    report_rows, summary_rows, selected_json = [], [], {}
    for target, offset in TARGET_OFFSETS.items():
        fold_reports, pca_components = [], []
        for fold, train_mask in enumerate(train_folds(frame["timestamp"], n_splits, gap=offset), start=1):
            train = frame.loc[train_mask]
            selector = PCAFeatureSelector().fit(train[ALL_FEATURES], train[target])
            fold_reports.append(selector.report_.assign(fold=fold))
            pca_components.append(selector.pca_.n_components_)

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
        selected_json[target] = {"selected": selected, "dropped": dropped}
        n_encoded = len(aggregated)
        summary_rows.append({
            "target": target,
            "n_raw_features": len(ALL_FEATURES),
            "n_encoded_features": n_encoded,
            "n_selected": len(selected),
            "reduction_pct": round(100 * (1 - len(selected) / n_encoded), 1),
            "pca_components_mean": float(np.mean(pca_components)),
            "folds": n_splits,
        })

    report = pd.concat(report_rows, ignore_index=True)
    report = report[["target"] + [c for c in report.columns if c != "target"]]
    report.to_csv(output_dir / "feature_selection_report.csv", index=False, float_format="%.6f")
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output_dir / "dimension_summary.csv", index=False)
    with (output_dir / "selected_features.json").open("w", encoding="utf-8") as file:
        json.dump(selected_json, file, ensure_ascii=False, indent=2)

    # Cặp đặc trưng dư thừa: chỉ mô tả dữ liệu, không phụ thuộc nhãn và không dùng để lọc.
    redundant = FeatureSelector().fit(frame[ALL_FEATURES], frame["y_t15"]).redundant_pairs_
    redundant.sort_values("pearson_r", key=np.abs, ascending=False).to_csv(
        output_dir / "pearson_redundant_pairs.csv", index=False, float_format="%.4f"
    )

    print(summary.to_string(index=False))
    for target, result in selected_json.items():
        print(f"\n{target} bị loại: {result['dropped']}")
    print(f"\nĐã ghi kết quả vào {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="[K2] Chạy Feature Selection theo từng fold TimeSeriesSplit.")
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--splits", type=int, default=5)
    args = parser.parse_args()
    run_on_dataset(args.data, args.output_dir, args.splits)


if __name__ == "__main__":
    main()
