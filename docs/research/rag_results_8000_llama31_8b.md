# RAG Results — chunk_length=8000, llama3.1:8b (Ollama), 371 examples

| Chunker | EM | F1 | Precision | Recall |
|---------|-----|-----|-----------|--------|
| legacy (C0) | 6.20% | 17.54% | 16.42% | 25.38% |
| overlap (C1) | 8.36% | 16.65% | 15.23% | 23.93% |
| recursive_paragraph (C3) | 6.74% | 15.48% | 14.15% | 21.79% |
| semantic (C4) | 9.16% | 17.26% | 16.12% | 23.55% |
| document_structure (C5) | 7.55% | 15.31% | 14.00% | 22.42% |
| semantic_tree (C6) | **9.70%** | **18.22%** | 17.46% | 23.98% |

## Observations

- **C6 (semantic_tree)** achieves highest EM (9.70%) and F1 (18.22%) — binary tree with beam search k=4
- **C4 (semantic)** second-best on EM (9.16%), competitive F1 (17.26%)
- **C1 (overlap)** improves EM over baseline (+2.16 pp) but slightly lowers F1
- **C3 (recursive_paragraph)** and **C5 (document_structure)** underperform baseline on F1
- Baseline (C0) has highest recall (25.38%) — may indicate more extractions passed to reduce stage

## Config
- Task: `rag` (HotpotQA, 371 examples from `rag_1000k.jsonl`)
- Model: `llama3.1:8b` via Ollama (`http://localhost:11434/v1`)
- `chunk_length=8000`, `input_length=128000`, `context_length=32768`
- `num_workers=4`, temperature=0.1 (local model default)
- Eval: `hotpot_evaluate_v1.py` vs `sampled_hotpot_questions.json`
- Commit: (record git SHA)
- Date: 2026-11-06