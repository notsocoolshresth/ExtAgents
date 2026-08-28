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
| *(none yet — pre-experiment phase)* | | | | | | | | | | | |
