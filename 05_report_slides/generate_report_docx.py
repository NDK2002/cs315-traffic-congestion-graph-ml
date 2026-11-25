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
add_header_paragraph("BÁO CÁO TIẾN ĐỘ TUẦN 4 — ĐỒ ÁN MÔN HỌC CS315", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

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
    "Trong Tuần 4 (từ ngày 11/11/2026 đến ngày 17/11/2026, nghiệm thu và tích hợp kỹ thuật hoàn tất ngày 19/11/2026), "
    "nhóm tiến hành triển khai giai đoạn Fast-track Sprint nhằm xây dựng nền tảng hạ tầng kỹ thuật và giải thuật học máy cho bài toán "
    "“Nghiên cứu mô hình học máy dự báo sự lan truyền sóng ùn tắc trên đồ thị giao thông đô thị TP.HCM kết hợp dữ liệu thời tiết đa phương thức "
    "và khai thác đồ thị tri thức hỗ trợ cảnh báo lộ trình”. Nhờ áp dụng triệt để nguyên tắc Contract-First và bộ dữ liệu mẫu Mock Spatio-Temporal Dataset, "
    "cả 5 thành viên trong nhóm đã tiến hành nghiên cứu, triển khai song song và độc lập trên 5 phân hệ chuyên môn mà không gặp tình trạng nghẽn "
    "tiến độ chờ đợi lẫn nhau. Toàn bộ các sản phẩm kỹ thuật Tuần 4 đã được kiểm thử, rà soát chất lượng và tích hợp sạch vào nhánh main của "
    "repository GitHub mrkiss-it/cs315-traffic-congestion-graph-ml thông qua 7 Pull Request (PR #1 đến PR #7) đã được hợp nhất hoàn tất."
)

add_normal_p("Các nội dung công việc trọng tâm đã hoàn thành bao gồm:")

add_bullet_item(
    "• Khởi tạo kiến trúc Repository 5 thư mục & Quản trị kho mã nguồn ([H1], [H2]): ",
    "Hoàn tất đăng ký đề tài chính thức cho Nhóm 14 trên biểu mẫu chung của lớp; thiết lập cấu trúc Repository chuẩn mực gồm 5 thư mục chức năng "
    "(01_data_sample đến 05_report_slides), ban hành file .gitignore chặt chẽ loại trừ dữ liệu nặng và môi trường ảo, "
    "khóa phiên bản thư viện trong requirements.txt đảm bảo tính tái lập (reproducibility) cao."
)

add_bullet_item(
    "• Trích xuất & Lọc gọn đồ thị mạng lưới đường Hàng Xanh bằng OSMnx ([H3]): ",
    "Xây dựng công cụ extract_hang_xanh_graph.py trích xuất đồ thị giao thông thực tế quanh ngã tư Hàng Xanh bán kính 1.000m từ OpenStreetMap; "
    "lọc và rút gọn thành công cấu trúc 20 nút giao trọng điểm (HX_01 – HX_20), 37 cạnh đường có hướng (E_01 – E_37), "
    "xuất file ma trận kề 20x20 adjacency_matrix.csv và định dạng hang_xanh.graphml chuẩn cho các mô hình Graph ML."
)

add_bullet_item(
    "• Thu thập dữ liệu thời tiết Open-Meteo & Chuẩn hóa lịch triều cường Phú An ([T1]): ",
    "Xây dựng script fetch_open_meteo_sample.py thu thập 72 mốc giờ dữ liệu thời tiết thực địa (lượng mưa mm/h, độ ẩm, nhiệt độ) "
    "tại tọa độ Hàng Xanh; chuẩn hóa bảng dữ liệu cực trị triều cường trạm Phú An phu_an_tide_reference.csv theo Bản tin 307/2026 "
    "của Đài KTTV Nam Bộ, ánh xạ chính xác 3 cấp báo động ngập (BĐ1: 1.40m, BĐ2: 1.50m, BĐ3: 1.60m)."
)

add_bullet_item(
    "• Xây dựng bộ dữ liệu giả lập không gian - thời gian Mock Spatio-Temporal Dataset ([T2]): ",
    "Phát triển script build_mock_hang_xanh_dataset.py sinh thành công 4.640 dòng dữ liệu không gian - thời gian (232 mốc thời gian 15 phút × 20 nút giao), "
    "tích hợp đầy đủ các đặc trưng thời tiết, đặc trưng topo lân cận (upstream/downstream), cờ kịch bản mưa stress test và 3 cột nhãn lan truyền sóng "
    "ùn tắc sau 15, 30, 60 phút (y_t15, y_t30, y_t60), giải phóng hoàn toàn sự phụ thuộc dữ liệu cho các phân hệ phía sau."
)

add_bullet_item(
    "• Thiết kế Data Contract & Từ điển đặc trưng Feature Dictionary ([K1]): ",
    "Ban hành tài liệu chuẩn feature_dictionary.md định nghĩa chi tiết cấu trúc 28 biến đầu vào thô, mã hóa One-Hot thành 31 đặc trưng; "
    "phân loại chặt chẽ thành biến số (Numeric: 22 biến), biến thứ tự (Ordinal: 3 biến - rain_level, time_slot, tide_alert) và biến danh mục "
    "(Nominal: 3 biến - road_type, is_weekend, has_twoway); chốt quy tắc nội suy thời gian 1 giờ sang 15 phút bằng phương pháp nội suy tuyến tính."
)

