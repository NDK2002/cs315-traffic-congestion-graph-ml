"""Evaluate balanced tree baselines with timestamp-grouped walk-forward CV."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, average_precision_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT.parent / "01_data_sample" / "mock_hang_xanh_traffic_weather.csv"
OUTPUT_DIR = ROOT / "results"
NUMERIC_FEATURES = [
    "speed_kmh", "volume_veh", "speed_ratio", "speed_lag1", "speed_lag2", "speed_lag4",
    "speed_delta1", "upstream_speed_min", "upstream_congested_cnt", "rain_mm_h",
    "rain_cum_3h_mm", "temperature_c", "humidity_pct", "tide_level_m", "hour_sin", "hour_cos",
    "time_slot", "rain_level", "tide_alert", "free_flow_kmh", "lanes_in_mean",
    "maxspeed_in_kmh", "in_degree", "out_degree", "dist_center_m",
]
CATEGORICAL_FEATURES = ["road_type", "is_weekend", "has_twoway"]
TARGETS = ("y_t15", "y_t30", "y_t60")
TARGET_OFFSETS = {"y_t15": 1, "y_t30": 2, "y_t60": 4}
CLASS_LABELS = np.array([0, 1, 2])


def _make_models(seed: int) -> dict[str, object]:
    models: dict[str, object] = {
        "RandomForest": RandomForestClassifier(
            n_estimators=200,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=seed,
            n_jobs=-1,
        )
    }
    try:
        from lightgbm import LGBMClassifier

        models["LightGBM"] = LGBMClassifier(
            n_estimators=200,
            learning_rate=0.05,
            num_leaves=15,
            class_weight="balanced",
            random_state=seed,
            verbosity=-1,
            n_jobs=-1,
        )
    except ImportError:
        warnings.warn("LightGBM is not installed; only RandomForest will run.", stacklevel=2)
    return models


def _make_pipeline(classifier: object) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("numeric", "passthrough", NUMERIC_FEATURES),
            (
                "categorical",
                OneHotEncoder(
                    categories=[["primary", "secondary", "tertiary", "trunk"], [0, 1], [0, 1]],
                    handle_unknown="ignore",
                    drop="if_binary",
                ),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    return Pipeline([("preprocess", preprocess), ("classifier", classifier)])


def _average_precision_for_class_2(model: Pipeline, x: pd.DataFrame, y_true: np.ndarray) -> float:
    probabilities = model.predict_proba(x)
    classes = model.named_steps["classifier"].classes_
    if 2 not in classes or not np.any(y_true == 2):
        return float("nan")
    class_2_column = int(np.flatnonzero(classes == 2)[0])
    return float(average_precision_score(y_true == 2, probabilities[:, class_2_column]))


def run_pipeline(
    data_path: Path = DATA_PATH,
    output_dir: Path = OUTPUT_DIR,
    n_splits: int = 5,
    seed: int = 31514,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = pd.read_csv(data_path, parse_dates=["timestamp"])
    required = {"timestamp", "node_id", *NUMERIC_FEATURES, *CATEGORICAL_FEATURES, *TARGETS}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    if frame[list(required - {"timestamp", "node_id"})].isna().any().any():
        raise ValueError("Feature/target columns contain missing values")

    timestamps = np.array(sorted(frame["timestamp"].unique()))
    if len(timestamps) <= n_splits:
        raise ValueError(f"Need more unique timestamps ({len(timestamps)}) than CV folds ({n_splits})")
    timestamp_deltas = pd.Series(pd.to_datetime(timestamps)).diff().dropna()
    if not timestamp_deltas.eq(pd.Timedelta(minutes=15)).all():
        raise ValueError("TimeSeriesSplit requires a complete, equally spaced 15-minute timestamp grid")
    models = _make_models(seed)
    records: list[dict[str, object]] = []
    confusion = {f"{model_name}:{target}": np.zeros((3, 3), dtype=int) for model_name in models for target in TARGETS}

    for target, horizon_steps in TARGET_OFFSETS.items():
        # The labels describe outcomes 1, 2, or 4 time steps ahead. Purge the
        # corresponding number of unique timestamps so no training label uses
        # a traffic state from the validation period.
        splitter = TimeSeriesSplit(n_splits=n_splits, gap=horizon_steps)
        for fold, (train_time_index, valid_time_index) in enumerate(splitter.split(timestamps), start=1):
            train_times, valid_times = timestamps[train_time_index], timestamps[valid_time_index]
            train = frame.loc[frame["timestamp"].isin(train_times)]
            valid = frame.loc[frame["timestamp"].isin(valid_times)]
            if set(train["timestamp"]).intersection(set(valid["timestamp"])):
                raise RuntimeError("A timestamp leaked across the train/validation boundary")
            last_train_label_time = pd.Timestamp(train_times[-1]) + pd.Timedelta(minutes=15 * horizon_steps)
            if last_train_label_time >= pd.Timestamp(valid_times[0]):
                raise RuntimeError(f"{target} training labels overlap the validation period")
            x_train = train[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
            x_valid = valid[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
            y_train, y_valid = train[target].to_numpy(), valid[target].to_numpy()
            for model_name, classifier in models.items():
                estimator = _make_pipeline(classifier.__class__(**classifier.get_params()))
                estimator.fit(x_train, y_train)
                prediction = estimator.predict(x_valid)
                matrix = confusion_matrix(y_valid, prediction, labels=CLASS_LABELS)
                confusion[f"{model_name}:{target}"] += matrix
                records.append({
                    "model": model_name,
                    "target": target,
                    "fold": fold,
                    "train_timestamps": len(train_times),
                    "valid_timestamps": len(valid_times),
                    "purged_timestamps": horizon_steps,
                    "train_start": str(pd.Timestamp(train_times[0])),
                    "train_end": str(pd.Timestamp(train_times[-1])),
                    "valid_start": str(pd.Timestamp(valid_times[0])),
                    "valid_end": str(pd.Timestamp(valid_times[-1])),
                    "class_2_recall": recall_score(y_valid, prediction, labels=CLASS_LABELS, average=None, zero_division=0)[2],
                    "class_2_precision": precision_score(y_valid, prediction, labels=CLASS_LABELS, average=None, zero_division=0)[2],
                    "class_2_f1": f1_score(y_valid, prediction, labels=CLASS_LABELS, average=None, zero_division=0)[2],
                    "macro_f1": f1_score(y_valid, prediction, labels=CLASS_LABELS, average="macro", zero_division=0),
                    "class_2_pr_auc": _average_precision_for_class_2(estimator, x_valid, y_valid),
                    "accuracy": accuracy_score(y_valid, prediction),
                })

    fold_metrics = pd.DataFrame(records)
    summary = (
        fold_metrics.groupby(["model", "target"], as_index=False)
        .agg(
            folds=("fold", "count"),
            class_2_recall_mean=("class_2_recall", "mean"),
            class_2_recall_std=("class_2_recall", "std"),
            class_2_precision_mean=("class_2_precision", "mean"),
            class_2_precision_std=("class_2_precision", "std"),
            class_2_f1_mean=("class_2_f1", "mean"),
            class_2_f1_std=("class_2_f1", "std"),
            macro_f1_mean=("macro_f1", "mean"),
            macro_f1_std=("macro_f1", "std"),
            class_2_pr_auc_mean=("class_2_pr_auc", "mean"),
            class_2_pr_auc_std=("class_2_pr_auc", "std"),
            accuracy_mean=("accuracy", "mean"),
        )
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    fold_metrics.to_csv(output_dir / "mock_cv_fold_metrics.csv", index=False, float_format="%.6f")
    summary.to_csv(output_dir / "mock_cv_summary.csv", index=False, float_format="%.6f")
    with (output_dir / "mock_cv_confusion_matrices.json").open("w", encoding="utf-8") as file:
        json.dump({key: matrix.tolist() for key, matrix in confusion.items()}, file, indent=2)

    # Keep one final-fit t+15 model per family for the separate SHAP smoke-check.
    # Cross-validation metrics above remain the evaluation estimate.
    x_all = frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    for model_name, classifier in models.items():
        final_model = _make_pipeline(classifier.__class__(**classifier.get_params()))
        final_model.fit(x_all, frame["y_t15"].to_numpy())
        prefix = model_name.lower().replace(" ", "_")
        joblib.dump(final_model, output_dir / f"{prefix}_y_t15_mock.joblib")
        names = final_model.named_steps["preprocess"].get_feature_names_out().tolist()
        with (output_dir / f"{prefix}_y_t15_feature_names.json").open("w", encoding="utf-8") as file:
            json.dump(names, file, indent=2, ensure_ascii=False)

    return fold_metrics, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--seed", type=int, default=31514)
    args = parser.parse_args()
    folds, summary = run_pipeline(args.data, args.output_dir, args.splits, args.seed)
    print(f"Saved {len(folds)} fold/target/model metric rows to {args.output_dir}")
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.3f}"))


if __name__ == "__main__":
    main()
