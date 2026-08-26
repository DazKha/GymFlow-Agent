# GymFlow Policy Evaluation Set v1

## Scope

Evaluation set được xây dựng từ 5 policy documents và 71 chunks trong corpus version `373ad058df32`:

- Complaint resolution policy
- Payment policy
- Personal data protection policy
- Privacy policy
- Terms and conditions

File chính: `policy_eval_set_v1.jsonl`.

## Distribution

| Category | Cases |
|---|---:|
| Complaint | 3 |
| Payment | 4 |
| Personal data protection | 8 |
| Privacy | 7 |
| Terms and conditions | 5 |
| Cross-document | 2 |
| Unanswerable | 3 |
| **Total** | **32** |

## Intended evaluation

### Retrieval-only

Với các case `answerable=true`, sử dụng:

- Document Hit@K từ `expected_document_ids`
- Chunk Recall@K từ `reference_chunk_ids`
- MRR / First Relevant Rank
- nDCG nếu cần đánh giá ranking nhiều relevant chunks

Chạy tối thiểu tại `K = 1, 3, 5, 8`.

Với case `answerable=false`, không dùng empty `reference_chunk_ids` để tính Recall. Thay vào đó đo false-positive hoặc refusal behavior ở tầng end-to-end.

### Ragas/end-to-end

Map schema:

```text
user_input       <- user_input
reference        <- reference_answer
retrieved_contexts <- contents returned by PolicyRetriever
response         <- generated answer
```

Metrics gợi ý:

- Context Precision
- Context Recall
- Faithfulness
- Answer Relevancy
- Answer Correctness (secondary, không dùng làm metric duy nhất)

Nên bổ sung deterministic evaluators cho:

- Citation source URL accuracy
- Citation chunk accuracy
- Answerability/refusal accuracy
- Unsupported-claim rate

## Important cautions

1. Đây là seed evaluation set, không phải legal QA benchmark được chuyên gia pháp lý thẩm định.
2. Reference answers là bản tóm tắt bám theo snapshot đã crawl, không phải tư vấn pháp lý.
3. Một số policy gốc có tham chiếu mục không nhất quán; evaluator nên dựa vào `reference_chunk_ids`, không suy ra chunk từ số mục.
4. Không tuning retriever trên toàn bộ 32 cases rồi dùng cùng tập để báo kết quả cuối. Sau baseline đầu tiên, nên giữ lại một nhóm holdout hoặc mở rộng corpus test.
5. Khi chunk pipeline hoặc corpus version thay đổi, cần remap và validate toàn bộ `reference_chunk_ids`.

## Recommended baseline table

```text
experiment_id: dense_e5_v1
corpus_version: 373ad058df32
collection: gymflow_policy_e5_v1
embedding_model: intfloat/multilingual-e5-base
distance: cosine
reranker: none
hybrid: false
K: [1, 3, 5, 8]
```