add_bullet_item(
    "• Xây dựng Pipeline Lựa chọn đặc trưng 2 nhánh + Đối chứng PCA ([K2]): ",
    "Lập trình module 01_feature_selection_pipeline.py gồm: nhánh lọc biến số (VarianceThreshold > 0.01 loại bỏ speed_delta1 do phương sai thấp, "
    "kết hợp kiểm tra tương quan Pearson r để nhận diện đa cộng tuyến nhưng không lọc cứng nhằm bảo toàn các quan hệ phi tuyến); "
    "nhánh lọc biến phân loại (One-Hot + kiểm định Chi-square với ngưỡng tới hạn χ² = 5.99 ứng với df = 2, α = 0.05 loại bỏ is_weekend_1); "
    "kết quả chọn lọc 29/31 đặc trưng tối ưu (giảm 6.5% số chiều mà không làm mất thông tin thời tiết); xây dựng nhánh đối chứng PCA (trung bình 9.8 thành phần "
    "giải thích ≥ 95% tổng phương sai trên 5 folds)."
)

add_bullet_item(
    "• Huấn luyện Mock ML Pipeline & Đánh giá TimeSeriesSplit Purged ([T3]): ",
    "Lập trình module mock_ml_pipeline.py huấn luyện và đánh giá chéo 5-fold TimeSeriesSplit kèm cơ chế Purging/Embargo chống rò rỉ dữ liệu (Data Leakage); "
    "so sánh hiệu năng giữa Random Forest và LightGBM trên cả 3 chân trời dự báo (t+15, t+30, t+60). Kết quả trên lớp kẹt xe nghiêm trọng (Lớp 2): "
    "LightGBM đạt Recall/F1 là 86.6%/88.4% (t+15), 89.5%/92.9% (t+30), 87.5%/90.8% (t+60); Random Forest đạt 84.8%/87.2% (t+15), 85.0%/85.0% (t+30), 96.4%/98.0% (t+60), "
    "chứng minh tính thông suốt của pipeline trước khi bước vào huấn luyện chính thức trên dữ liệu thật."
)

add_bullet_item(
    "• Dựng bản đồ GIS Folium kiểm tra tọa độ thực địa & Điểm ngập ([D1]): ",
    "Xây dựng công cụ build_gis_check_map.py xuất bản đồ tương tác hang_xanh_gis_check.html; kiểm tra tự động xác nhận 20/20 nút giao khớp tọa độ thực địa (sai số ≤ 5m), "
    "37/37 cạnh có chiều dài hợp lệ; đối chiếu chi tiết chiều đường thực tế trên OSMnx (xác nhận đúng chiều XVNT hướng Bắc, Đinh Bộ Lĩnh hướng Nam, cầu vượt Hàng Xanh); "
    "lập báo cáo gis_check_notes.md chuyển giao cho Trưởng nhóm xử lý 2 vấn đề biên mạng lưới."
)

add_bullet_item(
    "• Thử nghiệm tương thích SHAP TreeExplainer trên mô hình Mock ([D2]): ",
    "Lập trình script shap_smoke_test.py kiểm thử thành công tính tương thích của thư viện SHAP (0.49.1) với các mô hình cây quyết định (RandomForestClassifier, LGBMClassifier); "
    "đảm bảo giữ nguyên 31/31 tên biến gốc có ý nghĩa ngữ nghĩa (lượng mưa, triều cường, lưu lượng ngược dòng) để giải thích đóng góp của từng yếu tố, giải quyết triệt để tính chất hộp đen."
)

add_bullet_item(
    "• Khảo sát tài liệu khoa học 2022–2024 có DOI & Phân tích Research Gap ([S1]): ",
    "Biên soạn tài liệu literature_survey_notes.md khảo sát và xác minh nguồn gốc 4 công trình khoa học quốc tế và trong nước bám sát 4 trụ cột kỹ thuật: "
    "D2STGNN (VLDB 2022), STGAFormer (Information Fusion 2024), Amaral et al. (NHESS 2023 - ngập kép TP.HCM), KFGNN (Physica A 2023); "
    "xác định rõ khoảng trống nghiên cứu: chưa có giải pháp nào kết hợp đồng thời lan truyền sóng đồ thị với đặc thù ngập kép mưa/triều TP.HCM, SHAP XAI và AI Agent."
)

add_bullet_item(
    "• Thiết kế Ontology / Schema Traffic Knowledge Graph & Prototype NetworkX ([S2]): ",
    "Ban hành tài liệu traffic_kg_schema.md và module thực thi traffic_kg_schema.py; thiết lập ontology gồm 3 lớp Node (Intersection, FloodHotspot, WeatherCondition) "
    "và 3 lớp Edge (CONNECTS_TO, PRONE_TO_FLOOD, AFFECTED_BY_WEATHER); cài đặt hàm phạt trọng số di chuyển động effective_cost tự động định tuyến lộ trình né kẹt và ngập "
    "qua trục Nguyễn Gia Trí (D2) khi mưa > 30 mm/h."
)

