# Experiment Registry

> **Rule**: One row per benchmark run (or arm of a run). Copy final numbers here —
> raw `results*/` dirs are gitignored. A row without config hash / eval variant is invalid.
>
> Conventions:
> - `run_id`: `YYYYMMDD-<task>-<chunker>-<chunklen>-<modeltag>[-rN]` (rN = repetition)
> - `config`: chunker ID (active candidates per research-plan §4), chunk_length, input_length, context_length, num_workers, temperature
> - `task`: `rag` or `en` only — English-only scope per charter v1.2
> - `eval variant`: exact eval script used (e.g., `compute_scores_partial-enhanced.py`)
> - `commit`: git SHA at generation time
> - Cost columns: extraction/scoring/reduce call counts and total wall-clock if logged.

| run_id | date | commit | task | data | model (+endpoint tag) | config | eval variant | metric(s) | score(s) | cost (#calls / time) | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261101-rag-legacy-8000-llama31-8b | 2026-11-01 | 41c416e | rag | rag_1000k (371) | llama3.1:8b (Ollama) | chunker=legacy, chunk_length=8000, input_length=128000, context_length=32768, workers=4, temp=0.1 | hotpot_evaluate_v1.py | EM, F1, P, R | EM=6.2%, F1=17.6%, P=16.4%, R=25.4% | — | Baseline (C0) |
| 20261101-rag-overlap-8000-llama31-8b | 2026-11-01 | 41c416e | rag | rag_1000k (371) | llama3.1:8b (Ollama) | chunker=overlap, chunk_length=8000, input_length=128000, context_length=32768, workers=4, temp=0.1 | hotpot_evaluate_v1.py | EM, F1, P, R | EM=8.6%, F1=16.8%, P=15.4%, R=24.1% | — | C1: 50% overlap |
| 20261101-rag-semantic-8000-llama31-8b | 2026-11-01 | 41c416e | rag | rag_1000k (371) | llama3.1:8b (Ollama) | chunker=semantic, chunk_length=8000, input_length=128000, context_length=32768, workers=4, temp=0.1 | hotpot_evaluate_v1.py | EM, F1, P, R | EM=9.2%, F1=17.3%, P=16.1%, R=23.5% | — | C4: semantic breakpoints (bge-base-en-v1.5) |
| 20261101-rag-semantic_tree-8000-llama31-8b | 2026-11-01 | 41c416e | rag | rag_1000k (371) | llama3.1:8b (Ollama) | chunker=semantic_tree, chunk_length=8000, input_length=128000, context_length=32768, workers=4, temp=0.1 | hotpot_evaluate_v1.py | EM, F1, P, R | EM=10.0%, F1=18.6%, P=17.5%, R=25.7% | — | C6: binary tree + beam search k=4 |