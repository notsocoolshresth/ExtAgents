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
| 20261101-rag-legacy-8000-llama31-8b | 2026-11-01 | 41c416e | rag | rag_1000k (371) | llama3.1:8b (Ollama) | chunker=legacy, chunk_length=8000, input_length=128000, context_length=32768, workers=4, temp=0.1 | hotpot_evaluate_v1.py | EM, F1, P, R | EM=6.20%, F1=17.54%, P=16.42%, R=25.38% | — | Baseline (C0) |
| 20261101-rag-overlap-8000-llama31-8b | 2026-11-01 | 41c416e | rag | rag_1000k (371) | llama3.1:8b (Ollama) | chunker=overlap, chunk_length=8000, input_length=128000, context_length=32768, workers=4, temp=0.1 | hotpot_evaluate_v1.py | EM, F1, P, R | EM=8.36%, F1=16.65%, P=15.23%, R=23.93% | — | C1: 50% overlap |
| 20261106-rag-recursive_paragraph-8000-llama31-8b | 2026-11-06 | (current) | rag | rag_1000k (371) | llama3.1:8b (Ollama) | chunker=recursive_paragraph, chunk_length=8000, input_length=128000, context_length=32768, workers=4, temp=0.1 | hotpot_evaluate_v1.py | EM, F1, P, R | EM=6.74%, F1=15.48%, P=14.15%, R=21.79% | — | C3: paragraph→sentence→word recursion |
| 20261106-rag-document_structure-8000-llama31-8b | 2026-11-06 | (current) | rag | rag_1000k (371) | llama3.1:8b (Ollama) | chunker=document_structure, chunk_length=8000, input_length=128000, context_length=32768, workers=4, temp=0.1 | hotpot_evaluate_v1.py | EM, F1, P, R | EM=7.55%, F1=15.31%, P=14.00%, R=22.42% | — | C5: chapter/heading detection, C3 fallback |
| 20261101-rag-semantic-8000-llama31-8b | 2026-11-01 | 41c416e | rag | rag_1000k (371) | llama3.1:8b (Ollama) | chunker=semantic, chunk_length=8000, input_length=128000, context_length=32768, workers=4, temp=0.1 | hotpot_evaluate_v1.py | EM, F1, P, R | EM=9.16%, F1=17.26%, P=16.12%, R=23.55% | — | C4: semantic breakpoints (bge-base-en-v1.5) |
| 20261101-rag-semantic_tree-8000-llama31-8b | 2026-11-01 | 41c416e | rag | rag_1000k (371) | llama3.1:8b (Ollama) | chunker=semantic_tree, chunk_length=8000, input_length=128000, context_length=32768, workers=4, temp=0.1 | hotpot_evaluate_v1.py | EM, F1, P, R | EM=9.70%, F1=18.22%, P=17.46%, R=23.98% | — | C6: binary tree + beam search k=4 |