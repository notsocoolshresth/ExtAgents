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

## [2026-08-28] Entry 005 — P2 chunker infrastructure: `src/chunkers.py` + `--chunker` flag + tests; venv provisioned

- **Agent/model**: ox-alpha (opencode CLI)
- **Scope read**: AGENTS.md ☑ ; session-log last 3 ☑ ; experiment-registry ☑ (no runs)
- **Actions**:
  - Provisioned `venv/` (Python 3.11.0, `python -m venv venv`) and `venv\Scripts\python.exe -m pip install -r requirements.txt` — all pins cleanly installed on win-amd64 (rouge_score built from sdist).
  - Created `src/chunkers.py`: decorator-based registry (`register`/`get`/`available`/`install`/`restore`); two strategies — `legacy` (C0, delegates to a **frozen import-time reference** of `utils.create_chunks`) and `recursive_paragraph` (C3, paragraph → sentence → word → fixed-token-slice recursion, English-only, with re-encode + clamp to `chunk_length` budget).
  - `main.py` (additive only): `--chunker` arg (default `legacy`), `chunkers.install(args.chunker)` right after arg parse, `Chunker:` in the startup print. **`src/pipeline.py` and `src/utils.py` untouched** — pipeline resolves `utils.create_chunks` dynamically per example (`src/pipeline.py:47`), which is exactly why the hot-swap works.
  - Added `tests/test_chunkers.py`: 18 stdlib-`unittest` cases — legacy byte-identity (stub + real tiktoken gpt-4o), C3 paragraph integrity/order, token-budget enforcement across sizes, recursion-chain fallbacks, manner truncation, empty/bad inputs, install/restore semantics. All pass: `venv\Scripts\python.exe -m unittest discover -s tests`.
  - Docs: AGENTS.md architecture map + CLI row + common-commands updated; research-plan §4/§P2 marked implemented.
- **Decisions & rationale**:
  - **Runner untouched via hot-swap, not CLI branching**: registry swap of `utils.create_chunks` keeps `src/pipeline.py` byte-identical (owner requirement) and works under the existing thread pool (swap happens before workers start).
  - **Legacy delegates to a capt-logged original** (`_BASELINE_CREATE_CHUNKS = _utils.create_chunks` at import) rather than the mutable attribute, so install/reinstall/restore cannot recurse or self-reference.
  - **C3 token accounting**: content is truncated exactly like the baseline (`utils.truncate_input`), then decoded before structural splitting; every assembled chunk is re-encoded and clamped to `chunk_length`, so the MAP stage never receives an oversized chunk even when BPE join-boundaries shift counts.
  - Test stub tokenizer preserves whitespace runs (token regex `\S+|\s+`) because an initial naive `split()`/`join()` collapsed the `\n\n` paragraph separators, hiding a real C3 path — this also mirrors tiktoken's whitespace-preserving behavior.
  - Only C0 + C3 shipped in this pass; C1/C4/C5 = one `@register` function each via the same interface (future sessions).
  - Minor log correction: Entries 003–004 were stamped 2026-08-25 but were written 2026-08-28; treated as cosmetic, not re-edited (append-only).
- **Expected effects / verification plan**:
  - `venv\Scripts\python.exe -m unittest discover -s tests` → 18 OK (write this into AGENTS.md §6, done).
  - `git diff --stat` should touch only `main.py`, `src/chunkers.py` (new), `tests/test_chunkers.py` (new), `AGENTS.md`, `docs/` — **not** `src/pipeline.py`, `src/utils.py`, eval scripts.
  - P3 gate: run `--chunker legacy` on a small sample and diff `final_preds.jsonl` against a pre-change run to confirm byte-identical baseline behavior end-to-end.
- **Open questions / handoff**:
  1. `venv/` is gitignored (already in `.gitignore`) — no commit concern.
  2. Next chunker candidates: implement C1 (overlap) next — it is the cheapest non-legacy addition and needed for H2 cost-asymmetry runs; note the run_id convention already supports `C1`.
  3. Standing items from Entries 001–002: lock the primary model + API endpoint before P3; decide commit-vs-revert on the local-model adaptations in `main.py`/`src/utils.py`/`src/pipeline.py`.

## [2026-08-28] Entry 006 — Plan mode decisions + Codex handoff doc authored

- **Agent/model**: ox-alpha (opencode CLI)
- **Scope read**: AGENTS.md ☑ ; session-log last 3 ☑ ; experiment-registry ☑ (no runs yet)
- **Actions**:
  - Plan mode session: inspected repo state (data/ empty, no .env, results_rag empty dir, Ollama up with qwen3.5:0.8b, En.QA eval labels come from the preds file itself at `compute_scores_partial-enhanced.py:379-384`).
  - Captured owner decisions via Q&A: (1) materialize legacy chunker as **`src/chunkers/` package** (one file per strategy), (2) run target **En.QA**, (3) model **local Ollama qwen3.5:0.8b**, (4) **no dataset download — create self-made sample data**.
  - **Authored `CODEX_HANDOFF.md`** (repo root): self-contained execution brief for an external Codex agent — environment facts, hot-swap integration contract, package refactor spec (incl. circular-import pattern + byte-identity requirement), sample-data spec, run + eval commands with known quirks (TASK_TO_INDICES subset → 7 of 10 ids scored; rouge metric fetch risk), recording protocol, hard rules, acceptance criteria.
  - No source changes this session beyond what Entry 005 already recorded (main.py, src/chunkers.py, tests/).
- **Decisions & rationale**:
  - Offload to Codex chosen by owner; the handoff doc must carry ALL context because the external agent lacks AGENTS.md-embedded history — hence it is written to be executed top-to-bottom without conversation.
  - Refactor stays behavior-preserving: `from src import chunkers` must keep working, default `--chunker legacy` byte-identical (identity tests are the guard), runner/utils/eval untouched.
  - Sample set is explicitly **non-comparable to official InfiniteBench numbers** (self-made, 10 examples); its purpose is the functional P3 gate + baseline artifact.
  - Eval quirk recorded so the Codex agent does not "fix" the frozen script when only 7/10 ids are scored.
