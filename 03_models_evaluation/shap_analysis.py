"""Phân tích SHAP tác động của mưa và triều cường tới dự báo kẹt xe nghiêm trọng (CS315 - Tuần 6, Duy).

Dùng lại đúng cấu hình model của [T3] trong mock_ml_pipeline.py (danh sách đặc trưng, Pipeline One-Hot + classifier).
Với mỗi mốc dự báo y_t15, y_t30, y_t60:
1. Chia theo thời gian: 80% mốc thời gian đầu để huấn luyện, bỏ một khoảng gap bằng số bước dự báo,
   phần còn lại để giải thích (model không nhìn thấy phần này khi học).
2. Tính SHAP bằng TreeExplainer cho lớp 2 (kẹt xe nghiêm trọng).
3. Xuất Summary Plot, bảng mức ảnh hưởng theo từng biến và theo nhóm biến, Dependence Plot của
   rain_mm_h và tide_level_m, Force Plot tại một số nút giao trong cơn mưa lớn giả lập.

Chạy:
    python 03_models_evaluation/shap_analysis.py
    python 03_models_evaluation/shap_analysis.py --model RandomForest --nodes 1 4 13
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from mock_ml_pipeline import (  # noqa: E402
    CATEGORICAL_FEATURES,
    DATA_PATH,
    NUMERIC_FEATURES,
    TARGET_OFFSETS,
    _make_models,
    _make_pipeline,
)
from shap_smoke_test import unwrap_pipeline  # noqa: E402

OUTPUT_DIR = HERE / "results" / "shap"
TARGET_CLASS = 2
TRAIN_SHARE = 0.8
SEED = 31514
DEFAULT_NODES = (1, 4, 13)

# Nhóm biến để trả lời câu hỏi "mưa, triều đóng góp bao nhiêu so với các yếu tố khác"
FEATURE_GROUPS = {
    "Mưa": ["rain_mm_h", "rain_cum_3h_mm", "rain_level"],
    "Triều cường": ["tide_level_m", "tide_alert"],
    "Thời tiết khác": ["temperature_c", "humidity_pct"],
    "Giao thông hiện tại & quá khứ": ["speed_kmh", "volume_veh", "speed_ratio", "speed_lag1", "speed_lag2",
                                      "speed_lag4", "speed_delta1"],
    "Lan truyền từ nút nguồn": ["upstream_speed_min", "upstream_congested_cnt"],
    "Thời gian": ["hour_sin", "hour_cos", "time_slot", "is_weekend_1"],
    "Thuộc tính tĩnh của nút": ["free_flow_kmh", "lanes_in_mean", "maxspeed_in_kmh", "in_degree", "out_degree",
                                "dist_center_m", "road_type_primary", "road_type_secondary", "road_type_tertiary",
                                "road_type_trunk", "has_twoway_1"],
}


def split_by_time(frame: pd.DataFrame, horizon_steps: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """80% mốc thời gian đầu để train, bỏ gap = số bước dự báo để nhãn train không chạm vào phần giải thích."""
    times = np.array(sorted(frame["timestamp"].unique()))
    cut = int(len(times) * TRAIN_SHARE)
    train_times = times[:cut]
    explain_times = times[cut + horizon_steps:]
    return frame[frame["timestamp"].isin(train_times)], frame[frame["timestamp"].isin(explain_times)]


def class_shap(classifier, X_enc: pd.DataFrame) -> tuple[np.ndarray, float]:
    """SHAP của lớp 2 và giá trị nền (expected value) tương ứng."""
    explainer = shap.TreeExplainer(classifier)
    values = explainer.shap_values(X_enc)
    if isinstance(values, list):
        values = np.stack(values, axis=-1)
    idx = list(classifier.classes_).index(TARGET_CLASS)
    base = np.atleast_1d(explainer.expected_value)[idx]
    return values[:, :, idx], float(base)


def group_table(values: np.ndarray, columns: list[str]) -> pd.DataFrame:
    """Cộng SHAP của các biến trong cùng nhóm cho từng dòng, rồi lấy trung bình trị tuyệt đối."""
    shap_df = pd.DataFrame(values, columns=columns)
    grouped = {name: shap_df[[c for c in cols if c in columns]].sum(axis=1) for name, cols in FEATURE_GROUPS.items()}
    missing = set(columns) - {c for cols in FEATURE_GROUPS.values() for c in cols}
    if missing:
        raise ValueError(f"Biến chưa được xếp nhóm: {sorted(missing)}")
    table = pd.DataFrame({
        "group": list(grouped),
        "mean_abs_shap": [s.abs().mean() for s in grouped.values()],
    })
    table["share_pct"] = (100 * table["mean_abs_shap"] / table["mean_abs_shap"].sum()).round(1)
    return table.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)


def storm_vs_dry(values: np.ndarray, columns: list[str], storm_mask: np.ndarray) -> pd.DataFrame:
    """Đóng góp trung bình (có dấu) của từng nhóm khi đang mưa lớn giả lập so với lúc không mưa lớn."""
    shap_df = pd.DataFrame(values, columns=columns)
    rows = []
    for name, cols in FEATURE_GROUPS.items():
        s = shap_df[[c for c in cols if c in columns]].sum(axis=1)
        rows.append({"group": name,
                     "mean_shap_storm": s[storm_mask].mean(),
                     "mean_shap_no_storm": s[~storm_mask].mean()})
    return pd.DataFrame(rows).sort_values("mean_shap_storm", ascending=False).reset_index(drop=True)


def save_summary(values, X_enc, path, title) -> None:
    shap.summary_plot(values, X_enc, show=False, max_display=15)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close("all")


def save_dependence(values, X_enc, path, title) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, feature in zip(axes, ("rain_mm_h", "tide_level_m")):
        shap.dependence_plot(feature, values, X_enc, interaction_index=None, ax=ax, show=False)
        ax.axhline(0, color="gray", linewidth=0.8)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close("all")


def save_force(base, row_values, row_features, path, title) -> None:
    shap.force_plot(base, row_values, row_features.round(2), matplotlib=True, show=False,
                    text_rotation=15, figsize=(16, 3.2))
    plt.gcf().text(0.01, -0.08, title, fontsize=11)
    plt.savefig(path, dpi=110, bbox_inches="tight")
    plt.close("all")


def pick_storm_timestamp(explain: pd.DataFrame, predicted: np.ndarray) -> pd.Timestamp:
    """Chọn mốc trong mưa lớn giả lập có nhiều nút bị dự báo kẹt nặng nhất."""
    storm = explain.assign(pred_class_2=(predicted == TARGET_CLASS)).query("rain_scenario_synthetic == 1")
    if storm.empty:
        raise ValueError("Phần dữ liệu giải thích không có mốc mưa lớn giả lập")
    return storm.groupby("timestamp")["pred_class_2"].sum().idxmax()


def run(model_name: str, nodes: list[int], data_path: pathlib.Path, out_dir: pathlib.Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(data_path, parse_dates=["timestamp"])
    models = _make_models(SEED)
    if model_name not in models:
        raise ValueError(f"Model {model_name} không có. Chọn một trong: {list(models)}")
    tag = model_name.lower()
    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    importance_rows, group_rows, storm_rows = [], [], []

    print(f"shap={shap.__version__} | model={model_name} | dữ liệu={data_path.name} ({len(frame)} dòng)")
    for target, steps in TARGET_OFFSETS.items():
        train, explain = split_by_time(frame, steps)
        pipe = _make_pipeline(models[model_name].__class__(**models[model_name].get_params()))
        pipe.fit(train[feature_cols], train[target])
        classifier, X_enc = unwrap_pipeline(pipe, explain[feature_cols])
        values, base = class_shap(classifier, X_enc)
        columns = list(X_enc.columns)
        storm_mask = explain["rain_scenario_synthetic"].to_numpy() == 1
        predicted = pipe.predict(explain[feature_cols])

        imp = pd.DataFrame({"feature": columns, "mean_abs_shap": np.abs(values).mean(axis=0)})
        imp["group"] = imp["feature"].map({c: g for g, cols in FEATURE_GROUPS.items() for c in cols})
        importance_rows.append(imp.assign(target=target))
        groups = group_table(values, columns)
        group_rows.append(groups.assign(target=target))
        storm_rows.append(storm_vs_dry(values, columns, storm_mask).assign(target=target))

        horizon = f"t+{15 * steps}'"
        save_summary(values, X_enc, out_dir / f"summary_{tag}_{target}.png",
                     f"{model_name} — SHAP lớp 2 (kẹt nặng), dự báo {horizon}")
        save_dependence(values, X_enc, out_dir / f"dependence_rain_tide_{tag}_{target}.png",
                        f"{model_name} — ảnh hưởng của mưa và triều tới lớp 2, dự báo {horizon}")

        storm_time = pick_storm_timestamp(explain, predicted)
        for node in nodes:
            pos = np.flatnonzero((explain["timestamp"] == storm_time).to_numpy()
                                 & (explain["node_id"] == node).to_numpy())
            if len(pos) == 0:
                print(f"  bỏ qua force plot nút {node}: không có dòng tại {storm_time}")
                continue
            i = int(pos[0])
            save_force(base, values[i], X_enc.iloc[i], out_dir / f"force_{tag}_{target}_node{node:02d}.png",
                       f"HX_{node:02d} lúc {storm_time:%d/%m %H:%M} (mưa lớn giả lập) — "
                       f"dự báo {horizon}: lớp {predicted[i]}, thực tế: lớp {explain[target].iloc[i]}")

        print(f"\n[{target}] train {train['timestamp'].nunique()} mốc | giải thích {explain['timestamp'].nunique()} mốc "
              f"({len(explain)} dòng, {int(storm_mask.sum())} dòng mưa lớn) | force plot tại {storm_time}")
        print(groups.to_string(index=False))

    pd.concat(importance_rows).sort_values(["target", "mean_abs_shap"], ascending=[True, False]).to_csv(
        out_dir / f"feature_importance_{tag}.csv", index=False, float_format="%.6f")
    pd.concat(group_rows).to_csv(out_dir / f"group_importance_{tag}.csv", index=False, float_format="%.6f")
    pd.concat(storm_rows).to_csv(out_dir / f"group_storm_vs_no_storm_{tag}.csv", index=False, float_format="%.6f")
    print(f"\nĐã lưu kết quả vào: {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phân tích SHAP mưa/triều cường (CS315 - Tuần 6).")
    parser.add_argument("--model", default="LightGBM", choices=["LightGBM", "RandomForest"])
    parser.add_argument("--nodes", type=int, nargs="+", default=list(DEFAULT_NODES),
                        help="node_id cần vẽ Force Plot")
    parser.add_argument("--data", type=pathlib.Path, default=DATA_PATH)
    parser.add_argument("--out-dir", type=pathlib.Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    run(args.model, args.nodes, args.data, args.out_dir)


if __name__ == "__main__":
    main()
