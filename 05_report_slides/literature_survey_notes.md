# TỔNG QUAN TÀI LIỆU & XÁC MINH NGUỒN GỐC NGHIÊN CỨU (`[S1]`)

* **Học phần:** `CS315.G12.LT.TTNT` — Máy học nâng cao (Nhóm 14)
* **Phụ trách:** Hoàng Cao Sơn (`25730061`) — *Kỹ sư Đồ thị tri thức & AI Agent (`Lead WBS-03`)*
* **Tiêu chí lọc tài liệu (theo yêu cầu Giảng viên):** Chỉ sử dụng các công bố khoa học **trong giai đoạn 2022 – 2026**, đã xác minh đầy đủ **tên bài báo, danh sách tác giả thật, năm xuất bản, tạp chí/hội nghị và DOI hợp lệ** (tuyệt đối không trích dẫn bài cũ trước 2022 hoặc trích dẫn chưa kiểm chứng).

---

## 1. Ghi chú đối chiếu với bản Đề cương sơ bộ (`Mục I.1`)

Trong bản [De_Cuong_Chi_Tiet_Do_An_May_Hoc_Nang_Cao.md](../De_Cuong_Chi_Tiet_Do_An_May_Hoc_Nang_Cao.md#L46-L52), 4 tài liệu tham khảo ban đầu mới ở dạng mô tả chủ đề tóm tắt (chưa có tác giả/DOI, hoặc gắn nhầm tên bài STGCN cũ năm 2018 thành 2023). Bảng dưới đây thay thế hoàn toàn bằng **4 công trình xác thực giai đoạn 2022 – 2024** bám đúng 4 trụ cột kỹ thuật của đồ án:
1. Mô hình đồ thị không gian – thời gian cho dự báo giao thông (`ST-GNN`).
2. Hợp nhất đa phương thức & cơ chế chú ý trên đồ thị (`Graph Attention / Information Fusion`).
3. Nghiên cứu ngập lụt đô thị kết hợp mưa lớn – triều cường tại **TP.HCM**.
4. Kết hợp **Đồ thị tri thức (Knowledge Graph)** và **GNN** trong dự báo giao thông.

---

## 2. Danh mục 4 công trình đã xác minh (2022 – 2026)

### [Ref-1] Đồ thị Không gian – Thời gian động cho Dự báo Giao thông (2022)
* **Tác giả:** Zezhi Shao, Zhao Zhang, Wei Wei, Fei Wang, Yongjun Xu, Xin Cao, & Christian S. Jensen
* **Tên bài báo:** *Decoupled Dynamic Spatial-Temporal Graph Neural Network for Traffic Forecasting* (`D2STGNN`)
* **Nơi xuất bản:** *Proceedings of the VLDB Endowment (PVLDB)*, 2022
* **DOI:** `10.14778/3551793.3551827`
* **Đóng góp cốt lõi:** Khắc phục hạn chế của đồ thị tĩnh bằng cách tách riêng thành phần khuếch tán lưu lượng (*diffusion stream*) và đặc trưng nội tại mạng lưới đường bộ; thiết lập chuẩn đánh giá thực nghiệm trên tập dữ liệu cảm biến `METR-LA` và `PEMS-BAY`.

### [Ref-2] Hợp nhất thông tin & Gated Attention Transformer trên Đồ thị (2024)
* **Tác giả:** Zili Geng, Jie Xu, Rongsen Wu, Changming Zhao, Jin Wang, Yunji Li, & Chenlin Zhang
* **Tên bài báo:** *STGAFormer: Spatial–temporal Gated Attention Transformer based Graph Neural Network for traffic flow forecasting*
* **Nơi xuất bản:** *Information Fusion* (Elsevier), Vol. 105, Article 102228, May 2024
* **DOI:** `10.1016/j.inffus.2024.102228`
* **Đóng góp cốt lõi:** Kết hợp cơ chế chú ý có cổng không–thời gian (*Spatial-Temporal Gated Attention*) với mạng nơ-ron đồ thị để học trọng số phụ thuộc động giữa các nút giao lân cận khi lưu lượng biến động phi tuyến. *(Ghi chú bổ sung: cùng chuyên san Information Fusion 2024 có bài tổng quan hợp nhất dữ liệu thời tiết – giao thông bằng GNN tại DOI `10.1016/j.inffus.2024.102466`).*

### [Ref-3] Nghiên cứu Tác nhân kép Mưa lớn – Triều cường gây Ngập tại TP.HCM (2023)
* **Tác giả:** Francisco Rodrigues do Amaral, Nicolas Gratiot, Thierry Pellarin, & Trần Anh Tú (`Tran Anh Tu`)
* **Tên bài báo:** *Assessing typhoon-induced compound flood drivers: a case study in Ho Chi Minh City, Vietnam*
* **Nơi xuất bản:** *Natural Hazards and Earth System Sciences (NHESS)*, Vol. 23, pp. 3379–3398, 2023
* **DOI:** `10.5194/nhess-23-3379-2023`
* **Đóng góp cốt lõi:** Phân tích định lượng hiện tượng **ngập kép (compound flooding)** tại TP.HCM do tương tác giữa mưa cực đoan và mực nước triều cường sông Sài Gòn–Đồng Nai; cung cấp cơ sở khoa học thực địa cho việc đưa cả 2 biến ngoại sinh `precipitation` (`Open-Meteo`) và `tide_level` (trạm Phú An) vào mô hình dự báo ùn tắc.

### [Ref-4] Kết hợp Đồ thị tri thức (Knowledge Graph) & GNN dự báo Giao thông (2023)
* **Tác giả:** Shun Wang, Yong Zhang, Yongli Hu, & Baocai Yin
* **Tên bài báo:** *Knowledge fusion enhanced graph neural network for traffic flow prediction* (`KFGNN`)
* **Nơi xuất bản:** *Physica A: Statistical Mechanics and its Applications* (Elsevier), Article 128842, 2023
* **DOI:** `10.1016/j.physa.2023.128842`
* **Đóng góp cốt lõi:** Đề xuất mô-đun hợp nhất tri thức (*Knowledge Fusion*) biểu diễn ngữ cảnh ngoại sinh (cấu trúc đường, điểm nghẽn, yếu tố môi trường) dưới dạng đồ thị tri thức để bổ trợ cho GNN, giúp mô hình nắm bắt chính xác hơn các điểm nghẽn cục bộ.

---

## 3. Bảng tổng hợp so sánh & Khoảng trống nghiên cứu (`Research Gap`)

| Công trình (2022–2024) | Phương pháp chính | Dữ liệu & Bối cảnh | Điểm mạnh | Khoảng trống nghiên cứu (`Research Gap`) |
| :--- | :--- | :--- | :--- | :--- |
| **[Ref-1] Shao et al. (2022)** — *D2STGNN* | Decoupled Dynamic ST-GNN | `METR-LA`, `PEMS-BAY` (cao tốc Mỹ) | Mô hình hóa chính xác lan truyền sóng lưu lượng không–thời gian | Tập trung vào cảm biến cao tốc khô ráo, **chưa xét tác nhân mưa ngập/triều cường** và **chưa có XAI** |
| **[Ref-2] Geng et al. (2024)** — *STGAFormer* | Spatial-Temporal Gated Attention + GNN | Chuỗi lưu lượng đô thị | Học trọng số liên kết động giữa các nút giao tốt hơn GCN tĩnh | Kiến trúc sâu mang tính **"hộp đen"**, chưa gắn với suy luận lộ trình né kẹt |
| **[Ref-3] Amaral, Gratiot, Pellarin & Trần Anh Tú (2023)** | Phân tích thủy văn – ngập kép (*Compound Flood*) | Thực địa **TP. Hồ Chí Minh** (mưa + triều cường) | Chứng minh định lượng cơ chế ngập kép mưa + triều đặc thù TP.HCM | Nghiên cứu ở góc độ thủy văn/ngập lụt, **chưa kết nối vào bài toán ML dự báo lan truyền ùn tắc 15'–60'** |
| **[Ref-4] Wang et al. (2023)** — *KFGNN* | Knowledge Graph Fusion + GNN | Mạng lưới đường đô thị + tri thức ngữ cảnh | Tích hợp tri thức ngữ nghĩa giúp cải thiện dự báo điểm nghẽn | Chưa kết hợp **SHAP TreeExplainer** bóc tách định lượng mưa/triều và **AI Agent tool-calling** cảnh báo lộ trình |

### Định vị đóng góp của Đề tài Nhóm 14 (`CS315`)
Từ 4 khoảng trống trên, đồ án giải quyết trực tiếp 3 điểm giao thoa còn thiếu:
1. **Song hành 2 nhánh dữ liệu:** Đối chứng thuật toán trên tập cảm biến chuẩn `METR-LA` kết hợp kịch bản đặc thù **Cụm Ngã tư Hàng Xanh (TP.HCM)** với `OSMnx` + `Open-Meteo` + lịch triều cường Phú An.
2. **Minh bạch hóa (XAI):** Dùng `SHAP TreeExplainer` trên tập đặc trưng gốc (không ép qua PCA) để định lượng mức đóng góp của mưa/triều tới pha kẹt nặng (`Recall >= 85%`).
3. **Tri thức & Hành động:** Tổ chức trạng thái dự báo thành **Traffic Knowledge Graph** (`NetworkX`) gắn với **AI Agent** để chuyển hóa dự báo thành khuyến nghị lộ trình né kẹt cụ thể (ví dụ: né Đinh Bộ Lĩnh / Xô Viết Nghệ Tĩnh khi mưa $>30\text{ mm/h}$).