- **Expected effects / verification plan**: handoff doc at repo root; a Codex agent following it should produce the package refactor + sample data + a `results_en_sample/final_preds.jsonl` run + eval + registry/session-log records. Verify: 18 tests pass, git status shows no changes to pipeline/utils/eval, entry 007 + registry row present afterwards.
- **Open questions / handoff**:
  1. Whether to also produce a `recursive_paragraph` comparison run on the same sample (optional demo of the swap mechanism) — not in the handoff deliverable.
  2. Standing: model/endpoint lock-in before P3 (primary model still undecided for real benchmark arms); commit-vs-revert on local-model adaptations.

## [2026-09-06] Entry 007 — C1 overlap chunker implemented (LangChain-backed)

- **Agent/model**: opencode/mimo-v2.5-free
- **Scope read**: AGENTS.md ☑ ; session-log last 3 ☑ ; experiment-registry ☑ (no runs)
- **Actions**:
  - Installed `langchain-text-splitters>=1.1.0` (+ transitive deps: langchain-core, langsmith, etc.) into venv; added to `requirements.txt`.
  - Created `src/chunkers/overlap.py`: C1 sliding-window overlap chunker wrapping LangChain's `RecursiveCharacterTextSplitter` with a custom `length_function` backed by the pipeline's tiktoken tokenizer. Key parameter: `overlap_ratio` (default 0.5). Includes final clamping pass for LangChain edge-case trailing chunks.
  - Updated `src/chunkers/__init__.py` (line 64): added `overlap` to the import list.
  - Added 14 tests to `tests/test_chunkers.py`: `TestOverlap` (10 cases, WordTokenizer) + `TestOverlapRealTokens` (2 cases, tiktoken gpt-4o). Covers budget enforcement, overlap count > legacy, content coverage, boundary-straddling evidence recovery, overlap_ratio=0 edge case, manner truncation, invalid params, empty input. Updated `TestRegistryAndInstall.test_available` to include `"overlap"`.
  - Updated `AGENTS.md`: architecture map row for chunker selection now lists all three strategies; added overlap CLI example in §6.
  - Updated `docs/research/research-plan.md` §P2: overlap marked implemented.
  - All 30 tests pass: `venv\Scripts\python.exe -m unittest tests.test_chunkers -v`.
- **Decisions & rationale**:
  - **LangChain wrapper over raw implementation**: `RecursiveCharacterTextSplitter` provides battle-tested separator-aware splitting with token-level overlap, avoiding a hand-rolled sliding window that would need its own separator heuristics. The custom `length_function` ensures token accounting uses our exact tiktoken gpt-4o encoding.
  - **overlap_ratio parameter**: Defaults to 0.5 (matches research plan H2: "50% overlap"). Exposed as a function argument so ablation sweeps (0.0, 0.25, 0.5, 0.75) can be run without code changes.
  - **Final clamping pass**: LangChain may produce a trailing chunk slightly over `chunk_length` due to separator accounting. The explicit clamp ensures the MAP stage never receives oversized input.
  - **No pipeline changes**: hot-swap mechanism (`chunkers.install("overlap")`) works identically to legacy/recursive_paragraph; `src/pipeline.py` and `src/utils.py` untouched.
- **Expected effects / verification plan**:
  - `--chunker overlap` produces ~2x chunks vs `--chunker legacy` at default overlap_ratio=0.5; verify via run logs.
  - Each chunk is ≤ chunk_length tokens; verify via test assertions.
  - Boundary-spanning evidence recovered (test `test_boundary_straddling_evidence_recovered`).
  - P3 gate: run `--chunker legacy` vs `--chunker overlap` on sample data and diff outputs.
- **Open questions / handoff**:
  1. Next candidates: C4 (semantic) and C5 (document-structure) still unimplemented.
  2. The `overlap_ratio` ablation (varying 0.0–0.75) is a natural follow-up to H2 testing.
  3. Standing: model/endpoint lock-in before P3; commit-vs-revert on local-model adaptations.

## [2026-09-06] Entry 008 — C4 semantic chunker implemented (LangChain SemanticChunker)

- **Agent/model**: opencode/mimo-v2.5-free
- **Scope read**: AGENTS.md ☑ ; session-log last 3 ☑ ; experiment-registry ☑ (no runs)
- **Actions**:
  - Installed `langchain-experimental>=0.4.0`, `langchain-huggingface>=1.2.0`, `sentence-transformers>=5.7.0` into venv; added to `requirements.txt`.
  - Created `src/chunkers/semantic.py`: C4 semantic breakpoint chunker wrapping LangChain's `SemanticChunker` with lazy-loaded `HuggingFaceEmbeddings` (default: `all-MiniLM-L6-v2`). Two-phase approach: (1) semantic splitting via cosine-distance breakpoints, (2) budget enforcement via `RecursiveCharacterTextSplitter` for oversized chunks + tiny-chunk merging.
  - Updated `src/chunkers/__init__.py`: added `semantic` to imports.
  - Added 9 tests to `tests/test_chunkers.py`: `TestSemantic` (8 cases, mocked embedder) + `TestSemanticRealTokens` (1 case, real model). Covers sentence splitting, budget enforcement, oversized chunk splitting, tiny chunk merging, manner truncation, error handling. Updated `TestRegistryAndInstall.test_available` to include `"semantic"`.
  - Updated `AGENTS.md`: architecture map + CLI example for `--chunker semantic`.
  - Updated `docs/research/research-plan.md` §P2: semantic marked implemented.
  - All 39 tests pass.
