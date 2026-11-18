# 02_feature_selection — Data Contract & Lựa chọn đặc trưng

* **Phụ trách chính:** Nguyễn Duy Khang (`[K1]`, `[K2]`)
* **Sản phẩm:**
  * `feature_dictionary.md` (`[K1]`): schema cột, đơn vị, quy tắc nội suy `1h -> 15'`, phân loại biến số / *Ordinal* / *Nominal* và 3 cột nhãn `y_t15`, `y_t30`, `y_t60`
  * `01_feature_selection_pipeline.py` (`[K2]`):
    * `FeatureSelector`: nhánh chính, dùng cho mô hình cây và SHAP. Gồm nhánh số (`VarianceThreshold`, `Pearson r` chỉ để tham khảo) và nhánh phân loại (`OrdinalEncoder` / `OneHotEncoder` + $\chi^2 > 5.99$). Đầu ra giữ giá trị và tên cột gốc.
    * `PCAFeatureSelector`: nhánh đối chứng `PCA` (95% phương sai), tách riêng.
    * Cả hai đều là transformer của sklearn. Đặt vào `Pipeline` thì mỗi fold chỉ `fit` trên tập train, không rò rỉ dữ liệu.
  * `results/` (sinh ra khi chạy module trên mock dataset):
    * `selected_features.json`: đặc trưng được chọn / bị loại cho từng nhãn (giữ nếu được chọn ở đa số fold `TimeSeriesSplit`)
    * `feature_selection_report.csv`: điểm phương sai, $\chi^2$, p-value, tần suất được chọn và Pearson với nhãn của từng đặc trưng
    * `pearson_redundant_pairs.csv`: các cặp đặc trưng số có $|r| \ge 0.9$ (chỉ để tham khảo)
    * `dimension_summary.csv`: số chiều trước/sau khi lọc và số thành phần PCA
  * `01_Feature_Selection.ipynb` (Tuần 5): import module `.py` tại thư mục này

## Chạy

```bash
python 02_feature_selection/01_feature_selection_pipeline.py            # mặc định: mock Hàng Xanh
python 02_feature_selection/01_feature_selection_pipeline.py --data <file.csv> --output-dir <thư mục>
```

## Dùng trong pipeline huấn luyện (`[T3]`, notebook)

Tên file bắt đầu bằng chữ số nên phải import qua `importlib`:

```python
import importlib, sys
from sklearn.pipeline import Pipeline

sys.path.insert(0, "02_feature_selection")
fs = importlib.import_module("01_feature_selection_pipeline")

pipe = Pipeline([("select", fs.FeatureSelector()), ("model", LGBMClassifier(class_weight="balanced"))])
pipe.fit(train[fs.ALL_FEATURES], train["y_t15"])
pipe.named_steps["select"].get_feature_names_out()  # tên gốc, dùng cho SHAP
```
