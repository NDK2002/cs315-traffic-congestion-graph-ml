"""Bản đồ GIS kiểm tra tọa độ nút, chiều cạnh và đoạn dễ ngập cụm Hàng Xanh (CS315 - [D1]).

Đầu vào: nodes.csv, edges.csv trong 01_data_sample/ (sản phẩm [H3]).
Đầu ra: 01_data_sample/hang_xanh_gis_check.html và bảng kiểm tra in ra màn hình.

Các phép kiểm tra tự động:
1. Khoảng cách nút tới tâm (haversine) so với cột dist_center_m.
2. Chiều dài cạnh so với khoảng cách đường chim bay giữa hai nút.
3. Cạnh chỉ có một chiều (không có cạnh ngược v -> u).
4. Cặp cạnh hai chiều có cờ oneway khác nhau.
5. Nút không có cạnh đi vào hoặc không có cạnh đi ra.
Cạnh chỉ có một chiều được đối chiếu với tag oneway của OSM (OSM_CHECK, tra ngày 18/11/2026).
Các nghi vấn còn lại kiểm bằng mắt trên nền bản đồ OpenStreetMap.
"""

from __future__ import annotations

import argparse
import math
import pathlib

import folium
import pandas as pd
from folium.plugins import PolyLineTextPath

CENTER = (10.8012, 106.7114)
RADIUS_M = 1000
DIST_TOLERANCE_M = 5.0
LENGTH_RATIO_MIN = 0.9
LENGTH_RATIO_MAX = 2.0
EDGE_OFFSET_M = 6.0

# Đoạn trũng dễ ngập theo Đề cương Mục I.1 và Kế hoạch Tuần 4 [D1]
FLOOD_ROADS = ("Đinh Bộ Lĩnh", "Ung Văn Khiêm")
FLOOD_NOTE = "Đoạn dễ ngập theo Đề cương (Mục I.1)"

# Kết quả đối chiếu cạnh một chiều với OSM (API openstreetmap.org, bbox 106.703,10.791,106.721,10.811)
# True = khớp thực tế OSM, False = nghi lỗi trích xuất
OSM_CHECK = {
    "E_05": (True, "XVNT Hàng Xanh -> Cầu Sơn là đường một chiều hướng Bắc (way 1330784594, 191666357, 33103592)"),
    "E_27": (True, "XVNT phía Bắc Cầu Sơn một chiều hướng Bắc (way 1330784596, 1411067484)"),
    "E_13": (True, "Đinh Bộ Lĩnh một chiều hướng Nam về Hàng Xanh (way 192512367, 330374319)"),
    "E_31": (True, "Cầu Đinh Bộ Lĩnh một chiều hướng Nam (way 1527090810, 1225831527)"),
    "E_36": (True, "Ung Văn Khiêm một chiều hướng Đông từ XVNT (way 987276648, 1324261893)"),
    "E_08": (True, "ĐBP có dải phân cách: chiều Đông đi 2 -> 8, chiều Tây đi 8 -> 7 -> 2 (way 408245967, 35085959)"),
    "E_19": (True, "ĐBP chiều Tây qua nút Nguyễn Gia Trí (way 55880235)"),
    "E_21": (True, "ĐBP chiều Tây qua nút Nguyễn Gia Trí (way 35085959)"),
    "E_35": (False, "XVNT phía Nam là 2 chiều (way 1267814252, 32577688 hướng Bắc) nhưng thiếu cạnh 20 -> 17. Nút 20 nằm ở biên vùng tải 1000 m"),
}

# Nút thiếu cạnh vào/ra nhưng đã giải thích được bằng OSM
NODE_OSM_NOTE = {
    14: "Điểm vào mạng của Đinh Bộ Lĩnh một chiều hướng Nam, khớp OSM",
}

