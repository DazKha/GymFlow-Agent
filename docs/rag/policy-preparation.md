# Policy Preparation

Policy sources belong in `data/policies/` and must retain their YAML front
matter and stable `document_id`. Normalize and validate them before rebuilding
the generated chunks and dense Chroma index:

```bash
python scripts/normalize_policies.py
python scripts/validate_policies.py
python -m rag.core.chunking --input-dir data/policies \
  --output data/generated/policy_chunks.jsonl \
  --report data/generated/policy_chunk_report.json
python -m rag.core.ingest --input data/generated/policy_chunks.jsonl --dry-run
```

`data/generated/` is local build output and is not a source-of-truth location.
