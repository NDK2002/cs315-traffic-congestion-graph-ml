# 04_knowledge_graph_demo — Traffic Knowledge Graph & AI Agent

* **Phụ trách chính:** Hoàng Cao Sơn (`[S1]`, `[S2]`)
* **Sản phẩm:**
  * `traffic_kg_schema.md`: đặc tả Ontology (Nút giao – Tuyến đường – Điểm ngập – Trạng thái ùn tắc – Lộ trình thay thế)
  * `traffic_kg_schema.py`: module dựng đồ thị tri thức `NetworkX` (`24` nút gồm `20` nút giao + `3` điểm ngập + `1` trạng thái thời tiết, `38` cạnh vật lý đồng bộ cờ `flood_prone` của `[H1]`)
  * `dynamic_routing.py` (`[S1]` Tuần 6): thuật toán Dynamic Dijkstra (`find_optimal_route`) tính trọng số động theo xác suất kẹt $P(y=2)$ và vùng ngập `flood_prone`, trả về JSON giải thích lộ trình né ngập/né kẹt cho AI Agent
  * `tests/test_dynamic_routing.py`: unit/smoke test kiểm chứng đồng bộ `flood_prone`, đổi đường né ngập khi mưa lớn, ngưỡng hotspot và không mutate đồ thị đầu vào
  * `03_Traffic_KG_Agent_Demo.ipynb` (`[S2]` Tuần 6–7): tích hợp `dynamic_routing.py` với kết quả dự báo ML và AI Agent Tool-calling

## Chạy nhanh

```bash
python 04_knowledge_graph_demo/dynamic_routing.py
python -m pytest 04_knowledge_graph_demo/tests -q
```

