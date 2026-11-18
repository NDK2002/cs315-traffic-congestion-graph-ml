# 03_models_evaluation — Huấn luyện mô hình ML/GNN & Giải thích XAI

* **Phụ trách chính:** Phạm Thành Trung (`[T3]`), Vũ Văn Duy (`[D2]`)
* **Sản phẩm dự kiến:**
  * `mock_ml_pipeline.py` (`[T3]`): chia `TimeSeriesSplit` theo `unique timestamp`, baseline `RandomForest`/`LightGBM` với `class_weight='balanced'`, đo `Recall` lớp `2`, `Macro-F1`, One-vs-Rest `PR-AUC` lớp `2` & `Confusion Matrix`
  * `shap_smoke_test.py` (`[D2]`): smoke-test `shap.TreeExplainer` trên `RandomForest`/`LightGBM` 3 lớp với tên biến gốc theo `feature_dictionary.md`. Chưa có model `[T3]` thì chạy trên dữ liệu giả. Khi có model: `python 03_models_evaluation/shap_smoke_test.py --model <model.joblib> --data <X_valid.csv>`. Lưu ý: SHAP của `RandomForest` tính theo xác suất, của `LightGBM` theo log-odds, nên chỉ so thứ hạng biến trong từng model, không so độ lớn giữa hai model
  * `02_Model_Training.ipynb` (Tuần 5–6): import module `.py` tại thư mục này để huấn luyện Baseline ML, ST-GNN và xuất biểu đồ SHAP