COLOR_TWO_WAY = "#1f77b4"
COLOR_ONE_WAY = "#ff7f0e"
COLOR_ONE_WAY_SUSPECT = "#d62828"
COLOR_FLOOD = "#7b2cbf"
COLOR_NODE_OK = "#2a9d8f"
COLOR_NODE_WARN = "#d62828"


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def offset_line(lat1: float, lon1: float, lat2: float, lon2: float, offset_m: float) -> list[list[float]]:
    """Dịch đoạn thẳng sang phải theo chiều đi để 2 chiều của một tuyến không chồng lên nhau."""
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians((lat1 + lat2) / 2))
    dx = (lon2 - lon1) * m_per_deg_lon
    dy = (lat2 - lat1) * m_per_deg_lat
    norm = math.hypot(dx, dy) or 1.0
    ox_m, oy_m = dy / norm * offset_m, -dx / norm * offset_m
    d_lat, d_lon = oy_m / m_per_deg_lat, ox_m / m_per_deg_lon
    return [[lat1 + d_lat, lon1 + d_lon], [lat2 + d_lat, lon2 + d_lon]]


def is_flood_road(name: str) -> bool:
    return any(road in str(name) for road in FLOOD_ROADS)


def check_nodes(nodes: pd.DataFrame) -> pd.DataFrame:
    df = nodes.copy()
    df["dist_center_check_m"] = [
        round(haversine_m(CENTER[0], CENTER[1], lat, lon), 1) for lat, lon in zip(df["lat"], df["lon"])
    ]
    df["dist_diff_m"] = (df["dist_center_check_m"] - df["dist_center_m"]).abs().round(1)
    df["coord_mismatch"] = df["dist_diff_m"] > DIST_TOLERANCE_M
    df["no_in_edge"] = df["in_degree"] == 0
    df["no_out_edge"] = df["out_degree"] == 0
    df["outside_radius"] = df["dist_center_check_m"] > RADIUS_M
    return df


def check_edges(edges: pd.DataFrame, nodes: pd.DataFrame) -> pd.DataFrame:
    df = edges.copy()
    pos = nodes.set_index("node_id")[["lat", "lon"]]
    pairs = set(zip(df["u"], df["v"]))
    oneway_by_pair = {(u, v): ow for u, v, ow in zip(df["u"], df["v"], df["oneway"])}

    df["straight_m"] = [
        round(haversine_m(pos.at[u, "lat"], pos.at[u, "lon"], pos.at[v, "lat"], pos.at[v, "lon"]), 1)
        for u, v in zip(df["u"], df["v"])
    ]
    df["length_ratio"] = (df["length"] / df["straight_m"]).round(2)
    df["length_suspect"] = (df["length_ratio"] < LENGTH_RATIO_MIN) | (df["length_ratio"] > LENGTH_RATIO_MAX)
    df["has_reverse"] = [(v, u) in pairs for u, v in zip(df["u"], df["v"])]
    df["oneway_conflict"] = [
        (v, u) in pairs and oneway_by_pair[(v, u)] != ow for u, v, ow in zip(df["u"], df["v"], df["oneway"])
    ]
    df["flood_road"] = df["name"].map(is_flood_road)
    return df