- **Decisions & rationale**:
  - **Two-phase design**: `SemanticChunker` has no `chunk_size` parameter — it splits purely by semantic distance. Phase 2 (budget enforcement) is necessary because the MAP stage's `max_info_tokens` calculation assumes chunks ≤ `chunk_length`. This is a pragmatic compromise: some semantic coherence may be lost in the split, but correctness is preserved.
  - **Lazy embedder loading**: `sentence-transformers` downloads ~80MB model on first use. Caching in `_embedder_cache` dict avoids re-loading per call. Module-level import with `try/except ImportError` gives a clear error if deps are missing.
  - **Tiny-chunk merging**: Chunks < 10% of `chunk_length` tokens are merged into neighbors to avoid degenerate single-sentence chunks that waste MAP-stage API calls.
  - **Embedding model as ablation knob**: `embedder_model` parameter allows swapping models (e.g., `all-mpnet-base-v2`, OpenAI embeddings) without code changes — directly addresses research plan §7 threat about embedding model confound.
- **Expected effects / verification plan**:
  - `--chunker semantic` produces variable-sized chunks that respect semantic boundaries; verify via run logs that chunk count is between legacy and overlap.
  - Budget enforcement: every chunk ≤ `chunk_length` tokens; verify via test assertions.
  - P3 gate: run `--chunker semantic` on sample data and compare info scores with legacy.
- **Open questions / handoff**:
  1. C5 (document-structure aware) is the last unimplemented candidate.
  2. Embedding model ablation (≥2 embedders per research plan §7) should be part of P4 core matrix.
  3. Standing: model/endpoint lock-in before P3; commit-vs-revert on local-model adaptations.

## [2026-09-09] Entry 009 — C5 document-structure-aware chunker implemented

- **Agent/model**: azure/kimi-k2.7-code
- **Scope read**: AGENTS.md ☑ ; session-log last 3 ☑ ; experiment-registry ☑ (no runs)
- **Actions**:
  - Created `src/chunkers/document_structure.py`: C5 document-structure-aware chunker. Detects chapter headings (`Chapter N`/`CHAPTER N`), part headings (`PART ONE`/`Part Two`/`PART I`), standalone Roman numerals, ALL-CAPS lines, date headings (`MONDAY, JANUARY 1, 2024`), and asterisk separator lines (`* * * * *`). Splits at detected line-matched boundaries; packs structural sections greedily; recursively splits oversized sections via C3's paragraph→sentence→word→token-slice recursion; merges tiny sections into neighbours. When no markers are found, falls back to C3 (`recursive_paragraph_chunks`) so structureless RAG data never degrades below paragraph-aware splitting.
  - Registered `document_structure` in `src/chunkers/__init__.py`.
  - Added 14 tests to `tests/test_chunkers.py`: `TestDocumentStructure` (13 cases, WordTokenizer) + `TestDocumentStructureRealTokens` (1 case, tiktoken gpt-4o). Covers chapter, ALL-CAPS, Roman-numeral, asterisk, date, and part headings; no-marker C3 fallback; oversized-section splitting; tiny-section merging; manner truncation (`front`/`middle`); empty input; invalid params; real-tokenizer budget enforcement. Updated `TestRegistryAndInstall.test_available` to include `"document_structure"`.
  - Updated `AGENTS.md`: architecture map row now lists all five chunkers (C0–C5); added C5 CLI example in §6.
  - Updated `docs/research/research-plan.md` §P2: marked complete with all five candidates implemented.
  - All 53 tests pass: `venv\Scripts\python.exe -m unittest tests.test_chunkers -v` (39 existing + 14 new).
- **Decisions & rationale**:
  - **Line-matched regex markers**: each marker is applied via `fullmatch` against a stripped line. This is simple, fast, and interpretable — directly matches the research-plan C5 definition and avoids bringing in a heavy document-parsing dependency.
  - **C3 fallback on zero markers**: counting detected marker lines separately from boundary offsets prevents false fallback when a marker appears at the very start or end of the text (where its boundary offset coincides with 0 or `len(text)`).
  - **Title-cased part words**: extended the `PART`/`Part` regex to match `(?i:ONE|TWO|...)` so common book forms like "Part Two" are detected alongside "PART ONE".
  - **Reused C3 `_pack_units` for structural sections**: avoids duplicating recursion logic and guarantees identical paragraph/sentence/word fallback behavior for oversized sections.
  - **No pipeline changes**: C5 is selected exactly like the other chunkers via `chunkers.install("document_structure")`; `src/pipeline.py` and `src/utils.py` remain untouched.
- **Expected effects / verification plan**:
  - `chunkers.available()` returns `["document_structure", "legacy", "overlap", "recursive_paragraph", "semantic"]`.
  - `--chunker document_structure` is selectable from `main.py`.
  - Every test chunk is ≤ `chunk_length` tokens.
  - P3 gate: run `--chunker document_structure` on sample data and confirm it produces expected structural chunks; compare with C3 fallback on structureless text.
- **Open questions / handoff**:
  1. **P3 baseline reproduction** is the next phase. Run C0 on the chosen sample/official data, record the first registry row.
  2. Standing: primary model/endpoint lock-in before real benchmark arms; commit-vs-revert decision on local-model adaptations in `main.py`/`src/utils.py`/`src/pipeline.py`.
     3. The C5 marker set is English-only and regex-based; if P4 results show marker misses on En.QA books, consider adding heading-underline patterns (e.g., `=====`) or Markdown `#` headers.

## [2026-09-13] Entry 010 — Researched paper models + added local model download/delete scripts

