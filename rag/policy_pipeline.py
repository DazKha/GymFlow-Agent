from __future__ import annotations

import os
from pathlib import Path
from typing import Any, TypedDict

from dotenv import load_dotenv

load_dotenv()

# Paths (notebook: ../data/policy-terms-db from rag/)
_ROOT = Path(__file__).resolve().parents[1]
PERSIST_DIR = os.getenv("GYM_POLICY_CHROMA_DIR", str(_ROOT / "data" / "policy-terms-db"))
COLLECTION_NAME = os.getenv("GYM_POLICY_CHROMA_COLLECTION", "gym-policy-terms")

# 0 = không gọi LLM mở rộng (tránh output kiểu "Câu hỏi gốc / mở rộng" lọt vào retrieval)
EXPAND_N = int(os.getenv("GYM_POLICY_EXPAND_N", "0"))
RETRIEVE_TOP_K = 4
RERANK_TOP_K = 4
# 1 = bỏ cross-encoder rerank (nhanh hơn; dùng thứ tự theo điểm Chroma)
SKIP_RERANK = os.getenv("GYM_POLICY_SKIP_RERANK", "1").lower() in ("1", "true", "yes", "on")


class RAGState(TypedDict):
    query: str
    expanded_queries: list[str]
    retrieved_docs: list[dict[str, Any]]
    reranked_docs: list[dict[str, Any]]
    answer: str


_llm: Any = None
_embeddings: Any = None
_vectordb: Any = None
_reranker: Any = None
_pipeline = None  # cached Runnable or chain

_EMBED_MODEL = os.getenv("GYM_POLICY_EMBED_MODEL", "intfloat/multilingual-e5-base")
_RERANK_MODEL = os.getenv("GYM_POLICY_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
_LLM_MODEL = os.getenv("GYM_POLICY_LLM", os.getenv("EDU_AGENT_MODEL", "openai-gpt-4o-mini"))


def _get_llm() -> Any:
    global _llm
    if _llm is not None:
        return _llm
    api_key = os.getenv("DIGITALOCEAN_INFERENCE_KEY") or os.getenv("GRADIENT_MODEL_ACCESS_KEY")
    if not api_key:
        return None
    from langchain_gradient import ChatGradient

    _llm = ChatGradient(model=_LLM_MODEL, api_key=api_key, temperature=0.0)
    return _llm


def _get_embeddings() -> Any:
    global _embeddings
    if _embeddings is not None:
        return _embeddings
    from langchain_huggingface import HuggingFaceEmbeddings

    _embeddings = HuggingFaceEmbeddings(
        model_name=_EMBED_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )
    return _embeddings


def _get_vectordb() -> Any:
    global _vectordb
    if _vectordb is not None:
        return _vectordb
    from langchain_community.vectorstores import Chroma

    p = Path(PERSIST_DIR)
    if not p.is_dir():
        raise FileNotFoundError(
            f"Chưa có vector store tại {PERSIST_DIR}. Chạy rag/build_db.ipynb (hoặc build tương đương) trước."
        )
    _vectordb = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=_get_embeddings(),
        persist_directory=str(p),
    )
    return _vectordb


def _get_reranker() -> Any:
    global _reranker
    if _reranker is not None:
        return _reranker
    from sentence_transformers import CrossEncoder

    dev = os.getenv("POLICY_RERANKER_DEVICE", "cpu")
    if dev == "auto":
        import torch

        if torch.cuda.is_available():
            dev = "cuda"
        elif torch.backends.mps.is_available():
            dev = "mps"
        else:
            dev = "cpu"
    _reranker = CrossEncoder(_RERANK_MODEL, device=dev)
    return _reranker


def expand_query_node(state: RAGState) -> RAGState:
    q = state["query"]
    llm = _get_llm()
    if llm is None or EXPAND_N < 1:
        state["expanded_queries"] = [q]
        return state
    prompt = f"""
Bạn tạo thêm tối đa {EXPAND_N} câu hỏi tìm kiếm (tiếng Việt) từ câu gốc, để tìm đoạn văn liên quan trong tài liệu điều khoản.

Luật xuất (bắt buộc):
- Chỉ in ra từng dòng, mỗi dòng = một câu hỏi hoặc cụm từ khóa tìm kiếm, không số thứ tự, không gạch đầu dòng, không tiêu đề.
- Không dùng chữ cái kiểu "Câu hỏi gốc", "Câu hỏi mở rộng", "Query", "Original" — không có nhãn trước dấu hai chấm.
- Dòng đầu: viết lại câu gốc nếu cần (rõ hơn), hoặc giữ nội dung; các dòng sau: diễn đạt khác từng chút.
- Tối đa {1 + EXPAND_N} dòng tổng cộng (1 + số câu bổ sung).

Câu gốc: {q}
"""
    try:
        resp = llm.invoke(prompt).content
        if not isinstance(resp, str):
            resp = str(resp)
    except Exception:  # noqa: BLE001
        state["expanded_queries"] = [q]
        return state
    lines = [s.strip() for s in (resp or "").splitlines() if s.strip()]
    out: list[str] = [q]
    for line in lines:
        if line not in out:
            out.append(line)
    state["expanded_queries"] = out
    return state


