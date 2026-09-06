# Research Plan — Systematic Study of Chunking Techniques in ExtAgents

> Status: **Charter v1.2** (pre-experiment). Amendments only via session-log entries.
> v1.2: English-only scope — all Zh.QA/Chinese content removed from research sections — see session-log Entry 004.
> v1.1: Removed C2 (sentence-boundary packing) — see session-log Entry 003.
> Owner: Shresth. Target venue: **ACL** (main conference or Findings).

---

## 1. Motivation

ExtAgents answers questions over ~128k-token contexts by map-reduce over LLM agents with
fixed context windows. The very first step of that pipeline — how the context is cut into
chunks (`src/utils.py:104-133`) — is currently the *least principled* step:

- Fixed-size token slices ignore sentence, paragraph, and document structure → evidence
  fragments mid-sentence/mid-argument, degrading per-chunk extraction (MAP stage).
- No overlap → an answer whose supporting span straddles a boundary is split across two
  chunks; neither chunk alone contains it.
- Truncation to `input_length` ("front" for RAG, "middle" for En.QA) discards content
  arbitrarily relative to where evidence lives.
- Chunk count drives cost: `#chunks × iterations` extraction calls + scoring calls +
  reduce attempts. Chunking choices therefore trade accuracy against API cost/latency.

No prior work (including the original ExtAgents paper) systematically isolates the effect
of chunking granularity/boundaries in a multi-agent map-reduce QA pipeline. That is our gap.

## 2. Research Questions

- **RQ1**: Do linguistically/pragmatically motivated chunk boundaries improve final QA
  accuracy over fixed-size token chunks at equal token budget?
- **RQ2**: Does chunk overlap recover boundary-spanning evidence, and at what cost
  (extra chunks → extra API calls)?
- **RQ3**: Does semantic/document-structure-aware chunking improve the MAP-stage info
  quality and hence REDUCE-stage efficiency (fewer candidate-rank attempts, fewer
  "no answer" retries)?
- **RQ4**: How do these effects interact with task type (single-hop-ish RAG vs long-book
  narrative En.QA) and chunk size (4000 / 8000 / 16000 tokens)?

## 3. Hypotheses

| ID | Hypothesis | Primary evidence |
|---|---|---|
| H1 | Boundary-aware chunking (paragraph/discourse units) ≥ fixed-size on EM/F1 at equal budget | C3 vs C0 |
| H2 | Overlap improves recall of boundary-spanning evidence; gains shrink as chunks grow | C1 vs C0, interaction with chunk_length |
| H3 | Semantic chunking concentrates relevant evidence per chunk → higher info scores, fewer reduce attempts | C4 vs C0/C3 |
| H4 | Document-structure awareness helps most on En.QA (books have chapter structure), least on RAG (concatenated snippets) | C5 vs others per task |

## 4. Candidate Techniques

All techniques implement the existing interface:
`create_chunks(tokenizer, context, chunk_length, input_length, manner) -> list[str]`
(module `src/chunkers.py` — implemented in P2, selected via `--chunker <id>`; default `legacy` = baseline behavior).

| ID | Technique | Definition | Expected effect | Risks/costs |
|---|---|---|---|---|
| **C0** | Fixed-size token blocks *(baseline)* | Current code path, unchanged | Reference point | — 
| **C1** | Sliding window + overlap | Fixed blocks with stride < window (e.g., 50% overlap); dedupe downstream info if needed | Recovers boundary-straddling evidence (H2) | ↑ #chunks (~2×) → ↑ cost; duplicate info may pollute reduce prompt |
| **C3** | Recursive paragraph-aware splitting | Split on paragraphs first; oversized paragraphs recurse to sentences then words (LangChain-style, adapted to token counts) | Respects discourse units (H1) | Implementation complexity; edge cases (no paragraph breaks) |
| **C4** | Semantic breakpoint chunking | Embed sliding windows; cut at local minima of adjacent-window cosine similarity; enforce min/max chunk sizes | Groups topically coherent content (H3) | Needs an embedding model (new dependency + runtime cost); embedding choice is itself a confound to ablate |
| **C5** | Document-structure aware | Detect chapters/headings (regex/markers in InfiniteBench books; section titles in RAG wiki text); chunks align to structural units, splitting oversized ones recursively | Aligns with authorial segmentation (H4) | Structure detection brittleness |