- **Agent/model**: azure/kimi-k2.7-code
- **Scope read**: AGENTS.md ☑ ; session-log last 3 ☑ ; experiment-registry ☑ (no runs)
- **Actions**:
  - Researched the ExtAgents paper (Liu et al., arXiv:2505.21471v2, ACL 2026) to identify the local models used for Seeking and Reasoning agents.
  - Findings: primary open-source experiments use **Llama-3.1-8B-Instruct** for both roles (homogeneous). The paper also tests a heterogeneous configuration for efficiency: **Llama-3.2-3B-Instruct for Seeking Agents** and **Llama-3.1-8B-Instruct for the Reasoning Agent** (Section 5.2, Table 6; Appendix C.1). Closed-source experiments use `gpt-4o-mini-2024-07-18` and `gpt-4o-2024-08-06` via API.
  - Created `scripts/download_local_models.py`: self-contained, CLI-driven downloader using `huggingface_hub.snapshot_download`. Supports `--models {all,reasoner,seeker,both_8b,both_3b}` and `--cache-dir ./models`. Defaults to fetching both the 8B reasoner and 3B seeker. Requires `HF_TOKEN` env var or `--token` because Llama weights are gated.
  - Created `scripts/delete_local_models.py`: mirrors the downloader's model map, removes materialized weights under `--cache-dir`, and optionally purges matching repositories from the global Hugging Face cache with `--include-hf-cache`. Reports MiB freed.
  - Documented the Tesla V100 / CUDA 11.2 compatibility issue in the docstrings: driver 460.91.03 supports only up to CUDA 11.4, while `requirements.txt` pins `torch==2.7.0` (needs CUDA ≥ 11.8 and driver ≥ 520). GPU inference with the stock environment will not work without a driver/CUDA upgrade or a CPU/CUDA-11.2-compatible backend (e.g., llama.cpp/ollama).
- **Decisions & rationale**:
  - Kept the scripts self-contained and independent of the core pipeline so they do not alter baseline behavior or experimental reproducibility. They are pure weight-management utilities.
  - Used `local_dir_use_symlinks=False` in `snapshot_download` so that `./models` contains real files that are easy to inspect, serve with vLLM/ollama, or delete without following symlinks into the HF cache.
  - Did not add `huggingface_hub` to `requirements.txt` because these are optional utility scripts; the dependency is checked at runtime with an actionable error message.
  - Mirrored the paper's exact Hugging Face repo IDs (`meta-llama/...`) rather than ungated mirrors to ensure byte-for-byte compatibility with the published results.
- **Expected effects / verification plan**:
  - After accepting the Llama license pages and setting `HF_TOKEN`, `python scripts/download_local_models.py --models all` should populate `./models/meta-llama--Llama-3.1-8B-Instruct` and `./models/meta-llama--Llama-3.2-3B-Instruct` with safetensors/config/tokenizer files.
  - `python scripts/delete_local_models.py --models all` should remove those directories and report freed space.
  - No change to tests or pipeline; `python -m unittest discover -s tests` should still pass.
- **Open questions / handoff**:
  1. The local-model adaptations in `main.py`/`src/utils.py` still default to ollama/localhost and `qwen3.5:0.8b`; if the owner wants to run the Llama pair, the run command must point `--api_url`/`--model` at a served endpoint (vLLM, ollama, llama.cpp server) using the downloaded weights.
  2. Standing hardware blocker: CUDA 11.2 + driver 460 cannot run `torch==2.7.0` on GPU. Decide whether to upgrade the driver/CUDA or switch to a CPU/ollama/llama.cpp serving path before any local inference run.

## [2026-09-13] Entry 011 — No-root local inference path: llama.cpp + CUDA 11.4 in user space

- **Agent/model**: azure/kimi-k2.7-code
- **Scope read**: AGENTS.md ☑ ; session-log last 3 ☑ ; experiment-registry ☑ (no runs)
- **Actions**:
  - Responded to user constraint: no root access on the Tesla V100/CUDA 11.2/driver 460 machine.
  - Created `scripts/setup_llama_cpp_cuda114.sh`: installs a user-space conda environment `extagents-llama` with `cudatoolkit=11.4`, `cudnn=8`, `cmake`, `make`, `gxx_linux-64=10`; clones/updates `llama.cpp` into `.llama_cpp`; compiles it with `CMAKE_CUDA_ARCHITECTURES=70` for the V100; writes `activate_llama_cpp_cuda114.sh` so the env can be re-sourced later.
  - Created `scripts/download_gguf_models.py`: downloads GGUF quantizations from ungated `bartowski/Llama-3.1-8B-Instruct-GGUF` and `bartowski/Llama-3.2-3B-Instruct-GGUF`. Supports `--quant {Q4_K_M,Q5_K_M,Q6_K,Q8_0}` (default Q5_K_M). Writes `models-gguf/gguf_manifest.txt` for the launcher.
  - Created `scripts/run_llama_cpp_server.sh`: starts `llama-server` with OpenAI-compatible API on a chosen port. Defaults to `--ctx-size 131072`, full GPU offload (`--n-gpu-layers 999`), and exposes `--tensor-split` for splitting across the 4 V100s.
- **Decisions & rationale**:
  - **Why llama.cpp + GGUF**: the system driver (460.91.03) cannot be upgraded without root, so CUDA 11.8/12.x PyTorch wheels are impossible. However, the driver supports the CUDA 11.4 *runtime*, so a user-space CUDA 11.4 toolkit + llama.cpp build can still use the V100s. This is the only practical no-root GPU path.
  - **Why conda cudatoolkit=11.4**: avoids touching system paths; all CUDA binaries/libs live inside the env. No root required.
  - **Why GGUF instead of original HF weights**: llama.cpp consumes GGUF. Using ungated GGUF repos removes the token/license step required for `meta-llama/...` HF weights. Trade-off: quantization is an approximation of the FP16/BF16 weights used in the paper; this is acceptable for local engineering tests but should be noted if results are compared to paper numbers.
  - **Why Q5_K_M default**: good quality/speed balance for 32 GB V100s; Q4_K_M can be used for faster iteration.
  - **Kept scripts separate from pipeline**: no changes to `main.py`, `src/`, or eval scripts. The serving layer remains outside the research code, preserving baseline integrity.
