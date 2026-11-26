"""
Dynamic Dijkstra Routing Engine on Traffic Knowledge Graph (CS315 - Nhom 14)
Phu trach: Hoang Cao Son (25730061) - Lead WBS-03 ([S1] Tuan 6)

Thuat toan Dynamic Dijkstra tinh trong so canh dong theo cong thuc:
    w(u, v) = length_m * (1 + alpha * P(congestion_v) + beta * flood_indicator(u, v))

Ho tro:
- Dong bo duy nhat co `flood_prone` cua [H1] (nodes.csv / edges.csv) va trang thai
  FloodHotspot trong Traffic KG (`traffic_kg_schema.py`).
- Phat ngap phan tach giua doan duong ngap truc tiep (`edge.flood_prone`) va canh
  khong ngap chi di vao nut ngap (`v`), tranh phat oan canh kho roi nut xuat phat `u`.
- Nhan xac suat ket xe P(y=2) tu mo hinh ML/ST-GNN hoac nhan 0/1/2 (ho tro ca
  `node_code`, `node_id` int va `str(node_id)`).
- Khong mutate do thi `G` truyen vao; tra ve dict JSON-serializable gom lo trinh
  toi uu, so sanh baseline, diem/doan ngap & ket da ne va ly do khuyen nghi cho [S2].
"""

from __future__ import annotations

from itertools import islice
from typing import Any

import networkx as nx

try:
    from .traffic_kg_schema import (
        _is_node_flooded,
        _node_flood_hotspots,
        _node_flood_severity,
        build_hang_xanh_kg,
        update_environment_state,
    )
except ImportError:
    from traffic_kg_schema import (
        _is_node_flooded,
        _node_flood_hotspots,
        _node_flood_severity,
        build_hang_xanh_kg,
        update_environment_state,
    )

CONGESTION_LEVEL_TO_PROB = {
    0: 0.05,
    1: 0.45,
    2: 0.90,
}

_SEVERITY_RANK = {"normal": 0, "warning": 1, "critical": 2}


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


def _lookup_node_value(mapping: dict[Any, Any], node_code: str, node_id: int) -> tuple[bool, Any]:
    """Tra cuu gia tri trong dict ho tro dong bo key node_code, int node_id va str(node_id)."""
    if node_code in mapping:
        return True, mapping[node_code]
    if node_id in mapping:
        return True, mapping[node_id]
    node_id_str = str(node_id)
    if node_id_str in mapping:
        return True, mapping[node_id_str]
    return False, None


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

        has_prob, raw_prob = _lookup_node_value(prob_input, node_code, node_id)
        has_lvl, raw_lvl = _lookup_node_value(level_input, node_code, node_id)

        if has_prob:
            p = float(raw_prob)
        elif has_lvl:
            p = CONGESTION_LEVEL_TO_PROB.get(int(raw_lvl), 0.05)
        else:
            p = 0.0

        p = max(0.0, min(1.0, p))
        probs[node_code] = p

        if has_lvl:
            levels[node_code] = int(raw_lvl)
        elif p >= 0.65:
            levels[node_code] = 2
        elif p >= 0.30:
            levels[node_code] = 1
        else:
            levels[node_code] = 0

    return probs, levels


def _default_weather_severity(rain_mm_h: float, tide_level_m: float) -> str:
    """Muc do ngap mac dinh khi do thi tuy bien khong co nut FloodHotspot."""
    heavy = rain_mm_h > 30.0
    combo = rain_mm_h > 15.0 and tide_level_m >= 1.50
    if heavy and tide_level_m >= 1.50:
        return "critical"
    if heavy or combo:
        return "warning"
    return "normal"


def _resolve_node_flood_state(
    G: nx.MultiDiGraph,
    node_code: str,
    rain_mm_h: float,
    tide_level_m: float,
) -> tuple[bool, bool, str, list[str]]:
    """Tra ve (is_flood_prone, is_flood_active, severity, active_hotspot_names) tu KG."""
    attrs = G.nodes[node_code]
    hotspot_ids = _node_flood_hotspots(G, node_code)
    is_prone = bool(attrs.get("flood_prone", False)) or bool(hotspot_ids)

    if hotspot_ids:
        active_names = _is_node_flooded(G, node_code)
        severity = _node_flood_severity(G, node_code)
        return is_prone, bool(active_names), severity, active_names

    if is_prone:
        severity = _default_weather_severity(rain_mm_h, tide_level_m)
        return True, severity != "normal", severity, []

    return False, False, "normal", []


