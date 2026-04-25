# Alex — trợ lý FlexFit Gym

**Alex** là trợ lý ảo tư vấn trực tuyến cho **FlexFit Gym**, một trung tâm thể hình (mô tả demo) với tiện ích như hồ bơi, sauna, lớp nhóm, PT, v.v. Alex hỗ trợ khách bằng **tiếng Việt**: tìm gói tập phù hợp, trả lời thắc mắc về chính sách/điều khoản, và hướng dẫn **đặt lịch tập thử** — ưu tiên thông tin **có nguồn** (API, RAG) thay vì tự bịa.

Dự án xây dạng **agent nhiều tác vụ** trên **LangGraph**, tách đồ thị theo **intent** (tư vấn / chính sách / đặt lịch) và dùng **công cụ (tools)** tương tác với backend HTTP và kho tài liệu nội bộ.

---

## Luồng hoạt động (tóm tắt)

1. **Router** — phân loại `consult` | `policy` | `booking` dựa trên tin nhắn mới (có hỗ trợ ngữ cảnh hội thoại, trạng thái booking khi cần).
2. **Consult** — tư vấn gói, giá, tiện ích; gọi tool tìm kiếm/ chi tiết gói, so sánh, tiện ích cơ sở.
3. **Policy** — câu hỏi điều khoản, hoàn tiền, nội quy, camera, v.v.; gọi **RAG** qua `query_gym_policy`.
4. **Booking** — thu thập thông tin, xác nhận, tạo lịch qua `create_booking`, có mốc thời gian Việt Nam qua `get_vietnam_now`.

Sau bước gọi tool, **ToolNode** thực thi và đưa lại **đúng agent** tương ứng với `intent` hiện tại.

---

## Công cụ (tools)

Các tool được **đăng ký trong graph** (xem `agent/graph.py`) gồm:

| Tool | Mục đích |
|------|----------|
| `search_packages` | Tìm gói tập theo bộ lọc (mô tả, ngân sách, nhu cầu). |
| `get_package_detail` | Chi tiết một gói (giá, cam kết, tiện ích, v.v.). |
| `compare_packages` | Lấy dữ liệu nhiều gói để so sánh. |
| `get_facilities` | Thiết bị / khu vực theo loại. |
| `get_vietnam_now` | Mốc thời gian hiện tại theo múi **Asia/Ho_Chi_Minh** (hỗ trợ suy "mai", "tối nay"…). |
| `create_booking` | Tạo booking tập thử qua API (`POST /bookings`). |
| `query_gym_policy` | Tra cứu chính sách/điều khoản từ **RAG** (Chroma + embedding + pipeline trong `rag/policy_pipeline.py`). |

Gói `tools/` còn export thêm (vd. `get_booking`, `get_slots`) — có thể dùng mở rộng, hiện **chưa** gắn vào `ToolNode` mặc định.

**Backend HTTP** — cấu hình qua `BACKEND_URL` / `BASE_URL` (mặc định `http://127.0.0.1:8000`), xem `tools/client.py`.

---

## Công nghệ sử dụng

- **LangGraph** — biểu đồ trạng thái, `ToolNode`, `tools_condition`, compile graph `gym_agent` (`langgraph.json`).
- **LangChain Core** — tin nhắn, công cụ, `bind_tools`.
- **ChatGradient (langchain-gradient)** — LLM suy luận (ví dụ `openai-gpt-4o`), khoá qua `DIGITALOCEAN_INFERENCE_KEY` / `GRADIENT_MODEL_ACCESS_KEY` (tùy môi trường).
- **Pydantic / python-dotenv** — cấu hình, biến môi trường.
- **RAG (policy)**: `langchain-community` (Chroma), `langchain-huggingface` (embeddings), `chromadb`, `sentence-transformers` (cross-encoder khi bật rerank), `torch` — vector store tại `data/policy-terms-db` (build từ `rag/build_db.ipynb`).
- **HTTP**: `requests` tới API gym mock/thật.

---

## Chạy & cấu hình (gợi ý nhanh)

- Sao chép `.env` với khoá inference và (tuỳ chọn) `BACKEND_URL`.
- Cài phụ thuộc: `pip install -r requirements.txt`
- RAG: build DB nếu chưa có thư mục vector store; biến môi trường liên quan nằm trong `rag/policy_pipeline.py` (ví dụ `GYM_POLICY_CHROMA_DIR`, `GYM_POLICY_SKIP_RERANK`, …).
- **LangGraph Studio / CLI**: `langgraph dev` (graph export `agent.graph:graph`).

---

## Cấu trúc thư mục (rút gọn)

```
agent/          # graph, state, nodes (router, consult, policy, booking), prompts
tools/          # client HTTP + definition @tool
rag/            # pipeline RAG, notebook build / test
data/           # tài liệu chính sách, vector store (có thể .gitignore)
```

---

*FlexFit Gym và “Alex” trong repo là bối cảnh demo/đồ án; điều chỉnh thương hiệu hoặc API theo sản phẩm thực tế nếu triển khai ngoài môi trường thử nghiệm.*