add_bullet_item(
    "• Xác lập phương án thực nghiệm & Họp đồng bộ kỹ thuật, QA tích hợp ([H4], [H5]): ",
    "Tham vấn ThS. Đặng Việt Dũng chốt phạm vi bài toán và phương án 2 nhánh dữ liệu (sử dụng tập cảm biến METR-LA đối chứng thuật toán kết hợp dữ liệu Hàng Xanh mô phỏng tăng cường); "
    "tổ chức rà soát chéo chất lượng kỹ thuật (QA), khớp nối schema và merge thành công toàn bộ 7 Pull Request lên nhánh main GitHub."
)

# 3. PHÂN CÔNG THỰC HIỆN
add_section_title("Phân công thực hiện")

add_normal_p(
    "Nhằm tối ưu hóa năng suất và bảo đảm tiến độ theo mô hình Agile WBS, các đầu việc trong Tuần 4 được phân công "
    "chi tiết cho 5 thành viên theo bảng sau:"
)

# Table 1: WBS Assignment
wbs_data = [
    ("STT", "HỌ VÀ TÊN", "MSSV", "VAI TRÒ TRỌNG TÂM", "MÃ CÔNG VIỆC PHÂN CÔNG"),
    ("1", "Trần Hoàng Hôn", "26410046", "Trưởng nhóm / PM & Đồ thị giao thông", "[H1], [H2], [H3], [H4], [H5]"),
    ("2", "Nguyễn Duy Khang", "26410055", "Kỹ sư Dữ liệu & Feature Selection", "[K1], [K2]"),
    ("3", "Phạm Thành Trung", "26410141", "Kỹ sư AI & Mô hình hóa ML", "[T1], [T2], [T3]"),
    ("4", "Vũ Văn Duy", "26410031", "Kỹ sư Giải thích XAI & GIS Heatmap", "[D1], [D2]"),
    ("5", "Hoàng Cao Sơn", "25730061", "Kỹ sư Đồ thị tri thức (GraphRAG) & Agent", "[S1], [S2]")
]

table1 = doc.add_table(rows=len(wbs_data), cols=5)
table1.alignment = WD_TABLE_ALIGNMENT.CENTER
table1.style = 'Table Grid'
col_widths1 = [Inches(0.6), Inches(1.8), Inches(1.1), Inches(2.2), Inches(1.3)]

for r_idx, row in enumerate(wbs_data):
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
    "• Trần Hoàng Hôn — Đầu việc [H1] (11/11 – 12/11): ",
    "Chịu trách nhiệm chốt danh sách Nhóm 14, hoàn thiện nội dung và nộp đăng ký chính thức lên thư mục lớp DS_Nhom_CS315.G12.LT.TTNT.xlsx (Hoàn thành 100%)."
)
add_bullet_item(
    "• Trần Hoàng Hôn — Đầu việc [H2] (11/11 – 12/11): ",
    "Khởi tạo cấu trúc Repository chuẩn 5 thư mục chức năng, cấu hình chặt chẽ file .gitignore bảo vệ kho mã nguồn và danh mục thư viện requirements.txt (Hoàn thành 100%, Commit a35cd8b)."
)
add_bullet_item(
    "• Trần Hoàng Hôn — Đầu việc [H3] (12/11 – 13/11): ",
    "Lập trình công cụ trích xuất và lọc gọn mạng lưới đường OSMnx cụm Hàng Xanh, xuất các file nodes.csv, edges.csv, adjacency_matrix.csv và hang_xanh.graphml (Hoàn thành 100%, Commit 57dc344)."
)
add_bullet_item(
    "• Trần Hoàng Hôn — Đầu việc [H4] (13/11): ",
    "Xác lập phương án 2 nhánh dữ liệu thực nghiệm (METR-LA đối chứng & Hàng Xanh) và chuẩn hóa các nguyên tắc kỹ thuật cốt lõi (Hoàn thành 100%)."
)
add_bullet_item(
    "• Trần Hoàng Hôn — Đầu việc [H5] (16/11 – 19/11): ",
    "Điều phối họp sync kỹ thuật nhóm, kiểm tra chéo schema và mã nút node_id, review và merge toàn bộ 7 Pull Request vào nhánh main GitHub, cập nhật kế hoạch thực hiện đồ án (Hoàn thành 100%, PR #7)."
)

add_bullet_item(
    "• Nguyễn Duy Khang — Đầu việc [K1] (11/11 – 13/11): ",
    "Thiết kế Data Contract và xây dựng Từ điển đặc trưng feature_dictionary.md, quy định rõ quy tắc nội suy thời gian, phân loại biến số, Ordinal, Nominal và 3 cột nhãn (Hoàn thành 100%, PR #1)."
)
add_bullet_item(
    "• Nguyễn Duy Khang — Đầu việc [K2] (14/11 – 18/11): ",
    "Xây dựng module lựa chọn đặc trưng 2 nhánh 01_feature_selection_pipeline.py kết hợp nhánh đối chứng PCA, chạy kiểm thử thực nghiệm trên mock dataset và xuất báo cáo kết quả (Hoàn thành 100%, PR #3)."
)

