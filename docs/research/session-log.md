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

## [2026-08-25] Entry 003 — Charter amendment v1.0 → v1.1: removed C2 (sentence-boundary packing)

- **Agent/model**: ox-alpha (opencode CLI)
- **Scope read**: AGENTS.md ☑ ; session-log last 3 ☑ ; experiment-registry ☐ (no runs)
- **Actions**:
  - Removed C2 row from candidate table (`docs/research/research-plan.md` §4). C IDs kept stable (C3–C5 not renumbered) to preserve referential integrity with hypotheses and any prior notes.
  - Updated all dependent references: H1 evidence now `C3 vs C0` (§3); H3 comparators now `C4 vs C0/C3`; ablation grid `{C0, C1, C3, C4, C5}` = 45 cells (was 54); priority-2 size-interaction runs now `C0/C1 × tasks × {4000, 16000}` (12 runs); min-chunk extension sweep now applies to C3 only (§5.3).
  - Version-bumped charter header to v1.1 per §8 amendment rule.
  - Updated AGENTS.md §2 mission list: dropped "sentence-aware" from technique families.
- **Decisions & rationale**:
  - **Owner decision**: sentence-boundary packing (C2) removed because at long-context QA chunk sizes (4000–16000 tokens), whole-sentence packing differs from fixed-size slicing only in boundary placement within a ±1-sentence margin — a negligible fraction of an 8000-token chunk. Expected accuracy delta ≈ 0 while costing one full ablation column (~9 core-grid cells) plus a zh-capable sentence tokenizer dependency. Not worth the experimental budget; C3 already subsumes sentence-level handling inside oversized paragraphs.
  - Kept motivation text in §1 mentioning sentences — it describes the *problem* with fixed-size slicing (mid-sentence cuts), which C3 still addresses via recursion.
- **Expected effects / verification plan**: no code impact (P2 not started). Verify by grep: no standalone `C2` references remain in `docs/` or `AGENTS.md`.
- **Open questions / handoff**: none new. Standing items from Entries 001–002 still apply (model lock-in before P3; commit-vs-revert decision on local-model adaptations).

## [2026-08-25] Entry 004 — Charter amendment v1.1 → v1.2: English-only scope (all Zh.QA/Chinese removed from research docs)

- **Agent/model**: ox-alpha (opencode CLI)
- **Scope read**: AGENTS.md ☑ ; session-log last 3 ☑ ; experiment-registry ☑
- **Actions**:
  - **Owner decision**: study scope narrowed to English-only (`rag`, `en`). All Zh.QA/Chinese planning content removed from research-facing docs.
  - `docs/research/research-plan.md` → charter v1.2: RQ4 task interaction now RAG vs En.QA only; C5 risk note ("zh book conventions") dropped; §5.1 factors `{rag, en}`; ablation grid 30 cells (was 45); priority-1 main-table runs 10 (was 18); Zh.QA metric bullet removed from §5.4; diagnostics "(en)"; P2 "unit tests incl. zh" → "unit tests".
  - `AGENTS.md`: added explicit English-only scope bullet to §1 ("never run, cite, or plan around" the upstream zh pipeline); mission §2 benchmarks → HotpotQA-RAG + InfiniteBench En.QA; Zh.QA row removed from eval table; `longbook_qa_chn.jsonl` removed from data list; `eval_zh.sh` command removed from §6.
  - `docs/research/experiment-registry.md`: conventions now state `task ∈ {rag, en}` per v1.2; also fixed stale "C0–C5" chunker-ID reference left over from Entry 003.
  - Session log is append-only: historical zh mentions in Entries 001–003 are retained by policy; this entry supersedes them as the governing decision.
- **Decisions & rationale**:
  - **Docs only — no code/scripts touched.** Baseline code (`main.py`, `src/*.py`), eval scripts (`eval_zh.sh`, compute_scores variants), and `download_data.sh` keep upstream zh support: removing it would violate hard rules #2 (baseline integrity) and #3 (frozen eval scripts), and zh branches in code are inert for `--task rag|en`. Upstream `README.md` also left unchanged since it documents actual code capabilities; research intent is governed by AGENTS.md/research-plan.
  - Architecture-map rows in AGENTS.md that mention `"en/zh"` (CLI choices, truncation manner, info scoring) kept verbatim — they describe frozen baseline code facts needed to implement chunkers correctly; the new §1 scope bullet governs what we *run*.
  - Grid shrinkage (45→30 cells) materially cuts planned API cost; priority-2 size-interaction runs unchanged (C0/C1 × tasks × {4000,16000} = 12).
- **Expected effects / verification plan**: grep `zh|Zh|Chinese` across `docs/`, `AGENTS.md` → only hits should be this entry, Entries 001–003 history, the AGENTS.md scope bullet + baseline-code map rows, and registry scope note. No behavioral change until P2/P3.
- **Open questions / handoff**:
  1. Optional follow-up (needs owner approval, touches non-eval script): skip the `longbook_qa_chn.jsonl` download in `scripts/download_data.sh` to save bandwidth — currently left untouched for baseline integrity.
  2. Standing items from Entries 001–002 still apply (model lock-in before P3; commit-vs-revert decision on local-model adaptations).
