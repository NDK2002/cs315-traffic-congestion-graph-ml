# PHÂN TÍCH SHAP TÁC ĐỘNG CỦA MƯA & TRIỀU CƯỜNG — TUẦN 6

> **Phụ trách:** Vũ Văn Duy (`26410031`) · **Ngày chạy:** 24/11/2026
> **Đầu vào:** `01_data_sample/mock_hang_xanh_traffic_weather.csv` (`[T2]`), cấu hình model trong `mock_ml_pipeline.py` (`[T3]`)
> **Sản phẩm:** `shap_analysis.py` → `results/shap/` (Summary Plot, Dependence Plot, Force Plot, bảng CSV)

**Cách chạy:**

```bash
python 03_models_evaluation/shap_analysis.py                      # LightGBM, Force Plot cho nút 1, 4, 13
python 03_models_evaluation/shap_analysis.py --model RandomForest --nodes 1 4 13 --out-dir /tmp/shap_rf
```

---

## I. CÁCH LÀM

* **Model:** `LightGBM` (`class_weight='balanced'`), dùng lại đúng danh sách đặc trưng và `Pipeline` One-Hot của `[T3]`. Chọn `LightGBM` vì F1 lớp `2` cao nhất ở `t+15'` và `t+30'` theo `results/mock_cv_summary.csv`.
* **Chia dữ liệu theo thời gian:** `185` mốc đầu để huấn luyện. Bỏ một khoảng `gap` bằng số bước dự báo. `43–46` mốc cuối dùng để giải thích, model không thấy phần này khi học. Phần giải thích có `1` cơn mưa lớn giả lập (`12` mốc × `20` nút = `240` dòng).
* **SHAP:** `shap.TreeExplainer` cho lớp `2` (kẹt nghiêm trọng). Với `LightGBM`, SHAP tính theo đơn vị log-odds.
* **Nhóm biến:** cộng SHAP của các biến cùng nhóm trên từng dòng, rồi lấy trung bình trị tuyệt đối. Lý do: 3 biến mưa (`rain_mm_h`, `rain_cum_3h_mm`, `rain_level`) liên quan chặt với nhau. Xét lẻ từng biến thì phần đóng góp của mưa bị chia nhỏ và trông như không quan trọng.

---

## II. KẾT QUẢ TRÊN MOCK (`LightGBM`, % tổng đóng góp cho lớp 2)

| Nhóm biến | `t+15'` | `t+30'` | `t+60'` |
| :--- | ---: | ---: | ---: |
| Giao thông hiện tại & quá khứ | `65.1%` | `63.9%` | `72.4%` |
| **Mưa** | **`32.9%`** | **`34.0%`** | **`25.1%`** |
| Thuộc tính tĩnh của nút | `1.6%` | `1.8%` | `2.3%` |
| Lan truyền từ nút nguồn | `0.1%` | `0.1%` | `0.1%` |
| **Triều cường** | **`0.0%`** | **`0.0%`** | **`0.1%`** |
| Thời gian, thời tiết khác | `≤ 0.2%` | `≤ 0.1%` | `≤ 0.1%` |

* Chạy lại với `RandomForest` cho cùng thứ hạng: giao thông hiện tại đứng đầu (`58–67%`), mưa thứ hai (`15–24%`), triều `1–3%`.
* So với cách đoán đơn giản "kẹt bây giờ thì lát nữa vẫn kẹt" (giữ nguyên lớp hiện tại), trên phần dữ liệu giải thích:

| Mốc | F1 lớp 2 — `LightGBM` | F1 lớp 2 — giữ nguyên hiện tại |
| :--- | ---: | ---: |
| `t+15'` | `1.00` | `0.88` |
| `t+30'` | `1.00` | `0.75` |
| `t+60'` | `1.00` | `0.50` |

  Model hơn rõ khi dự báo xa, và phần hơn này đến từ biến mưa. Lưu ý: phần giải thích chỉ có `1` cơn mưa, nên con số `1.00` chưa có ý nghĩa thống kê.

---

## III. ĐỌC KẾT QUẢ