Truncation manner (`front`/`middle`) is held fixed per task as in baseline.

## 5. Experimental Design

### 5.1 Factors

- **Chunker**: C0–C5 (C0 = control)
- **Task**: `rag`, `en` — English-only scope per charter v1.2 (full official sample sets, no subsampling without justification)
- **chunk_length**: 4000 / 8000 / 16000 tokens (8000 = published default)
- **Model**: one primary model for all arms (record exact version; default plan: gpt-4o-mini-2024-07-18 via official API endpoint; local-model runs are exploratory only unless promoted)

### 5.2 Controlled constants

- Decoding: temperature 0.0 (API) — never varied within a comparison (`src/utils.py:42`)
- Tokenizer for all length accounting: tiktoken gpt-4o encoding (`main.py:61`)
- `input_length=128000`, `context_length=32768`, `max_iterations=5`, `num_workers` recorded but irrelevant to outputs
- Eval scripts frozen; compute_scores variant recorded per run
- Same data files, same example IDs (resume logic in `run_pipeline` must not silently skip arms)

### 5.3 Ablation matrix (core)

Core grid = {C0, C1, C3, C4, C5} × {rag, en} × {4000, 8000, 16000} = 30 cells,
all at primary model. Full-grid runs are expensive; priority order:

1. All chunkers × all tasks @ 8000 (10 runs) — main table of paper
2. C0/C1 × all tasks × {4000, 16000} (12 runs) — size interaction
3. Extensions (overlap ratio sweep for C1, embedding ablation for C4, min-chunk sweep for C3) as follow-ups justified by results

### 5.4 Metrics

Accuracy (official scripts, unmodified):
- RAG: HotpotQA EM, F1
- En.QA: word-level QA F1

Efficiency (computed from run logs; report alongside accuracy):
- #chunks per example; #extraction calls; #scoring calls; #reduce calls
- Wall-clock map/reduce time (already instrumented in `pipeline.run_pipeline`)
- Total completion tokens (add lightweight logging in Phase 2; do not alter model behavior)

Diagnostics (for analysis sections):
- Info-score distributions (en)
- Fraction of examples ending in "NO ANSWER"
- Reduce-attempt count until answer found

### 5.5 Statistical protocol

- Per-example paired comparisons between each technique and C0 on the same questions.
- Report mean deltas with 95% bootstrap confidence intervals (resample examples, ≥10k resamples).
- Paired permutation/sign test for headline claims; state test, effect size, n, CI in the paper.
- No post-hoc metric or subset switching; any added analysis is labeled exploratory.

## 6. Roadmap

| Phase | Work | Exit criteria |
|---|---|---|
| P1 ✅ | Knowledge base (this doc set) | Done |
| P2 ⏳ | Literature review notes; `src/chunkers.py` behind CLI flag (default legacy) — **implemented (legacy + overlap + recursive_paragraph + tests)**; logging of call counts/tokens; optional linter/type-check proposal | Baseline byte-identical outputs vs pre-change run on small sample |
| P3 | Baseline reproduction runs (C0) on all tasks; registry rows complete | Numbers stable & recorded; compare with published ExtAgents numbers |
| P4 | Core matrix runs (§5.3 priorities 1–2) | All registry rows filled w/ config hashes |
| P5 | Analysis, significance testing, diagnostics plots | Tables/figures reproducible from scripts |
| P6 | Paper drafting (ACL format): method, experiments, limitations | Internal review pass |

## 7. Threats to Validity (to address in paper)

- **Cost asymmetry**: C1 doubles chunk count → more extraction calls. Mitigate by reporting
  accuracy-vs-cost curves, plus a budget-matched variant (same total token input, e.g., C1
  with half window).
- **Semantic chunker dependency**: embedding model choice confounds C4 → ablate ≥2 embedders.
- **Data leakage**: none anticipated (benchmarks untouched), but freeze eval data versions and record checksums.
- **Nondeterminism**: temperature 0.0 reduces but does not eliminate API nondeterminism;
  report variance via repeated runs on a subsample if needed.
- **Resume-logic interactions**: `run_pipeline` skips already-processed IDs; ensure output dirs
  are fresh per arm to avoid cross-contamination.

## 8. Decision Log Pointers

All deviations from this charter (technique swaps, protocol changes) must be recorded in
`docs/research/session-log.md` with rationale, and reflected here as amendments with a
version bump.
