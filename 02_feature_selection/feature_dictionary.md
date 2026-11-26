# DATA CONTRACT & TỪ ĐIỂN ĐẶC TRƯNG (`FEATURE DICTIONARY`) — `[K1]`

> **Phụ trách:** Nguyễn Duy Khang (`26410055`) · **Trạng thái:** Bản nháp v0.1 (16/11/2026) — Trung đã chốt tên cột thời tiết và đối chiếu ngưỡng triều ngày 18/11/2026
> **Người dùng tài liệu:** Trung (`[T2]` sinh mock, `[T3]` mock ML pipeline) · Khang (`[K2]` Feature Selection) · Duy (`[D2]` SHAP trên tên biến gốc)
> **Nguồn đầu vào:** [`01_data_sample/nodes.csv`](../01_data_sample/nodes.csv), [`01_data_sample/edges.csv`](../01_data_sample/edges.csv) (`[H3]`) · `open_meteo_sample.csv`, `phu_an_tide_reference.csv` (`[T1]`) · Nội dung 2 trong [Đề cương](../De_Cuong_Chi_Tiet_Do_An_May_Hoc_Nang_Cao.md#L126-L129)

---

## I. QUY ƯỚC CHUNG CỦA BẢNG DỮ LIỆU

| Hạng mục | Quy ước |
| :--- | :--- |
| **File đích (mock)** | `01_data_sample/mock_hang_xanh_traffic_weather.csv` |
| **Đơn vị 1 dòng (grain)** | 1 cặp (`timestamp`, `node_id`) = trạng thái của 1 nút giao trong 1 bước `15'` |
| **Khóa chính** | (`timestamp`, `node_id`) — không trùng lặp |
| **Lưới thời gian** | Đủ **mọi** nút × **mọi** bước `15'` liên tục, không thiếu bước (các phép `shift` lag/nhãn dựa trên giả định này) |
| **Thứ tự dòng** | Sắp theo `timestamp` rồi `node_id` tăng dần |
| **Múi giờ** | Giờ địa phương `UTC+7`, lưu dạng *naive* `YYYY-MM-DD HH:MM:SS` (không ghi hậu tố múi giờ) |
| **Định dạng file** | CSV, phân tách `,`, mã hóa `UTF-8`, dấu thập phân `.` |
| **Kiểu boolean** | Lưu `0`/`1` (số nguyên), **không** dùng `True`/`False` |
| **Giá trị thiếu** | Nhãn `y_*` **không được** thiếu. Các dòng cuối chuỗi không đủ tương lai để gán nhãn (thiếu `t+60'`) và các dòng đầu chuỗi chưa đủ lag thì **bỏ hẳn**, không điền giá trị |
| **Tên cột** | `snake_case` tiếng Anh, không dấu, có hậu tố đơn vị khi cần (`_kmh`, `_mm_h`, `_m`, `_pct`) |

---

## II. CỘT KHÓA & CỘT KHÔNG DÙNG LÀM ĐẶC TRƯNG

| Cột | Kiểu | Mô tả | Ghi chú |
| :--- | :--- | :--- | :--- |
| `timestamp` | datetime | Mốc đầu của bước `15'` | Dùng để chia `TimeSeriesSplit` theo **mốc duy nhất** (`[T3]`) |
| `node_id` | int (`1–20`) | Khớp `node_id` trong `nodes.csv` | **Không** đưa vào mô hình: với 20 nút, cột này đóng vai trò định danh nên mô hình sẽ học thuộc lòng |
| `rain_scenario_synthetic` | int `0/1` | Cờ do `build_mock_hang_xanh_dataset.py` (`[T2]`) gắn cho các bước có kịch bản mưa giả lập | **Chỉ có trong mock, không phải đặc trưng.** Cờ này cho biết trực tiếp cách dữ liệu được sinh ra, đưa vào mô hình sẽ gây rò rỉ |

> `node_code`, `lat`, `lon`, `utm_x`, `utm_y`, `roads` trong `nodes.csv` **không** đưa vào bảng đặc trưng vì cùng lý do định danh. Bản đồ GIS (`[D1]`) và KG (`[S2]`) sẽ join lại các cột này qua `node_id` khi cần.

---

## III. NHÃN DỰ BÁO (3 LỚP × 3 MỐC THỜI GIAN)

### 1. Mức ùn tắc tại một thời điểm

Tỉ lệ vận tốc so với vận tốc dòng tự do của nút:

$$\text{speed\_ratio}_{v,t} = \frac{\text{speed\_kmh}_{v,t}}{\text{free\_flow\_kmh}_v}$$

| Lớp | Tên | Điều kiện | Quy đổi khi `free_flow_kmh = 35` |
| :---: | :--- | :--- | :--- |
| `0` | Thông thoáng | `speed_ratio ≥ 0.6` | `≥ 21 km/h` |
| `1` | Ùn ứ | `0.3 ≤ speed_ratio < 0.6` | `10.5 – 21 km/h` |
| `2` | Kẹt xe nghiêm trọng | `speed_ratio < 0.3` | `< 10.5 km/h` |

*Lý do dùng tỉ lệ thay vì ngưỡng tuyệt đối:* cùng một quy tắc áp được cho cả nhánh Hàng Xanh (`~35 km/h`) lẫn nhánh `METR-LA` (cao tốc `~100 km/h`). Ngưỡng lớp `2` khớp với mô tả trong Đề cương: vận tốc tụt *"từ 35 km/h xuống dưới 8 km/h"* khi mưa ngập.

### 2. Ba cột nhãn

| Cột | Kiểu | Định nghĩa |
| :--- | :--- | :--- |
| `y_t15` | int `{0,1,2}` | Lớp ùn tắc của **cùng nút** `v` tại `t + 15'` (dịch `−1` bước) |
| `y_t30` | int `{0,1,2}` | Lớp ùn tắc tại `t + 30'` (dịch `−2` bước) |
| `y_t60` | int `{0,1,2}` | Lớp ùn tắc tại `t + 60'` (dịch `−4` bước) |

**Ràng buộc với mock dataset `[T2]`:** lớp `2` chiếm khoảng `5–15%` số dòng. Phải có kịch bản mưa `> 30 mm/h` rải đều theo thời gian, để **mọi fold** `TimeSeriesSplit` đều có đủ cả 3 lớp ở cả 3 cột nhãn.

---

## IV. TỪ ĐIỂN ĐẶC TRƯNG

Cột **Nhánh lọc** cho biết đặc trưng đi vào nhánh nào của pipeline `[K2]` (chi tiết ở Mục V): **SỐ** = nhánh số · **ORD** = *Ordinal* · **NOM** = *Nominal*.

### 1. Giao thông động (thay đổi theo `timestamp`)

| Cột | Kiểu | Đơn vị | Mô tả / Công thức | Nhánh lọc |
| :--- | :--- | :--- | :--- | :---: |
| `speed_kmh` | float | km/h | Vận tốc trung bình tại nút `v` trong bước `t` (Hàng Xanh: mô phỏng; `METR-LA`: đo thật) | SỐ |
| `volume_veh` | int | xe/15' | Lưu lượng xe qua nút trong bước `t` | SỐ |
| `speed_ratio` | float | — | `speed_kmh / free_flow_kmh` (Mục III.1) | SỐ |
| `speed_lag1` | float | km/h | `speed_kmh` tại `t − 15'` | SỐ |
| `speed_lag2` | float | km/h | `speed_kmh` tại `t − 30'` | SỐ |
| `speed_lag4` | float | km/h | `speed_kmh` tại `t − 60'` | SỐ |
| `speed_delta1` | float | km/h | `speed_kmh − speed_lag1` (âm nghĩa là đang giảm tốc) | SỐ |
| `upstream_speed_min` | float | km/h | Vận tốc **nhỏ nhất** trong số các nút nguồn `u` có cạnh `u → v` (theo `edges.csv`) tại `t`. Đặc trưng chính mô tả **sóng lan truyền** | SỐ |
| `upstream_congested_cnt` | int | nút | Số nút nguồn `u → v` đang ở lớp `2` (`speed_ratio < 0.3`) tại `t` | SỐ |

> **Nút không có nút nguồn** (hiện tại: `node_id = 14`, `in_degree = 0`): gán `upstream_speed_min = free_flow_kmh` của chính nút đó và `upstream_congested_cnt = 0`.

### 2. Thời tiết (`Open-Meteo`, theo giờ → bước `15'`)

| Cột | Kiểu | Đơn vị | Mô tả | Nhánh lọc |
| :--- | :--- | :--- | :--- | :---: |
| `rain_mm_h` | float | mm/h | Cường độ mưa: lượng mưa của **giờ gần nhất đã kết thúc** (`precipitation` của Open-Meteo) | SỐ |
| `rain_cum_3h_mm` | float | mm | Tổng mưa 3 giờ gần nhất (thể hiện độ ngấm/ngập tích lũy) | SỐ |
| `temperature_c` | float | °C | `temperature_2m` | SỐ |
| `humidity_pct` | float | % | `relative_humidity_2m` | SỐ |

**Quy tắc chuyển `1h → 15'`: ghép theo mốc gần nhất trong quá khứ** (`pd.merge_asof(direction="backward")`, tức *forward-fill*). Các bước `14:00`, `14:15`, `14:30`, `14:45` đều nhận bản ghi Open-Meteo mốc `14:00`.

* **Không chia lượng mưa cho 4.** `rain_mm_h` luôn là **cường độ** mm/h, nhờ vậy ngưỡng `30 mm/h` có cùng một nghĩa ở mọi chỗ.
* **Không dùng nội suy tuyến tính.** Nội suy giữa `14:00` và `15:00` để lấy giá trị `14:15` sẽ dùng số liệu của `15:00`, tức là thông tin tương lai bị lộ vào đặc trưng (*look-ahead leakage*).
* Open-Meteo ghi `precipitation` tại mốc `HH:00` là **tổng mưa của giờ trước đó**. Vì vậy giá trị nhận được ở `14:15` là mưa trong khoảng `13:00–14:00`: đã xảy ra, không rò rỉ.

### 3. Triều cường (trạm Phú An)

| Cột | Kiểu | Đơn vị | Mô tả | Nhánh lọc |
| :--- | :--- | :--- | :--- | :---: |
| `tide_level_m` | float | m | Mực nước trạm Phú An tại `t` | SỐ |

**Quy tắc `→ 15'`:** từ bảng đỉnh/chân triều của `[T1]`, nội suy dạng **cosine** giữa hai cực trị liên tiếp (đường cong triều có dạng hình sin). Ở đây nội suy **được phép dùng mốc tương lai**, vì lịch triều là dự báo thiên văn được công bố trước, nên không tính là rò rỉ dữ liệu.

### 4. Thời gian

| Cột | Kiểu | Giá trị | Mô tả | Nhánh lọc |
| :--- | :--- | :--- | :--- | :---: |
| `hour_sin`, `hour_cos` | float | `[-1, 1]` | `sin/cos(2π · phút_trong_ngày / 1440)`: mã hóa vòng, để `23:45` nằm sát `00:00` | SỐ |
| `time_slot` | int | `0, 1, 2` | `0` = đêm (`22:00–05:59`) · `1` = bình thường · `2` = cao điểm (`06:30–08:59`, `16:30–18:59`) | ORD |
| `is_weekend` | int | `0/1` | `1` nếu Thứ Bảy hoặc Chủ Nhật | NOM |

### 5. Phân loại theo thời tiết/triều (dẫn xuất từ cột số)

| Cột | Kiểu | Giá trị | Ngưỡng | Nhánh lọc |
| :--- | :--- | :--- | :--- | :---: |
| `rain_level` | int | `0–4` | `0`: `< 0.1` · `1`: `0.1–2.5` · `2`: `2.5–10` · `3`: `10–30` · `4`: `> 30 mm/h` (**kịch bản ngập**) | ORD |
| `tide_alert` | int | `0–3` | `0`: `< BĐ1` · `1`: `≥ BĐ1` · `2`: `≥ BĐ2` · `3`: `≥ BĐ3` (bản tin Đài KTTV Nam Bộ dùng các ngưỡng tham chiếu `1.40 / 1.50 / 1.60 m`; Trung đã đối chiếu bản tin triều tháng 11/2026) | ORD |

### 6. Thuộc tính tĩnh của nút (từ `nodes.csv`, `edges.csv`; không đổi theo thời gian)

| Cột | Kiểu | Đơn vị | Cách tính | Nhánh lọc |
| :--- | :--- | :--- | :--- | :---: |
| `free_flow_kmh` | float | km/h | Vận tốc dòng tự do của nút. **Mock:** Trung đặt cho từng nút (gợi ý `30–45 km/h`, trục `trunk` cao hơn). **`METR-LA`:** phân vị 85 của `speed_kmh` từng cảm biến, chỉ tính trên phần dữ liệu train | SỐ |
| `lanes_in_mean` | float | làn | Trung bình `lanes` của các cạnh đi vào `v` (nút `14` dùng cạnh đi ra) | SỐ |
| `maxspeed_in_kmh` | float | km/h | Trung bình `maxspeed` của các cạnh đi vào `v` (nút `14` dùng cạnh đi ra) | SỐ |
| `in_degree`, `out_degree` | int | cạnh | Lấy nguyên từ `nodes.csv` | SỐ |
| `dist_center_m` | float | m | Khoảng cách tới tâm ngã tư Hàng Xanh, lấy từ `nodes.csv` | SỐ |
| `road_type` | str | `trunk`, `primary`, `secondary`, `tertiary` | **Cấp đường cao nhất** trong `highway_classes` của nút (thứ tự ưu tiên `trunk > primary > secondary > tertiary`). Ví dụ: `"tertiary \| trunk"` → `trunk` | NOM |
| `has_twoway` | int | `0/1` | `1` nếu nút có ít nhất 1 cạnh nối vào hoặc ra với `oneway = False` | NOM |
| `flood_prone` | int | `0/1` | *(Bổ sung Tuần 6, `[K1]`)* `1` nếu nút thuộc vùng trũng ngập Đinh Bộ Lĩnh, Ung Văn Khiêm, Cầu Sơn / Xô Viết Nghệ Tĩnh (cột `flood_prone` trong `nodes.csv` do `[H1]` gắn, commit `fe4191c`; hiện là nút `3, 4, 11, 14, 15, 18`). Mock dataset chưa có cột này: `load_dataset()` trong `01_feature_selection_pipeline.py` tự ghép theo `node_id`. `METR-LA` không có thông tin ngập nên gán `0` | NOM |

> **Về `oneway`:** đây là thuộc tính của **cạnh**, trong khi bảng dữ liệu tính theo **nút**, nên được quy về cột `has_twoway`. Hiện `34/37` cạnh là một chiều, nên cột này có thể gần như hằng số. Nếu vậy, `VarianceThreshold` sẽ tự loại nó. Đây là hành vi mong muốn, không phải lỗi.

---

## V. ÁNH XẠ NHÓM BIẾN → KỸ THUẬT LỌC (ĐẦU VÀO CHO `[K2]`)

| Nhánh | Cột | Mã hóa | Kỹ thuật lọc | Ngưỡng |
| :--- | :--- | :--- | :--- | :--- |
| **SỐ** | 22 cột đánh dấu SỐ | `MinMaxScaler` (chỉ để lọc phương sai) | `VarianceThreshold` | `0.01` trên dữ liệu đã MinMax |
| | | — | `Pearson r` **chỉ để tham khảo**: (a) tương quan với từng nhãn; (b) cặp đặc trưng có `\|r\| ≥ 0.9` được gắn cờ dư thừa | **Không lọc cứng** (xem Mục VII.3) |
| **ORD** | `time_slot`, `rain_level`, `tide_alert` | Đã là số nguyên có thứ tự (`OrdinalEncoder` với `categories` cố định) | $\chi^2$ với từng nhãn | Giữ nếu $\chi^2 > 5.99$ ($\alpha = 0.05$, $df = 3 - 1 = 2$) |
| **NOM** | `road_type`, `is_weekend`, `has_twoway`, `flood_prone` | `OneHotEncoder(handle_unknown="ignore", drop="if_binary")` | $\chi^2$ với từng nhãn, tính trên từng cột dummy | Giữ nếu $\chi^2 > 5.99$ |
| **PCA (đối chứng)** | Các cột SỐ còn lại sau `VarianceThreshold` | `StandardScaler` | `PCA` giữ `95%` phương sai | **Nhánh riêng**, chỉ để so sánh. **Không** đưa vào mô hình cây chính hay SHAP |

**Quy tắc bắt buộc của pipeline:**

1. **Chống rò rỉ dữ liệu (`Data Leakage`):** mọi bước `fit` (scaler, `VarianceThreshold`, $\chi^2$, `PCA`) chỉ được fit trên phần **train của từng fold**, rồi mới `transform` tập validation.
2. **Lọc riêng cho từng mốc dự báo:** chạy $\chi^2$ và Pearson riêng cho `y_t15`, `y_t30`, `y_t60`. Tập đặc trưng được chọn có thể khác nhau giữa 3 mốc.
3. **Giữ nguyên tên biến gốc:** đầu ra nhánh chính phải giữ tên cột như trong từ điển này (sau One-Hot có dạng `road_type_trunk`, ...) để Duy chạy `shap.TreeExplainer` trong `[D2]`.

---

## VI. HƯỚNG DẪN TÍNH CỘT DẪN XUẤT (THAM KHẢO CHO `[T2]`)

Giả định mock đã có các cột thô: `timestamp`, `node_id`, `speed_kmh`, `volume_veh`, `free_flow_kmh`. Tên cột của file Open-Meteo được giả định theo API; sửa lại sau khi `[T1]` chốt.

```python
import numpy as np
import pandas as pd

# --- Thời tiết: hourly -> 15' bằng ghép theo mốc quá khứ (không nội suy tuyến tính) ---
w = pd.read_csv("01_data_sample/open_meteo_sample.csv", parse_dates=["time"]).sort_values("time")
w["rain_cum_3h_mm"] = w["precipitation"].rolling(3, min_periods=1).sum()
w = w.rename(columns={"precipitation": "rain_mm_h", "temperature_2m": "temperature_c",
                      "relative_humidity_2m": "humidity_pct"})
df = pd.merge_asof(df.sort_values("timestamp"), w, left_on="timestamp", right_on="time",
                   direction="backward").drop(columns="time")

# --- Lag & nhãn: theo từng nút, dựa trên lưới 15' liên tục ---
df = df.sort_values(["node_id", "timestamp"])
df["speed_ratio"] = df["speed_kmh"] / df["free_flow_kmh"]
g = df.groupby("node_id", sort=False)["speed_kmh"]
for k in (1, 2, 4):
    df[f"speed_lag{k}"] = g.shift(k)
df["speed_delta1"] = df["speed_kmh"] - df["speed_lag1"]

def to_class(ratio: pd.Series) -> pd.Series:
    cls = pd.Series(np.select([ratio < 0.3, ratio < 0.6], [2, 1], 0), index=ratio.index)
    return cls.where(ratio.notna())

for k, h in ((1, 15), (2, 30), (4, 60)):
    df[f"y_t{h}"] = to_class(g.shift(-k) / df["free_flow_kmh"])

# --- Lan truyền từ nút nguồn u -> v ---
e = pd.read_csv("01_data_sample/edges.csv")[["u", "v"]].drop_duplicates()
up = e.merge(df[["timestamp", "node_id", "speed_kmh", "speed_ratio"]], left_on="u", right_on="node_id")
agg = up.groupby(["v", "timestamp"]).agg(
    upstream_speed_min=("speed_kmh", "min"),
    upstream_congested_cnt=("speed_ratio", lambda s: int((s < 0.3).sum())),
)
df = df.merge(agg, left_on=["node_id", "timestamp"], right_index=True, how="left")
df["upstream_speed_min"] = df["upstream_speed_min"].fillna(df["free_flow_kmh"])  # nút 14
df["upstream_congested_cnt"] = df["upstream_congested_cnt"].fillna(0).astype(int)

# --- Bỏ dòng thiếu lag/nhãn ở hai đầu chuỗi, ép kiểu nhãn ---
label_cols = ["y_t15", "y_t30", "y_t60"]
df = df.dropna(subset=["speed_lag4", *label_cols])
df[label_cols] = df[label_cols].astype(int)
df = df.sort_values(["timestamp", "node_id"]).reset_index(drop=True)
```

---

## VII. CÁC ĐIỂM CẦN CHỐT

| # | Nội dung | Người chốt | Đề xuất hiện tại |
| :---: | :--- | :--- | :--- |
| 1 | Tên cột và mốc thời gian trong `open_meteo_sample.csv` (`time`, `precipitation`, `temperature_2m`, `relative_humidity_2m`?) | **Trung** (`[T1]`) | Giữ đúng tên của API Open-Meteo, đổi tên khi ghép (Mục VI) |
| 2 | Đơn vị và mốc chuẩn của `tide_level`; ngưỡng báo động BĐ1/BĐ2/BĐ3 trạm Phú An | **Trung** (`[T1]`) | Mét; bản tin Đài KTTV Nam Bộ tháng 11/2026 nêu `1.40 / 1.50 / 1.60 m` ([bản tin số 307/2026](https://www.phongchonglutbaotphcm.gov.vn/phocadownload/2026/11-2026/HCMC_TVHN_20261103.pdf)). Mực nước trong tệp nguồn là dự báo cực trị, không phải số đo. |
| 3 | **Mâu thuẫn quy tắc Pearson:** [Đề cương dòng 128](../De_Cuong_Chi_Tiet_Do_An_May_Hoc_Nang_Cao.md#L128) ghi *"lọc các biến `\|r\| ≥ 0.5`"*, còn [Kế hoạch Tuần 4](../Ke_Hoach_Thuc_Hien_Tuan_4.md) ghi *"chỉ tham khảo, không lọc cứng"* | **Cả nhóm** (`[H5]`) | Theo Kế hoạch Tuần 4. Pearson chỉ đo quan hệ **tuyến tính**, trong khi tác động của mưa và triều là **phi tuyến** (theo chính Đề cương). Lọc cứng có thể loại mất `rain_mm_h` và `tide_level_m`, là hai biến trung tâm của đề tài và của phần giải thích SHAP. Báo cáo sẽ trình bày bảng Pearson như một phân tích, không dùng làm bộ lọc |
| 4 | Ngưỡng nhãn `0.6 / 0.3` và `free_flow_kmh` mỗi nút trong mock | **Trung** + **Khang** | Như Mục III; điều chỉnh nếu tỉ lệ lớp `2` lệch khỏi khoảng `5–15%` |
| 5 | Quy tắc lấy `road_type` cho nút có nhiều cấp đường | **Hôn** (`[H3]`) | Lấy cấp cao nhất (Mục IV.6) |
| 6 | *(Tuần 6)* Giá trị `flood_prone` cho nhánh `METR-LA` (cao tốc Los Angeles, không có dữ liệu vùng ngập) | **Trung** (`[T1]`) + **Khang** | Gán `0` cho mọi cảm biến. Khi đó cột là hằng số nên pipeline tự loại ($\chi^2 = 0$), và hai nhánh vẫn dùng chung một schema |
| 7 | *(Tuần 6)* Mục tiêu "giảm ≥ 40% số chiều" (Kế hoạch Tuần 5, `[K2]`) | **Cả nhóm** (`[H2]`) | Trên mock, chỉ nhánh PCA đạt (40,6%); tập giữ tên gốc `selected_compact` giảm 15,6%. Đề xuất báo cáo cả hai con số và **không** ép giảm thêm, vì muốn giảm thêm thì phải bỏ biến mưa/triều (trái Mục VII.3). Chạy lại khi có dữ liệu `[T1]` |
| 8 | *(Tuần 6)* Cách đọc bảng xếp hạng Mutual Information | **Duy** (`[D2]`) + **Khang** | MI của `tide_level_m`, `humidity_pct`, `temperature_c` bị **thổi phồng** trên mock: các biến này chung cho cả 20 nút tại mỗi mốc, mà chuỗi chỉ dài 232 mốc (~2,4 ngày), nên mang luôn nhịp giờ cao điểm. **Không** dùng hạng MI để kết luận tác động của triều; kết luận dựa trên SHAP và kiểm tra lại với dữ liệu dài hơn |
