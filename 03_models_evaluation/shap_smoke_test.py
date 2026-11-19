"""Smoke-test SHAP TreeExplainer trên mô hình cây 3 lớp với tên biến gốc (CS315 - [D2]).

Mục tiêu:
1. Xác nhận shap.TreeExplainer chạy thông với RandomForest và LightGBM 3 lớp (0, 1, 2).
2. Xác nhận kết quả SHAP giữ đúng tên cột theo 02_feature_selection/feature_dictionary.md.
3. Xác nhận phiên bản shap trong môi trường khớp requirements.txt (shap>=0.46.0).

Chạy với dữ liệu giả (khi chưa có model của [T3]):
    python 03_models_evaluation/shap_smoke_test.py

Chạy với model và dữ liệu của [T3] (sinh model trước bằng mock_ml_pipeline.py):
    python 03_models_evaluation/mock_ml_pipeline.py
    python 03_models_evaluation/shap_smoke_test.py \
        --model 03_models_evaluation/results/randomforest_y_t15_mock.joblib \
                03_models_evaluation/results/lightgbm_y_t15_mock.joblib \
        --data 01_data_sample/mock_hang_xanh_traffic_weather.csv
Model của [T3] là sklearn Pipeline (One-Hot + classifier); script tự tách để TreeExplainer chạy được.

Lưu ý về đơn vị SHAP: TreeExplainer giải thích đầu ra gốc của từng loại model.
- RandomForest: SHAP tính trên xác suất (0–1), giá trị thường nhỏ (~0.05).
- LightGBM / XGBoost: SHAP tính trên log-odds (raw margin), giá trị lớn hơn nhiều (~1–2).
Vì vậy không so trực tiếp độ lớn |SHAP| giữa hai loại model; chỉ so thứ hạng biến trong từng model.
"""

from __future__ import annotations

import argparse
import pathlib

import joblib
import lightgbm
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import sklearn
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

MIN_SHAP_VERSION = (0, 46)
TARGET_CLASS = 2
EXPLAIN_ROWS = 300
SEED = 42

# Tên cột sau Feature Selection theo feature_dictionary.md (biến số + Ordinal + One-Hot giữ tên gốc)
NUMERIC_COLS = [
    "speed_kmh", "volume_veh", "speed_ratio", "speed_lag1", "speed_lag2", "speed_lag4", "speed_delta1",
    "upstream_speed_min", "upstream_congested_cnt",
    "rain_mm_h", "rain_cum_3h_mm", "temperature_c", "humidity_pct", "tide_level_m",
    "hour_sin", "hour_cos",
    "free_flow_kmh", "lanes_in_mean", "maxspeed_in_kmh", "in_degree", "out_degree", "dist_center_m",
]
ORDINAL_COLS = ["time_slot", "rain_level", "tide_alert"]
ONEHOT_COLS = ["road_type_primary", "road_type_secondary", "road_type_tertiary", "road_type_trunk",
               "is_weekend_1", "has_twoway_1"]
FEATURE_COLS = NUMERIC_COLS + ORDINAL_COLS + ONEHOT_COLS


