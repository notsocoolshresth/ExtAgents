# AGENTS.md — Mandatory Context for Every AI Agent Session

> **Every AI agent (and human contributor) working in this repository MUST read this file
> first, then the latest entries of `docs/research/session-log.md`, before making any change.**

---

## 1. Project Identity

- **Name**: ExtAgents (forked from [THUNLP-MT/ExtAgents](https://github.com/THUNLP-MT/ExtAgents), ACL 2026)
  - Original paper: *Scaling External Knowledge Input Beyond The Context Length of LLMs via Multi-Agent Collaboration* ([arXiv:2505.21471](https://arxiv.org/abs/2505.21471))
- **Our work**: An **original research extension** — a systematic study of **NLP chunking techniques** inside the ExtAgents map-reduce pipeline, targeting a **new ACL submission**.
- **Status**: Pre-experiment phase. Baseline code is untouched. Documentation/knowledge base under construction.
- **Research scope**: **English-only** — tasks `rag` and `en`. The upstream Zh.QA (Chinese) pipeline exists in the baseline code/eval scripts but is **out of scope** for this study; never run, cite, or plan around it.

## 2. Research Mission (Non-Negotiable North Star)

1. Replace/augment the current **naive fixed-size token chunking** (`src/utils.py:104-133`) with principled chunking techniques (overlap, recursive/structural, semantic, document-structure-aware).
2. Measure impact on **world-standard benchmarks**: HotpotQA-based RAG and InfiniteBench En.QA — using the repo's official eval scripts, unmodified.
3. Produce an **ACL-submittable paper**: every claim must be reproducible, ablated, and statistically defensible.

**Quality bar**: This is not a college project. Every line of code must be reviewable, justified, and attributable to a decision recorded in `docs/research/session-log.md`. If you cannot explain *why* a change improves or preserves correctness, do not make it.

## 3. Architecture Map (verified against code)

| Component | Location | What it does |
|---|---|---|
| CLI entry | `main.py:9-21` | Args: `task` (`rag`/`en`/`zh`), `chunk_length` (**8000** default), `input_length` (**128000**), `context_length` (**32768**), model/API config |
| Tokenizer | `main.py:61` | Always `tiktoken` gpt-4o encoding for length accounting |
| **Chunking (baseline)** | `src/utils.py:104-133` | `create_chunks`: encode → truncate to `input_length` → slice into fixed `chunk_length` token blocks → decode |
| Truncation manner | `src/pipeline.py:46` + `src/utils.py:68-87` | `"front"` for RAG, `"middle"` for En/Zh |
| MAP stage | `src/pipeline.py:59-97` | Per-chunk LLM extraction; iterations > 1 prepend previously extracted info (`max_info_tokens = context_length − chunk_length − 1000`) |
| Info scoring | `src/utils.py:136-165` | LLM returns `Score: X` (regex `Score:\s*(\d+)`); en/zh only; infinite retry on parse failure |
| RAG info filter | `src/pipeline.py:99-108` | Drops entries containing substring `"no information"` |
| REDUCE stage | `src/pipeline.py:110-217` | Sorts info by score; tries top-r candidates with r doubling 1→2→4→… until answer found (no `"no answer"`/`"no info"`); up to `max_iterations=5` |
| Local-model postprocess | `src/pipeline.py:220-225`, `src/utils.py:168-191` | RAG-only, when model looks local (llama/qwen/ollama) |
| Prompts | `src/prompt.py` | First-iteration extraction (`:5`), later iterations (`:88`), scoring (`:59`) |

### Evaluation (official, DO NOT MODIFY without session-log justification)

| Task | Script | Metric |
|---|---|---|
| RAG | `scripts/eval_rag.sh` → `src/eval/hotpot_evaluate_v1.py` vs `data/sampled_hotpot_questions.json` | HotpotQA EM + F1 |
| En.QA | `scripts/eval_en.sh` → `src/eval/compute_scores_partial-enhanced.py --task longbook_qa_eng` | Word-level QA F1 (`compute_scores.py:63`) |

Note: three compute_scores variants exist (`compute_scores.py`, `-full-enhanced`, `-partial-enhanced`). Always record which variant a run used in `docs/research/experiment-registry.md`.

### Data (gitignored; download via `bash scripts/download_data.sh`)

`data/sampled_hotpot_questions.json`, `data/rag_1000k.jsonl`, `data/longbook_qa_eng.jsonl`

## 4. Hard Rules for All Agents

1. **Accountability**: any code change requires a session-log entry stating what, why, expected effect, and how to verify.
2. **Baseline integrity**: keep the original pipeline behavior reproducible. New functionality goes behind new flags/modules (e.g., a future `src/chunkers.py` selected by a CLI arg), defaulting to legacy behavior unless explicitly stated.
3. **Eval scripts are frozen** during experiments. If a change is unavoidable, it must be justified in the session log and applied identically across all compared runs.
4. **Controlled decoding**: temperature 0.0 (API) / 0.1 (local), per `src/utils.py:42`. Never vary decoding settings between arms of a comparison.
5. **No secrets**: API keys via env vars (`OPENAI_BASE_URL`, `OPENAI_API_KEY`) or `.env` (gitignored). Never commit keys.
6. **No sloppy code**: no dead code, no silent exception swallowing, follow existing style (no type-checker/linter is configured yet — propose adding one before Phase 2 coding).
7. **Results are gitignored** (`results*/`, `*.jsonl`) — copy final numbers into `docs/research/experiment-registry.md`.

## 5. Session Protocol (every session, no exceptions)

1. Read this file fully.
2. Read the last ~3 entries of `docs/research/session-log.md`.
3. Check `docs/research/experiment-registry.md` if doing anything experiment-related.
4. Do the work.
5. **Before ending**: append an entry to `docs/research/session-log.md` using the mandated format (see header of that file). Include decisions + rationale + open questions.
6. Record any benchmark run in `docs/research/experiment-registry.md`.

## 6. Common Commands

```bash
# Setup (Windows: use conda or venv as available)
conda create -n extagents python=3.10 -y && conda activate extagents
pip install -r requirements.txt

# Data
bash scripts/download_data.sh

# Generation (example: RAG task, baseline behavior)
python main.py --task rag --output_dir results_rag --chunk_length 8000 \
    --input_length 128000 --api_url "$OPENAI_BASE_URL" --api_key "$OPENAI_API_KEY" \
    --model "gpt-4o-mini-2024-07-18" --num_workers 8

# Evaluation
bash scripts/eval_rag.sh results_rag   # HotpotQA EM/F1
bash scripts/eval_en.sh results_en     # InfiniteBench longbook_qa_eng F1
```

Environment note: primary dev machine is Windows (`C:\Users\Shresth\vscode2\ExtAgents`); bash scripts assume a POSIX shell (Git Bash/WSL).

## 7. Document Index

| File | Purpose |
|---|---|
| `docs/research/research-plan.md` | Study charter: research questions, hypotheses, candidate techniques C0/C1/C3–C5, ablation matrix, metrics, statistics protocol |
| `docs/research/session-log.md` | Append-only journal; mandated entry format; one entry per session |
| `docs/research/experiment-registry.md` | One row per benchmark run: run_id, config, scores, cost, notes |
