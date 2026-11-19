# 01_data_sample — Đồ thị mạng lưới đường, Thời tiết & Dữ liệu mẫu

* **Phụ trách chính:** Trần Hoàng Hôn (`[H3]`), Phạm Thành Trung (`[T1]`, `[T2]`), Vũ Văn Duy (`[D1]`)
* **Sản phẩm dự kiến:**
  * `extract_hang_xanh_graph.py` $\rightarrow$ `nodes.csv` (`15–25` nút), `edges.csv`, `adjacency_matrix.csv`, `hang_xanh.graphml`
  * `fetch_open_meteo_sample.py` $\rightarrow$ `open_meteo_sample.csv` (`[T1]`, hourly historical sample, local `UTC+7`)
  * `phu_an_tide_reference.csv` (`[T1]`, published high/low-water forecast extrema with source bulletin and issue date)
  * `build_mock_hang_xanh_dataset.py` $\rightarrow$ `mock_hang_xanh_traffic_weather.csv` (`[T2]`, deterministic 15-minute scenario data)
  * `build_gis_check_map.py` $\rightarrow$ `hang_xanh_gis_check.html` + `gis_check_notes.md` (`[D1]`)
  * Bộ dữ liệu sạch Tuần 5 (nhánh đối chứng `METR-LA` & kịch bản Hàng Xanh)

## Dữ liệu của Phạm Thành Trung (`[T1]`, `[T2]`)

- `open_meteo_sample.csv` có 72 quan sát theo giờ từ `2026-11-05 00:00` đến `2026-11-07 23:00`, lấy tại tọa độ tâm Hàng Xanh bằng Open-Meteo Historical Weather API. Đây là dữ liệu lịch sử dạng tái phân tích/lưới, không phải máy đo tại từng nút đường. Các cột giữ tên API (`time`, `temperature_2m`, `relative_humidity_2m`, `precipitation`); thời gian là giờ địa phương `Asia/Ho_Chi_Minh`.
- `phu_an_tide_reference.csv` ghi các cực trị triều dự báo (đỉnh/chân) cho 04–07/11/2026 trong bản tin số 307/2026 phát ngày 03/11. Các đỉnh ngày 05–07/11 vượt báo động I và II, để kiểm tra biến `tide_alert`. Đây là mực nước dự báo tại trạm Phú An, không phải số đo thực địa hay độ sâu ngập từng tuyến; trong mock nó chỉ là biến bối cảnh chung cho cụm Hàng Xanh. Dataset nội suy cosine giữa các cực trị để tạo `tide_level_m` mỗi 15 phút.
- `mock_hang_xanh_traffic_weather.csv` có 4.640 dòng, 20 nút và 232 mốc thời gian liên tục 15 phút (`2026-11-05 01:00`–`2026-11-07 10:45`). Bốn bước đầu bị loại vì chưa đủ lag 60 phút và bốn bước cuối thiếu nhãn t+60. Dataset được sinh lặp lại với seed cố định, dùng đồ thị OSMnx, thời tiết API và lịch triều đã nêu. Giao thông là **mô phỏng**, không phải tốc độ/lưu lượng đo thật.
- Các khoảng mưa `rain_mm_h > 30` được chèn có chủ đích thành sáu kịch bản stress-test, mỗi đợt 3 giờ (18/60 giờ của cửa sổ mô phỏng). Cột `rain_scenario_synthetic` chỉ là cờ provenance, không phải đặc trưng mô hình. Tần suất này được thiết kế để kiểm tra pipeline, không đại diện tần suất thời tiết thật; không diễn giải metric trên bộ mock là hiệu năng ngoài đời.
- Tạo lại mock đúng theo các snapshot đã lưu: `python 01_data_sample/build_mock_hang_xanh_dataset.py`. Có thể gọi `fetch_open_meteo_sample.py` để tải lại API; Open-Meteo có thể cập nhật bản tái phân tích, nên CSV hiện có được giữ trong repo làm snapshot của lần chạy này. Tide extrema được giữ kèm URL bản tin trong CSV để truy nguyên.