1. **Model dựa nhiều nhất vào trạng thái hiện tại** (`speed_ratio`): nút đang kẹt thì 15 phút sau khả năng cao vẫn kẹt.
2. **Mưa được đo qua `rain_cum_3h_mm`, còn `rain_mm_h` gần như bằng 0.**
   * Trong mock, `rain_mm_h` chỉ có 2 mức (gần `0` hoặc `36 mm/h`). `rain_cum_3h_mm` tăng thêm `9 mm` sau mỗi bước 15 phút mưa, nên thể hiện được **mưa đã kéo dài bao lâu**.
   * Kiểm tra tại `HX_04` (Đinh Bộ Lĩnh): lớp `2` bắt đầu đúng lúc `rain_cum_3h_mm = 36`, tức đã mưa đủ 1 giờ. Đây chính là quy tắc trong `build_mock_hang_xanh_dataset.py` (nút dễ ngập kẹt nặng khi `_storm_age ≥ 4`).
   * Sau khi tạnh mưa, `rain_cum_3h_mm` vẫn cao thêm 3 giờ nhưng giao thông trong mock hồi phục ngay. Vì vậy trên Summary Plot có các điểm `rain_cum_3h_mm` cao mà SHAP âm.
3. **Triều cường và lan truyền từ nút nguồn gần như không đóng góp.** Trong mock, hiệu ứng triều chỉ `0.07` trên mỗi mét vượt `1.1 m`, hiệu ứng lan truyền tối đa `0.1`. Cả hai quá nhỏ để đẩy một nút sang lớp `2`.
4. **Force Plot cùng thời điểm mưa lớn (07/11 04:15, `t+15'`):**
   * `HX_04` (Đinh Bộ Lĩnh, đoạn dễ ngập): dự báo lớp `2`, đúng thực tế. Lực đẩy chính là `speed_ratio = 0.42` và `rain_cum_3h_mm = 36`.
   * `HX_13` (Bạch Đằng): cùng lúc vẫn dự báo lớp `0`, đúng thực tế. `speed_ratio = 0.72` kéo dự báo xuống mạnh hơn phần đẩy lên của mưa.

---

## IV. GIỚI HẠN CẦN NÓI RÕ TRONG BÁO CÁO

* **SHAP trên mock chỉ cho thấy model học lại đúng quy tắc của script sinh dữ liệu.** Đây là bằng chứng pipeline và phần giải thích hoạt động đúng, **không phải** kết luận về giao thông Hàng Xanh thật.
* **Chưa chỉ ra được "ngưỡng mưa mm/h bắt đầu kích hoạt sóng ùn tắc"** (Kết quả dự kiến trong Đề cương), vì mock chỉ có 2 mức mưa. Dependence Plot của `rain_mm_h` chỉ có 2 cụm điểm.
* `METR-LA` không có dữ liệu thời tiết, nên phân tích mưa/triều chỉ làm được trên nhánh Hàng Xanh.

---

## V. ĐỀ XUẤT CHO BUỔI SYNC

| # | Nội dung | Người liên quan |
| :---: | :--- | :--- |
| 1 | Mock cần nhiều mức mưa (ví dụ `5 / 15 / 30 / 50 mm/h`) để Dependence Plot tìm được ngưỡng mưa. Giao thông nên hồi phục chậm sau mưa (nước rút) cho gần thực tế hơn | Trung (`[T2]`) |
| 2 | Muốn SHAP đo được triều cường và lan truyền thì hiệu ứng của chúng trong mock phải đủ lớn để có lúc gây kẹt nặng | Trung (`[T2]`) |
| 3 | Mock có cột `flood_susceptible` nội bộ nhưng không xuất ra. Feature dictionary vẫn chưa có biến ngập. Nên đưa vào làm đặc trưng tĩnh của nút để SHAP đo được tác động của "ngập" | Khang (`[K1]`), Trung |
| 4 | Model `[T3]` đang dùng đủ `31` biến, chưa dùng tập đã lọc của `[K2]` (ví dụ `t+15'` bỏ `speed_delta1`, `is_weekend_1`). Cần chốt tập biến cho model cuối, rồi chạy lại `shap_analysis.py` | Khang, Trung |
| 5 | Nên báo cáo thêm cách đoán "giữ nguyên trạng thái hiện tại" làm mốc so sánh, để thấy model hơn bao nhiêu (Mục II) | Trung |
