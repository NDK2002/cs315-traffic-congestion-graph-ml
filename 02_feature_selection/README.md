# 02_feature_selection — Data Contract & Lựa chọn đặc trưng

* **Phụ trách chính:** Nguyễn Duy Khang (`[K1]`, `[K2]`)
* **Sản phẩm:**
  * `feature_dictionary.md`: schema cột, đơn vị, quy tắc nội suy `1h -> 15'`, phân loại biến số / *Ordinal* / *Nominal* và 3 cột nhãn `y_t15`, `y_t30`, `y_t60`. Tuần 6 bổ sung cờ tĩnh `flood_prone`
  * `01_feature_selection_pipeline.py`:
    * `load_dataset()`: đọc mock dataset và ghép `flood_prone` từ `01_data_sample/nodes.csv` (`[H1]`) theo `node_id`
    * `FeatureSelector`: nhánh chính, dùng cho mô hình cây và SHAP. Gồm nhánh số (`VarianceThreshold`, `Pearson r` chỉ để tham khảo) và nhánh phân loại (`OrdinalEncoder` / `OneHotEncoder` + $\chi^2 > 5.99$). Đầu ra giữ giá trị và tên cột gốc.
    * `PCAFeatureSelector`: nhánh đối chứng `PCA` (95% phương sai), tách riêng.
    * Cả hai đều là transformer của sklearn. Đặt vào `Pipeline` thì mỗi fold chỉ `fit` trên tập train, không rò rỉ dữ liệu.
    * Tuần 6: xếp hạng Mutual Information và tập rút gọn cho ST-GNN (`prune_collinear`). Cả hai đều tính trên phần train của từng fold.
  * `01_Feature_Selection.ipynb`: notebook chạy module, trình bày kết quả, biểu đồ và hướng dẫn dựng tensor `X (T, N, F)` cho ST-GNN
  * `tests/test_feature_selection.py`: smoke test (ghép `flood_prone`, chống rò rỉ, bảo vệ biến mưa/triều, định dạng file kết quả)
  * `results/` (sinh ra khi chạy module trên mock dataset):
    * `selected_features.json`, với mỗi nhãn:
      * `selected` / `dropped`: kết quả lọc Variance + $\chi^2$ (giữ nếu được chọn ở đa số fold `TimeSeriesSplit`). Dùng cho mô hình cây + SHAP
      * `selected_compact`: `selected` trừ các biến đa cộng tuyến (`collinear_dropped`: cặp $|r| \ge 0.9$, bỏ biến có MI thấp hơn; **không bao giờ bỏ biến mưa/triều**). Khuyến nghị cho ST-GNN
      * `stgnn.dynamic` / `stgnn.static`: `selected_compact` chia theo đặc trưng động (theo bước 15') và thuộc tính tĩnh của nút
    * `feature_importance_ranking.csv`: hạng theo Mutual Information (trung bình 5 fold) của toàn bộ 32 cột mã hóa, kèm nhóm, trạng thái chọn và mean |SHAP| của `[D2]` để đối chiếu
    * `feature_selection_report.csv`: điểm phương sai, $\chi^2$, p-value, tần suất được chọn và Pearson với nhãn của từng đặc trưng
    * `pearson_redundant_pairs.csv`: các cặp đặc trưng số có $|r| \ge 0.9$
    * `dimension_summary.csv`: số chiều trước/sau lọc, tập rút gọn và nhánh PCA

## Kết quả hiện tại (mock 4.640 dòng, 5 fold)

| | Số cột | Giảm |
| :--- | :---: | :---: |
| Sau mã hóa | 32 | — |
| `selected` (Variance + $\chi^2$) | 30 | 6.2% |
| `selected_compact` (ST-GNN) | 27 (15 động + 12 tĩnh) | 15.6% |
| Nhánh PCA (đối chứng) | 19 | 40.6% |

* Bị loại khi lọc: `speed_delta1` (phương sai thấp), `is_weekend_1` (không đạt $\chi^2$)
* Bị loại do đa cộng tuyến: `speed_kmh` (giữ `speed_ratio`), `speed_lag2` (giữ `speed_lag1`), `temperature_c` (giữ `humidity_pct`)
* `flood_prone_1` đạt $\chi^2 \approx 76$ ở cả 3 mốc. Tỉ lệ kẹt nặng ở nút ngập là 20.7%, ở nút khác là 7.4%
* **Lưu ý khi đọc MI:** biến thời tiết/triều có giá trị chung cho mọi nút tại một mốc, và mock chỉ dài khoảng 2,4 ngày, nên MI của chúng bị thổi phồng (biến đóng vai trò "đồng hồ"). Xem mục 6 của notebook

## Chạy

```bash
python 02_feature_selection/01_feature_selection_pipeline.py            # mặc định: mock Hàng Xanh
python 02_feature_selection/01_feature_selection_pipeline.py --data <file.csv> --nodes <nodes.csv> --output-dir <thư mục>
python -m pytest 02_feature_selection/tests -q                          # smoke test
```

## Dùng trong pipeline huấn luyện (`[T2]`, notebook)

Tên file bắt đầu bằng chữ số nên phải import qua `importlib`:

```python
import importlib, json, sys
from sklearn.pipeline import Pipeline

sys.path.insert(0, "02_feature_selection")
fs = importlib.import_module("01_feature_selection_pipeline")

frame = fs.load_dataset()  # đã có cột flood_prone
pipe = Pipeline([("select", fs.FeatureSelector()), ("model", LGBMClassifier(class_weight="balanced"))])
pipe.fit(train[fs.ALL_FEATURES], train["y_t15"])
pipe.named_steps["select"].get_feature_names_out()  # tên gốc, dùng cho SHAP

# ST-GNN: danh sách đặc trưng đã chốt
cfg = json.load(open("02_feature_selection/results/selected_features.json", encoding="utf-8"))
features = cfg["y_t15"]["stgnn"]["dynamic"] + cfg["y_t15"]["stgnn"]["static"]
```
