# 🤖 Alex — FlexFit Gym Assistant

Alex is a virtual consulting assistant for **FlexFit Gym** — a demo fitness center with amenities including a swimming pool, sauna, group classes, personal training, and more. Alex helps customers in Vietnamese: finding the right membership package, answering questions about policies and terms, and guiding them through booking a trial session — always prioritizing sourced information (API, RAG) over hallucination.

The project is built as a **multi-task agent on LangGraph**, with the graph split by intent (consult / policy / booking) and tools that interact with an HTTP backend and an internal document store.

---

## 🔄 Flow Overview

```
User Message
     ↓
  Router ── classifies intent: consult | policy | booking
     ↓                        (with conversation context +
     ├── Consult              booking state when needed)
     │     └── packages, pricing, amenities
     │         tools: search_packages, get_package_detail,
     │                compare_packages, get_facilities
     │
     ├── Policy
     │     └── terms, refunds, rules, cameras, etc.
     │         tools: query_gym_policy (RAG)
     │
     └── Booking
           └── collect info → confirm → create
               tools: create_booking, get_vietnam_now
                         ↓
                      ToolNode
               (executes tool, returns result
                to the matching intent agent)
```

---

## 🛠️ Tools

Registered in the graph (see `agent/graph.py`):

| Tool | Purpose |
|---|---|
| `search_packages` | Search membership packages by filter (description, budget, needs) |
| `get_package_detail` | Full detail of one package (price, commitment, amenities, etc.) |
| `compare_packages` | Fetch data for multiple packages for side-by-side comparison |
| `get_facilities` | Equipment / zones by type |
| `get_vietnam_now` | Current timestamp in `Asia/Ho_Chi_Minh` (supports "tomorrow", "tonight", etc.) |
| `create_booking` | Create a trial booking via API (`POST /bookings`) |
| `query_gym_policy` | Retrieve policy / terms from RAG (Chroma + embedding + pipeline in `rag/policy_pipeline.py`) |

> The `tools/` package also exports additional tools (e.g. `get_booking`, `get_slots`) — available for extension, not attached to the default ToolNode.

**HTTP backend** — configured via `BACKEND_URL` / `BASE_URL` (default `http://127.0.0.1:8000`), see `tools/client.py`.

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| **Agent graph** | LangGraph — state graph, ToolNode, tools_condition, compiled as `gym_agent` (`langgraph.json`) |
| **LLM** | ChatGradient (`langchain-gradient`) — e.g. `openai-gpt-4o`, keyed via `DIGITALOCEAN_INFERENCE_KEY` / `GRADIENT_MODEL_ACCESS_KEY` |
| **Chains / tools** | LangChain Core — messages, tool definitions, `bind_tools` |
| **RAG (policy)** | `langchain-community` (Chroma), `langchain-huggingface` (embeddings), `chromadb`, `sentence-transformers` (cross-encoder for optional reranking), `torch` — vector store at `data/policy-terms-db` (built from `rag/build_db.ipynb`) |
| **Config** | Pydantic · python-dotenv |
| **HTTP** | `requests` → gym mock / real API |

---

## 🚀 Quick Start

**1. Environment**
```bash
cp .env.example .env
# fill in inference key and optionally BACKEND_URL
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Build RAG vector store** (first time only)
```bash
# open and run rag/build_db.ipynb
# relevant env vars: GYM_POLICY_CHROMA_DIR, GYM_POLICY_SKIP_RERANK, ...
# see rag/policy_pipeline.py for full list
```

**4. Run with LangGraph Studio / CLI**
```bash
langgraph dev   # graph export: agent.graph:graph
```

---

## 📁 Project Structure

```
agent/
├── graph.py          # LangGraph graph definition + ToolNode wiring
├── state.py          # Shared agent state schema
├── nodes/
│   ├── router.py     # Intent classifier
│   ├── consult.py    # Membership consultation agent
│   ├── policy.py     # Policy Q&A agent
│   └── booking.py    # Booking flow agent
└── prompts/          # System prompts per node

tools/
├── client.py         # HTTP client (BACKEND_URL config)
└── definitions.py    # @tool decorated functions

rag/
├── policy_pipeline.py  # Chroma retrieval + optional reranking
├── build_db.ipynb      # Build / rebuild vector store
└── test_rag.ipynb      # RAG evaluation notebook

data/
├── policy-terms-db/    # Chroma vector store (may be .gitignored)
└── documents/          # Raw policy / terms source files
```

---

> **Note:** FlexFit Gym and "Alex" in this repo are a demo/project context. Adjust branding or API endpoints to match your production environment before deploying outside of testing.