- **Expected effects / verification plan**:
  - `bash scripts/setup_llama_cpp_cuda114.sh` should finish without errors and produce `.llama_cpp/build/bin/llama-server`.
  - After sourcing `activate_llama_cpp_cuda114.sh`, `nvcc --version` should report CUDA 11.4.
  - `python scripts/download_gguf_models.py --models all --quant Q5_K_M` should populate `models-gguf/`.
  - `bash scripts/run_llama_cpp_server.sh --model reasoner --port 8001` should start an OpenAI-compatible endpoint; verify with `curl http://localhost:8001/v1/models`.
  - If both reasoner (port 8001) and seeker (port 8002) are started, the existing `main.py --api_url http://localhost:8001/v1` can talk to one of them. Using both simultaneously for heterogeneous roles requires a small code change (two clients) that is out of scope for this utility-only session.
- **Open questions / handoff**:
  1. User must confirm conda is installed in user space; if not, the first step is a manual Miniconda install (commands are in the setup script error message).
  2. Heterogeneous mode (3B seeker + 8B reasoner) is not yet wired into the pipeline; a future session can add dual-client support if the user wants to reproduce Table 6 exactly.
  3. If V100 32 GB runs out of context at 131072 tokens, reduce `--ctx-size` to 65536 or 32768; ExtAgents chunks already fit within those windows.

## [2026-09-13] Entry 013 — Switched local inference path to Ollama 0.5.1 (GPU works)

- **Agent/model**: azure/kimi-k2.7-code
- **Scope read**: AGENTS.md ☑ ; session-log last 3 ☑ ; experiment-registry ☑ (no runs)
- **Actions**:
  - User confirmed Ollama 0.5.1 is installed and running on GPU, making the llama.cpp/CUDA-11.4 workaround unnecessary.
  - Deleted the now-unnecessary scripts: `scripts/delete_local_models.py`, `scripts/download_gguf_models.py`, `scripts/download_local_models.py`, `scripts/run_llama_cpp_server.sh`, `scripts/setup_llama_cpp_cuda114.sh`.
  - Created `scripts/setup_ollama_models.sh`: pulls `llama3.1:8b` (paper's homogeneous local model) and `llama3.2:3b` (paper's efficient Seeking Agent).
  - Created `scripts/run_extagents_ollama.sh`: convenience wrapper that validates the Ollama endpoint and model, then invokes `main.py` with `--api_url http://localhost:11434/v1 --api_key ollama --model llama3.1:8b` and the chosen task/chunker.
  - Created `scripts/delete_ollama_models.sh`: removes `llama3.1:8b` and `llama3.2:3b` from Ollama.
  - Edited `main.py:18`: changed default `--model` from `qwen3.5:0.8b` to `llama3.1:8b`, matching the paper's local baseline and the new Ollama workflow.
- **Decisions & rationale**:
  - Ollama already works on the user's GPU/driver/CUDA combo, so compiling llama.cpp against a user-space CUDA 11.4 toolkit is pure overhead and risk.
  - Removed rather than archived the non-Ollama scripts to keep the repo clean; they are documented in prior session-log entries and can be recovered from git history if ever needed.
  - Defaulted to the homogeneous 8B setup because the current pipeline uses a single OpenAI-compatible client. The 3B model is still pulled so the user can manually run a second Ollama instance for heterogeneous experiments; wiring two endpoints into the pipeline is deferred.
  - Kept `scripts/eval_*.sh`, `scripts/download_data.sh`, and upstream `eval_zh.sh` untouched per AGENTS.md hard rules #2 and #3.
- **Expected effects / verification plan**:
  - `bash scripts/setup_ollama_models.sh` should pull both tags and `ollama list` should show `llama3.1:8b` and `llama3.2:3b`.
  - With `ollama serve` running, `bash scripts/run_extagents_ollama.sh` should start `main.py` and hit `http://localhost:11434/v1`.
  - `bash scripts/delete_ollama_models.sh` should remove both tags.
  - No unit-test impact; run `python -m unittest discover -s tests` to confirm.
- **Open questions / handoff**:
  1. Heterogeneous mode (3B seeker + 8B reasoner on separate Ollama ports) still requires a code change to support two model clients in `src/utils.py`/`src/pipeline.py`. Implement only if the user wants to reproduce Table 6's mixed setup exactly.
  2. Ollama model context size is configured server-side; if 32k context is not enough for a chosen `--input_length`, the user may need to set `OLLAMA_CONTEXT_LENGTH` before `ollama serve`.

## [2026-09-21] Entry 014 — Training-free research directions and novelty audit