add_bullet_item(
    "• Phạm Thành Trung — Đầu việc [T1] (11/11 – 13/11): ",
    "Thu thập mẫu dữ liệu thời tiết thực tế từ Open-Meteo API và chuẩn hóa bảng dữ liệu lịch triều cường trạm Phú An phu_an_tide_reference.csv (Hoàn thành 100%, PR #2)."
)
add_bullet_item(
    "• Phạm Thành Trung — Đầu việc [T2] (13/11 – 14/11): ",
    "Lập trình module build_mock_hang_xanh_dataset.py sinh 4.640 dòng dữ liệu giả lập không gian - thời gian phục vụ chạy thông suốt toàn bộ pipeline dự án (Hoàn thành 100%, PR #2)."
)
add_bullet_item(
    "• Phạm Thành Trung — Đầu việc [T3] (14/11 – 18/11): ",
    "Xây dựng module mock_ml_pipeline.py huấn luyện và đánh giá mô hình phân loại (Random Forest, LightGBM) qua 5-fold TimeSeriesSplit kèm cơ chế Purging/Embargo (Hoàn thành 100%, PR #2)."
)

add_bullet_item(
    "• Vũ Văn Duy — Đầu việc [D1] (13/11 – 18/11): ",
    "Lập trình công cụ build_gis_check_map.py xuất bản đồ tương tác Folium hang_xanh_gis_check.html, kiểm tra tính đúng đắn tọa độ thực địa và chiều lưu thông trên OSMnx (Hoàn thành 100%, PR #4)."
)
add_bullet_item(
    "• Vũ Văn Duy — Đầu việc [D2] (16/11 – 19/11): ",
    "Lập trình script shap_smoke_test.py kiểm thử độ tương thích của SHAP TreeExplainer trên các mô hình ML mock và xác nhận bảo toàn 31/31 tên biến gốc (Hoàn thành 100%, PR #6)."
)

add_bullet_item(
    "• Hoàng Cao Sơn — Đầu việc [S1] (11/11 – 13/11): ",
    "Khảo sát và xác minh nguồn gốc 4 công trình nghiên cứu khoa học giai đoạn 2022–2024 có DOI đầy đủ, phân tích ma trận so sánh và xác định rõ khoảng trống nghiên cứu (Hoàn thành 100%, PR #5)."
)
add_bullet_item(
    "• Hoàng Cao Sơn — Đầu việc [S2] (13/11 – 19/11): ",
    "Thiết kế Ontology / Schema Traffic Knowledge Graph trên NetworkX, lập trình module traffic_kg_schema.py và kiểm thử prototype thuật toán định tuyến né kẹt/ngập khi mưa lớn (Hoàn thành 100%, PR #5)."
)

# 4. KẾT QUẢ ĐẠT ĐƯỢC
add_section_title("Báo cáo quá trình thực hiện")

add_normal_p(
    "Dưới đây là báo cáo chi tiết về kết quả thực hiện, số liệu đo đạc thực nghiệm và các phát hiện kỹ thuật đạt được "
    "trong Tuần 4 của từng phân hệ:"
)

# 4.1 Hôn
add_normal_p("3.1. Quản trị dự án & Đồ thị mạng lưới giao thông OSMnx ([H1]–[H5] — Trần Hoàng Hôn)")
add_normal_p(
    "• Khởi tạo kiến trúc dự án & Data Contract ([H1], [H2]): Hoàn tất đăng ký đề tài chính thức cho Nhóm 14 trên biểu mẫu lớp. "
    "Thiết lập cấu trúc Repository chuẩn 5 thư mục (01_data_sample đến 05_report_slides) cùng file .gitignore loại trừ triệt để cache, "
    "môi trường ảo và dữ liệu dung lượng lớn. Ban hành requirements.txt khóa cứng các thư viện cốt lõi (osmnx 2.0.1, networkx 3.4.2, "
    "scikit-learn 1.5.2, lightgbm 4.5.0, shap 0.49.1, folium 0.18.0)."
)
add_normal_p(
    "• Trích xuất và chuẩn hóa đồ thị cụm Hàng Xanh ([H3]): Sử dụng OSMnx tải mạng lưới đường bộ trong bán kính 1.000m quanh ngã tư Hàng Xanh "
    "(tọa độ 10.8012, 106.7114). Thực hiện quy trình đơn giản hóa và rút gọn đồ thị: loại bỏ các nút phụ không phải giao lộ, gộp các cạnh ngắn, "
    "giữ lại 20 nút giao trọng điểm (HX_01 đến HX_20) trên 6 trục đường chính (Điện Biên Phủ, Xô Viết Nghệ Tĩnh, Đinh Bộ Lĩnh, Bạch Đằng, "
    "Nguyễn Gia Trí/D2, Ung Văn Khiêm) và 37 cạnh đường có hướng (E_01 đến E_37). Xuất thành công ma trận kề 20x20 adjacency_matrix.csv và file hang_xanh.graphml."
)
add_normal_p(
    "• Xác lập phương án thực nghiệm & Đồng bộ tích hợp ([H4], [H5]): Thống nhất lộ trình 2 nhánh dữ liệu Tuần 5: "
    "(1) Sử dụng bộ dữ liệu cảm biến thật METR-LA làm tập chuẩn đối chứng độ chính xác giải thuật; "
    "(2) Sử dụng tập dữ liệu Hàng Xanh mô phỏng tăng cường kết hợp thời tiết thực tế để chứng minh tính ứng dụng tại TP.HCM. Chủ trì buổi họp sync "
    "kỹ thuật ngày 16/11–17/11, rà soát mã nguồn, kiểm tra tính tương thích dữ liệu và hợp nhất sạch 7 Pull Request lên nhánh main vào ngày 19/11."
)

