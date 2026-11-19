# ĐẶC TẢ ONTOLOGY / SCHEMA — TRAFFIC KNOWLEDGE GRAPH (`[S2]`)

* **Học phần:** `CS315.G12.LT.TTNT` — Máy học nâng cao (Nhóm 14)
* **Phụ trách:** Hoàng Cao Sơn (`25730061`) — *Lead `WBS-03`*
* **Module thực thi:** [traffic_kg_schema.py](./traffic_kg_schema.py)
* **Nguồn dữ liệu đồ thị & hợp đồng dữ liệu:** Khớp trực tiếp `node_id` (`1..20`), `node_code` (`HX_01..HX_20`) từ [nodes.csv](../01_data_sample/nodes.csv), `edge_id` (`E_01..E_37`) từ [edges.csv](../01_data_sample/edges.csv) và chuẩn cột (`rain_mm_h`, `rain_cum_3h_mm`, `tide_level_m`, `y_t15`/`y_t30`/`y_t60`) từ [feature_dictionary.md](../02_feature_selection/feature_dictionary.md) (`[K1]`).

---

## 1. Mục tiêu thiết kế

Xây dựng tầng biểu diễn tri thức ngữ nghĩa (**Traffic Knowledge Graph**) trên `NetworkX` (`MultiDiGraph`) để:
1. Lưu trữ cấu trúc vật lý cụm Ngã tư Hàng Xanh (`20` nút, `37` cạnh có hướng) cùng tri thức miền về **điểm trũng dễ ngập tại Bình Thạnh**.
2. Tiếp nhận trạng thái động gồm: lượng mưa (`rain_mm_h`), mực nước triều (`tide_level_m`) và nhãn dự báo ùn tắc từ mô hình ML Tuần 5–6 (`y_t15`, `y_t30`, `y_t60` $\in \{0, 1, 2\}$).
3. Tính toán trọng số di chuyển động (*effective travel cost*) và cung cấp các hàm truy vấn (*tool-calling interface*) cho **AI Agent** (`03_Traffic_KG_Agent_Demo.ipynb`) gợi ý lộ trình né sóng ùn tắc và giải thích nguyên nhân.

---

## 2. Ontology: Các loại Thực thể (Node Types)

| `node_type` | Định danh mẫu | Thuộc tính chính (`attributes`) | Nguồn dữ liệu |
| :--- | :--- | :--- | :--- |
| **`Intersection`** | `HX_01` .. `HX_20` | `node_id` (int), `node_code` (str), `lat`, `lon`, `roads`, `highway_classes`, `in_degree`, `out_degree`, `congestion_level` (`0/1/2`), `congestion_label` (`Thông thoáng` / `Ùn ứ` / `Kẹt xe nghiêm trọng`) | [nodes.csv](../01_data_sample/nodes.csv) + Output ML |
| **`FloodHotspot`** | `FH_DINH_BO_LINH`, `FH_XVNT_BINH_TRIEU`, `FH_UNG_VAN_KHIEM` | `hotspot_id`, `name`, `road_name`, `rain_threshold_mm_h` (`30.0`), `tide_threshold_m` (`1.50`), `is_flooded` (bool), `severity` (`normal`/`warning`/`critical`) | Tri thức thực địa Bình Thạnh (Mục I.1 & I.5 Đề cương) |
| **`WeatherCondition`** | `WEATHER_CURRENT` | `rain_mm_h` (float), `tide_level_m` (float), `is_heavy_rain` (`> 30.0 mm/h`), `is_high_tide` (`>= 1.40 m`, BĐ1 Phú An; BĐ2 `1.50 m`, BĐ3 `1.60 m`), `timestamp` | `Open-Meteo` + Lịch triều Phú An |

---

## 3. Ontology: Các loại Quan hệ (Edge / Relation Types)

Đồ thị dùng `nx.MultiDiGraph` để tách bạch cạnh vật lý đường bộ và cạnh ngữ nghĩa tri thức:

| `rel_type` | Chiều quan hệ | Thuộc tính chính | Ý nghĩa suy luận |
| :--- | :--- | :--- | :--- |
| **`CONNECTS_TO`** | `Intersection` $\rightarrow$ `Intersection` | `edge_id` (`E_01..E_37`), `road_name`, `highway`, `lanes`, `length_m`, `oneway`, `maxspeed_kmh`, `base_time_s`, `effective_cost` | Lưu thông hợp lệ theo chiều đường một chiều/hai chiều thực tế từ OSMnx |
| **`PRONE_TO_FLOOD`** | `Intersection` $\rightarrow$ `FloodHotspot` | `risk_weight` (float) | Đánh dấu nút giao nằm trong vùng trũng ngập khi mưa lớn/triều cường |
| **`AFFECTED_BY_WEATHER`** | `FloodHotspot` $\rightarrow$ `WeatherCondition` | `trigger_rule` (str) | Kích hoạt trạng thái ngập khi `rain_mm_h > 30.0` hoặc (`rain_mm_h > 15.0` & `tide_level_m >= 1.50`) |

---

## 4. Quy tắc tính trọng số động & Khuyến nghị lộ trình né kẹt

Khi tìm đường từ `origin` $\rightarrow$ `destination` (ví dụ `HX_05` $\rightarrow$ `HX_15` hoặc `HX_02` $\rightarrow$ `HX_18`), chi phí mỗi cạnh `CONNECTS_TO` $(u \rightarrow v)$ được tính:

$$\text{effective\_cost}(u, v) = \text{base\_time\_s}(u, v) \times \alpha_{\text{congestion}}(v) \times \beta_{\text{flood}}(u, v)$$

Trong đó:
* $\text{base\_time\_s} = \frac{\text{length\_m}}{\text{maxspeed\_kmh} / 3.6}$ (mặc định `40 km/h` nếu `maxspeed` trống).
* $\alpha_{\text{congestion}}(v)$: `1.0` (lớp `0` Thông thoáng), `2.2` (lớp `1` Ùn ứ), `6.0` (lớp `2` Kẹt xe nghiêm trọng).
* $\beta_{\text{flood}}(u, v)$: `1.0` nếu bình thường; `4.5` nếu `u` hoặc `v` nối tới `FloodHotspot` đang kích hoạt ngập (`is_flooded=True`).

Nhờ hàm phạt này, khi mưa $>30\text{ mm/h}$ làm ngập/kẹt **Ngã tư Hàng Xanh (`HX_01`)**, **Đinh Bộ Lĩnh (`HX_03`, `HX_04`, `HX_14`)** hoặc **Xô Viết Nghệ Tĩnh (`HX_11`, `HX_18`)**, thuật toán định tuyến trên KG tự động né vùng lõi ngập/kẹt và ưu tiên trục **Nguyễn Gia Trí / D2 (`HX_07` $\leftrightarrow$ `HX_10` $\leftrightarrow$ `HX_15`)** hoặc nhánh ít ảnh hưởng hơn.

---

## 5. Giao diện hàm sẵn sàng cho AI Agent (Tuần 6)

* `build_hang_xanh_kg(nodes_csv, edges_csv) -> nx.MultiDiGraph`
* `update_environment_state(G, rain_mm_h, tide_level_m, congestion_by_node=None, timestamp="mock")`
* `recommend_avoidance_routes(G, origin, destination, top_k=2) -> dict`
* `query_node_context(G, node_code) -> dict`
