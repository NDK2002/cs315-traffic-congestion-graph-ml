# 03_models_evaluation — Huấn luyện mô hình ML/GNN & Giải thích XAI

* **Phụ trách chính:** Phạm Thành Trung (`[T3]`), Vũ Văn Duy (`[D2]`)
* **Sản phẩm dự kiến:**
  * `mock_ml_pipeline.py` (`[T3]`): chia `TimeSeriesSplit` theo `unique timestamp`, purge theo horizon, baseline `RandomForest`/`LightGBM` với `class_weight='balanced'`, đo `Recall`/`Precision`/`F1` lớp `2`, `Macro-F1`, OvR Average Precision (PR-AUC) & `Confusion Matrix`
    * `results/mock_cv_fold_metrics.csv`, `mock_cv_summary.csv`, `mock_cv_confusion_matrices.json`: kết quả đánh giá mock theo fold, nhãn `y_t15`, `y_t30`, `y_t60`
    * `results/*_feature_names.json`: danh sách đặc trưng sau mã hóa One-Hot, phục vụ Duy (`[D2]`) giải thích SHAP
    * `results/*_y_t15_mock.joblib`: model $t+15$ được sinh tự động bởi `mock_ml_pipeline.py` (được bỏ qua trong Git `.gitignore` để tránh phình dung lượng kho mã nguồn)
  * `shap_smoke_test.py` (`[D2]`): smoke-test `shap.TreeExplainer` trên `RandomForest`/`LightGBM` 3 lớp với tên biến gốc theo `feature_dictionary.md`. Không truyền `--model` thì chạy trên dữ liệu giả. Với model `[T3]` (sklearn `Pipeline`, script tự tách One-Hot + classifier): `python 03_models_evaluation/shap_smoke_test.py --model 03_models_evaluation/results/randomforest_y_t15_mock.joblib 03_models_evaluation/results/lightgbm_y_t15_mock.joblib --data 01_data_sample/mock_hang_xanh_traffic_weather.csv`. Đã chạy thông ngày `19/11/2026`: cả 2 model giữ đủ `31/31` tên biến gốc, SHAP lớp `2` kích thước `(300, 31)`. Lưu ý: SHAP của `RandomForest` tính theo xác suất, của `LightGBM` theo log-odds, nên chỉ so thứ hạng biến trong từng model, không so độ lớn giữa hai model.
  * `shap_analysis.py` (Tuần 6, Duy): dùng lại cấu hình model `[T3]`, chia theo thời gian (80% đầu để học, phần cuối để giải thích), tính SHAP lớp `2` cho `y_t15`, `y_t30`, `y_t60`. Xuất Summary Plot, Dependence Plot mưa/triều, Force Plot tại các nút chọn trong cơn mưa giả lập, bảng đóng góp theo biến và theo nhóm biến vào `results/shap/`. Chạy: `python 03_models_evaluation/shap_analysis.py`. Kết quả và giới hạn xem `shap_analysis_notes.md`.
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