# 4.2 Khang
add_normal_p("3.2. Chuẩn hóa dữ liệu & Pipeline Lựa chọn đặc trưng ([K1], [K2] — Nguyễn Duy Khang)")
add_normal_p(
    "• Thiết kế Từ điển đặc trưng & Data Contract ([K1]): Hoàn thiện tài liệu feature_dictionary.md quy chuẩn toàn bộ 28 đặc trưng thô, "
    "sau khi mã hóa One-Hot đạt 31 đặc trưng đầu vào cho mô hình học máy. Phân định rõ 3 nhóm biến: (1) Biến số (22 biến): lượng mưa hiện tại rain_mm_h, "
    "mưa tích lũy 3 giờ rain_cum_3h_mm, mực nước triều tide_level_m, lưu lượng và vận tốc quá khứ các mốc trễ t-15, t-30, lưu lượng ngược dòng/xuôi dòng; "
    "(2) Biến thứ tự (3 biến): time_slot (4 khung giờ trong ngày), rain_level (4 cấp mưa), tide_alert (3 cấp báo động); "
    "(3) Biến danh mục (3 biến): road_type (primary, secondary, trunk), is_weekend, has_twoway. "
    "Chốt quy tắc nội suy tuyến tính bước nhảy 1 giờ từ Open-Meteo thành các mốc 15 phút."
)
add_normal_p(
    "• Xây dựng Module Lựa chọn đặc trưng 2 nhánh ([K2]): Lập trình hoàn chỉnh module 01_feature_selection_pipeline.py bám sát nội dung Buổi 2 của môn học:"
)
add_sub_bullet_item(
    "  - Nhánh lọc biến số: ",
    "Áp dụng VarianceThreshold(0.01) trên dữ liệu đã chuẩn hóa MinMax; quy trình loại bỏ thành công biến speed_delta1 do phương sai cực thấp (0.0039 < 0.01). "
    "Tính ma trận tương quan Pearson r giữa các biến số để phân tích đa cộng tuyến (phát hiện các cặp tương quan cao như temperature_c và humidity_pct r = -0.977, "
    "speed_kmh và speed_ratio r = 0.964); tuy nhiên, pipeline không dùng Pearson r để loại cứng nhằm bảo toàn trọn vẹn quan hệ phi tuyến của biến thời tiết và chuỗi trễ."
)
add_sub_bullet_item(
    "  - Nhánh lọc biến phân loại: ",
    "Áp dụng OneHotEncoder trên các biến danh mục (tạo 6 cột dummy: road_type 4 dummies, is_weekend 1 dummy, has_twoway 1 dummy) và thực hiện kiểm định Chi-square (χ² test). "
    "Đối với bài toán phân loại 3 lớp (Thông thoáng, Ùn ứ, Kẹt xe), bậc tự do df = c - 1 = 2, với mức ý nghĩa α = 0.05, nhóm sử dụng chính xác giá trị tới hạn χ² = 5.99; "
    "kết quả kiểm định loại bỏ biến dummy is_weekend_1 do không đạt ý nghĩa thống kê."
)
add_sub_bullet_item(
    "  - Kết quả chọn lọc & Nhánh đối chứng PCA: ",
    "Từ 31 đặc trưng mã hóa ban đầu, quy trình đã chọn lọc được đúng 29 đặc trưng tối ưu trên cả 3 chân trời dự báo (t+15, t+30, t+60), đạt tỷ lệ rút gọn 6.5% "
    "mà vẫn bảo toàn 100% biến thời tiết và cấu trúc đồ thị. Nhánh đối chứng PCA cấu hình giữ ≥ 95% tổng phương sai (PCA_VARIANCE = 0.95), "
    "kết quả thực nghiệm xác định trung bình cần 9.8 thành phần chính trên 5 folds, phục vụ làm nhánh thử nghiệm đối chứng với mô hình cây."
)