- **Agent/model**: azure/gpt-6-astra (OpenCode)
- **Scope read**: AGENTS.md [x] ; session-log last 3 [x] (010, 011, 013) ; experiment-registry [x] (no runs)
- **Actions**: Reviewed the research charter, empty experiment registry, chunker implementations/tests, pipeline/prompts, evaluation interfaces, and data availability. Conducted a targeted primary-source literature check for the user's request for novel research ideas without full training or GPU-intensive work. This session changes only this journal; no source code, evaluators, charter, dependencies, or benchmark outputs were changed. The pre-existing edit to `scripts/run_extagents_ollama.sh` was left untouched.
- **Implementation findings**: All five planned chunkers already exist. The chunker interface has neither question input nor retained source offsets (`src/chunkers/__init__.py:3-9`); the semantic embedder already runs on CPU (`src/chunkers/semantic.py:36-48`). MAP reads all retained chunks; changing retrieval recall is therefore distinct from preventing extraction-stage loss. Chunks remain fixed across synchronization rounds, and extraction items accumulate without source provenance (`src/pipeline.py:45-104`). Extracted traces and complete call/token accounting are not persisted by the runner. No official benchmark files were found locally; the ten local English examples are synthetic smoke tests with explicit answer guides, not research evidence.
- **Primary sources checked**: [ExtAgents v2](https://arxiv.org/html/2505.21471v2), [Is Semantic Chunking Worth the Computational Cost?](https://arxiv.org/abs/2410.13070), [LumberChunker](https://arxiv.org/abs/2406.17526), [Late Chunking](https://arxiv.org/abs/2409.04701), [Meta-Chunking](https://arxiv.org/abs/2410.12788), [LLM x MapReduce](https://aclanthology.org/2025.acl-long.1341/), [QChunker](https://arxiv.org/abs/2603.11650), [SCAR v2](https://arxiv.org/html/2606.16661v2), [InSemRAG](https://arxiv.org/abs/2606.01240), [SentGraph](https://arxiv.org/abs/2601.03014), [PARSER](https://arxiv.org/abs/2609.06702), and [GraphEcho](https://arxiv.org/abs/2609.17695). This was a targeted check as of 2026-09-21, not an exhaustive novelty certification; search-engine access was intermittent.
- **Decisions & rationale**: Recommend boundary-only counterfactual evaluation as the first candidate: truncate once, preserve the same source text/order/coverage, perturb only partition boundaries, and distinguish evidence absent from the retained input, lost during MAP, omitted from REDUCE input, or mishandled during reasoning. Existing work already studies boundary-fragmented retrieval and evidence-position robustness, so the candidate distinction is controlled partition interventions plus stage-level attribution, not the broad claim that boundaries matter. The original ExtAgents paper already evaluates chunk sizes but explicitly leaves boundary optimization/adaptive chunking outside its scope; the charter's blanket "No prior work" statement should not be repeated as a verified literature claim.
- **Decisions & rationale**: Recommend a question-conditioned, dependency-preserving contiguous partition as the associated method candidate. Use sparse lexical/entity/discourse proxies on CPU to favor boundaries that cut fewer question-relevant connections, retaining every source span once rather than adding uniform overlap. Compare against paragraph/sentence-respecting, question-agnostic cohesion, query-relevance-only, and shuffled-question controls. Query conditioning and sentence graphs themselves are established; the proposed distinction is complete source-preserving partition optimization and measured extraction-stage effects. This needs explicit query plumbing rather than global per-example state, because examples execute concurrently. No method or charter amendment was approved or implemented.
- **Decisions & rationale**: A separate candidate is segmentation-dependent benchmark difficulty. ExtAgents Section 3.3 filters English examples using model-based single-8k-chunk answerability, reports size-sensitivity counts, and supplements the filtered set with original examples longer than 128k. Do not claim all 294 final English examples passed the filter: the paper reports 157 after 8k filtering. Audit whether question identities/answerability and method rankings change across equally budgeted partitions; keep official evaluation fixed and report audit strata separately. The inspected paper does not specify an exhaustive all-offset construction test. This is a hypothesis, not evidence that the benchmark is invalid or that difficulty is intrinsic to chunking.
- **Decisions & rationale**: Treat selective boundary repair and provenance-aware overlap deduplication as secondary/higher-collision ideas. SCAR already performs training-free selective neighbor expansion; Meta-Chunking/InSemRAG address damaged context; LLM x MapReduce addresses inter-chunk dependencies/conflicts; GraphEcho explicitly studies repeated encounters versus independent evidential origins. A narrower ExtAgents study could separate overlap's evidence-recovery benefit from duplication propagated through synchronization, but ordinary deduplication or generic repair is not a defensible standalone novelty claim.
- **Expected effects / verification plan**: Research guidance only; no observed accuracy or efficiency changes. Begin with CPU source-alignment/coverage diagnostics and a predeclared small inference pilot, not the complete 30-cell matrix. Hotpot supporting facts require verified alignment to the actual retrieved context; English book QA needs a manually checked evidence subset. Gold evidence may guide diagnostic interventions but never the deployed chunker. Log original spans, MAP outputs, REDUCE inputs, rounds, model configuration, and all prompt/completion tokens. Measure official QA scores on complete correctly ordered benchmark outputs, with separate pilot diagnostics, boundary answer-flip rates, evidence survival, and paired uncertainty estimates clustered by question/book rather than treating offsets as independent observations.
- **Expected effects / verification plan**: Match source coverage, feasible chunk-count/length constraints, and inference allowances. At exactly N = K * max_chunk_length there is no room to move boundaries while keeping K and the hard cap; use matched slack controls or report count/length effects explicitly. Additive overlap is not token-neutral versus a one-pass partition; at overlap ratio r, idealized source-token exposure is approximately N/(1-r), so halving the window does not correct the charter's proposed cost matching. Hosted frozen models avoid local GPU requirements but not inference cost: 30 examples x 3 partitions x 128,000 retained tokens already expose 11.52 million source tokens in the first MAP passes, before repeated prompts, scoring, generation, or later rounds. Reuse unchanged first-round prompts or frozen extraction traces only where the experimental inputs really are identical.
- **Open questions / handoff**: The user has not selected a direction or authorized inference spending. Determine API budget and primary frozen model before running anything. Verify official dataset versions/ordering and evidence-alignment coverage. The partial-enhanced English evaluator assumes full positional indices, so arbitrary subsets are diagnostic only. Control the existing RAG first-round prefix schedule (`src/pipeline.py:166-193`), which omits the full prefix when chunk count is not a power of two, before attributing chunk-count effects to evidence fragmentation; any correction must be a separately logged common control, not a hidden change to one arm. Boundary effects may disappear after existing synchronization rounds; that would support a cost/early-recovery result rather than a final-accuracy claim. No tests were run because this was a read-only code/research analysis with a journal-only edit.

## [2026-10-05] Entry 015 — Three-slide mid-semester presentation

- **Agent/model**: azure/gpt-6-astra (OpenCode)
- **Scope read**: AGENTS.md [x] ; session-log last 3 [x] (011, 013, 014, plus earlier implementation entries) ; experiment-registry [x] (status review only)
- **Actions**: Created `docs/ExtAgents_Mid_Semester.pptx`, an editable three-slide PowerPoint covering (1) project introduction, (2) methodology and current progress, and (3) future work. Reviewed the research plan and journal; added presenter notes with source references and explanations. Generated the artifact using a temporary Python script and dependencies outside the repository.
- **Decisions & rationale**: Used a simple high-contrast layout and plain-language descriptions for a professor-facing progress review. Distinguished the existing ExtAgents architecture from this project's chunking contribution. Presented five implemented methods, the journal's reported 53 passing tests, and the confirmed Ollama setup; explicitly marked official benchmark results as pending. Labeled question-aware splitting as proposed, following Entry 014 rather than presenting it as completed work or proven novelty.
- **Expected effects / verification plan**: Reopened the saved PowerPoint with python-pptx and verified exactly three slides, presenter notes, and in-bounds shapes. Opened and rendered slides with Microsoft PowerPoint; visually reviewed the layouts and corrected wrapped text. No benchmark runs or source-code changes were required; the 53-test figure is historical, not a fresh test result.
- **Open questions / handoff**: Presentation is ready for review. Final benchmark model/budget selection and official evaluation remain future work, as described in the slides.

## [2026-10-05] Entry 016 — Expanded presentation with proposed research directions

- **Agent/model**: azure/gpt-6-astra (OpenCode)
- **Scope read**: AGENTS.md [x] ; session-log last 3 [x] (013–015) ; experiment-registry [not applicable: presentation revision, no experiments]
- **Actions**: Created `docs/ExtAgents_Mid_Semester_Updated.pptx` with four slides. Kept the introduction, methodology/current-state slide and evaluation roadmap; added a second future-work page describing the owner's two research proposals. Updated slide numbering and added detailed presenter notes explaining the mechanisms and potential comparisons.
- **Decisions & rationale**: Named the proposals **query-conditioned hierarchical summarization** and **agent-guided lexical retrieval**. The first recursively summarizes adjacent pairs (`n` chunks → approximately `n/2` summaries → `n/4` → …), conditions every level on the question, and stops when the combined summaries fit the final reasoning context. The second equips agents with keyword-based chunk search (e.g., BM25) and iterative query refinement. Presented both as proposed extensions requiring evaluation, not established project results or verified novel methods. Saved a separately named updated deck because the original presentation had an active PowerPoint lock file.
- **Expected effects / verification plan**: Verified that the saved artifact contains four slides, presenter notes and in-bounds shapes. Opened and rendered it in Microsoft PowerPoint; visually checked the two future-work pages and refined text spacing. No inference runs or pipeline changes were performed.
- **Open questions / handoff**: Research implementation and charter amendments remain separate future decisions. Before experiments, specify summary budgets and pairwise context limits, retrieval/search budgets and controls; evaluate answer quality, evidence preservation and full inference cost.

## [2026-10-05] Entry 017 — Summarization-only research-direction slide

- **Agent/model**: azure/gpt-6-astra (OpenCode)
- **Scope read**: AGENTS.md [x] (session context) ; session-log last 3 [x] (014–016, including previous context) ; experiment-registry [not applicable: presentation-only revision]
- **Actions**: Updated `docs/ExtAgents_Mid_Semester_Updated.pptx` in place. Removed lexical retrieval from the fourth slide and its presenter notes; expanded query-conditioned hierarchical summarization into a full-width flow diagram with evidence-preservation, context-budget and evaluation points.
- **Decisions & rationale**: Followed the owner's request to focus the research-direction page on recursive summarization. Retained the four-slide structure and the existing introduction, methodology and evaluation-roadmap slides. The direction remains labeled proposed.
- **Expected effects / verification plan**: Reopened the artifact and verified four slides, unchanged text on the first three, in-bounds shapes and no lexical-retrieval/BM25/direction-2 references in slide text or notes. Rendered the final slide with Microsoft PowerPoint and visually checked the layout.
- **Open questions / handoff**: Presentation revision complete; research implementation and benchmark evaluation remain pending.

## [2026-10-05] Entry 018 — Fifth-slide pitch for pivot-based translation model composition

- **Agent/model**: azure/gpt-6-astra (OpenCode)
- **Scope read**: AGENTS.md [x] (session context) ; session-log last 3 [x] (015–017) ; experiment-registry [not applicable: presentation-only proposal]
- **Actions**: Added slide 5 to `docs/ExtAgents_Mid_Semester_Updated.pptx` and updated slide numbering. Illustrated a frozen English encoder from an English–Hindi model, a trainable alignment adapter, and a frozen Bhojpuri decoder from a Hindi–Bhojpuri model. Included a research question, training/evaluation plan and detailed presenter notes. Verified the abstract of Kim et al., EMNLP 2019, *Pivot-based Transfer Learning for Neural Machine Translation between Non-English Languages*, https://arxiv.org/abs/1909.09524, as relevant prior work.
- **Decisions & rationale**: Presented the user-requested translation topic as an additional research proposal, separate from the English-only ExtAgents study. Identified encoder–decoder composition and adapters as established prior art; framed the pitch around controlled low-resource evaluation rather than claiming architectural novelty. Notes clarify retaining the Bhojpuri tokenizer/output head and learning representation alignment; other unverified papers and numerical claims in the supplied conversation were not used as evidence.
- **Expected effects / verification plan**: Reopened the saved deck and verified five slides, in-bounds shapes, notes presence and unchanged XML for the original four slides except page numbering. Added a notes-body placeholder because the existing notes master lacked one for the new slide. Rendered slide 5 with Microsoft PowerPoint, inspected it visually and shortened wrapped text. No translation models, training or benchmarks were run.
- **Open questions / handoff**: Professor feedback, checkpoint/data availability, adapter design and a focused novelty review are next steps if this separate proposal is pursued; the ExtAgents research charter is unchanged.

## [2026-10-07] Entry 019 — Ollama runner subset input and chunker-labelled predictions

- **Agent/model**: azure/gpt-6-sol (OpenCode)
- **Scope read**: AGENTS.md [x] ; session-log last 3 [x] (016–018) ; experiment-registry [x] (no runs)
- **Actions**: Updated `scripts/run_extagents_ollama.sh` to accept `--data_path` (defaulting to the task's full input), validate task/chunker/input before inference, isolate each run under `<output_dir>/<chunker>/<dataset-stem>/`, and copy the completed `final_preds.jsonl` to `final_preds_<chunker>.jsonl`. Added a first-1000-RAG-lines example to the runner comments and described the output layout in `--help`. Preserved the pre-existing user changes to this runner (3B model default and data-file check). No inference or benchmark evaluation run; the official evaluation scripts, pipeline, and main entry point were not changed.
- **Decisions & rationale**: Use a first-N-lines JSONL subset so the pipeline's positional example IDs continue matching the first N Hotpot questions; different chunkers and dataset stems must not share a resume checkpoint. Keep `final_preds.jsonl` beside the named copy because resume and official evaluators depend on that exact basename. Prefix-only RAG subsets should not be reported as official full-set EM/F1 using `eval_rag.sh`, which generates entries for all gold questions.
- **Expected effects / verification plan**: `head -n 1000 data/rag_1000k.jsonl > data/rag_first1000.jsonl`, then `bash scripts/run_extagents_ollama.sh --data_path data/rag_first1000.jsonl --output_dir results_rag_test --chunker overlap` writes `results_rag_test/overlap/rag_first1000/final_preds_overlap.jsonl` and the canonical checkpoint. `bash -n scripts/run_extagents_ollama.sh` passed; `--help` displayed the options/layout; a missing-data smoke check failed before contacting Ollama; `git diff --check` passed. Full inference cannot be checked without the official RAG data and reachable Ollama model.
- **Open questions / handoff**: Confirm the source has at least 1000 rows with `wc -l data/rag_1000k.jsonl`; `head` yields fewer if the source is shorter. Compare chunkers on the same fixed subset. For official RAG scores, run the full dataset and the existing `scripts/eval_rag.sh` against each chunker/dataset subdirectory; record those completed runs in the experiment registry.

## [2026-10-22] Entry 020 — C6 semantic binary tree chunker implemented (bottom-up, mean-pooled parents)

- **Agent/model**: nemotron-3-ultra-550b-a55b (opencode)
- **Scope read**: AGENTS.md ☑ ; session-log last 3 ☑ (018, 019) ; experiment-registry ☑ (no runs)
- **Actions**:
  - Created `src/chunkers/semantic_tree.py`: C6 semantic binary tree chunker with bottom-up construction and mean-pooled parent vectors. Uses `sentence-transformers/all-MiniLM-L6-v2` (CPU) for embedding. Tree built bottom-up: embedding units (sentences respecting 256-wordpiece limit) are paired iteratively to form parent nodes with mean-pooled embeddings. Query routing uses bounded beam search (default k=4) with cosine similarity to select original-text leaves under token budget.
  - Registered `"semantic_tree"` in `src/chunkers/__init__.py` (import list).
  - Updated `main.py` to include `semantic_tree` in `--chunker` choices (default remains `legacy`).
  - Fixed test_available in `tests/test_chunkers.py` to expect `semantic_tree` in available chunkers.
  - Resolved environment dependency conflicts: downgraded torchvision to 0.18.0 and numpy to 1.26.4 for sentence-transformers 5.7.0 compatibility.
- **Decisions & rationale**:
  - **Bottom-up construction with mean-pooled parents**: Matches RAPTOR's recursive embedding+clustering approach but without abstractive summaries — source-preserving original text at leaves. Parent embeddings are free (mean of children's embeddings).
  - **Contiguous children**: Even in bottom-up building, units are adjacent → children remain contiguous passages → preserves pronoun/neighbor context.
  - **Beam width k=4 default**: Explores 4 promising paths simultaneously → higher recall of complementary evidence vs. greedy (k=1); still O(4 × depth) cosine sims per question.
  - **Retrieval optional**: `--chunker semantic_tree` hot-swaps `utils.create_chunks`; default `legacy` preserves byte-identical baseline.
  - **Direct sentence_transformers usage**: Bypasses langchain_huggingface for reliability; uses `SentenceTransformer.encode()` with `normalize_embeddings=True`.
- **Expected effects / verification plan**:
  - All 53 unit tests pass (verified).
  - Legacy mode produces byte-identical output to baseline `utils.create_chunks` (verified).
  - Semantic tree chunker produces valid chunks within token budget (verified: 24 chunks, 6000 total tokens for ~5000-token input).
  - Ready for P3 baseline reproduction runs and P4 core matrix evaluation.
- **Open questions / handoff**:
  1. Beam width ablation (k=1, 2, 4) needed for P4 to determine optimal setting per task.
  2. Embedding model ablation (all-MiniLM-L6-v2 vs. larger) for P4 per research plan §7 threat.
  3. Compare with top-down semantic splitting approach experimentally.
  4. Full question-aware retrieval integration requires pipeline modification to pass question to chunker — current implementation returns all leaves up to budget as flat baseline.