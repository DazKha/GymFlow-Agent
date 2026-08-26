# Ragas Validation

Ragas is opt-in and is never imported by the agent or offline evaluation tests.
The documented default selection is the dense baseline and the best recorded
`combined` configuration. The validator accepts repeated `--result-path` values,
so no result is required for the other experiment combinations.

List defaults without loading Ragas:

```bash
python -m rag.evaluation.ragas_validation --list
```

Run selected JSONL results only:

```bash
python -m rag.evaluation.ragas_validation --result-path PATH --result-path OTHER_PATH
```

Per-case JSONL, expansion caches, and generated responses remain ignored artifacts.
