# Alex Gym — Tổng quan Dự án

## 1. Giới thiệu

**Alex** là trợ lý ảo tư vấn cho FlexFit Gym — một trung tâm thể hình demo. Alex hỗ trợ khách hàng bằng tiếng Việt với các tác vụ:

- Tư vấn gói tập, so sánh giá cả
- Trả lời câu hỏi về chính sách và điều khoản
- Hướng dẫn đặt lịch tập thử

**Nguyên tắc hoạt động**: Ưu tiên thông tin từ nguồn có sẵn (API, RAG) thay vì tự bịa đặt.

---

## 2. Kiến trúc tổng quan

```
┌─────────────┐     ┌──────────┐     ┌────────────┐
│  Router     │────▶│ Intent   │────▶│  ToolNode  │
│  (phân loại)│     │ Agent    │     │  (gọi API) │
└─────────────┘     └──────────┘     └────────────┘
      │                                        │
      │           ┌──────────────┐             │
      └───────────▶│  Consult     │◀────────────┘
                  │  Policy     │
                  │  Booking   │
                  └────────────┘
```

### Intent Flow

| Intent | Mô tả |
|--------|-------|
| `consult` | Tư vấn gói tập, so sánh, tiện ích |
| `policy` | Câu hỏi điều khoản, chính sách |
| `booking` | Đặt lịch tập thử |
| `off_topic` | Tin nhắn không liên quan |

---

## 3. Cấu trúc thư mục

```
gym-agent/
├── agent/              # Logic agent chính
│   ├── graph.py        # Định nghĩa LangGraph
│   ├── state.py       # TypedDict AgentState
│   ├── nodes.py       # Các node: router, consult, policy, booking
│   ├── prompts.py     # Prompt templates
│   └── router.py      # Router logic (nếu có)
├── tools/             # Tool definitions
│   ├── client.py      # HTTP client
│   ├── query_gym_policy.py    # Tool RAG tra cứu policy
│   ├── search_packages.py    # Tìm gói tập
│   ├── get_package_detail.py   # Chi tiết gói
│   ├── compare_packages.py   # So sánh gói
│   ├── get_facilities.py     # Danh sách tiện ích
│   ├── get_vietnam_now.py    # Thời gian Việt Nam
│   ├── create_booking.py     # Tạo booking
│   └── ...
├── rag/               # RAG pipeline
│   ├── policy_pipeline.py   # Pipeline tra cứu policy
│   ├── build_db.ipynb      # Build vector store
│   └── test_rag.ipynb      # Test RAG
├── data/              # Data và vector store
│   ├── gym-policy-terms.md # Tài liệu policy gốc
│   └── policy-terms-db/    # Chroma vector store
├── README.md          # Tài liệu chính
└── alex_gym.md        # File này
```

---

## 4. Tools

Tất cả tools được đăng ký trong `graph.py` và export qua `tools/__init__.py`:

| Tool | Chức năng |
|------|----------|
| `search_packages` | Tìm gói tập theo bộ lọc |
| `get_package_detail` | Xem chi tiết một gói |
| `compare_packages` | So sánh nhiều gói |
| `get_facilities` | Danh sách thiết bị/khu vực |
| `get_vietnam_now` | Lấy thời gian hiện tại (VN) |
| `create_booking` | Tạo booking tập thử |
| `query_gym_policy` | Tra cứu policy qua RAG |

Ngoài ra còn có `get_booking`, `get_slots` — chưa được gắn vào graph mặc định.

---

## 5. State Management

`AgentState` (trong `agent/state.py`):

```python
class AgentState(TypedDict, total=False):
    messages: list  # Tin nhắn hội thoại

    # Routing
    intent: Intent | None  # "consult" | "policy" | "booking" | "off_topic"

    # Booking flow
    booking_info: dict | None
    booking_stage: str | None  # "collecting" | "confirming"
    booking_confirmed: bool | None

    # Policy RAG
    policy_result: str | None
```

---

## 6. RAG Pipeline

**Location**: `rag/policy_pipeline.py`

**Flow**:
```
Query → (Expand) → Retrieve → (Rerank) → Answer
```

- **Expand**: Mở rộng query bằng LLM (tắt mặc định qua `EXPAND_N=0`)
- **Retrieve**: Chroma similarity search, top-k = 4
- **Rerank**: Cross-encoder (tắt mặc định qua `SKIP_RERANK=1`)
- **Answer**: LLM sinh câu trả lời dựa trên context

**Cấu hình qua env**:
- `GYM_POLICY_CHROMA_DIR` — thư mục vector store
- `GYM_POLICY_SKIP_RERANK` — bỏ qua rerank
- `GYM_POLICY_EXPAND_N` — số query mở rộng

---

## 7. Công nghệ sử dụng

| Thành phần | Công nghệ |
|-----------|-----------|
| Agent framework | LangGraph |
| LLM | ChatGradient (DigitalOcean) |
| Embeddings | HuggingFace (`intfloat/multilingual-e5-base`) |
| Reranker | BAAI/bge-reranker-v2-m3 |
| Vector store | Chroma |
| HTTP client | requests |
| Config | python-dotenv |

---

## 8. Cách chạy

### Required env vars:
```bash
# LLM
DIGITALOCEAN_INFERENCE_KEY=...  # hoặc GRADIENT_MODEL_ACCESS_KEY

# Backend (mock)
BACKEND_URL=http://127.0.0.1:8000

# RAG (tùy chọn)
GYM_POLICY_CHROMA_DIR=data/policy-terms-db
```

### Build RAG:
```bash
jupyter lab rag/build_db.ipynb
```

### Chạy agent:
```bash
langgraph dev  # hoặc chạy trực tiếp qua code
```

---

## 9. Lưu ý khi mở rộng

1. **Thêm tool**: Định nghĩa trong `tools/` và import vào `graph.py`
2. **Thêm intent**: Cập nhật `Intent` type trong `state.py` và `router_node`
3. **Cập nhật policy RAG**: Thêm document vào `data/gym-policy-terms.md` và rebuild
4. **Mock backend**: Cấu hình `BACKEND_URL` trỏ tới server phù hợp

---

*Document tạo ngày: 2026-05-05*