# 4.3 Trung
add_normal_p("3.3. Dữ liệu thời tiết - triều cường & Mô hình hóa Machine Learning ([T1], [T2], [T3] — Phạm Thành Trung)")
add_normal_p(
    "• Thu thập dữ liệu ngoại sinh thực địa ([T1]): Hoàn thiện script trích xuất 72 mốc dữ liệu thời tiết từ Open-Meteo API tại tọa độ Hàng Xanh. "
    "Chuẩn hóa bảng lịch triều cường trạm Phú An phu_an_tide_reference.csv dựa trên Bản tin 307/2026 của Đài Khí tượng Thủy văn Nam Bộ, "
    "ghi nhận các đợt triều cực trị đạt 1.50m – 1.62m (vượt mức Báo động 2 và chạm Báo động 3)."
)
add_normal_p(
    "• Phát triển Mock Spatio-Temporal Dataset ([T2]): Xây dựng script build_mock_hang_xanh_dataset.py kết hợp cấu trúc đồ thị 20 nút từ [H3], "
    "chuỗi thời tiết từ [T1] và schema từ [K1]. Sinh thành công 4.640 bản ghi (232 mốc thời gian 15 phút × 20 nút), tích hợp 6 kịch bản mưa stress test "
    "rải đều qua các fold dữ liệu. Tập dữ liệu giả lập mô phỏng chân thực quy luật lan truyền ùn tắc từ nút nguồn ra các nút lân cận sau 15–60 phút."
)
add_normal_p(
    "• Xây dựng Mock ML Pipeline & Thẩm định rủi ro ([T3]): Thiết lập quy trình đánh giá 5-fold TimeSeriesSplit kèm khoảng cách ly (Purging/Embargo "
    "tương ứng 1, 2, 4 bước trễ cho các nhãn t+15, t+30, t+60) để triệt tiêu hiện tượng rò rỉ dữ liệu chuỗi thời gian. Huấn luyện và đánh giá 2 kiến trúc:"
)
add_sub_bullet_item(
    "  - Mô hình LightGBM: ",
    "Đạt hiệu năng vượt chỉ tiêu trên lớp kẹt xe nghiêm trọng (Lớp 2): Tại t+15 đạt Recall = 86.6%, Precision = 93.9%, F1 = 88.4%, PR-AUC = 0.973; "
    "Tại t+30 đạt Recall = 89.5%, Precision = 99.5%, F1 = 92.9%, PR-AUC = 0.998; Tại t+60 đạt Recall = 87.5%, Precision = 99.8%, F1 = 90.8%, PR-AUC = 0.993."
)
add_sub_bullet_item(
    "  - Mô hình Random Forest: ",
    "Tại t+15 đạt Recall = 84.8% (xấp xỉ ngưỡng 85%), Precision = 94.6%, F1 = 87.2%, PR-AUC = 0.993; Tại t+30 đạt Recall = 85.0%, Precision = 90.9%, F1 = 85.0%, PR-AUC = 0.999; "
    "Tại t+60 đạt Recall = 96.4%, Precision = 100%, F1 = 98.0%, PR-AUC = 1.000. Cả 2 mô hình đã thông suốt luồng huấn luyện - thẩm định; độ lệch chuẩn Recall giữa các fold "
    "còn cao (std ~ 0.23 - 0.29) do kịch bản mưa giả lập phân bố không đều giữa các fold, sẽ được đánh giá ổn định hơn trên dữ liệu cảm biến thật trong Tuần 5."
)

# 4.4 Sơn
add_normal_p("3.4. Khảo sát tài liệu khoa học & Đồ thị tri thức Traffic KG ([S1], [S2] — Hoàng Cao Sơn)")
add_normal_p(
    "• Khảo sát tài liệu & Xác minh nguồn gốc nghiên cứu ([S1]): Hoàn thiện tài liệu literature_survey_notes.md, đối chiếu và thay thế các trích dẫn "
    "sơ bộ bằng 4 công trình khoa học quốc tế và trong nước giai đoạn 2022–2024 có chỉ số DOI hợp lệ:"
)
add_sub_bullet_item(
    "  - [Ref-1] D2STGNN (VLDB 2022, DOI: 10.14778/3551793.3551827): ",
    "Chứng minh ưu thế của mô hình đồ thị động phi Euclid trong việc tách biệt luồng khuếch tán giao thông trên tập METR-LA."
)
add_sub_bullet_item(
    "  - [Ref-2] STGAFormer (Information Fusion 2024, DOI: 10.1016/j.inffus.2024.102228): ",
    "Ứng dụng cơ chế Gated Attention Transformer kết hợp GNN để nắm bắt trọng số phụ thuộc động giữa các nút giao."
)
add_sub_bullet_item(
    "  - [Ref-3] Amaral et al. (NHESS 2023, DOI: 10.5194/nhess-23-3379-2023): ",
    "Phân tích định lượng hiện tượng ngập kép do tương tác giữa mưa lớn và triều cường tại TP.HCM, cung cấp cơ sở đưa biến ngoại sinh vào mô hình."
)
add_sub_bullet_item(
    "  - [Ref-4] KFGNN (Physica A 2023, DOI: 10.1016/j.physa.2023.128842): ",
    "Đề xuất mô-đun tích hợp tri thức ngữ cảnh đồ thị nhằm nâng cao chất lượng dự báo điểm nghẽn."
)
add_normal_p(
    "• Thiết kế Ontology & Prototype Traffic Knowledge Graph ([S2]): Xây dựng tài liệu traffic_kg_schema.md và module thực thi traffic_kg_schema.py. "
    "Ontology gồm 3 loại Node (Intersection: 20 nút, FloodHotspot: 3 điểm trũng ngập Đinh Bộ Lĩnh, XVNT gần Bình Triệu, Ung Văn Khiêm, WeatherCondition: thời tiết hiện tại) "
    "và 3 loại quan hệ Edge (CONNECTS_TO, PRONE_TO_FLOOD, AFFECTED_BY_WEATHER). Cài đặt hàm phạt chi phí di chuyển động effective_cost: nhân hệ số phạt kẹt xe "
    "(α = 6.0 cho lớp 2) và phạt ngập nước (β = 4.5 khi mưa > 30 mm/h). Thử nghiệm định tuyến prototype tự động né cụm Hàng Xanh – Đinh Bộ Lĩnh và điều hướng sang "
    "trục đường Nguyễn Gia Trí (D2)."
)