def build_map(nodes: pd.DataFrame, edges: pd.DataFrame) -> folium.Map:
    fmap = folium.Map(location=CENTER, zoom_start=16, tiles="OpenStreetMap", control_scale=True)
    pos = nodes.set_index("node_id")[["lat", "lon"]]

    g_radius = folium.FeatureGroup(name=f"Phạm vi {RADIUS_M} m quanh tâm Hàng Xanh")
    g_two = folium.FeatureGroup(name="Cạnh có đủ 2 chiều")
    g_one = folium.FeatureGroup(name="Cạnh chỉ có 1 chiều")
    g_flood = folium.FeatureGroup(name="Đoạn dễ ngập (Đề cương)")
    g_nodes = folium.FeatureGroup(name="Nút giao")

    folium.Circle(CENTER, radius=RADIUS_M, color="#555555", weight=1, fill=False, dash_array="6").add_to(g_radius)
    folium.Marker(CENTER, tooltip="Tâm Ngã tư Hàng Xanh (10.8012, 106.7114)",
                  icon=folium.Icon(color="gray", icon="star")).add_to(g_radius)

    for row in edges.itertuples(index=False):
        lat1, lon1 = pos.at[row.u, "lat"], pos.at[row.u, "lon"]
        lat2, lon2 = pos.at[row.v, "lat"], pos.at[row.v, "lon"]
        coords = offset_line(lat1, lon1, lat2, lon2, EDGE_OFFSET_M if row.has_reverse else 0.0)
        osm_ok, osm_note = OSM_CHECK.get(row.edge_id, (None, ""))
        if row.has_reverse:
            color = COLOR_TWO_WAY
        else:
            color = COLOR_ONE_WAY if osm_ok else COLOR_ONE_WAY_SUSPECT
        group = g_two if row.has_reverse else g_one
        tooltip = (
            f"{row.edge_id}: {row.u} → {row.v} | {row.name}<br>"
            f"highway={row.highway}, lanes={row.lanes}, oneway={row.oneway}<br>"
            f"length={row.length} m, chim bay={row.straight_m} m (tỉ lệ {row.length_ratio})"
            + (f"<br>OSM: {osm_note}" if osm_note else "")
        )
        line = folium.PolyLine(coords, color=color, weight=4 if row.has_reverse else 5, opacity=0.85, tooltip=tooltip)
        line.add_to(group)
        PolyLineTextPath(line, "   ►   ", repeat=True, offset=5,
                         attributes={"fill": color, "font-size": "14"}).add_to(group)
        if row.flood_road:
            folium.PolyLine([[lat1, lon1], [lat2, lon2]], color=COLOR_FLOOD, weight=12, opacity=0.25,
                            tooltip=f"{FLOOD_NOTE}: {row.name}").add_to(g_flood)

    for row in nodes.itertuples(index=False):
        node_note = NODE_OSM_NOTE.get(row.node_id, "")
        warn = row.coord_mismatch or ((row.no_in_edge or row.no_out_edge) and not node_note)
        issues = []
        if row.coord_mismatch:
            issues.append(f"lệch dist_center {row.dist_diff_m} m")
        if row.no_in_edge:
            issues.append("không có cạnh đi vào")
        if row.no_out_edge:
            issues.append("không có cạnh đi ra")
        popup = (
            f"<b>{row.node_code}</b> (node_id={row.node_id})<br>{row.roads}<br>"
            f"lat={row.lat}, lon={row.lon}<br>in={row.in_degree}, out={row.out_degree}, "
            f"cách tâm {row.dist_center_check_m} m"
            + (f"<br><b style='color:{COLOR_NODE_WARN}'>{'; '.join(issues)}</b>" if issues else "")
            + (f"<br>OSM: {node_note}" if node_note else "")
        )
        folium.CircleMarker(
            [row.lat, row.lon], radius=7, color=COLOR_NODE_WARN if warn else COLOR_NODE_OK,
            fill=True, fill_opacity=0.9, popup=folium.Popup(popup, max_width=320),
            tooltip=folium.Tooltip(row.node_code.replace("HX_", ""), permanent=True, direction="right",
                                   style="font-size: 11px; padding: 0 3px;"),
        ).add_to(g_nodes)

    for group in (g_radius, g_flood, g_two, g_one, g_nodes):
        group.add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)

    legend = f"""
    <div style="position: fixed; bottom: 24px; left: 24px; z-index: 9999; background: white;
                padding: 8px 12px; border: 1px solid #999; font: 13px Arial, sans-serif; line-height: 1.6;">
      <b>CS315 [D1] — Kiểm tra đồ thị Hàng Xanh</b><br>
      <span style="color:{COLOR_TWO_WAY}">━ ►</span> Cạnh có đủ 2 chiều (vẽ lệch sang phải chiều đi)<br>
      <span style="color:{COLOR_ONE_WAY}">━ ►</span> Cạnh 1 chiều, khớp OSM<br>
      <span style="color:{COLOR_ONE_WAY_SUSPECT}">━ ►</span> Cạnh 1 chiều, nghi lỗi trích xuất<br>
      <span style="color:{COLOR_FLOOD}">▬</span> Đoạn dễ ngập theo Đề cương<br>
      <span style="color:{COLOR_NODE_OK}">●</span> Nút bình thường &nbsp;
      <span style="color:{COLOR_NODE_WARN}">●</span> Nút cần kiểm (nhãn = node_id)
    </div>"""
    fmap.get_root().html.add_child(folium.Element(legend))
    return fmap


