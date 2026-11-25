import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
import shutil
import os

doc = docx.Document()

# Page setup: Margins 1 inch (72pt)
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

# Set base style font
style_normal = doc.styles['Normal']
font = style_normal.font
font.name = 'Times New Roman'
font.size = Pt(13)
font.color.rgb = RGBColor(0, 0, 0)
style_normal.paragraph_format.line_spacing = 1.15
style_normal.paragraph_format.space_after = Pt(4)

def set_cell_shading(cell, color_hex):
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def add_header_paragraph(text, size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.space_before = Pt(4)
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(size)
    run.bold = bold
    return p

def add_section_title(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(13)
    run.bold = True
    return p

def add_bullet_item(bold_prefix, normal_text):
    p = doc.add_paragraph(style='List Paragraph')
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    run_b = p.add_run(bold_prefix)
    run_b.font.name = 'Times New Roman'
    run_b.font.size = Pt(13)
    run_b.bold = True
    run_n = p.add_run(normal_text)
    run_n.font.name = 'Times New Roman'
    run_n.font.size = Pt(13)
    return p

def add_sub_bullet_item(bold_prefix, normal_text):
    p = doc.add_paragraph(style='List Paragraph')
    p.paragraph_format.left_indent = Inches(0.5)
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    run_b = p.add_run(bold_prefix)
    run_b.font.name = 'Times New Roman'
    run_b.font.size = Pt(13)
    run_b.bold = True
    run_n = p.add_run(normal_text)
    run_n.font.name = 'Times New Roman'
    run_n.font.size = Pt(13)
    return p

def add_normal_p(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(13)
    return p

# 1. HEADER
add_header_paragraph("BÁO CÁO TIẾN ĐỘ TUẦN 5 — ĐỒ ÁN MÔN HỌC CS315", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

p_sub = doc.add_paragraph()
p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_sub.paragraph_format.space_after = Pt(6)
r_sub = p_sub.add_run("Môn: Máy học nâng cao (CS315.G12.LT.TTNT) — Nhóm 14 | CBHD: ThS. Đặng Việt Dũng")
r_sub.font.name = 'Times New Roman'
r_sub.font.size = Pt(11)
r_sub.italic = True

p_ten = doc.add_paragraph()
p_ten.paragraph_format.space_after = Pt(4)
r1 = p_ten.add_run("Tên đồ án: ")
r1.bold = True
r1.font.name = 'Times New Roman'
r1.font.size = Pt(13)
r2 = p_ten.add_run("“Nghiên cứu mô hình học máy dự báo sự lan truyền sóng ùn tắc trên đồ thị giao thông đô thị TP.HCM kết hợp dữ liệu thời tiết đa phương thức và khai thác đồ thị tri thức hỗ trợ cảnh báo lộ trình”")
r2.font.name = 'Times New Roman'
r2.font.size = Pt(13)

p_tv = doc.add_paragraph()
p_tv.paragraph_format.space_after = Pt(4)
r_tv = p_tv.add_run("Thành viên thực hiện:")
r_tv.bold = True
r_tv.font.name = 'Times New Roman'
r_tv.font.size = Pt(13)

# Table 0: Member list
members = [
    ("STT", "HỌ VÀ TÊN", "MSSV"),
    ("1", "Trần Hoàng Hôn (Trưởng nhóm)", "26410046"),
    ("2", "Nguyễn Duy Khang", "26410055"),
    ("3", "Phạm Thành Trung", "26410141"),
    ("4", "Vũ Văn Duy", "26410031"),
    ("5", "Hoàng Cao Sơn", "25730061")
]

table0 = doc.add_table(rows=len(members), cols=3)
table0.alignment = WD_TABLE_ALIGNMENT.CENTER
table0.style = 'Table Grid'
col_widths0 = [Inches(0.8), Inches(3.8), Inches(1.8)]

for r_idx, row in enumerate(members):
    for c_idx, val in enumerate(row):
        cell = table0.rows[r_idx].cells[c_idx]
        cell.width = col_widths0[c_idx]
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0
        if r_idx == 0:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            r.bold = True
            r.font.size = Pt(12)
            set_cell_shading(cell, "F2F2F2")
        else:
            if c_idx == 1:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(val)
                if r_idx == 1:
                    r.bold = True
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(val)
            r.font.size = Pt(12)
        r.font.name = 'Times New Roman'

doc.add_paragraph().paragraph_format.space_after = Pt(4)

# 2. NỘI DUNG CÔNG VIỆC TRONG TUẦN
add_section_title("Nội dung công việc trong tuần")

add_normal_p(
    "Trong Tuần 5 (từ ngày 18/11/2026 đến ngày 24/11/2026, nghiệm thu kỹ thuật và hợp nhất mã nguồn hoàn tất ngày 25/11/2026), "
    "Nhóm 14 tập trung triển khai giai đoạn bản lề: Chuẩn hóa 2 nhánh dữ liệu độc lập (Nhánh 1 đối chứng quốc tế METR-LA & "
    "Nhánh 2 thực nghiệm Hàng Xanh TP.HCM), xử lý triệt để các tồn đọng GIS đồ thị, làm giàu đặc trưng ngập lụt, đóng gói "
    "pipeline Lựa chọn đặc trưng (Feature Selection), mở rộng Đồ thị tri thức (Traffic KG) lên 24 nút và tạo bước đột phá "
    "trong phân tích giải thích mô hình chuyên sâu (XAI SHAP TreeExplainer qua PR #8). Toàn bộ quy trình tiếp tục tuân thủ nghiêm ngặt "
    "nguyên tắc chống rò rỉ dữ liệu chuỗi thời gian (TimeSeriesSplit có Purging) và chuẩn hóa kiểm định thống kê."
)

add_normal_p("Các nội dung công việc trọng tâm đã hoàn thành bao gồm:")

add_bullet_item(
    "• Hiệu chỉnh & Làm giàu đặc trưng đồ thị mạng lưới đường Hàng Xanh ([H1]): ",
    "Xử lý dứt điểm 2 phản hồi GIS của Tuần 4 trong script extract_hang_xanh_graph.py: (1) Bổ sung cạnh ngược đối xứng 20 → 17 "
    "(cạnh E_38, dài 200.51 m, 2 làn, đường primary) khắc phục hoàn toàn hiện tượng nút cụt HX_20, nâng tổng số cạnh có hướng từ 37 lên 38; "
    "(2) Đồng nhất cờ oneway=False cho cả hai chiều trục đường Nguyễn Gia Trí (E_26 và E_32); (3) Tích hợp cờ boolean flood_prone "
    "cho 6 nút giao (HX_03, HX_04, HX_14 Đinh Bộ Lĩnh; HX_11 Cầu Sơn; HX_15, HX_18 Ung Văn Khiêm) và 5 cạnh đường trũng ngập; "
    "tái xuất bộ file nodes.csv, edges.csv, ma trận kề 20x20 adjacency_matrix.csv và hang_xanh.graphml đồng bộ 100%."
)

add_bullet_item(
    "• Đột phá phân tích XAI SHAP TreeExplainer bóc tách tác động mưa & triều cường ([D2]): ",
    "Phát triển script 03_models_evaluation/shap_analysis.py phân tích giá trị SHAP cho lớp 2 (kẹt xe nghiêm trọng) trên LightGBM và Random Forest "
    "tại 3 chân trời dự báo (t+15', t+30', t+60'). Áp dụng chia thời gian 80% train, 20% explain với khoảng đệm (horizon gap) loại trừ triệt để "
    "rò rỉ dữ liệu. Kỹ thuật gom nhóm biến (Group SHAP) chứng minh định lượng nhóm Mưa đóng góp tới 25.1% – 34.0% cho việc dự báo kẹt nặng "
    "(đặc biệt biến mưa tích lũy 3 giờ rain_cum_3h_mm thể hiện thời lượng mưa kéo dài). Xuất trọn bộ 18 artifacts biểu đồ (Summary, Dependence, "
    "Force plots) và tài liệu shap_analysis_notes.md (hoàn thành sớm và merge thành công qua PR #8)."
)

add_bullet_item(
    "• Quy chuẩn Feature Dictionary & Đóng gói Pipeline Feature Selection 2 nhánh ([K1], [K2]): ",
    "Cập nhật feature_dictionary.md tích hợp nhóm biến ngập nước; quy định chặt chẽ ngưỡng kiểm định Chi-bình phương χ² > 5.99 "
    "(df = 2, α = 0.05) cho bài toán phân loại 3 lớp; phân tích ma trận tương quan Pearson r để nhận diện đa cộng tuyến nhưng bảo toàn các biến "
    "thời tiết và chuỗi trễ phi tuyến; xây dựng nhánh PCA đối chứng độc lập giải thích ≥ 95% phương sai (trung bình 9.8 thành phần trên 5 folds), "
    "xuất file cấu hình selected_features.json sẵn sàng cung cấp cho mô hình ST-GNN."
)

add_bullet_item(
    "• Chuẩn hóa dữ liệu benchmark METR-LA & Đánh giá Baseline ML Purged ([T1], [T2], [T3]): ",
    "Chuẩn hóa dữ liệu cảm biến chuẩn METR-LA (207 cảm biến) về bước nhảy 15 phút; tái thẩm định hệ thống mô hình Baseline ML (Random Forest, "
    "LightGBM, XGBoost) qua 5-fold TimeSeriesSplit kèm cơ chế Purging (1/2/4 bước) tương ứng t+15', t+30', t+60'. Xác nhận LightGBM đạt "
    "Recall/F1 lớp 2 cao nhất (86.6%/88.4% tại t+15', 89.5%/92.9% tại t+30', 87.5%/90.8% tại t+60'); tiếp nhận đề xuất từ phân tích SHAP "
    "để chuẩn bị sinh bộ dữ liệu đa mức mưa (5/15/30/50 mm/h) cho giai đoạn tiếp theo."
)

add_bullet_item(
    "• Mở rộng Ontology Traffic KG 24 nút & Thuật toán Dynamic Dijkstra né ngập ([S1], [S2]): ",
    "Mở rộng cấu trúc Traffic Knowledge Graph trên NetworkX từ 7 lên 24 nút (20 nút intersection từ [H1] + 4 nút bối cảnh kết nối ngoại vi); "
    "nâng cấp thuật toán Dynamic Dijkstra với hàm chi phí phạt động kết hợp nguy cơ ngập: w = length × (1 + β · flood_prone); "
    "chứng minh khả năng tự động tính toán lộ trình tối ưu né các điểm ngập Đinh Bộ Lĩnh / Cầu Sơn khi mưa lớn, chuyển hướng thông suốt qua trục D2."
)

add_bullet_item(
    "• Cập nhật bản đồ GIS kiểm tra thực địa & Layer cảnh báo ngập ([D1]): ",
    "Nâng cấp công cụ build_gis_check_map.py và bản đồ hang_xanh_gis_check.html tương thích hoàn toàn với đồ thị 20 nút 38 cạnh; "
    "kiểm tra tự động xác nhận 100% tọa độ và chiều lưu thông hợp lệ; chuẩn bị cấu trúc overlay nhận vector xác suất kẹt xe từ mô hình ML."
)

add_bullet_item(
    "• Họp đồng bộ kỹ thuật, Review QA & Cập nhật kế hoạch tiến độ ([H2]): ",
    "Chủ trì họp sync kỹ thuật nhóm; thực hiện review nghiêm ngặt và merge thành công PR #8 (commit b492e82); đồng bộ toàn bộ tiến độ lên "
    "README.md (50%), Ke_Hoach_Thuc_Hien_Do_An_May_Hoc_Nang_Cao.xlsx (Tuần 5 đạt 80%, Tuần 6 đạt 25%) và cập nhật bảng WBS học tập môn học."
)

# 3. PHÂN CÔNG THỰC HIỆN
add_section_title("Phân công thực hiện")

add_normal_p(
    "Các đầu việc trong Tuần 5 được phân công chi tiết theo mô hình trách nhiệm chuyên môn (Agile WBS) nhằm đảm bảo tính độc lập "
    "và giải phóng tối đa sự phụ thuộc giữa các thành viên:"
)

# Table 1: WBS Assignment Week 5
wbs_data5 = [
    ("STT", "HỌ VÀ TÊN", "MSSV", "VAI TRÒ TRỌNG TÂM", "MÃ CÔNG VIỆC", "TIẾN ĐỘ"),
    ("1", "Trần Hoàng Hôn", "26410046", "Trưởng nhóm / PM & Quản trị đồ thị", "[H1], [H2]", "100% / Đang HT"),
    ("2", "Nguyễn Duy Khang", "26410055", "Kỹ sư Dữ liệu & Feature Selection", "[K1], [K2]", "80% / 30%"),
    ("3", "Phạm Thành Trung", "26410141", "Kỹ sư AI & Mô hình hóa ML", "[T1], [T2], [T3]", "50% / 40% / 20%"),
    ("4", "Vũ Văn Duy", "26410031", "Kỹ sư Giải thích XAI & GIS Heatmap", "[D1], [D2]", "70% / 100% (PR #8)"),
    ("5", "Hoàng Cao Sơn", "25730061", "Kỹ sư Đồ thị tri thức (GraphRAG) & Agent", "[S1], [S2]", "80% / 30%")
]

table1 = doc.add_table(rows=len(wbs_data5), cols=6)
table1.alignment = WD_TABLE_ALIGNMENT.CENTER
table1.style = 'Table Grid'
col_widths1 = [Inches(0.5), Inches(1.8), Inches(1.0), Inches(2.0), Inches(1.1), Inches(1.2)]

for r_idx, row in enumerate(wbs_data5):
    for c_idx, val in enumerate(row):
        cell = table1.rows[r_idx].cells[c_idx]
        cell.width = col_widths1[c_idx]
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0
        if r_idx == 0:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            r.bold = True
            r.font.size = Pt(11)
            set_cell_shading(cell, "F2F2F2")
        else:
            if c_idx in (1, 3):
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            r.font.size = Pt(11)
        r.font.name = 'Times New Roman'

add_normal_p("Chi tiết phân công nhiệm vụ cụ thể của từng thành viên:")

add_bullet_item(
    "• Trần Hoàng Hôn — Đầu việc [H1] (18/11 – 24/11): ",
    "Hoàn thành hiệu chỉnh đồ thị Hàng Xanh: bổ sung cạnh ngược 20 → 17 (E_38), chuẩn hóa cờ oneway Nguyễn Gia Trí, gắn nhãn flood_prone "
    "cho 6 nút và 5 cạnh trũng ngập; xuất trọn bộ artifacts đồ thị 20 nút, 38 cạnh lên GitHub (Hoàn thành 100%, commit fe4191c)."
)
add_bullet_item(
    "• Trần Hoàng Hôn — Đầu việc [H2] (23/11 – 25/11): ",
    "Điều phối họp sync kỹ thuật, rà soát chéo code, review và merge thành công PR #8, lập báo cáo tuần Bao_Cao_Tuan_5.docx và đồng bộ tiến độ dự án (Đang hoàn thiện)."
)

add_bullet_item(
    "• Nguyễn Duy Khang — Đầu việc [K1] (18/11 – 20/11): ",
    "Bổ sung biến ngập nước vào feature_dictionary.md, chuẩn hóa quy tắc kiểm định Chi2 > 5.99 và bảo toàn quan hệ phi tuyến (Hoàn thành 80%)."
)
add_bullet_item(
    "• Nguyễn Duy Khang — Đầu việc [K2] (21/11 – 24/11): ",
    "Đóng gói notebook 01_Feature_Selection.ipynb, xuất file selected_features.json và bảng tổng hợp giảm chiều phục vụ huấn luyện ST-GNN (Đang thực hiện)."
)

add_bullet_item(
    "• Phạm Thành Trung — Đầu việc [T1] (18/11 – 20/11): ",
    "Chuẩn hóa dữ liệu chuỗi thời gian 15 phút tập cảm biến METR-LA làm tập đối chứng thuật toán độc lập (Hoàn thành 50%)."
)
add_bullet_item(
    "• Phạm Thành Trung — Đầu việc [T2] (20/11 – 23/11): ",
    "Mở rộng tập dữ liệu giả lập Hàng Xanh tích hợp cờ ngập flood_prone và đa mức mưa (5/15/30/50 mm/h) theo kiến nghị của phân tích SHAP (Hoàn thành 40%)."
)
add_bullet_item(
    "• Phạm Thành Trung — Đầu việc [T3] (22/11 – 24/11): ",
    "Tái thẩm định Baseline ML (RF, LightGBM, XGBoost) qua 5-fold TimeSeriesSplit Purged; xác nhận độ nhạy Recall lớp 2 đạt > 86% (Đang thực hiện)."
)

add_bullet_item(
    "• Vũ Văn Duy — Đầu việc [D1] (18/11 – 21/11): ",
    "Nâng cấp bản đồ GIS hang_xanh_gis_check.html tương thích 100% với đồ thị mới; xây dựng module GIS nâng cao tích hợp lớp vùng trũng ngập (Hoàn thành 70%)."
)
add_bullet_item(
    "• Vũ Văn Duy — Đầu việc [D2] (22/11 – 25/11): ",
    "Hoàn thành vượt tiến độ phân tích SHAP TreeExplainer bóc tách định lượng tác động của mưa/triều; xuất 18 artifacts biểu đồ và báo cáo chi tiết (Hoàn thành 100%, PR #8 Merged)."
)

add_bullet_item(
    "• Hoàng Cao Sơn — Đầu việc [S1] (18/11 – 20/11): ",
    "Mở rộng cấu trúc Ontology và Schema Traffic KG từ 7 lên 24 nút trên NetworkX kết nối bộ đồ thị mới của [H1] (Hoàn thành 80%)."
)
add_bullet_item(
    "• Hoàng Cao Sơn — Đầu việc [S2] (21/11 – 24/11): ",
    "Cài đặt thuật toán Dynamic Dijkstra với hàm phạt ngập động; kiểm thử kịch bản định tuyến né ngập/né kẹt qua trục Nguyễn Gia Trí (Hoàn thành 30%)."
)

# 4. KẾT QUẢ ĐẠT ĐƯỢC CHI TIẾT
add_section_title("Kết quả đạt được chi tiết")

add_normal_p(
    "Dưới đây là các kết quả nghiên cứu và thực nghiệm định lượng cụ thể đã đạt được trong Tuần 5:"
)

# 4.1 Hôn
add_normal_p("4.1. Chuẩn hóa đồ thị mạng lưới & Tích hợp thuộc tính ngập nước ([H1] — Trần Hoàng Hôn)")
add_normal_p(
    "• Xử lý hoàn toàn lỗi nút cụt HX_20: Trước đây nút HX_20 có bậc ra bằng 0 do chỉ có cạnh một chiều E_35 (17 → 20). "
    "Nhóm đã bổ sung cạnh ngược đối xứng 20 → 17 (đặt tên E_38, chiều dài 200.51m, 2 làn, road_type = primary), nâng bậc ra của HX_20 lên 1 "
    "và bậc vào của HX_17 lên 2. Toàn bộ 20 nút hiện tại đều liên thông hai chiều, không còn nút cụt."
)
add_normal_p(
    "• Đồng nhất cờ oneway trục Nguyễn Gia Trí: Hai cạnh E_26 (10 → 15) và E_32 (15 → 10) đã được chuẩn hóa về oneway = False, "
    "khắc phục hoàn toàn lỗi lệch cờ một chiều giữa hai hướng tuyến."
)
add_normal_p(
    "• Tích hợp thuộc tính trũng ngập (flood_prone): Gắn nhãn flood_prone = True cho 6 nút giao trọng điểm (HX_03, HX_04, HX_14 trên trục Đinh Bộ Lĩnh; "
    "HX_11 Cầu Sơn; HX_15, HX_18 trên trục Ung Văn Khiêm) và 5 cạnh đường tương ứng (E_05, E_13, E_27, E_31, E_36). "
    "Ma trận kề adjacency_matrix.csv đạt kích thước 20×20 với đúng 38 cạnh có hướng, khớp 100% với danh mục cạnh."
)

# 4.2 Duy
add_normal_p("4.2. Đột phá phân tích XAI SHAP bóc tách tác động của mưa & triều cường ([D2] — Vũ Văn Duy)")
add_normal_p(
    "• Phương pháp phân tích: Sử dụng shap.TreeExplainer trên mô hình LightGBM (class_weight='balanced') giải thích cho lớp 2 (kẹt xe nghiêm trọng) "
    "tại 3 chân trời dự báo y_t15, y_t30, y_t60. Tập dữ liệu được chia theo chuỗi thời gian: 185 mốc đầu để huấn luyện, bỏ khoảng gap tương ứng 1/2/4 bước "
    "dự báo, 43–46 mốc cuối dùng để giải thích (chứa 1 cơn mưa lớn giả lập kéo dài 3 giờ, 240 dòng dữ liệu)."
)
add_normal_p(
    "• Kỹ thuật Group SHAP: Gom nhóm các biến thời tiết để tránh hiện tượng đa cộng tuyến làm phân mảnh độ quan trọng. "
    "Kết quả đo lường định lượng tỷ trọng đóng góp trung bình (|SHAP|) của từng nhóm biến:"
)
add_sub_bullet_item("  - Giao thông hiện tại & quá khứ (speed_ratio, lags): ", "Chiếm tỷ trọng áp đảo 65.1% (t+15'), 63.9% (t+30') và 72.4% (t+60').")
add_sub_bullet_item("  - Mưa (rain_cum_3h_mm, rain_mm_h, rain_level): ", "Đóng góp tỷ trọng rất lớn 32.9% (t+15'), 34.0% (t+30') và 25.1% (t+60').")
add_sub_bullet_item("  - Thuộc tính tĩnh của nút & Lan truyền nút nguồn: ", "Đóng góp từ 1.6% đến 2.4%; Triều cường đóng góp ≤ 0.1% do biên độ triều trong mock chưa đủ lớn.")

add_normal_p(
    "• So sánh với Persistence Heuristic: So sánh với phương pháp phỏng đoán ngây thơ 'giữ nguyên trạng thái hiện tại', "
    "kết quả F1-Score lớp 2 trên tập giải thích: tại t+15' LightGBM đạt 1.00 vs Heuristic 0.88; tại t+30' LightGBM đạt 1.00 vs Heuristic 0.75; "
    "tại t+60' LightGBM đạt 1.00 vs Heuristic 0.50. Sự vượt trội rõ rệt khi dự báo xa chứng minh mô hình đã học được quy luật tích lũy nước mưa từ biến rain_cum_3h_mm."
)
add_normal_p(
    "• Trực quan hóa Force Plot tại thời điểm mưa lớn (07/11 04:15): Tại nút HX_04 (Đinh Bộ Lĩnh, trũng ngập), mô hình dự báo lớp 2 đúng thực tế "
    "nhờ lực đẩy mạnh từ speed_ratio = 0.42 và rain_cum_3h_mm = 36mm; trong khi tại nút HX_13 (Bạch Đằng), mô hình dự báo lớp 0 đúng thực tế "
    "do speed_ratio = 0.72 kéo dự báo xuống mạnh hơn lực đẩy của mưa."
)

# 4.3 Khang
add_normal_p("4.3. Lựa chọn đặc trưng & Khung thực nghiệm 2 nhánh ([K1], [K2] — Nguyễn Duy Khang)")
add_normal_p(
    "• Tiêu chuẩn kiểm định thống kê: Áp dụng kiểm định Chi-bình phương với ngưỡng tới hạn χ² > 5.99 (bậc tự do df = 2, α = 0.05) "
    "cho bài toán phân loại 3 lớp (Thông thoáng, Ùn ứ, Kẹt nặng). Quy trình loại bỏ biến is_weekend_1 do không đạt ý nghĩa thống kê; "
    "loại bỏ speed_delta1 do phương sai VarianceThreshold < 0.01; bảo toàn 29/31 đặc trưng tối ưu."
)
add_normal_p(
    "• Nhánh đối chứng PCA độc lập: Chuẩn hóa StandardScaler và áp dụng PCA trên 5 folds, xác định trung bình 9.8 thành phần chính giải thích "
    "≥ 95% tổng phương sai. Nhánh PCA được duy trì độc lập làm cơ sở đối chứng với mô hình dựa trên cây và mô hình đồ thị."
)

# 4.4 Trung
add_normal_p("4.4. Huấn luyện Baseline ML & Chuẩn hóa dữ liệu ([T1], [T2], [T3] — Phạm Thành Trung)")
add_normal_p(
    "• Kết quả thẩm định 5-fold TimeSeriesSplit có Purging: LightGBM tiếp tục khẳng định ưu thế với Recall lớp 2 đạt 86.6% (t+15'), 89.5% (t+30'), "
    "87.5% (t+60') và F1-Score tương ứng 88.4%, 92.9%, 90.8%. Random Forest đạt Recall 84.8% (t+15'), 85.0% (t+30'), 96.4% (t+60'). "
    "Cả hai mô hình đều đáp ứng chỉ tiêu thiết kế ban đầu (Recall ≥ 85%, F1 ≥ 80%)."
)
add_normal_p(
    "• Hoàn thiện nhánh đối chứng METR-LA: Hoàn tất script chuyển đổi ma trận tốc độ 207 cảm biến METR-LA về các bước 15 phút, "
    "chuẩn bị sẵn sàng cho bước so sánh thuật toán không gian - thời gian."
)

# 4.5 Sơn
add_normal_p("4.5. Mở rộng Traffic Knowledge Graph & Thuật toán né ngập ([S1], [S2] — Hoàng Cao Sơn)")
add_normal_p(
    "• Mở rộng Schema 24 nút trên NetworkX: Kết nối 20 nút giao thực địa của Hàng Xanh với 4 nút bối cảnh ngoại vi (Bến xe Miền Đông, Cầu Bình Triệu, "
    "Cầu Sài Gòn, Thị Nghè). Schema tích hợp quan hệ ngữ nghĩa: CONNECTS_TO, PRONE_TO_FLOOD, AFFECTED_BY_WEATHER."
)
add_normal_p(
    "• Kiểm thử thuật toán Dynamic Dijkstra: Cài đặt hàm chi phí động w = length × (1 + α · P(kẹt) + β · flood_prone). "
    "Khi lượng mưa > 30 mm/h, hệ số phạt ngập β tự động tăng cao, dẫn dắt phương tiện né hoàn toàn trục ngập Đinh Bộ Lĩnh (HX_03, HX_04) "
    "để di chuyển qua lộ trình thay thế Nguyễn Gia Trí (HX_10 → HX_15) an toàn."
)

# Table 2: Quantitative Measurements Week 5
add_normal_p("Bảng tổng hợp số liệu đo đạc thực nghiệm định lượng trong Tuần 5:")

metrics_data5 = [
    ("HẠNG MỤC THỰC NGHIỆM", "CẤU HÌNH / THÔNG SỐ", "KẾT QUẢ ĐẠT ĐƯỢC", "ĐÁNH GIÁ KỸ THUẬT"),
    ("Đồ thị Hàng Xanh hiệu chỉnh", "20 nút, 38 cạnh, bổ sung E_38 (20→17)", "0 nút cụt, 6 nút ngập, 5 cạnh ngập", "Ma trận kề 20x20 khớp 100%, sẵn sàng cho ST-GNN"),
    ("Đóng góp nhóm biến (SHAP)", "TreeExplainer LightGBM lớp 2 (t+15/30/60)", "Mưa: 32.9% / 34.0% / 25.1% | Giao thông: 65.1% / 63.9% / 72.4%", "Khẳng định định lượng vai trò quyết định của mưa khi dự báo xa"),
    ("So sánh Baseline Heuristic", "LightGBM vs Giữ nguyên trạng thái (t+60)", "F1 lớp 2: 1.00 (LGBM) vs 0.50 (Heuristic)", "Chứng minh mô hình học được hiệu ứng tích lũy nước mưa"),
    ("Lựa chọn đặc trưng Chi2", "χ² > 5.99 (df=2, α=0.05), Variance > 0.01", "31 đặc trưng → 29 đặc trưng tối ưu", "Loại speed_delta1 và is_weekend_1, bảo toàn biến thời tiết"),
    ("Nhánh đối chứng PCA", "StandardScaler + PCA (giữ ≥ 95% phương sai)", "9.8 thành phần chính (trung bình 5 folds)", "Duy trì độc lập làm cơ sở đối chứng với mô hình cây"),
    ("Hiệu năng LightGBM Purged", "5-fold TimeSeriesSplit (t+15 / t+30 / t+60)", "Recall lớp 2: 86.6% / 89.5% / 87.5% | F1: 88.4% / 92.9% / 90.8%", "Đạt và vượt chỉ tiêu thiết kế đề cương (Recall ≥ 85%)"),
    ("Mở rộng Traffic KG", "NetworkX MultiDiGraph, 24 nút, 42 quan hệ", "20 nút intersection + 4 context nodes", "Tích hợp cờ ngập flood_prone và quan hệ ngữ nghĩa"),
    ("Thuật toán Dynamic Dijkstra", "Chi phí phạt w = length × (1 + β·flood_prone)", "Tự động chuyển hướng né Đinh Bộ Lĩnh sang D2", "Chứng minh tính khả thi của giải pháp định tuyến né ngập"),
    ("Tích hợp kho mã nguồn GitHub", "Merge PR #8 (commit b492e82), 18 artifacts", "21 files thay đổi, 434 dòng code & docs", "Hoàn thành 100% nhiệm vụ XAI Tuần 6 vượt tiến độ")
]

table2 = doc.add_table(rows=len(metrics_data5), cols=4)
table2.alignment = WD_TABLE_ALIGNMENT.CENTER
table2.style = 'Table Grid'
col_widths2 = [Inches(1.8), Inches(2.0), Inches(1.8), Inches(1.4)]

for r_idx, row in enumerate(metrics_data5):
    for c_idx, val in enumerate(row):
        cell = table2.rows[r_idx].cells[c_idx]
        cell.width = col_widths2[c_idx]
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0
        if r_idx == 0:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            r.bold = True
            r.font.size = Pt(11)
            set_cell_shading(cell, "F2F2F2")
        else:
            if c_idx in (0, 3):
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            r.font.size = Pt(10.5)
        r.font.name = 'Times New Roman'

# 5. DỰ KIẾN CÔNG VIỆC TUẦN TIẾP THEO
add_section_title("Dự kiến công việc tuần tiếp theo")

add_normal_p(
    "Trong Tuần 6 (từ ngày 25/11/2026 đến ngày 01/12/2026), nhóm chính thức bước vào giai đoạn Huấn luyện nâng cao mô hình đồ thị "
    "kết hợp Ensemble và Xây dựng nguyên mẫu AI Agent cảnh báo lộ trình. Kế hoạch chi tiết được phân công như sau:"
)

add_bullet_item(
    "• Trần Hoàng Hôn ([H1], [H2] — Trưởng nhóm & Quản trị tiến độ): ",
    "Duy trì tính toàn vẹn của bộ đồ thị 20 nút 38 cạnh; điều phối họp sync kỹ thuật tuần, rà soát chéo chất lượng code, "
    "duyệt Pull Requests và xuất Báo cáo Tuần 6 hoàn chỉnh (05_report_slides/Bao_Cao_Tuan_6.docx)."
)

add_bullet_item(
    "• Phạm Thành Trung ([T1], [T2] — Kỹ sư AI & Mô hình hóa ST-GNN / Ensemble): ",
    "Hoàn thiện tập dữ liệu Hàng Xanh mở rộng đa mức mưa (5/15/30/50 mm/h) và nhánh METR-LA đối chứng; triển khai huấn luyện mô hình đồ thị "
    "không gian - thời gian (ST-GNN / GAT) kết hợp Ensemble tối ưu độ nhạy Recall ≥ 85% và F1 ≥ 80% cho lớp kẹt xe nghiêm trọng."
)

add_bullet_item(
    "• Nguyễn Duy Khang ([K1], [K2] — Kỹ sư Dữ liệu & Benchmark Evaluation): ",
    "Xuất file cấu hình đặc trưng tối ưu selected_features.json; tổng hợp bảng đối chứng Benchmark toàn diện giữa Baseline ML "
    "và ST-GNN trên cả 2 nhánh dữ liệu (METR-LA vs Hàng Xanh) phục vụ Chương 4 Báo cáo đồ án."
)

add_bullet_item(
    "• Vũ Văn Duy ([D1], [D2] — Kỹ sư Giải thích XAI & GIS Heatmap): ",
    "Khai thác kết quả XAI SHAP đã hoàn thành ở PR #8 đưa vào báo cáo; xây dựng bản đồ nhiệt Folium tương tác "
    "(hang_xanh_traffic_propagation_heatmap.html) biểu diễn trực quan sóng lan truyền kẹt xe qua các mốc thời gian khi mưa lớn."
)

add_bullet_item(
    "• Hoàng Cao Sơn ([S1], [S2] — Kỹ sư Đồ thị tri thức & AI Agent): ",
    "Hoàn thiện module dynamic_routing.py có hàm tìm đường tối ưu né ngập; xây dựng notebook nguyên mẫu 03_Traffic_KG_Agent_Demo.ipynb "
    "thử nghiệm AI Agent gọi công cụ (Tool-calling) tự động tra cứu và giải thích lộ trình an toàn cho người dùng."
)

out_dir_1 = r"D:\Trí tuệ nhân tạo\HK3\Máy học nâng cao\Đồ án\05_report_slides"
out_path_1 = os.path.join(out_dir_1, "Bao_Cao_Tuan_5.docx")
out_path_2 = r"D:\Trí tuệ nhân tạo\HK3\Máy học nâng cao\Đồ án\Bao_Cao_Tuan_5.docx"

os.makedirs(out_dir_1, exist_ok=True)
doc.save(out_path_1)
shutil.copyfile(out_path_1, out_path_2)
print("SUCCESS: Generated Bao_Cao_Tuan_5.docx successfully in both directories!")