# 4.5 Duy
add_normal_p("3.5. Kiểm tra thực địa GIS Folium & Thử nghiệm giải thích XAI ([D1], [D2] — Vũ Văn Duy)")
add_normal_p(
    "• Kiểm chứng GIS thực địa bằng Folium ([D1]): Lập trình công cụ build_gis_check_map.py tạo bản đồ trực quan hang_xanh_gis_check.html. "
    "Kết quả kiểm tra tự động xác nhận 20/20 nút giao khớp hoàn toàn với thực địa (sai số vị trí ≤ 5m), 37/37 cạnh đường có chiều dài thực tế hợp lệ "
    "(tỷ lệ đường thực tế so với đường chim bay từ 0.9 đến 2.0). Đối chiếu chi tiết với dữ liệu OpenStreetMap xác nhận: trục Xô Viết Nghệ Tĩnh (phía Bắc) "
    "và Đinh Bộ Lĩnh tạo thành cặp đường một chiều hoàn chỉnh; nhánh cầu vượt Hàng Xanh (E_07, E_10) được tách riêng tầng lưu thông. "
    "Phát hiện và bàn giao 2 điểm nghi vấn biên mạng lưới (thiếu cạnh ngược chiều 20→17 và tính nhất quán cờ oneway đường Nguyễn Gia Trí) cho Trưởng nhóm xử lý."
)
add_normal_p(
    "• Thử nghiệm khói tính tương thích SHAP TreeExplainer ([D2]): Xây dựng script shap_smoke_test.py kiểm thử khả năng giải thích của SHAP (phiên bản 0.49.1) "
    "trên 2 mô hình mock y_t15 (RandomForestClassifier và LGBMClassifier). Kết quả kiểm thử thành công 100%: script tự động tách lớp tiền xử lý One-Hot để truyền "
    "đúng dữ liệu số vào TreeExplainer, bảo toàn đầy đủ 31/31 tên biến gốc từ feature_dictionary.md. Khẳng định SHAP sẵn sàng phân tích bóc tách định lượng "
    "mức độ đóng góp của từng biến ngoại sinh (lượng mưa mm/h, đỉnh triều, lưu lượng nút nguồn) trong các tuần tiếp theo."
)

# Table 2: Quantitative Measurements
add_normal_p("Bảng tổng hợp số liệu đo đạc thực nghiệm định lượng trong Tuần 4:")

metrics_data = [
    ("HẠNG MỤC THỰC NGHIỆM", "CẤU HÌNH / THÔNG SỐ", "KẾT QUẢ ĐẠT ĐƯỢC", "ĐÁNH GIÁ KỸ THUẬT"),
    ("Đồ thị mạng lưới Hàng Xanh", "OSMnx 2.0.1, R = 1.000m, drive network", "20 nút giao, 37 cạnh có hướng", "Đầy đủ 6 trục đường chính, ma trận kề 20x20"),
    ("Tập dữ liệu giả lập (Mock)", "232 mốc thời gian (15') × 20 nút, 6 kịch bản mưa", "4.640 dòng, 28 đặc trưng thô + 3 nhãn", "Giải phóng phụ thuộc dữ liệu cho cả nhóm"),
    ("Lựa chọn đặc trưng (FS)", "VarianceThreshold (0.01) + Chi2 (5.99)", "31 đặc trưng → 29 đặc trưng (giảm 6.5%)", "Loại speed_delta1 và is_weekend_1, giữ biến thời tiết"),
    ("Nhánh đối chứng PCA", "StandardScaler + PCA (giữ ≥ 95% phương sai)", "9.8 thành phần chính (trung bình 5 folds)", "Rút gọn chiều hiệu quả cho bài toán đối chứng"),
    ("Hiệu năng LightGBM (Lớp 2)", "5-fold TimeSeriesSplit Purged (t+15/t+30/t+60)", "Recall: 86.6% / 89.5% / 87.5% | F1: 88.4% / 92.9% / 90.8%", "Vượt chỉ tiêu đề cương (Recall ≥ 85%, F1 ≥ 80%)"),
    ("Hiệu năng Random Forest (Lớp 2)", "5-fold TimeSeriesSplit Purged (t+15/t+30/t+60)", "Recall: 84.8% / 85.0% / 96.4% | F1: 87.2% / 85.0% / 98.0%", "t+15 xấp xỉ 85%, t+30 và t+60 vượt chỉ tiêu"),
    ("Kiểm tra thực địa GIS", "Folium 0.18.0, đối chiếu OpenStreetMap", "20/20 nút khớp (≤ 5m), 37/37 cạnh hợp lệ", "Khớp thực địa, phát hiện 2 điểm cần tinh chỉnh"),
    ("Tương thích giải thích SHAP", "TreeExplainer, shap 0.49.1 trên RF & LightGBM", "Chạy thông 100%, bảo toàn 31/31 tên biến", "Sẵn sàng bóc tách yếu tố thời tiết mưa ngập"),
    ("Định tuyến Traffic KG", "NetworkX MultiDiGraph, mưa > 30mm/h", "Hệ số phạt α=6.0, β=4.5; né vùng lõi Hàng Xanh", "Chuyển hướng thành công sang Nguyễn Gia Trí (D2)")
]