def print_report(nodes: pd.DataFrame, edges: pd.DataFrame) -> None:
    print(f"Số nút: {len(nodes)} | Số cạnh: {len(edges)}")

    bad_coord = nodes[nodes["coord_mismatch"]]
    print(f"\n[1] Nút lệch dist_center_m > {DIST_TOLERANCE_M} m: {len(bad_coord)}")
    if len(bad_coord):
        print(bad_coord[["node_code", "dist_center_m", "dist_center_check_m", "dist_diff_m"]].to_string(index=False))

    outside = nodes[nodes["outside_radius"]]
    print(f"\n    Nút nằm ngoài bán kính {RADIUS_M} m: {', '.join(outside['node_code']) or 'không có'}")

    sus_len = edges[edges["length_suspect"]]
    print(f"\n[2] Cạnh có tỉ lệ length / chim bay ngoài [{LENGTH_RATIO_MIN}, {LENGTH_RATIO_MAX}]: {len(sus_len)}")
    if len(sus_len):
        print(sus_len[["edge_id", "u", "v", "name", "length", "straight_m", "length_ratio"]].to_string(index=False))

    one_dir = edges[~edges["has_reverse"]].copy()
    one_dir["osm"] = one_dir["edge_id"].map(
        lambda e: {True: "khớp OSM", False: "NGHI LỖI"}.get(OSM_CHECK.get(e, (None, ""))[0], "chưa đối chiếu")
    )
    print(f"\n[3] Cạnh chỉ có 1 chiều: {len(one_dir)}")
    if len(one_dir):
        print(one_dir[["edge_id", "u", "v", "name", "highway", "osm"]].to_string(index=False))

    conflict = edges[edges["oneway_conflict"]]
    print(f"\n[4] Cặp cạnh 2 chiều có cờ oneway khác nhau: {len(conflict)}")
    if len(conflict):
        print(conflict[["edge_id", "u", "v", "name", "oneway"]].to_string(index=False))

    print(f"\n[5] Nút không có cạnh đi vào: {', '.join(nodes.loc[nodes['no_in_edge'], 'node_code']) or 'không có'}")
    print(f"    Nút không có cạnh đi ra: {', '.join(nodes.loc[nodes['no_out_edge'], 'node_code']) or 'không có'}")

    flood = edges[edges["flood_road"]]
    print(f"\n[6] Cạnh thuộc đoạn dễ ngập ({', '.join(FLOOD_ROADS)}): {', '.join(flood['edge_id'])}")


def main() -> None:
    here = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Bản đồ GIS kiểm tra đồ thị Hàng Xanh (CS315 - [D1]).")
    parser.add_argument("--nodes", type=pathlib.Path, default=here / "nodes.csv")
    parser.add_argument("--edges", type=pathlib.Path, default=here / "edges.csv")
    parser.add_argument("--output", type=pathlib.Path, default=here / "hang_xanh_gis_check.html")
    args = parser.parse_args()

    nodes = check_nodes(pd.read_csv(args.nodes, encoding="utf-8-sig"))
    edges = check_edges(pd.read_csv(args.edges, encoding="utf-8-sig"), nodes)

    print_report(nodes, edges)
    build_map(nodes, edges).save(str(args.output))
    print(f"\nĐã lưu bản đồ: {args.output}")


if __name__ == "__main__":
    main()
