"""Smoke & unit tests cho Traffic KG va Dynamic Dijkstra routing ([S1] Tuan 6).

Chay: python -m pytest 04_knowledge_graph_demo/tests -q
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import networkx as nx
import pytest

KG_DIR = Path(__file__).resolve().parents[1]
if str(KG_DIR) not in sys.path:
    sys.path.insert(0, str(KG_DIR))

import dynamic_routing as dr  # noqa: E402
import traffic_kg_schema as tks  # noqa: E402


def test_kg_flood_prone_matches_h1_csv_single_source_of_truth():
    kg = tks.build_hang_xanh_kg()
    data_dir = tks.DEFAULT_DATA_DIR

    with (data_dir / "nodes.csv").open("r", encoding="utf-8-sig") as f:
        csv_flood_nodes = {
            r["node_code"].strip()
            for r in csv.DictReader(f)
            if r["flood_prone"].strip().lower() == "true"
        }
    with (data_dir / "edges.csv").open("r", encoding="utf-8-sig") as f:
        csv_flood_edges = {
            r["edge_id"].strip()
            for r in csv.DictReader(f)
            if r["flood_prone"].strip().lower() == "true"
        }

    kg_prone_nodes = {
        u for u, _, d in kg.edges(data=True) if d.get("rel_type") == "PRONE_TO_FLOOD"
    }
    kg_attr_flood_nodes = {
        n
        for n, d in kg.nodes(data=True)
        if d.get("node_type") == "Intersection" and d.get("flood_prone")
    }
    kg_flood_edges = {
        d["edge_id"]
        for _, _, d in kg.edges(data=True)
        if d.get("rel_type") == "CONNECTS_TO" and d.get("flood_prone")
    }

    assert kg_prone_nodes == csv_flood_nodes == {"HX_03", "HX_04", "HX_11", "HX_14", "HX_15", "HX_18"}
    assert kg_attr_flood_nodes == csv_flood_nodes
    assert kg_flood_edges == csv_flood_edges
    assert "HX_01" not in kg_prone_nodes


def test_clear_weather_matches_baseline_shortest_path():
    res = dr.find_optimal_route("HX_05", "HX_04", {"rain_mm_h": 0.0, "tide_level_m": 1.10})
    assert res["optimal_route"]["nodes"] == res["baseline_shortest_route"]["nodes"]
    assert res["avoided_flood_zones"] == []
    assert res["avoided_congested_nodes"] == []
    assert json.dumps(res, ensure_ascii=False)


def test_heavy_rain_only_reroutes_around_flooded_dinh_bo_linh():
    """Chi co mua lon + trieu cuong (khong truyen congestion) van phai ne doan ngap E_13."""
    for start, end in [("HX_04", "HX_03"), ("HX_06", "HX_16"), ("HX_13", "HX_16")]:
        res = dr.find_optimal_route(start, end, {"rain_mm_h": 42.0, "tide_level_m": 1.55})
        base_edges = {seg["edge_id"] for seg in res["baseline_shortest_route"]["segments"]}
        opt_edges = {seg["edge_id"] for seg in res["optimal_route"]["segments"]}
        assert "E_13" in base_edges
        assert "E_13" not in opt_edges
        assert any("E_13" in item for item in res["avoided_flood_zones"])
        assert "HX_01" in res["optimal_route"]["nodes"]
        assert "né được vùng ngập" in res["reason"]


def test_storm_and_congestion_reroutes_via_overpass():
    res = dr.find_optimal_route(
        start="HX_03",
        end="HX_15",
        weather_cond={
            "rain_mm_h": 42.0,
            "tide_level_m": 1.55,
            "congestion_prob": {"HX_01": 0.95, "HX_11": 0.90, "HX_02": 0.15},
        },
    )
    assert res["baseline_shortest_route"]["nodes"][:3] == ["HX_03", "HX_01", "HX_02"]
    assert res["optimal_route"]["nodes"][:2] == ["HX_03", "HX_02"]
    assert any("HX_01" in item for item in res["avoided_congested_nodes"])
    # HX_01 khong phai diem ngap theo [H1]
    assert not any("HX_01" in item for item in res["avoided_flood_zones"])


def test_hotspot_threshold_consistency_for_ung_van_khiem():
    # Ung Van Khiem (HX_15) co nguong rain > 35 mm/h hoac (rain > 15 & tide >= 1.55 m)
    res_below = dr.find_optimal_route("HX_02", "HX_15", {"rain_mm_h": 32.0, "tide_level_m": 1.52})
    assert all("Ung Văn Khiêm" not in hs for hs in res_below["weather"]["active_flood_hotspots"])
    assert res_below["optimal_route"]["flood_points"] == []

    res_above = dr.find_optimal_route("HX_02", "HX_15", {"rain_mm_h": 36.0, "tide_level_m": 1.55})
    assert any("Ung Văn Khiêm" in hs for hs in res_above["weather"]["active_flood_hotspots"])
    assert any("HX_15" in fp for fp in res_above["optimal_route"]["flood_points"])


def test_is_flood_prone_flag_is_static_across_weather():
    kg = tks.build_hang_xanh_kg()
    prone_sets = []
    for rain in (0.0, 20.0, 42.0):
        tks.update_environment_state(kg, rain_mm_h=rain, tide_level_m=1.2)
        R = dr._build_dynamic_routing_graph(kg, {}, rain, 1.2, alpha=4.0, beta=3.5)
        prone_sets.append({n for n, d in R.nodes(data=True) if d["is_flood_prone"]})
    assert prone_sets[0] == prone_sets[1] == prone_sets[2] == {"HX_03", "HX_04", "HX_11", "HX_14", "HX_15", "HX_18"}


def test_congestion_inputs_accept_code_int_and_str_id_symmetrically():
    kg = tks.build_hang_xanh_kg()
    for key in ("HX_01", 1, "1"):
        probs_p, lvls_p = dr._resolve_congestion_probs(kg, {"congestion_prob": {key: 0.85}})
        assert probs_p["HX_01"] == pytest.approx(0.85)
        assert lvls_p["HX_01"] == 2

        probs_l, lvls_l = dr._resolve_congestion_probs(kg, {"congestion_by_node": {key: 2}})
        assert probs_l["HX_01"] == pytest.approx(dr.CONGESTION_LEVEL_TO_PROB[2])
        assert lvls_l["HX_01"] == 2


def test_edge_cases_and_no_mutation_of_caller_graph():
    kg = tks.build_hang_xanh_kg()
    orig_rain = kg.nodes["WEATHER_CURRENT"]["rain_mm_h"]
    orig_hx01_lvl = kg.nodes["HX_01"]["congestion_level"]

    res_same = dr.find_optimal_route(1, "HX_01", {"rain_mm_h": 40.0, "congestion_by_node": {"1": 2}}, G=kg)
    assert res_same["optimal_route"]["nodes"] == ["HX_01"]
    assert res_same["optimal_route"]["total_length_m"] == 0.0
    # Do thi caller truyen vao khong bi thay doi trang thai
    assert kg.nodes["WEATHER_CURRENT"]["rain_mm_h"] == orig_rain
    assert kg.nodes["HX_01"]["congestion_level"] == orig_hx01_lvl

    with pytest.raises(ValueError):
        dr.find_optimal_route("HX_99", "HX_01")

    with pytest.raises(nx.NetworkXNoPath):
        dr.find_optimal_route("HX_01", "HX_14")
