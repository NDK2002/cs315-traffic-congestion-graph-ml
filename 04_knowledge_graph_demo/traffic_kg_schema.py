"""
Traffic Knowledge Graph Schema & Prototype (CS315 - Nhom 14)
Phu trach: Hoang Cao Son (25730061) - Lead WBS-03

Module dung do thi tri thuc (NetworkX MultiDiGraph) cho cum giao thong Hang Xanh
tu nodes.csv (HX_01..HX_20) va edges.csv (E_01..E_37), mo hinh hoa diem ngap
Binh Thanh, trang thai thoi tiet/trieu cuong va truy van lo trinh ne ket.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import networkx as nx

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "01_data_sample"

CONGESTION_LABELS = {
    0: "Thông thoáng",
    1: "Ùn ứ",
    2: "Kẹt xe nghiêm trọng",
}

CONGESTION_PENALTY = {
    0: 1.0,
    1: 2.2,
    2: 6.0,
}

# Tri thuc thuc dia cac diem trung de ngap tai Binh Thanh (Muc I.1 & I.5 De cuong)
FLOOD_HOTSPOTS: list[dict[str, Any]] = [
    {
        "hotspot_id": "FH_DINH_BO_LINH",
        "name": "Điểm ngập Đinh Bộ Lĩnh (đoạn gần Bến xe Miền Đông / Cầu Đinh Bộ Lĩnh)",
        "road_keywords": ["Đinh Bộ Lĩnh"],
        "rain_threshold_mm_h": 30.0,
        "tide_threshold_m": 1.50,
    },
    {
        "hotspot_id": "FH_XVNT_BINH_TRIEU",
        "name": "Điểm ngập Xô Viết Nghệ Tĩnh (hướng Cầu Sơn - Cầu Bình Triệu)",
        "road_keywords": ["Xô Viết Nghệ Tĩnh", "Cầu Sơn"],
        "rain_threshold_mm_h": 30.0,
        "tide_threshold_m": 1.50,
    },
    {
        "hotspot_id": "FH_UNG_VAN_KHIEM",
        "name": "Điểm ngập Ung Văn Khiêm (khu vực trũng gần D2 / Đài Liệt Sĩ)",
        "road_keywords": ["Ung Văn Khiêm"],
        "rain_threshold_mm_h": 35.0,
        "tide_threshold_m": 1.55,
    },
]


def _parse_bool(val: str) -> bool:
    return str(val).strip().lower() == "true"


def _parse_float(val: str, default: float) -> float:
    try:
        return float(val) if str(val).strip() else default
    except ValueError:
        return default


def build_hang_xanh_kg(
    nodes_csv: Path | str | None = None,
    edges_csv: Path | str | None = None,
) -> nx.MultiDiGraph:
    """Khoi tao Traffic Knowledge Graph tu nodes.csv va edges.csv cua Hang Xanh."""
    nodes_path = Path(nodes_csv) if nodes_csv else DEFAULT_DATA_DIR / "nodes.csv"
    edges_path = Path(edges_csv) if edges_csv else DEFAULT_DATA_DIR / "edges.csv"

    G = nx.MultiDiGraph()
    id_to_code: dict[int, str] = {}

    with nodes_path.open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            node_id = int(row["node_id"])
            node_code = row["node_code"].strip()
            id_to_code[node_id] = node_code
            G.add_node(
                node_code,
                node_type="Intersection",
                node_id=node_id,
                node_code=node_code,
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                roads=row["roads"].strip(),
                highway_classes=row["highway_classes"].strip(),
                in_degree=int(row["in_degree"]),
                out_degree=int(row["out_degree"]),
                congestion_level=0,
                congestion_label=CONGESTION_LABELS[0],
            )

    with edges_path.open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            u_code = id_to_code[int(row["u"])]
            v_code = id_to_code[int(row["v"])]
            length_m = _parse_float(row["length"], 100.0)
            maxspeed_kmh = _parse_float(row.get("maxspeed", ""), 40.0)
            base_time_s = length_m / (maxspeed_kmh / 3.6)
            G.add_edge(
                u_code,
                v_code,
                key=row["edge_id"].strip(),
                rel_type="CONNECTS_TO",
                edge_id=row["edge_id"].strip(),
                road_name=row["name"].strip(),
                highway=row["highway"].strip(),
                lanes=int(_parse_float(row["lanes"], 2.0)),
                length_m=length_m,
                oneway=_parse_bool(row["oneway"]),
                maxspeed_kmh=maxspeed_kmh,
                base_time_s=round(base_time_s, 2),
                effective_cost=round(base_time_s, 2),
            )

    # Them node thoi tiet hien tai & cac diem ngap lien ket ngu nghia
    G.add_node(
        "WEATHER_CURRENT",
        node_type="WeatherCondition",
        rain_mm_h=0.0,
        rain_cum_3h_mm=0.0,
        tide_level_m=1.0,
        is_heavy_rain=False,
        is_high_tide=False,
        horizon="t+15",
        timestamp="init",
    )

    for hs in FLOOD_HOTSPOTS:
        hs_id = hs["hotspot_id"]
        G.add_node(
            hs_id,
            node_type="FloodHotspot",
            hotspot_id=hs_id,
            name=hs["name"],
            rain_threshold_mm_h=hs["rain_threshold_mm_h"],
            tide_threshold_m=hs["tide_threshold_m"],
            is_flooded=False,
            severity="normal",
        )
        G.add_edge(
            hs_id,
            "WEATHER_CURRENT",
            key=f"AFFECTED_{hs_id}",
            rel_type="AFFECTED_BY_WEATHER",
            trigger_rule=f"rain > {hs['rain_threshold_mm_h']} mm/h or (rain > 15 & tide >= {hs['tide_threshold_m']} m)",
        )
        for node_code, attrs in G.nodes(data=True):
            if attrs.get("node_type") != "Intersection":
                continue
            if any(kw in attrs.get("roads", "") for kw in hs["road_keywords"]):
                G.add_edge(
                    node_code,
                    hs_id,
                    key=f"FLOOD_{node_code}_{hs_id}",
                    rel_type="PRONE_TO_FLOOD",
                    risk_weight=1.0,
                )

    return G


def _is_node_flooded(G: nx.MultiDiGraph, node_code: str) -> list[str]:
    """Tra ve danh sach ten diem ngap dang kich hoat tai nut giao."""
    flooded_names: list[str] = []
    for _, target, data in G.out_edges(node_code, data=True):
        if data.get("rel_type") == "PRONE_TO_FLOOD":
            hs_attrs = G.nodes[target]
            if hs_attrs.get("is_flooded", False):
                flooded_names.append(hs_attrs["name"])
    return flooded_names


def update_environment_state(
    G: nx.MultiDiGraph,
    rain_mm_h: float,
    tide_level_m: float,
    congestion_by_node: dict[str | int, int] | None = None,
    timestamp: str = "2026-11-15 17:30:00",
    rain_cum_3h_mm: float | None = None,
    horizon: str = "t+15",
) -> None:
    """Cap nhat trang thai mua, trieu cuong, diem ngap va trong so canh dong.

    congestion_by_node ho tro ca node_code ('HX_01') lan node_id (1) theo Data Contract [K1].
    """
    weather = G.nodes["WEATHER_CURRENT"]
    weather["rain_mm_h"] = rain_mm_h
    weather["rain_cum_3h_mm"] = rain_cum_3h_mm if rain_cum_3h_mm is not None else rain_mm_h
    weather["tide_level_m"] = tide_level_m
    weather["is_heavy_rain"] = rain_mm_h > 30.0
    # Nguong bao dong trieu tram Phu An (Dai KTTV Nam Bo 11/2026): BD1=1.40m, BD2=1.50m, BD3=1.60m
    weather["is_high_tide"] = tide_level_m >= 1.40
    weather["horizon"] = horizon
    weather["timestamp"] = timestamp

    for _, attrs in G.nodes(data=True):
        if attrs.get("node_type") == "FloodHotspot":
            heavy = rain_mm_h > attrs["rain_threshold_mm_h"]
            combo = rain_mm_h > 15.0 and tide_level_m >= attrs["tide_threshold_m"]
            attrs["is_flooded"] = heavy or combo
            if heavy and tide_level_m >= attrs["tide_threshold_m"]:
                attrs["severity"] = "critical"
            elif attrs["is_flooded"]:
                attrs["severity"] = "warning"
            else:
                attrs["severity"] = "normal"

    congestion_map = congestion_by_node or {}
    for node_code, attrs in G.nodes(data=True):
        if attrs.get("node_type") == "Intersection":
            node_id = attrs["node_id"]
            if node_code in congestion_map:
                lvl = int(congestion_map[node_code])
            elif node_id in congestion_map:
                lvl = int(congestion_map[node_id])
            else:
                lvl = 0
            attrs["congestion_level"] = lvl
            attrs["congestion_label"] = CONGESTION_LABELS.get(lvl, "Không rõ")

    for u, v, key, data in G.edges(keys=True, data=True):
        if data.get("rel_type") != "CONNECTS_TO":
            continue
        v_lvl = G.nodes[v].get("congestion_level", 0)
        u_flooded = bool(_is_node_flooded(G, u))
        v_flooded = bool(_is_node_flooded(G, v))
        flood_factor = 4.5 if (u_flooded or v_flooded) else 1.0
        congestion_factor = CONGESTION_PENALTY.get(v_lvl, 1.0)
        data["effective_cost"] = round(data["base_time_s"] * congestion_factor * flood_factor, 2)


def _build_routing_view(G: nx.MultiDiGraph) -> nx.DiGraph:
    """Chuyen tang CONNECTS_TO thanh DiGraph don gian de chay shortest_simple_paths."""
    R = nx.DiGraph()
    for node_code, attrs in G.nodes(data=True):
        if attrs.get("node_type") == "Intersection":
            R.add_node(node_code, **attrs)
    for u, v, data in G.edges(data=True):
        if data.get("rel_type") != "CONNECTS_TO":
            continue
        cost = data["effective_cost"]
        if not R.has_edge(u, v) or cost < R[u][v]["effective_cost"]:
            R.add_edge(u, v, **data)
    return R


def _describe_route(G: nx.MultiDiGraph, R: nx.DiGraph, path: list[str]) -> dict[str, Any]:
    segments = []
    total_length_m = 0.0
    total_cost = 0.0
    flood_warnings: set[str] = set()
    congested_nodes: list[str] = []

    for node in path:
        if G.nodes[node].get("congestion_level", 0) >= 2:
            congested_nodes.append(f"{node} ({G.nodes[node]['roads'].split('|')[0].strip()})")
        for fn in _is_node_flooded(G, node):
            flood_warnings.add(fn)

    for u, v in zip(path[:-1], path[1:]):
        edge = R[u][v]
        total_length_m += edge["length_m"]
        total_cost += edge["effective_cost"]
        segments.append(f"{u}->{v} [{edge['road_name']}, {edge['length_m']:.0f}m]")

    return {
        "path": path,
        "segments": segments,
        "total_length_m": round(total_length_m, 1),
        "effective_cost": round(total_cost, 1),
        "congested_nodes": congested_nodes,
        "flood_warnings": sorted(flood_warnings),
    }


def recommend_avoidance_routes(
    G: nx.MultiDiGraph,
    origin: str,
    destination: str,
    top_k: int = 2,
) -> dict[str, Any]:
    """Tra cuu lo trinh toi uu dong ne ket/ngap kem so sanh voi duong ngan nhat tinh."""
    R = _build_routing_view(G)
    if origin not in R or destination not in R:
        raise ValueError(f"Nút không hợp lệ: {origin} hoặc {destination}")

    static_path = nx.shortest_path(R, origin, destination, weight="base_time_s")
    dynamic_paths = list(nx.shortest_simple_paths(R, origin, destination, weight="effective_cost"))[:top_k]

    weather = G.nodes["WEATHER_CURRENT"]
    return {
        "weather": {
            "rain_mm_h": weather["rain_mm_h"],
            "tide_level_m": weather["tide_level_m"],
            "is_heavy_rain": weather["is_heavy_rain"],
            "is_high_tide": weather["is_high_tide"],
            "timestamp": weather["timestamp"],
        },
        "origin": origin,
        "destination": destination,
        "baseline_shortest_route": _describe_route(G, R, static_path),
        "recommended_routes": [_describe_route(G, R, p) for p in dynamic_paths],
    }


def query_node_context(G: nx.MultiDiGraph, node_code: str) -> dict[str, Any]:
    """Tool cho AI Agent tra cuu ngu canh day du cua 1 nut giao."""
    if node_code not in G or G.nodes[node_code].get("node_type") != "Intersection":
        raise ValueError(f"Không tìm thấy nút giao: {node_code}")
    attrs = G.nodes[node_code]
    return {
        "node_code": node_code,
        "roads": attrs["roads"],
        "congestion_level": attrs["congestion_level"],
        "congestion_label": attrs["congestion_label"],
        "active_flood_warnings": _is_node_flooded(G, node_code),
        "outgoing_roads": [
            {"to": v, "edge_id": d["edge_id"], "road": d["road_name"], "effective_cost": d["effective_cost"]}
            for _, v, d in G.out_edges(node_code, data=True)
            if d.get("rel_type") == "CONNECTS_TO"
        ],
    }


if __name__ == "__main__":
    kg = build_hang_xanh_kg()
    # Kich ban demo Muc I.4 / Noi dung 5: Mua to >30mm/h + trieu cuong + Nga tu Hang Xanh (HX_01) & Dinh Bo Linh ket nang
    mock_congestion = {
        "HX_01": 2,  # Nga tu Hang Xanh ket xe nghiem trong
        "HX_03": 2,  # Dinh Bo Linh - Dien Bien Phu ket xe nghiem trong
        "HX_04": 2,  # Dinh Bo Linh - Bach Dang ket xe nghiem trong
        "HX_11": 2,  # Cau Son - XVNT ket xe nghiem trong
        "HX_02": 1,  # Cau vuot Hang Xanh un u
        "HX_07": 0,  # Nguyen Gia Tri (D2) thong thoang
        "HX_10": 0,
        "HX_15": 0,
    }
    update_environment_state(
        kg,
        rain_mm_h=36.5,
        tide_level_m=1.55,
        congestion_by_node=mock_congestion,
        timestamp="2026-11-15T17:45:00+07:00",
    )

    result = recommend_avoidance_routes(kg, origin="HX_02", destination="HX_15", top_k=2)
    print("=== TRAFFIC KNOWLEDGE GRAPH DEMO (MUA 36.5 mm/h, TRIEU 1.55m) ===")
    print("So nut KG:", kg.number_of_nodes(), "| So canh KG:", kg.number_of_edges())
    print("\n[1] Đường ngắn nhất tĩnh (không xét kẹt/ngập):")
    print("   Path:", " -> ".join(result["baseline_shortest_route"]["path"]))
    print("   Cảnh báo ngập:", result["baseline_shortest_route"]["flood_warnings"])
    print("\n[2] Lộ trình KG khuyến nghị né sóng kẹt & ngập:")
    for idx, r in enumerate(result["recommended_routes"], 1):
        print(f"   Phương án {idx}: {' -> '.join(r['path'])} | Dài: {r['total_length_m']}m | Cost: {r['effective_cost']}")
        print(f"     Chặng: {' | '.join(r['segments'])}")