def _resolve_edge_flood_state(
    G: nx.MultiDiGraph,
    u: str,
    v: str,
    data: dict[str, Any],
    rain_mm_h: float,
    tide_level_m: float,
) -> tuple[bool, str, list[str]]:
    """Xac dinh muc do ngap cua chinh doan duong (u -> v) theo co flood_prone va FloodHotspot."""
    if not data.get("flood_prone", False):
        return False, "normal", []

    road_name = str(data.get("road_name", ""))
    matched_hs: list[str] = []
    for node_id, attrs in G.nodes(data=True):
        if attrs.get("node_type") != "FloodHotspot":
            continue
        keywords = attrs.get("road_keywords") or []
        if any(kw in road_name for kw in keywords):
            matched_hs.append(node_id)

    if not matched_hs:
        matched_hs = list(dict.fromkeys(_node_flood_hotspots(G, v) + _node_flood_hotspots(G, u)))

    if matched_hs:
        best = "normal"
        active_names: list[str] = []
        for hs_id in matched_hs:
            hs_attrs = G.nodes[hs_id]
            sev = hs_attrs.get("severity", "normal")
            if _SEVERITY_RANK.get(sev, 0) > _SEVERITY_RANK[best]:
                best = sev
            if hs_attrs.get("is_flooded", False):
                active_names.append(hs_attrs["name"])
        return best != "normal", best, active_names

    severity = _default_weather_severity(rain_mm_h, tide_level_m)
    return severity != "normal", severity, []


def _build_dynamic_routing_graph(
    G: nx.MultiDiGraph,
    congestion_probs: dict[str, float],
    rain_mm_h: float,
    tide_level_m: float,
    alpha: float,
    beta: float,
) -> nx.DiGraph:
    """Tao DiGraph voi trong so canh dong w = length * (1 + alpha*P(ket) + beta*flood)."""
    R = nx.DiGraph()

    for node_code, attrs in G.nodes(data=True):
        if attrs.get("node_type") != "Intersection":
            continue
        is_prone, is_active, severity, active_hotspots = _resolve_node_flood_state(
            G, node_code, rain_mm_h, tide_level_m
        )
        R.add_node(
            node_code,
            **attrs,
            is_flood_prone=is_prone,
            is_flood_active=is_active,
            flood_severity=severity,
            flood_hotspot_names=active_hotspots,
            p_congestion=congestion_probs.get(node_code, 0.0),
        )

    for u, v, data in G.edges(data=True):
        if data.get("rel_type") != "CONNECTS_TO":
            continue

        length_m = float(data["length_m"])
        p_ket = congestion_probs.get(v, 0.0)

        edge_flood_prone = bool(data.get("flood_prone", False))
        edge_flood_active, edge_severity, edge_hotspots = _resolve_edge_flood_state(
            G, u, v, data, rain_mm_h, tide_level_m
        )
        v_flood_prone = R.nodes[v]["is_flood_prone"]
        v_severity = R.nodes[v]["flood_severity"]

        # Phat cao cho doan duong truc tiep ngap (edge.flood_prone); canh kho di vao
        # nut ngap `v` chi chiu he so tiep can nhe va KHONG phat oan canh kho roi `u`.
        if edge_flood_active:
            flood_indicator = 1.5 if edge_severity == "critical" else 1.0
        elif edge_flood_prone and rain_mm_h > 15.0:
            flood_indicator = 0.25
        elif v_severity == "critical":
            flood_indicator = 0.35
        elif v_severity == "warning":
            flood_indicator = 0.25
        elif v_flood_prone and rain_mm_h > 15.0:
            flood_indicator = 0.10
        else:
            flood_indicator = 0.0

        dynamic_weight = length_m * (1.0 + alpha * p_ket + beta * flood_indicator)

        edge_payload = {
            **data,
            "p_congestion": round(p_ket, 4),
            "is_flood_prone": edge_flood_prone,
            "is_flood_active": edge_flood_active,
            "flood_severity": edge_severity,
            "flood_hotspot_names": edge_hotspots,
            "flood_indicator": flood_indicator,
            "dynamic_weight": round(dynamic_weight, 2),
        }

        if not R.has_edge(u, v) or dynamic_weight < R[u][v]["dynamic_weight"]:
            R.add_edge(u, v, **edge_payload)

    return R