def make_dummy_data(n_rows: int = 3000, seed: int = SEED) -> tuple[pd.DataFrame, pd.Series]:
    """Sinh dữ liệu giả đúng tên cột để kiểm tra kỹ thuật. Không dùng để kết luận về mô hình."""
    rng = np.random.default_rng(seed)
    free_flow = rng.uniform(30, 45, n_rows)
    rain = np.where(rng.random(n_rows) < 0.15, rng.uniform(10, 60, n_rows), rng.uniform(0, 3, n_rows))
    upstream_cnt = rng.integers(0, 3, n_rows)
    minute = rng.integers(0, 96, n_rows) * 15
    hour = minute / 60
    peak = ((hour >= 6.5) & (hour < 9)) | ((hour >= 16.5) & (hour < 19))
    tide = rng.uniform(0.8, 1.8, n_rows)

    ratio = np.clip(0.85 - 0.25 * peak - 0.01 * rain - 0.12 * upstream_cnt + rng.normal(0, 0.08, n_rows), 0.05, 1.0)
    speed = ratio * free_flow
    lag1 = speed * rng.uniform(0.9, 1.1, n_rows)
    road = rng.choice(["primary", "secondary", "tertiary", "trunk"], n_rows)

    X = pd.DataFrame({
        "speed_kmh": speed,
        "volume_veh": rng.integers(50, 400, n_rows),
        "speed_ratio": ratio,
        "speed_lag1": lag1,
        "speed_lag2": lag1 * rng.uniform(0.9, 1.1, n_rows),
        "speed_lag4": lag1 * rng.uniform(0.85, 1.15, n_rows),
        "speed_delta1": speed - lag1,
        "upstream_speed_min": free_flow * np.clip(ratio - 0.1 * upstream_cnt, 0.05, 1.0),
        "upstream_congested_cnt": upstream_cnt,
        "rain_mm_h": rain,
        "rain_cum_3h_mm": rain * rng.uniform(1, 3, n_rows),
        "temperature_c": rng.uniform(25, 34, n_rows),
        "humidity_pct": rng.uniform(60, 98, n_rows),
        "tide_level_m": tide,
        "hour_sin": np.sin(2 * np.pi * minute / 1440),
        "hour_cos": np.cos(2 * np.pi * minute / 1440),
        "free_flow_kmh": free_flow,
        "lanes_in_mean": rng.uniform(2, 5, n_rows),
        "maxspeed_in_kmh": rng.choice([50, 60], n_rows),
        "in_degree": rng.integers(0, 5, n_rows),
        "out_degree": rng.integers(0, 6, n_rows),
        "dist_center_m": rng.uniform(40, 1120, n_rows),
        "time_slot": np.where(peak, 2, np.where((hour >= 22) | (hour < 6), 0, 1)),
        "rain_level": np.digitize(rain, [0.1, 2.5, 10, 30]),
        "tide_alert": np.digitize(tide, [1.4, 1.5, 1.6]),  # BĐ1/2/3 Phú An theo feature_dictionary.md
        "road_type_primary": (road == "primary").astype(int),
        "road_type_secondary": (road == "secondary").astype(int),
        "road_type_tertiary": (road == "tertiary").astype(int),
        "road_type_trunk": (road == "trunk").astype(int),
        "is_weekend_1": rng.integers(0, 2, n_rows),
        "has_twoway_1": rng.integers(0, 2, n_rows),
    })[FEATURE_COLS]

    future_ratio = ratio - 0.004 * rain + rng.normal(0, 0.05, n_rows)
    y = pd.Series(np.select([future_ratio < 0.3, future_ratio < 0.6], [2, 1], 0), name="y_t15")
    return X, y


def check_versions() -> None:
    print(f"shap={shap.__version__} | numpy={np.__version__} | scikit-learn={sklearn.__version__} "
          f"| lightgbm={lightgbm.__version__}")
    major, minor = (int(x) for x in shap.__version__.split(".")[:2])
    if (major, minor) < MIN_SHAP_VERSION:
        raise RuntimeError(f"shap {shap.__version__} thấp hơn yêu cầu >= 0.46.0 trong requirements.txt")


def shap_unit(model) -> str:
    """Đơn vị của giá trị SHAP theo loại model (đầu ra gốc mà TreeExplainer giải thích)."""
    name = type(model).__name__
    if name.startswith(("LGBM", "XGB", "GradientBoosting", "HistGradientBoosting")):
        return "log-odds"
    return "xác suất"


