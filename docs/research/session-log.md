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
