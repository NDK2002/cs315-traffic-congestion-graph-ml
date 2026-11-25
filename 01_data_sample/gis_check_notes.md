# GHI CHÚ KIỂM TRA TỌA ĐỘ & CHIỀU ĐƯỜNG CỤM HÀNG XANH — `[D1]`

> **Phụ trách:** Vũ Văn Duy (`26410031`) · **Ngày kiểm:** 18/11/2026
> **Đầu vào:** `nodes.csv`, `edges.csv` của `[H3]` (commit `57dc344`)
> **Sản phẩm:** `build_gis_check_map.py` → `hang_xanh_gis_check.html`

**Cách chạy:**

```bash
pip install -r requirements.txt
python 01_data_sample/build_gis_check_map.py
```

Mở `01_data_sample/hang_xanh_gis_check.html` bằng trình duyệt. Rê chuột lên cạnh để xem thuộc tính và kết quả đối chiếu OSM. Bấm vào nút để xem chi tiết.

---

## I. KIỂM TRA TỰ ĐỘNG

| Hạng mục | Kết quả |
| :--- | :--- |
| Tọa độ nút so với `dist_center_m` (sai số `≤ 5 m`) | `20/20` nút khớp, không có nút lệch tọa độ |
| Chiều dài cạnh so với đường chim bay (tỉ lệ `0.9 – 2.0`) | `37/37` cạnh hợp lệ |
| Nút ngoài bán kính `1000 m` | `HX_20` (`1117 m`). Vùng tải của OSMnx là hình vuông nên nút ở góc vẫn được lấy |
| Cạnh chỉ có 1 chiều | `9` cạnh, đối chiếu OSM ở Mục II |
| Cặp cạnh 2 chiều có cờ `oneway` khác nhau | `E_26` / `E_32` (Nguyễn Gia Trí) |
| Nút không có cạnh vào / ra | `HX_14` không có cạnh vào · `HX_20` không có cạnh ra |

---

## II. ĐỐI CHIẾU CHIỀU ĐƯỜNG VỚI OPENSTREETMAP

Nguồn: tag `oneway` của các way trong OSM (API `openstreetmap.org`, khung `106.703,10.791,106.721,10.811`, tra ngày 18/11/2026).

| Cạnh | Tuyến | Kết quả |
| :--- | :--- | :--- |
| `E_05`, `E_27` | XVNT Hàng Xanh → Cầu Sơn → phía Bắc | ✅ Khớp. Đoạn này là đường **một chiều hướng Bắc** |
| `E_13`, `E_31` | Đinh Bộ Lĩnh, Cầu Đinh Bộ Lĩnh | ✅ Khớp. Đường **một chiều hướng Nam** về Hàng Xanh |
| `E_36` | Ung Văn Khiêm | ✅ Khớp. Một chiều hướng Đông, đi từ XVNT |
| `E_08`, `E_19`, `E_21` | Điện Biên Phủ phía Đông | ✅ Khớp. Đường có dải phân cách: chiều Đông đi `2 → 8`, chiều Tây đi `8 → 7 → 2` |
| `E_35` | XVNT phía Nam (`17 → 20`) | ❌ **Nghi lỗi.** OSM có đủ 2 chiều, nhưng đồ thị thiếu cạnh `20 → 17` |

* XVNT (phía Bắc) và Đinh Bộ Lĩnh tạo thành **cặp đường một chiều**. Vì vậy `HX_14` không có cạnh đi vào là **đúng thực tế**: đây là điểm xe từ Đinh Bộ Lĩnh đi vào mạng.
* Cầu vượt Hàng Xanh được giữ thành cạnh riêng `2 ↔ 3` (`E_07`, `E_10`), đi vượt qua nút mặt đường `HX_01`. Cách biểu diễn này khớp với thực tế.

---

## III. CẦN `[H3]` XỬ LÝ

1. **Thiếu cạnh `20 → 17` (`E_35`)**
   * `HX_20` nằm sát biên vùng tải (`1117 m`), gần Cầu Thị Nghè. Chiều đi lên hướng Bắc của XVNT bắt đầu từ ngoài biên nên khả năng cao đã bị cắt khi tải.
   * Hệ quả: `HX_20` thành nút cụt, không có cạnh ra. Đặc trưng `upstream_*` của `HX_17` sẽ không bao giờ nhận được tín hiệu từ phía Cầu Thị Nghè.
   * Hướng xử lý: thêm cạnh `20 → 17` (đối xứng `E_35`), hoặc bỏ `HX_20` khỏi đồ thị (vẫn còn `19` nút).