table2 = doc.add_table(rows=len(metrics_data), cols=4)
table2.alignment = WD_TABLE_ALIGNMENT.CENTER
table2.style = 'Table Grid'
col_widths2 = [Inches(1.8), Inches(2.0), Inches(1.8), Inches(1.4)]

for r_idx, row in enumerate(metrics_data):
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
    "Trong Tuần 5 (từ ngày 18/11/2026 đến ngày 24/11/2026), nhóm tiến hành chuyển giao toàn bộ luồng công việc từ "
    "môi trường Mock Stub sang Dữ liệu thật và Huấn luyện mô hình chuyên sâu (theo phương án 2 nhánh dữ liệu đã thống nhất với Giảng viên hướng dẫn). "
    "Kế hoạch chi tiết được phân bổ cho từng thành viên như sau:"
)

add_bullet_item(
    "• Trần Hoàng Hôn ([H1], [H2], [H3] — Trưởng nhóm & Quản trị dữ liệu đồ thị): ",
    "Xử lý dứt điểm 2 lỗi biên đồ thị OSMnx do Duy phát hiện (bổ sung cạnh 20→17 trên trục Xô Viết Nghệ Tĩnh và chuẩn hóa cờ oneway đường Nguyễn Gia Trí); "
    "tiếp nhận và tiền xử lý bộ dữ liệu cảm biến chuẩn METR-LA (207 cảm biến cao tốc) để sẵn sàng làm tập đối chứng thuật toán; "
    "điều phối cập nhật tiến độ đồ án trên hệ thống quản lý WBS."
)

add_bullet_item(
    "• Nguyễn Duy Khang ([K1], [K2] — Kỹ sư Dữ liệu & Lựa chọn đặc trưng): ",
    "Đóng gói pipeline lựa chọn đặc trưng 2 nhánh thành notebook hoàn chỉnh 01_Feature_Selection.ipynb; chạy thử nghiệm và đánh giá độ suy giảm "
    "phương sai trên tập dữ liệu thật; xuất bảng tổng hợp xếp hạng tầm quan trọng đặc trưng (Feature Importance Ranking) và ma trận tương quan phục vụ phân tích."
)

add_bullet_item(
    "• Phạm Thành Trung ([T1], [T2], [T3] — Kỹ sư AI & Mô hình hóa Machine Learning): ",
    "Xây dựng notebook huấn luyện chính thức 02_Model_Training.ipynb; triển khai huấn luyện song song các mô hình baseline (Random Forest, LightGBM, XGBoost) "
    "trên tập chuẩn METR-LA và tập Hàng Xanh mở rộng; áp dụng công cụ Optuna tối ưu hóa siêu tham số (Hyperparameter Tuning) và tinh chỉnh ngưỡng phân loại "
    "(Threshold Tuning) nhằm tối đa hóa chỉ số Recall lớp kẹt xe nghiêm trọng."
)

add_bullet_item(
    "• Vũ Văn Duy ([D1], [D2] — Kỹ sư Giải thích XAI & Trực quan hóa): ",
    "Triển khai phân tích SHAP values toàn diện trên các mô hình huấn luyện chính thức: xuất biểu đồ tổng quan SHAP Summary Plot, biểu đồ lực ép Force Plot "
    "và phân tích tương tác SHAP Dependence Plot cho các biến ngoại sinh (lượng mưa mm/h, đỉnh triều m); xây dựng nguyên mẫu bản đồ nhiệt trực quan hóa "
    "sự lan truyền sóng ùn tắc theo thời gian thực trên nền Folium."
)

add_bullet_item(
    "• Hoàng Cao Sơn ([S1], [S2] — Kỹ sư Đồ thị tri thức & AI Agent): ",
    "Xây dựng notebook nguyên mẫu 03_Traffic_KG_Agent_Demo.ipynb; kết nối đồ thị tri thức NetworkX với mô hình ngôn ngữ lớn (LLM Agent qua cơ chế Tool-calling) "
    "nhằm tự động hóa việc truy vấn trạng thái ùn tắc, diễn giải lý do kẹt xe do mưa ngập và đề xuất lộ trình thay thế tối ưu theo thời gian thực."
)

out_dir_1 = r"D:\Trí tuệ nhân tạo\HK3\Máy học nâng cao\Đồ án\05_report_slides"
out_path_1 = os.path.join(out_dir_1, "Bao_Cao_Tuan_4.docx")
out_path_2 = r"D:\Trí tuệ nhân tạo\HK3\Máy học nâng cao\Đồ án\Bao_Cao_Tuan_4.docx"

os.makedirs(out_dir_1, exist_ok=True)
doc.save(out_path_1)
shutil.copyfile(out_path_1, out_path_2)
print("SUCCESS: Updated both docx files successfully!")
