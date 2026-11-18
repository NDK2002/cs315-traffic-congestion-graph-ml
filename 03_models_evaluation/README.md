# 03_models_evaluation — Huấn luyện mô hình ML/GNN & Giải thích XAI

* **Phụ trách chính:** Phạm Thành Trung (`[T3]`), Vũ Văn Duy (`[D2]`)
* **Sản phẩm dự kiến:**
* `mock_ml_pipeline.py` (`[T3]`): chia `TimeSeriesSplit` theo `unique timestamp`, purge theo horizon, baseline `RandomForest`/`LightGBM` với `class_weight='balanced'`, đo `Recall`/`Precision`/`F1` lớp `2`, `Macro-F1`, OvR Average Precision (PR-AUC) & `Confusion Matrix`
  * `results/mock_cv_fold_metrics.csv`, `mock_cv_summary.csv`, `mock_cv_confusion_matrices.json`: kết quả đánh giá mock theo fold, nhãn `y_t15`, `y_t30`, `y_t60`
  * `results/*_feature_names.json`: danh sách đặc trưng sau mã hóa One-Hot, phục vụ Duy (`[D2]`) giải thích SHAP
  * `results/*_y_t15_mock.joblib`: model $t+15$ được sinh tự động bởi `mock_ml_pipeline.py` (được bỏ qua trong Git `.gitignore` để tránh phình dung lượng kho mã nguồn)
  * Smoke-test `shap.TreeExplainer` trên tên biến gốc (`[D2]`)
  * `02_Model_Training.ipynb` (Tuần 5–6): import module `.py` tại thư mục này để huấn luyện Baseline ML, ST-GNN và xuất biểu đồ SHAP

Cross-validation gom toàn bộ nút theo timestamp trước khi chia nên không có cùng một thời điểm ở cả train và validation. Mỗi chân trời có `gap` bằng đúng số bước dự báo (1/2/4 mốc 15 phút), để nhãn ở cuối tập train không chứa kết quả xảy ra trong kỳ validation. Preprocessing One-Hot được fit trong từng fold. Cờ `rain_scenario_synthetic` không nằm trong danh sách đặc trưng.

Kết quả hiện tại trên mock sau khi purge nhãn: LightGBM đạt Recall/F1 lớp 2 `0.866 / 0.884`, `0.895 / 0.929`, `0.875 / 0.908` và Macro-F1 `0.834 / 0.793 / 0.707` tại `t+15 / t+30 / t+60`; Random Forest đạt Recall/F1 lớp 2 `0.848 / 0.872`, `0.850 / 0.850`, `0.964 / 0.980` và Macro-F1 `0.857 / 0.794 / 0.738`. Độ lệch chuẩn Recall lớp 2 khá cao giữa các fold, nên đây chỉ là kiểm tra pipeline trên dữ liệu tổng hợp có mưa stress, không phải bằng chứng về hiệu năng giao thông thật. Xem CSV để có đầy đủ metric từng fold.

Để tạo model và chạy kiểm tra SHAP cục bộ (chạy `python 03_models_evaluation/mock_ml_pipeline.py` để sinh file `.joblib`):

```python
pipe = joblib.load("03_models_evaluation/results/randomforest_y_t15_mock.joblib")
x_encoded = pipe.named_steps["preprocess"].transform(x_raw)
if hasattr(x_encoded, "toarray"):
    x_encoded = x_encoded.toarray()
explainer = shap.TreeExplainer(pipe.named_steps["classifier"])
```

Dùng danh sách `*_feature_names.json` tương ứng để đặt tên cột one-hot; không cần PCA.