def _summarize_path(R: nx.DiGraph, path: list[str]) -> dict[str, Any]:
    """Tong hop chi tiet lo trinh: chang, do dai, trong so dong, diem/doan ngap va ket."""
    segments: list[dict[str, Any]] = []
    total_length_m = 0.0
    total_weight = 0.0
    total_base_time_s = 0.0
    flood_points: list[str] = []
    flood_edges: list[dict[str, str]] = []
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
        if e.get("is_flood_active"):
            flood_edges.append(
                {
                    "edge_id": e["edge_id"],
                    "from": u,
                    "to": v,
                    "road_name": e["road_name"],
                }
            )
            for hs_name in e.get("flood_hotspot_names", []):
                flood_hotspot_names.add(hs_name)
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
        "flood_edges": flood_edges,
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
        if not optimal["flood_points"] and not optimal["flood_edges"] and not optimal["congested_nodes"]:
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
        details.append(f"né được vùng ngập {', '.join(avoided_floods)}")
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
        G: Traffic KG da khoi tao (neu None se tu build tu CSV; khong bi mutate).

    Returns:
        Dict chua danh sach nut lo trinh toi uu, thong so tung chang,
        so sanh baseline, diem/doan ngap & ket da ne va ly do chon lo trinh.
    """
    cond = weather_cond or {}
    rain_mm_h = float(cond.get("rain_mm_h", 0.0))
    tide_level_m = float(cond.get("tide_level_m", 1.0))
    timestamp = str(cond.get("timestamp", "2026-11-26T17:00:00+07:00"))

    # Copy KG khi truyen tu ben ngoai de tranh lam thay doi trang thai cua caller
    kg = G.copy() if G is not None else build_hang_xanh_kg()
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

    R = _build_dynamic_routing_graph(
        kg,
        congestion_probs=congestion_probs,
        rain_mm_h=rain_mm_h,
        tide_level_m=tide_level_m,
        alpha=alpha,
        beta=beta,
    )

    if not nx.has_path(R, origin, destination):
        raise nx.NetworkXNoPath(f"Không có đường đi hợp lệ từ {origin} đến {destination}")

    baseline_path = nx.dijkstra_path(R, origin, destination, weight="length_m")
    dynamic_paths = list(
        islice(nx.shortest_simple_paths(R, origin, destination, weight="dynamic_weight"), max(1, top_k))
    )

    baseline_summary = _summarize_path(R, baseline_path)
    optimal_summary = _summarize_path(R, dynamic_paths[0])
    alternatives = [_summarize_path(R, p) for p in dynamic_paths[1:]]

    optimal_node_set = set(optimal_summary["nodes"])
    optimal_edge_ids = {seg["edge_id"] for seg in optimal_summary["segments"]}

    avoided_flood_nodes = [
        fp for fp in baseline_summary["flood_points"] if fp.split(" ")[0] not in optimal_node_set
    ]
    avoided_flood_edges = [
        f"đoạn {fe['road_name']} ({fe['from']}->{fe['to']}, {fe['edge_id']})"
        for fe in baseline_summary["flood_edges"]
        if fe["edge_id"] not in optimal_edge_ids
    ]
    avoided_floods = avoided_flood_nodes + avoided_flood_edges

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

    # Kich ban 2: Mua lon 42 mm/h + trieu 1.55 m (KHONG can input tac nghen) -> tu dong ne doan ngap Dinh Bo Linh (E_13)
    res_flood = find_optimal_route(
        start="HX_06",
        end="HX_16",
        weather_cond={"rain_mm_h": 42.0, "tide_level_m": 1.55},
    )
    print("\n[Kịch bản 2] Mưa lớn 42 mm/h + Triều 1.55 m, né đoạn ngập Đinh Bộ Lĩnh (HX_06 -> HX_16):")
    print("  Baseline:", " -> ".join(res_flood["baseline_shortest_route"]["nodes"]), f"| {res_flood['baseline_shortest_route']['total_length_m']}m")
    print("  Optimal :", " -> ".join(res_flood["optimal_route"]["nodes"]), f"| {res_flood['optimal_route']['total_length_m']}m")
    print("  Né ngập :", res_flood["avoided_flood_zones"])
    print("  Lý do   :", res_flood["reason"])

    # Kich ban 3: Mua lon 42 mm/h + trieu 1.55 m + Nga tu Hang Xanh (HX_01) ket nang -> ne qua Cau vuot Hang Xanh
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
    print("\n[Kịch bản 3] Mưa lớn 42 mm/h + Triều 1.55 m + HX_01 kẹt nặng (HX_03 -> HX_15):")
    print("  Baseline:", " -> ".join(res_storm["baseline_shortest_route"]["nodes"]), f"| {res_storm['baseline_shortest_route']['total_length_m']}m")
    print("  Optimal :", " -> ".join(res_storm["optimal_route"]["nodes"]), f"| {res_storm['optimal_route']['total_length_m']}m")
    print("  Né ngập :", res_storm["avoided_flood_zones"])
    print("  Né kẹt  :", res_storm["avoided_congested_nodes"])
    print("  Lý do   :", res_storm["reason"])
