"""
Dynamic Dijkstra Routing Engine on Traffic Knowledge Graph (CS315 - Nhom 14)
Phu trach: Hoang Cao Son (25730061) - Lead WBS-03 ([S1] Tuan 6)

Thuat toan Dynamic Dijkstra tinh trong so canh dong theo cong thuc:
    w(u, v) = length_m * (1 + alpha * P(congestion_v) + beta * flood_factor(u, v))

Ho tro:
- Doc truc tiep thuoc tinh `flood_prone` tu nodes.csv / edges.csv ([H1]) va
  trang thai FloodHotspot trong Traffic KG (`traffic_kg_schema.py`).
- Nhan xac suat ket xe P(y=2) tu mo hinh ML/ST-GNN hoac nhan 0/1/2.
- Tra ve danh sach nut lo trinh toi uu, so sanh voi duong ngan nhat tinh,
  danh sach diem ngap/ket da ne va ly do khuyen nghi (JSON-serializable cho AI Agent [S2]).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import networkx as nx

try:
    from .traffic_kg_schema import (
        DEFAULT_DATA_DIR,
        _is_node_flooded,
        build_hang_xanh_kg,
        update_environment_state,
    )
except ImportError:
    from traffic_kg_schema import (
        DEFAULT_DATA_DIR,
        _is_node_flooded,
        build_hang_xanh_kg,
        update_environment_state,
    )

CONGESTION_LEVEL_TO_PROB = {
    0: 0.05,
    1: 0.45,
    2: 0.90,
}


def _load_csv_flood_flags(
    nodes_csv: Path | str | None = None,
    edges_csv: Path | str | None = None,
) -> tuple[dict[str, bool], dict[str, bool]]:
    """Doc co flood_prone tu nodes.csv va edges.csv cua [H1]."""
    nodes_path = Path(nodes_csv) if nodes_csv else DEFAULT_DATA_DIR / "nodes.csv"
    edges_path = Path(edges_csv) if edges_csv else DEFAULT_DATA_DIR / "edges.csv"

    node_flood: dict[str, bool] = {}
    with nodes_path.open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = row["node_code"].strip()
            node_flood[code] = str(row.get("flood_prone", "False")).strip().lower() == "true"

    edge_flood: dict[str, bool] = {}
    with edges_path.open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            eid = row["edge_id"].strip()
            edge_flood[eid] = str(row.get("flood_prone", "False")).strip().lower() == "true"

    return node_flood, edge_flood


def _normalize_node(G: nx.MultiDiGraph, node_ref: str | int) -> str:
    """Chuan hoa node_id (int/str) hoac node_code ('HX_01') thanh node_code."""
    if isinstance(node_ref, str) and node_ref in G and G.nodes[node_ref].get("node_type") == "Intersection":
        return node_ref
    ref_str = str(node_ref).strip()
    if ref_str in G and G.nodes[ref_str].get("node_type") == "Intersection":
        return ref_str
    try:
        target_id = int(ref_str)
        for code, attrs in G.nodes(data=True):
            if attrs.get("node_type") == "Intersection" and attrs.get("node_id") == target_id:
                return code
    except ValueError:
        pass
    raise ValueError(f"Không tìm thấy nút giao hợp lệ: {node_ref}")


def _resolve_congestion_probs(
    G: nx.MultiDiGraph,
    weather_cond: dict[str, Any],
) -> tuple[dict[str, float], dict[str, int]]:
    """Chuyen doi input xac suat ket xe (hoac nhan 0/1/2) ve map theo node_code."""
    prob_input = weather_cond.get("congestion_prob") or {}
    level_input = weather_cond.get("congestion_by_node") or {}

    probs: dict[str, float] = {}
    levels: dict[str, int] = {}

    for node_code, attrs in G.nodes(data=True):
        if attrs.get("node_type") != "Intersection":
            continue
        node_id = attrs["node_id"]

        if node_code in prob_input:
            p = float(prob_input[node_code])
        elif node_id in prob_input:
            p = float(prob_input[node_id])
        elif str(node_id) in prob_input:
            p = float(prob_input[str(node_id)])
        elif node_code in level_input:
            lvl = int(level_input[node_code])
            p = CONGESTION_LEVEL_TO_PROB.get(lvl, 0.05)
        elif node_id in level_input:
            lvl = int(level_input[node_id])
            p = CONGESTION_LEVEL_TO_PROB.get(lvl, 0.05)
        else:
            p = 0.0

        p = max(0.0, min(1.0, p))
        probs[node_code] = p

        if node_code in level_input:
            levels[node_code] = int(level_input[node_code])
        elif node_id in level_input:
            levels[node_code] = int(level_input[node_id])
        elif p >= 0.65:
            levels[node_code] = 2
        elif p >= 0.30:
            levels[node_code] = 1
        else:
            levels[node_code] = 0

    return probs, levels


def _build_dynamic_routing_graph(
    G: nx.MultiDiGraph,
    node_flood_flags: dict[str, bool],
    edge_flood_flags: dict[str, bool],
    congestion_probs: dict[str, float],
    rain_mm_h: float,
    tide_level_m: float,
    alpha: float,
    beta: float,
) -> nx.DiGraph:
    """Tao DiGraph voi trong so canh dong w = length * (1 + alpha*P(ket) + beta*flood)."""
    R = nx.DiGraph()
    is_flood_weather = rain_mm_h > 30.0 or (rain_mm_h > 15.0 and tide_level_m >= 1.50)
    is_critical_flood = rain_mm_h > 30.0 and tide_level_m >= 1.50

    for node_code, attrs in G.nodes(data=True):
        if attrs.get("node_type") != "Intersection":
            continue
        kg_floods = _is_node_flooded(G, node_code)
        csv_flood = node_flood_flags.get(node_code, False) and is_flood_weather
        R.add_node(
            node_code,
            **attrs,
            is_flood_prone=node_flood_flags.get(node_code, False) or bool(kg_floods),
            is_flood_active=bool(kg_floods) or csv_flood,
            flood_hotspot_names=kg_floods,
            p_congestion=congestion_probs.get(node_code, 0.0),
        )

    for u, v, data in G.edges(data=True):
        if data.get("rel_type") != "CONNECTS_TO":
            continue

        edge_id = data["edge_id"]
        length_m = float(data["length_m"])
        p_ket = congestion_probs.get(v, 0.0)

        edge_is_flood_prone = (
            edge_flood_flags.get(edge_id, False)
            or R.nodes[u]["is_flood_prone"]
            or R.nodes[v]["is_flood_prone"]
        )
        edge_is_flood_active = (
            (edge_flood_flags.get(edge_id, False) and is_flood_weather)
            or R.nodes[u]["is_flood_active"]
            or R.nodes[v]["is_flood_active"]
        )

        if edge_is_flood_active:
            flood_indicator = 1.5 if is_critical_flood else 1.0
        elif edge_is_flood_prone and rain_mm_h > 15.0:
            flood_indicator = 0.25
        else:
            flood_indicator = 0.0

        dynamic_weight = length_m * (1.0 + alpha * p_ket + beta * flood_indicator)

        edge_payload = {
            **data,
            "p_congestion": round(p_ket, 4),
            "is_flood_prone": edge_is_flood_prone,
            "is_flood_active": edge_is_flood_active,
            "flood_indicator": flood_indicator,
            "dynamic_weight": round(dynamic_weight, 2),
        }

        if not R.has_edge(u, v) or dynamic_weight < R[u][v]["dynamic_weight"]:
            R.add_edge(u, v, **edge_payload)

    return R


def _summarize_path(R: nx.DiGraph, path: list[str]) -> dict[str, Any]:
    """Tong hop chi tiet lo trinh: chang, do dai, trong so dong, diem ngap va ket."""
    segments: list[dict[str, Any]] = []
    total_length_m = 0.0
    total_weight = 0.0
    total_base_time_s = 0.0
    flood_points: list[str] = []
    flood_hotspot_names: set[str] = set()
    congested_nodes: list[dict[str, Any]] = []

    for node in path:
        n_attrs = R.nodes[node]
        if n_attrs.get("is_flood_active"):
            road_label = n_attrs["roads"].split("|")[0].strip()
            flood_points.append(f"{node} ({road_label})")
            for hs_name in n_attrs.get("flood_hotspot_names", []):
                flood_hotspot_names.add(hs_name)
        if n_attrs.get("congestion_level", 0) >= 2 or n_attrs.get("p_congestion", 0.0) >= 0.65:
            road_label = n_attrs["roads"].split("|")[0].strip()
            congested_nodes.append(
                {
                    "node_code": node,
                    "road": road_label,
                    "p_congestion": round(n_attrs.get("p_congestion", 0.0), 3),
                }
            )

    for u, v in zip(path[:-1], path[1:]):
        e = R[u][v]
        total_length_m += e["length_m"]
        total_weight += e["dynamic_weight"]
        total_base_time_s += e["base_time_s"]
        segments.append(
            {
                "edge_id": e["edge_id"],
                "from": u,
                "to": v,
                "road_name": e["road_name"],
                "length_m": round(e["length_m"], 1),
                "dynamic_weight": round(e["dynamic_weight"], 1),
                "p_congestion": e["p_congestion"],
                "is_flood_active": e["is_flood_active"],
            }
        )

    return {
        "nodes": path,
        "segments": segments,
        "total_length_m": round(total_length_m, 1),
        "total_dynamic_weight": round(total_weight, 1),
        "base_time_s": round(total_base_time_s, 1),
        "flood_points": flood_points,
        "flood_hotspots": sorted(flood_hotspot_names),
        "congested_nodes": congested_nodes,
    }


def _build_reason(
    optimal: dict[str, Any],
    baseline: dict[str, Any],
    avoided_floods: list[str],
    avoided_congestion: list[str],
    rain_mm_h: float,
    tide_level_m: float,
) -> str:
    """Sinh cau giai thich tu nhien bang tieng Viet cho AI Agent va nguoi dung."""
    if optimal["nodes"] == baseline["nodes"]:
        if not optimal["flood_points"] and not optimal["congested_nodes"]:
            return (
                f"Thời tiết ổn định (mưa {rain_mm_h:.1f} mm/h, triều {tide_level_m:.2f} m). "
                "Lộ trình tối ưu trùng với đường ngắn nhất tĩnh và không gặp điểm ngập/kẹt."
            )
        return (
            f"Với mưa {rain_mm_h:.1f} mm/h và triều {tide_level_m:.2f} m, đây vẫn là lộ trình "
            "có tổng chi phí động thấp nhất dù đi qua khu vực có cảnh báo."
        )

    header = (
        f"Trong điều kiện mưa {rain_mm_h:.1f} mm/h, triều {tide_level_m:.2f} m, "
        "hệ thống chuyển hướng khỏi lộ trình ngắn nhất tĩnh để tối ưu thông thoáng"
    )
    details: list[str] = []
    if avoided_floods:
        details.append(f"né được điểm ngập {', '.join(avoided_floods)}")
    if avoided_congestion:
        details.append(f"tránh nút kẹt nặng {', '.join(avoided_congestion)}")

    extra_m = round(optimal["total_length_m"] - baseline["total_length_m"], 1)
    if extra_m > 0:
        details.append(f"dài hơn đường ngắn nhất {extra_m} m nhưng giảm mạnh rủi ro ùn tắc/ngập")

    if details:
        return f"{header}: {'; '.join(details)}."
    return f"{header}."


def find_optimal_route(
    start: str | int,
    end: str | int,
    weather_cond: dict[str, Any] | None = None,
    alpha: float = 4.0,
    beta: float = 3.5,
    top_k: int = 2,
    G: nx.MultiDiGraph | None = None,
) -> dict[str, Any]:
    """Tim lo trinh toi uu bang Dynamic Dijkstra tren Traffic KG 24 nut.

    Args:
        start: Ma nut xuat phat (vd 'HX_02' hoac 2).
        end: Ma nut dich (vd 'HX_15' hoac 15).
        weather_cond: Dict dieu kien moi truong, gom:
            - rain_mm_h (float): luong mua hien tai/du bao (mm/h)
            - tide_level_m (float): muc nuoc trieu Phu An (m)
            - congestion_prob (dict, optional): map node -> P(ket) trong [0, 1]
            - congestion_by_node (dict, optional): map node -> nhan 0/1/2
            - timestamp (str, optional)
        alpha: He so phat xac suat ket xe P(ket).
        beta: He so phat vung trung ngap (flood_prone).
        top_k: So luong phuong an lo trinh toi da tra ve.
        G: Traffic KG da khoi tao (neu None se tu build tu CSV).

    Returns:
        Dict chua danh sach nut lo trinh toi uu, thong so tung chang,
        so sanh baseline, diem ngap/ket da ne va ly do chon lo trinh.
    """
    cond = weather_cond or {}
    rain_mm_h = float(cond.get("rain_mm_h", 0.0))
    tide_level_m = float(cond.get("tide_level_m", 1.0))
    timestamp = str(cond.get("timestamp", "2026-11-26T17:00:00+07:00"))

    kg = G if G is not None else build_hang_xanh_kg()
    origin = _normalize_node(kg, start)
    destination = _normalize_node(kg, end)

    congestion_probs, congestion_levels = _resolve_congestion_probs(kg, cond)
    update_environment_state(
        kg,
        rain_mm_h=rain_mm_h,
        tide_level_m=tide_level_m,
        congestion_by_node=congestion_levels,
        timestamp=timestamp,
    )

    node_flood_flags, edge_flood_flags = _load_csv_flood_flags()
    R = _build_dynamic_routing_graph(
        kg,
        node_flood_flags=node_flood_flags,
        edge_flood_flags=edge_flood_flags,
        congestion_probs=congestion_probs,
        rain_mm_h=rain_mm_h,
        tide_level_m=tide_level_m,
        alpha=alpha,
        beta=beta,
    )

    if not nx.has_path(R, origin, destination):
        raise nx.NetworkXNoPath(f"Không có đường đi hợp lệ từ {origin} đến {destination}")

    baseline_path = nx.dijkstra_path(R, origin, destination, weight="length_m")
    dynamic_paths = list(nx.shortest_simple_paths(R, origin, destination, weight="dynamic_weight"))[: max(1, top_k)]

    baseline_summary = _summarize_path(R, baseline_path)
    optimal_summary = _summarize_path(R, dynamic_paths[0])
    alternatives = [_summarize_path(R, p) for p in dynamic_paths[1:]]

    optimal_node_set = set(optimal_summary["nodes"])
    avoided_floods = [
        fp for fp in baseline_summary["flood_points"] if fp.split(" ")[0] not in optimal_node_set
    ]
    avoided_congestion = [
        f"{cn['node_code']} ({cn['road']})"
        for cn in baseline_summary["congested_nodes"]
        if cn["node_code"] not in optimal_node_set
    ]

    reason = _build_reason(
        optimal=optimal_summary,
        baseline=baseline_summary,
        avoided_floods=avoided_floods,
        avoided_congestion=avoided_congestion,
        rain_mm_h=rain_mm_h,
        tide_level_m=tide_level_m,
    )

    active_hotspots = [
        attrs["name"]
        for _, attrs in kg.nodes(data=True)
        if attrs.get("node_type") == "FloodHotspot" and attrs.get("is_flooded")
    ]

    return {
        "origin": origin,
        "destination": destination,
        "weather": {
            "rain_mm_h": rain_mm_h,
            "tide_level_m": tide_level_m,
            "is_heavy_rain": rain_mm_h > 30.0,
            "is_high_tide": tide_level_m >= 1.40,
            "active_flood_hotspots": active_hotspots,
            "timestamp": timestamp,
        },
        "optimal_route": optimal_summary,
        "baseline_shortest_route": baseline_summary,
        "avoided_flood_zones": avoided_floods,
        "avoided_congested_nodes": avoided_congestion,
        "reason": reason,
        "alternative_routes": alternatives,
    }


if __name__ == "__main__":
    print("=== DYNAMIC DIJKSTRA ROUTING DEMO (HANG XANH 20 NUT / KG 24 NUT) ===")

    # Kich ban 1: Troi nang rao, khong ket xe
    res_clear = find_optimal_route(
        start="HX_05",
        end="HX_04",
        weather_cond={"rain_mm_h": 0.0, "tide_level_m": 1.10},
    )
    print("\n[Kịch bản 1] Trời tạnh ráo (HX_05 -> HX_04):")
    print("  Optimal :", " -> ".join(res_clear["optimal_route"]["nodes"]), f"| {res_clear['optimal_route']['total_length_m']}m")
    print("  Lý do   :", res_clear["reason"])

    # Kich ban 2: Mua lon 42 mm/h + trieu 1.55 m + Nga tu Hang Xanh (HX_01) ket & ngap -> ne qua Cau vuot Hang Xanh
    res_storm = find_optimal_route(
        start="HX_03",
        end="HX_15",
        weather_cond={
            "rain_mm_h": 42.0,
            "tide_level_m": 1.55,
            "congestion_prob": {
                "HX_01": 0.95,  # Nga tu Hang Xanh ket nang
                "HX_11": 0.90,  # Cau Son - XVNT ket nang & ngap
                "HX_02": 0.15,  # Cau vuot Hang Xanh thong thoang hon
                "HX_08": 0.10,
                "HX_07": 0.10,
                "HX_10": 0.08,
                "HX_15": 0.12,
            },
        },
    )
    print("\n[Kịch bản 2] Mưa lớn 42 mm/h + Triều 1.55 m (HX_03 -> HX_15):")
    print("  Baseline:", " -> ".join(res_storm["baseline_shortest_route"]["nodes"]), f"| {res_storm['baseline_shortest_route']['total_length_m']}m")
    print("  Optimal :", " -> ".join(res_storm["optimal_route"]["nodes"]), f"| {res_storm['optimal_route']['total_length_m']}m")
    print("  Né ngập :", res_storm["avoided_flood_zones"])
    print("  Né kẹt  :", res_storm["avoided_congested_nodes"])
    print("  Lý do   :", res_storm["reason"])