2. **Cờ `oneway` của Nguyễn Gia Trí không nhất quán (`E_26` = `False`, `E_32` = `True`)**
   * Thực tế đường 2 chiều. Giữa đoạn có một khúc ngắn tách làm 2 nhánh một chiều (way `1232064243`, `1265743194`).
   * Nguyên nhân trong code: hàm `contract_short_splits` lấy toàn bộ thuộc tính của đoạn đầu tiên (`nd = dict(d1)`). Vì vậy cờ `oneway` của cạnh gộp phụ thuộc vào việc đoạn đầu tiên là khúc nào.
   * Ảnh hưởng: chỉ tác động đến cột `has_twoway` trong `feature_dictionary.md`.

---

## IV. ĐOẠN DỄ NGẬP

* Đánh dấu theo tên đường trong Đề cương (Mục I.1) và Kế hoạch Tuần 4:
  * Đinh Bộ Lĩnh: `E_13`, `E_31`
  * Ung Văn Khiêm: `E_36`
* **"XVNT đoạn gần cầu Bình Triệu" chưa đưa lên bản đồ:** Đề cương chưa ghi vị trí cụ thể. Cần xác định đoạn này có nằm trong vùng đồ thị hay không.
* Danh sách điểm ngập hiện mới theo tên đường, chưa có nguồn số liệu ngập chính thức. Cần bổ sung nguồn trước khi đưa vào báo cáo.
* `feature_dictionary.md` hiện **chưa có biến ngập**. Muốn SHAP chỉ ra được tác động của "ngập" thì cần một biến cho việc này. Sẽ trao đổi với Khang tại buổi sync `[H5]`.

---

## V. KẾT QUẢ XỬ LÝ TRONG `[H1]` TUẦN 5 (Trần Hoàng Hôn — 24/11/2026)

Toàn bộ các nghi vấn kỹ thuật GIS Tuần 4 đã được xử lý triệt để trong script `extract_hang_xanh_graph.py` và tái xuất bộ file đồ thị:

1. **Khắc phục lỗi nút cụt `HX_20` (Cạnh `E_35`):**
   - Đã bổ sung cạnh ngược đối xứng `20 → 17` (`E_38`, chiều dài `200.51 m`, 2 làn, `primary`).
   - Cả `E_35` (`17 → 20`) và `E_38` (`20 → 17`) đều có `bidirectional_pair = True`.
   - Bậc ra của `HX_20` tăng từ `0` lên `1`; bậc vào của `HX_17` tăng từ `1` lên `2`. Hiện không còn nút nào bị cụt chiều ra.
2. **Đồng nhất cờ `oneway` Nguyễn Gia Trí:**
   - Cả hai cạnh `E_26` (`10 → 15`) và `E_32` (`15 → 10`) đều được chuẩn hóa về `oneway = False` (phản ánh đúng thực tế đường 2 chiều).
   - Số cặp cạnh 2 chiều có cờ `oneway` khác nhau giảm về **`0`**.
3. **Tích hợp cờ vùng trũng ngập `flood_prone` (`bool`):**
   - **`nodes.csv`:** Thêm cột `flood_prone`, gắn `True` cho `6` nút thuộc các trục trũng ngập: `HX_03`, `HX_04`, `HX_14` (Đinh Bộ Lĩnh), `HX_11` (Cầu Sơn / XVNT), `HX_15` (Ung Văn Khiêm / D2), `HX_18` (XVNT / Ung Văn Khiêm).
   - **`edges.csv`:** Thêm cột `flood_prone`, gắn `True` cho `5` cạnh ngập: `E_05` (Cầu Sơn / XVNT), `E_13` (Đinh Bộ Lĩnh), `E_27` (XVNT đoạn Cầu Sơn), `E_31` (Cầu Đinh Bộ Lĩnh), `E_36` (Ung Văn Khiêm).
   - Ma trận kề `adjacency_matrix.csv` kích thước `20 × 20`, tổng số cạnh có hướng đạt **`38`**, khớp 100% với `edges.csv`.
   - Đồ thị định dạng GraphML `hang_xanh.graphml` được xuất mới chứa đầy đủ thuộc tính đỉnh và cạnh đã làm giàu.