def retrieve_node(state: RAGState) -> RAGState:
    vdb = _get_vectordb()
    all_hits: dict[str, dict[str, Any]] = {}

    for q in state["expanded_queries"]:
        hits = vdb.similarity_search_with_relevance_scores(q, k=RETRIEVE_TOP_K)
        for doc, score in hits:
            key = doc.page_content.strip()
            if key not in all_hits or score > all_hits[key]["retrieval_score"]:
                all_hits[key] = {
                    "retrieval_score": float(score) if score is not None else 0.0,
                    "doc": doc,
                    "matched_query": q,
                }

    state["retrieved_docs"] = sorted(
        all_hits.values(), key=lambda x: x["retrieval_score"], reverse=True
    )
    return state


def rerank_node(state: RAGState) -> RAGState:
    cands = state["retrieved_docs"]
    if not cands:
        state["reranked_docs"] = []
        return state

    if SKIP_RERANK:
        # Giữ cùng shape với bước answer; sắp theo điểm vector search, không tải CrossEncoder
        ordered = sorted(cands, key=lambda x: x["retrieval_score"], reverse=True)[
            :RERANK_TOP_K
        ]
        state["reranked_docs"] = [
            {
                "doc": c["doc"],
                "matched_query": c["matched_query"],
                "reranking_score": c["retrieval_score"],
            }
            for c in ordered
        ]
        return state

    q = state["query"]
    rer = _get_reranker()
    pairs = [(q, c["doc"].page_content.strip()) for c in cands]
    scores = rer.predict(pairs)
    ranked = []
    for c, s in zip(cands, scores, strict=True):
        ranked.append(
            {
                "doc": c["doc"],
                "matched_query": c["matched_query"],
                "reranking_score": float(s),
            }
        )
    ranked.sort(key=lambda x: x["reranking_score"], reverse=True)
    state["reranked_docs"] = ranked[:RERANK_TOP_K]
    return state


def answer_node(state: RAGState) -> RAGState:
    docs = state["reranked_docs"]
    if not docs:
        state["answer"] = "Không đủ dữ liệu để trả lời chắc chắn."
        return state

    ctx = "\n\n".join(
        f"[Context {i + 1}]\n{d['doc'].page_content}" for i, d in enumerate(docs)
    )

    llm = _get_llm()
    if llm is None:
        state["answer"] = ctx[:1500]
        return state

    prompt = f"""
        Bạn là một Customer Service Agent chuyên trả lời câu hỏi về điều khoản sử dụng và chính sách.

        ## NHIỆM VỤ
        Trả lời câu hỏi của người dùng CHỈ dựa trên thông tin trong CONTEXT.

        ## QUY TẮC QUAN TRỌNG
        1. Chỉ sử dụng thông tin có trong CONTEXT. Không được suy đoán hoặc thêm kiến thức ngoài.
        2. Nếu CONTEXT không đủ để trả lời, phải trả lời:
        "Tài liệu không đề cập rõ thông tin này."
        3. Trả lời ngắn gọn, rõ ràng, đúng trọng tâm.
        4. Luôn trả lời bằng tiếng Việt.
        5. Khi có thông tin từ context, phải trích dẫn rõ:
        - Dùng format: (Điều khoản X.Y)
        - Có thể kết hợp nhiều context
        6. Không được fabricate điều khoản (ví dụ: "điều 6.1") nếu context không ghi rõ.

        ## FORMAT TRẢ LỜI
        - Trả lời trực tiếp câu hỏi; **không** in tiêu đề kiểu "Câu hỏi gốc", "Câu hỏi mở rộng", "Query expansion".
        - Không lặp lại nguyên văn toàn bộ câu hỏi dưới dạng bảng/ý phụ; vào thẳng nội dung chính sách.
        - Sau mỗi ý quan trọng, thêm citation (Context X)

        ## USER QUESTION
        {state["query"]}

        ## CONTEXT
        {ctx}
        """

    try:
        state["answer"] = llm.invoke(prompt).content
    except Exception as e:  # noqa: BLE001
        state["answer"] = f"[Lỗi tạo câu trả lời] {e}\n\nBản tóm tắt từ context:\n{ctx[:2000]}"
    return state


def _get_chain() -> Any:
    global _pipeline
    if _pipeline is None:
        from langchain_core.runnables import RunnableLambda

        _pipeline = (
            RunnableLambda(expand_query_node)
            | RunnableLambda(retrieve_node)
            | RunnableLambda(rerank_node)
            | RunnableLambda(answer_node)
        )
    return _pipeline


def run_policy_rag(query: str) -> str:
    """Chạy pipeline: expand (tùy chọn) → retrieve → (rerank nếu GYM_POLICY_SKIP_RERANK=0) → answer."""
    init: RAGState = {
        "query": (query or "").strip(),
        "expanded_queries": [],
        "retrieved_docs": [],
        "reranked_docs": [],
        "answer": "",
    }
    if not init["query"]:
        return "Câu hỏi trống, không thể tra cứu."
    try:
        out: RAGState = _get_chain().invoke(init)  # type: ignore[assignment]
    except FileNotFoundError as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return f"[Policy RAG lỗi] {type(e).__name__}: {e}"
    return out.get("answer") or "Không có câu trả lời."