def explain_class(model, X: pd.DataFrame, target_class: int = TARGET_CLASS,
                  check_names: bool = True) -> tuple[np.ndarray, pd.DataFrame]:
    """Tính SHAP của 1 lớp và trả về bảng mức ảnh hưởng trung bình |SHAP| theo tên biến gốc."""
    if not isinstance(X, pd.DataFrame):
        raise TypeError("X phải là pandas.DataFrame để giữ tên biến gốc")

    # Classifier tách từ Pipeline được fit trên mảng numpy (LightGBM tự đặt tên Column_i),
    # tên cột khi đó lấy từ preprocess nên chỉ kiểm số cột.
    if not check_names:
        if getattr(model, "n_features_in_", X.shape[1]) != X.shape[1]:
            raise ValueError(f"Số cột X ({X.shape[1]}) khác lúc huấn luyện ({model.n_features_in_})")
    elif (model_cols := list(getattr(model, "feature_names_in_", X.columns))) != list(X.columns):
        raise ValueError(f"Tên/thứ tự cột của X khác lúc huấn luyện model: {set(model_cols) ^ set(X.columns)}")

    classes = list(model.classes_)
    if target_class not in classes:
        raise ValueError(f"Model không có lớp {target_class}. Các lớp hiện có: {classes}")
    class_idx = classes.index(target_class)

    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(X)
    # shap >= 0.45 trả mảng (số dòng, số biến, số lớp). Bản cũ hơn trả list theo lớp.
    if isinstance(values, list):
        values = np.stack(values, axis=-1)
    expected_shape = (len(X), X.shape[1], len(classes))
    if values.shape != expected_shape:
        raise ValueError(f"Kích thước SHAP {values.shape} khác kỳ vọng {expected_shape}")

    class_values = values[:, :, class_idx]
    importance = (
        pd.DataFrame({"feature": X.columns, "mean_abs_shap": np.abs(class_values).mean(axis=0)})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    return class_values, importance


def save_summary_plot(class_values: np.ndarray, X: pd.DataFrame, path: pathlib.Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    shap.summary_plot(class_values, X, show=False, max_display=15)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=120)
    plt.close()


def run_dummy(out_dir: pathlib.Path) -> None:
    X, y = make_dummy_data()
    print(f"Dữ liệu giả: {X.shape[0]} dòng x {X.shape[1]} cột | phân bố lớp: {y.value_counts().sort_index().to_dict()}")
    X_explain = X.sample(EXPLAIN_ROWS, random_state=SEED)

    models = {
        "RandomForest": RandomForestClassifier(n_estimators=100, max_depth=8, class_weight="balanced",
                                               random_state=SEED, n_jobs=-1),
        "LightGBM": LGBMClassifier(n_estimators=200, class_weight="balanced", random_state=SEED, verbose=-1),
    }
    for name, model in models.items():
        model.fit(X, y)
        class_values, importance = explain_class(model, X_explain)
        unit = shap_unit(model)
        print(f"\n[{name}] TreeExplainer OK | SHAP lớp {TARGET_CLASS}: {class_values.shape} "
              f"| đơn vị: {unit} | top 8 biến:")
        print(importance.head(8).to_string(index=False))
        save_summary_plot(class_values, X_explain, out_dir / f"shap_summary_{name}_class{TARGET_CLASS}.png",
                          f"{name} - SHAP lớp {TARGET_CLASS} ({unit}, dữ liệu giả)")
    print("\nLưu ý: đơn vị SHAP khác nhau giữa các model, chỉ so thứ hạng biến trong từng model.")


def unwrap_pipeline(model, X_raw: pd.DataFrame):
    """Tách sklearn Pipeline của [T3] (preprocess + classifier) vì TreeExplainer chỉ nhận model cây.

    Trả về (classifier, X đã mã hóa One-Hot với tên cột gốc từ get_feature_names_out).
    Model không phải Pipeline thì trả nguyên.
    """
    if not isinstance(model, Pipeline):
        return model, X_raw
    preprocess = model[:-1]
    X_enc = preprocess.transform(X_raw)
    if hasattr(X_enc, "toarray"):
        X_enc = X_enc.toarray()
    names = list(preprocess.get_feature_names_out())
    return model[-1], pd.DataFrame(X_enc, columns=names, index=X_raw.index)


def run_real(model_path: pathlib.Path, data_path: pathlib.Path, out_dir: pathlib.Path) -> None:
    model = joblib.load(model_path)
    X = pd.read_csv(data_path, encoding="utf-8-sig")
    if not hasattr(model, "feature_names_in_"):
        print("Cảnh báo: model không lưu feature_names_in_ (huấn luyện bằng numpy?). "
              "Dùng FEATURE_COLS mặc định, không kiểm được tên cột lúc huấn luyện.")
    cols = list(getattr(model, "feature_names_in_", FEATURE_COLS))
    missing = [c for c in cols if c not in X.columns]
    if missing:
        raise ValueError(f"File dữ liệu thiếu cột mà model cần: {missing}")
    X = X[cols]
    if len(X) > EXPLAIN_ROWS:
        X = X.sample(EXPLAIN_ROWS, random_state=SEED)

    is_pipeline = isinstance(model, Pipeline)
    model, X = unwrap_pipeline(model, X)
    extra, absent = set(X.columns) - set(FEATURE_COLS), set(FEATURE_COLS) - set(X.columns)
    if extra or absent:
        print(f"Cảnh báo: tên biến lệch feature_dictionary.md | thừa: {sorted(extra)} | thiếu: {sorted(absent)}")
    else:
        print(f"Tên biến khớp feature_dictionary.md: {X.shape[1]}/{len(FEATURE_COLS)} cột")

    class_values, importance = explain_class(model, X, check_names=not is_pipeline)
    unit = shap_unit(model)
    print(f"\n[{type(model).__name__}] TreeExplainer OK | SHAP lớp {TARGET_CLASS}: {class_values.shape} "
          f"| đơn vị: {unit} | top 10 biến:")
    print(importance.head(10).to_string(index=False))
    save_summary_plot(class_values, X, out_dir / f"shap_summary_{model_path.stem}_class{TARGET_CLASS}.png",
                      f"{type(model).__name__} - SHAP lớp {TARGET_CLASS} ({unit})")


def main() -> None:
    here = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Smoke-test SHAP TreeExplainer (CS315 - [D2]).")
    parser.add_argument("--model", type=pathlib.Path, nargs="+",
                        help="Một hoặc nhiều model .joblib của [T3] (model cây hoặc sklearn Pipeline)")
    parser.add_argument("--data", type=pathlib.Path, help="CSV đặc trưng (tên cột gốc) dùng để giải thích")
    parser.add_argument("--out-dir", type=pathlib.Path, default=here / "_smoke_output")
    args = parser.parse_args()

    check_versions()
    if args.model and args.data:
        for model_path in args.model:
            run_real(model_path, args.data, args.out_dir)
    else:
        run_dummy(args.out_dir)
    print(f"\nĐã lưu biểu đồ SHAP vào: {args.out_dir}")


if __name__ == "__main__":
    main()
