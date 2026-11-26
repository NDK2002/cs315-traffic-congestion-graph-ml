"""Smoke test cho 02_feature_selection/01_feature_selection_pipeline.py ([K1], [K2]).

Chạy:  python -m pytest 02_feature_selection/tests -q
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "01_feature_selection_pipeline.py"
_spec = importlib.util.spec_from_file_location("feature_selection_pipeline", MODULE_PATH)
fs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fs)


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    return fs.load_dataset()


def test_load_dataset_attaches_flood_prone_from_nodes(frame):
    nodes = pd.read_csv(fs.NODES_PATH, encoding="utf-8-sig")
    expected = nodes.set_index("node_id")["flood_prone"].astype(bool).astype(int)
    per_node = frame.groupby("node_id")["flood_prone"].agg(["min", "max"])
    assert (per_node["min"] == per_node["max"]).all(), "flood_prone phải là thuộc tính tĩnh của nút"
    pd.testing.assert_series_equal(per_node["min"], expected, check_names=False)
    assert set(fs.ALL_FEATURES) <= set(frame.columns)


def test_missing_node_attribute_gives_hint(frame):
    with pytest.raises(KeyError, match="load_dataset"):
        fs.FeatureSelector().fit(frame.drop(columns="flood_prone"), frame["y_t15"])


def test_selector_normalizes_boolean_and_string_flood_prone(frame):
    base = fs.FeatureSelector().fit(frame[fs.ALL_FEATURES], frame["y_t15"])

    bool_df = frame.copy()
    bool_df["flood_prone"] = bool_df["flood_prone"].astype(bool)
    sel_bool = fs.FeatureSelector().fit(bool_df[fs.ALL_FEATURES], bool_df["y_t15"])
    assert sel_bool.selected_features_ == base.selected_features_
    pd.testing.assert_frame_equal(sel_bool.report_, base.report_)

    str_df = frame.copy()
    str_df["flood_prone"] = str_df["flood_prone"].map({1: "True", 0: "False"})
    sel_str = fs.FeatureSelector().fit(str_df[fs.ALL_FEATURES], str_df["y_t15"])
    assert sel_str.selected_features_ == base.selected_features_
    pd.testing.assert_frame_equal(sel_str.report_, base.report_)


def test_selector_drops_constant_flood_prone_for_metr_la(frame):
    metr_la = frame.copy()
    metr_la["flood_prone"] = 0
    selector = fs.FeatureSelector().fit(metr_la[fs.ALL_FEATURES], metr_la["y_t15"])
    assert "flood_prone_1" not in selector.selected_features_
    score = float(selector.report_.loc[selector.report_["feature"] == "flood_prone_1", "score"].iloc[0])
    assert score == 0.0


def test_selector_keeps_original_names_and_values(frame):
    train = frame.iloc[:2000]
    selector = fs.FeatureSelector().fit(train[fs.ALL_FEATURES], train["y_t15"])
    out = selector.transform(frame[fs.ALL_FEATURES])
    assert list(out.columns) == list(selector.get_feature_names_out())
    numeric = [c for c in out.columns if c in fs.NUMERIC_FEATURES]
    np.testing.assert_allclose(out[numeric].to_numpy(), frame[numeric].to_numpy(dtype=float))


def test_selector_fit_ignores_rows_outside_train(frame):
    """Chống rò rỉ: thay đổi dữ liệu ngoài tập train không làm đổi kết quả fit."""
    train = frame.iloc[:2000]
    a = fs.FeatureSelector().fit(train[fs.ALL_FEATURES], train["y_t15"])
    shuffled = frame.copy()
    shuffled.iloc[2000:, shuffled.columns.get_loc("rain_mm_h")] = 999.0
    b = fs.FeatureSelector().fit(shuffled.iloc[:2000][fs.ALL_FEATURES], shuffled.iloc[:2000]["y_t15"])
    assert a.selected_features_ == b.selected_features_
    pd.testing.assert_frame_equal(a.report_, b.report_)


def test_prune_collinear_never_drops_protected_features():
    rng = np.random.default_rng(0)
    base = rng.normal(size=500)
    numeric = pd.DataFrame({
        "rain_mm_h": base,
        "rain_cum_3h_mm": base * 2 + 1e-6 * rng.normal(size=500),  # cả hai được bảo vệ -> giữ cả hai
        "humidity_pct": -base + 1e-6 * rng.normal(size=500),       # trùng với mưa -> bỏ humidity
        "speed_kmh": rng.normal(size=500),
    })
    importance = pd.Series({"rain_mm_h": 0.0, "rain_cum_3h_mm": 0.0, "humidity_pct": 9.9, "speed_kmh": 0.1})
    dropped = {item["feature"] for item in fs.prune_collinear(numeric, importance)}
    assert dropped == {"humidity_pct"}


def test_prune_collinear_drops_lower_importance_member():
    rng = np.random.default_rng(1)
    base = rng.normal(size=500)
    numeric = pd.DataFrame({"speed_kmh": base, "speed_ratio": base + 1e-3 * rng.normal(size=500)})
    dropped = fs.prune_collinear(numeric, pd.Series({"speed_kmh": 0.2, "speed_ratio": 0.5}))
    assert [(d["feature"], d["kept"]) for d in dropped] == [("speed_kmh", "speed_ratio")]


def test_run_on_dataset_outputs(tmp_path):
    fs.run_on_dataset(fs.DATA_PATH, tmp_path, n_splits=3)
    for name in ["selected_features.json", "feature_importance_ranking.csv", "feature_selection_report.csv",
                 "dimension_summary.csv", "pearson_redundant_pairs.csv"]:
        assert (tmp_path / name).exists(), name

    selected = json.loads((tmp_path / "selected_features.json").read_text(encoding="utf-8"))
    ranking = pd.read_csv(tmp_path / "feature_importance_ranking.csv")
    assert set(selected) == set(fs.TARGET_OFFSETS)
    for target, result in selected.items():
        # Khóa cũ vẫn giữ nguyên để tương thích ngược với Tuần 4-5.
        assert {"selected", "dropped"} <= set(result)
        assert set(result["selected_compact"]) <= set(result["selected"])
        assert not fs.PROTECTED_FEATURES & {item["feature"] for item in result["collinear_dropped"]}
        assert sorted(result["stgnn"]["dynamic"] + result["stgnn"]["static"]) == sorted(result["selected_compact"])
        rows = ranking[ranking["target"] == target]
        assert len(rows) == len(result["selected"]) + len(result["dropped"])
        assert rows["rank_mi"].min() == 1
        assert (rows["mi_mean"] >= 0).all()
