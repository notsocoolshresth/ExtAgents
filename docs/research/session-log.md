# Session Log — Append-Only Journal

> **Mandate**: Every AI-agent session (and human working session) MUST append exactly one
> entry before ending. Never edit or delete prior entries; append corrections as new entries.
>
> **Entry format (mandatory)**:
>
> ```
> ## [YYYY-MM-DD] Entry NNN — <short title>
> - **Agent/model**: <model name or human name>
> - **Scope read**: AGENTS.md ☐ ; session-log last 3 ☐ ; experiment-registry ☐ (if experiment-related)
> - **Actions**: bullet list of concrete changes/analyses performed (file paths, line refs)
> - **Decisions & rationale**: every decision worth remembering + why
> - **Expected effects / verification plan**: what should change, how to check
> - **Open questions / handoff**: anything the next session must know
> ```

---

## [2026-08-23] Entry 001 — Project analysis & research knowledge base created

- **Agent/model**: ox-alpha (opencode CLI)
- **Scope read**: AGENTS.md ☐ (created this session) ; session-log last 3 ☐ (file did not exist) ; experiment-registry ☐ (created this session)
- **Actions**:
  - Full read-through of baseline code: `main.py`, `src/pipeline.py`, `src/utils.py`, `src/prompt.py` (first 100 lines), `scripts/eval_rag.sh`, `scripts/eval_en.sh`, `src/eval/compute_scores.py`, `.gitignore`, `requirements.txt`, `README.md`.
  - Verified evaluation metrics: RAG → HotpotQA EM/F1 (`src/eval/hotpot_evaluate_v1.py`); En.QA → word-level QA F1 (`compute_scores.py:63`, invoked via `compute_scores_partial-enhanced.py` in `eval_en.sh`); Zh.QA → char-level QA F1 (`compute_scores.py:82`).
  - Confirmed baseline chunking is naive fixed-size token slicing (`src/utils.py:104-133`) with manner `"front"` (rag) / `"middle"` (en/zh) truncation (`src/pipeline.py:46`).
  - Created `AGENTS.md` (root), `docs/research/research-plan.md`, `docs/research/session-log.md` (this file), `docs/research/experiment-registry.md`.
- **Decisions & rationale**:
  - Documentation hierarchy (AGENTS.md entry point + docs/research/*) chosen over single-file context — separation of concerns scales for a paper project. User-approved.
  - Research charter locks concrete candidates C0–C5 now rather than open-ended — forces early falsifiable hypotheses; amendments allowed via session log. User-approved.
  - Benchmarks restricted to repo-native ones (HotpotQA-RAG, InfiniteBench En/Zh) — direct comparability with published ExtAgents numbers gives cleanest delta attribution. External benchmarks (LongBench/RULER/NarrativeQA) explicitly deferred. User-approved.
  - No source code touched this session — baseline integrity preserved during documentation phase.
- **Expected effects / verification plan**: every future session inherits full project context via AGENTS.md; compliance measurable by presence of well-formed session-log entries.
- **Open questions / handoff**:
  1. Which primary model/API provider will be used for the core matrix? Must be locked before P3 (baseline reproduction) — record exact model string + endpoint in registry.
  2. No linter/type-checker configured yet; propose ruff+mypy (or similar) at start of P2 coding.
  3. Data files not yet downloaded locally (`data/*.jsonl` absent) — needed before any run.
  4. Note for P2: `.gitignore` ignores `*.json`, `*.jsonl`, `*.txt`, `*.log` broadly — be careful that new non-result artifacts (e.g., chunker fixtures) use extensions that remain trackable, or add explicit exceptions.

## [2026-08-23] Entry 002 — Addendum to 001: uncommitted baseline modifications discovered

- **Agent/model**: ox-alpha (opencode CLI)
- **Scope read**: AGENTS.md ☑ ; session-log last 3 ☑ ; experiment-registry ☐ (no runs)
- **Actions**:
  - Ran `git status` / `git diff` while verifying doc tracking. Found uncommitted modifications predating this session (not made by this agent): `main.py` (+local defaults: ollama URL/key, `qwen3.5:0.8b`, `context_length` 32768), `src/utils.py` (+`is_local_model()` detecting llama/qwen/ollama/localhost), `src/pipeline.py` (uses `utils.is_local_model()`).
- **Decisions & rationale**:
  - No code reverted and nothing committed — reverting could destroy intentional work; committing requires owner approval.
  - Documentation (AGENTS.md architecture map, line refs) describes the **working tree**, which matches what was analyzed; flagging here so no future agent mistakes HEAD for the analyzed baseline.
- **Expected effects / verification plan**: `git diff` reproduces the findings above.
- **Open questions / handoff**:
  1. **Owner decision required**: commit these local-model adaptations with an explanatory message (making them part of the documented baseline), or revert them before P3 experiments. Until resolved, all experiment rows must record the exact commit SHA **and** dirty-tree status.
