# MadData

[PRD - MODEL](https://www.notion.so/PRD-MODEL-30e9d6d920778013a47ee104797b42eb?pvs=21)

- Compatibility with Backend
    
    # Model ↔ Backend Compatibility Matrix — v4
    
    ## AI-Assisted Coding Interview Assessment Platform
    
    Maps every metric and data requirement in the Model PRD to the specific backend tables, event types, and endpoints that produce it. Updated for v4: Cursor-style diff editor + updated model architecture (CUPS/WildChat datasets, LightGBM Component 2, heuristic Component 3, weighted average aggregation).
    
    **Legend:** ✅ Fully satisfied | ⚠️ Requires listed work | ❌ Not addressed
    
    ---
    
    ## 1. Component 1 — Structural Behavior Classifier (XGBoost, trained on CUPS)
    
    All features map directly to v4 event types. The three new CUPS-specific features (`acceptance_rate`, `deliberation_time`, `post_acceptance_edit_rate`) are now **directly observable** from `chunk_decisions` — no proxying required.
    
    | CUPS feature | Backend source | v4 table | Computation | Status |
    | --- | --- | --- | --- | --- |
    | Verification frequency | `execute` events | `events` | Count / session minutes | ✅ |
    | Re-prompt ratio | `execute` → `prompt` sequence | `events` | Failed execute → prompt within 60s / total failures | ✅ |
    | Time in editor | `panel_focus` durations | `events` | Sum of durations where `content = editor` | ✅ |
    | Time in chat | `panel_focus` durations | `events` | Sum where `content = chat` | ✅ |
    | Time in file tree | `panel_focus` durations | `events` | Sum where `content = filetree` | ✅ |
    | Orientation time | `edit` events | `events` | Session start → first `edit` timestamp | ✅ |
    | Iteration count | `edit`, `execute` | `events` | Count of `edit → execute` transitions | ✅ |
    | Test lines written | `edit` content | `editor_events` | Regex on `edit_delta` for `def test_` | ✅ |
    | File open count | `file_open` | `events` | Unique files opened before first `edit` | ✅ |
    | Dwell time per file | `file_open`, `file_close` | `events` | Mean duration per matched open/close pair | ✅ |
    | Prompt count | `prompt` | `events` / `ai_interactions` | COUNT(*) | ✅ |
    | Prompt rate | `prompt` | `events` / `ai_interactions` | Count / session minutes | ✅ |
    | **Acceptance rate** | `chunk_decisions` | `chunk_decisions` | `decision = accepted` / total chunks — **direct, no proxy** | ✅ Better than CUPS proxy |
    | **Deliberation time** | `chunk_decisions` | `chunk_decisions` | Mean `time_on_chunk_ms` — **direct, no proxy** | ✅ Better than CUPS proxy |
    | **Post-acceptance edit rate** | `chunk_decisions` | `chunk_decisions` | Modification depth on `decision = accepted` OR `modified` chunks — **direct** | ✅ Better than CUPS proxy |
    
    **Component 1 status: ✅ Fully unblocked. All 15 features computable from v4 schema. The three new CUPS features are measured more precisely in v4 than in CUPS itself — CUPS infers these from Copilot ghost text telemetry; v4 records them explicitly via `chunk_decisions`.**
    
    ---
    
    ## 2. Component 2 — Prompt Quality Scorer (LightGBM + optional CodeBERT embeddings)
    
    All prompt text is already logged. Engineered features computable from existing fields. CodeBERT embeddings are optional and computed offline — no new backend work required.
    
    | Feature | Source | v4 table | Computation | Status |
    | --- | --- | --- | --- | --- |
    | Prompt length and structure | `prompt` event | `events` | `len(content)`, sentence count | ✅ |
    | Code context presence | `prompt` event | `events` | Backtick/code block detection, file/function name regex on `content` | ✅ |
    | Specificity signals | `prompt` event | `events` | Constraint language, scoped verb detection, named identifier count | ✅ |
    | Re-prompt indicator | `prompt` sequence | `events` / `ai_interactions` | Did next turn correct/redirect AI? Detectable from follow-up prompt text | ✅ |
    | Turns-to-resolution | `prompt`, `response` sequence | `ai_interactions` | Exchanges before conversation moved forward | ✅ |
    | Per-prompt score (for judge) | All above | Computed in `scoring.py` | Per-row scores stored in `session_scores.prompt_quality_scores` for judge | ✅ |
    | Prompt sequence trajectory | `prompt` ordering | `events` | `timestamp ASC` ordering guaranteed | ✅ |
    | Optional CodeBERT embeddings | `prompt` text | Offline cache | Pre-computed from `prompt` content, loaded from `models/component2_codebert_embeddings/` | ✅ Optional — LightGBM runs without them |
    
    **Component 2 status: ✅ Fully unblocked. Zero new backend work required. All prompt text in hand via existing `prompt` event logging.**
    
    ---
    
    ## 3. Component 3 — Critical Review Detector (Heuristic, CUPS-calibrated)
    
    No trained model artifact needed. Always runs as heuristic. v4 provides **cleaner and more direct inputs** than any prior version — `proposed_code` and `final_code` are explicit per chunk, eliminating snapshot diffing entirely.
    
    | Model requirement | v3 approach | v4 approach | Status |
    | --- | --- | --- | --- |
    | `proposed_code` per AI interaction | Stored in `chunk_decisions.proposed_code` | Same — unchanged from v3 | ✅ |
    | `final_code` (what candidate committed) | Stored in `chunk_decisions.final_code` | Same — unchanged from v3 | ✅ |
    | Normalized edit distance per chunk | `SequenceMatcher(proposed_code, final_code).ratio()` | Same computation | ✅ |
    | CUPS threshold calibration | Thresholds defined in `scoring.py` | Same — `< 0.05 → 1`, `0.05–0.15 → 2`, etc. | ✅ |
    | Rejected chunk handling | Not in v3 — rejection was unobservable | `decision = rejected` → score 5 (strongest critical review signal) | ✅ New in v4 |
    | Session-level score (minimum) | Min of per-chunk scores | Same | ✅ |
    | Per-interaction scores for judge | Computed in `scoring.py`, stored in `session_scores.review_scores` | Same | ✅ |
    | Worst review moment for judge | Query `chunk_decisions` for min score with `decision = accepted` | Same — directly queryable | ✅ |
    
    **Component 3 status: ✅ Fully unblocked. No artifact needed. v4 actually improves Component 3 inputs vs. v3 by explicitly scoring rejected chunks.**
    
    ---
    
    ## 4. Aggregation Layer (Weighted Average)
    
    Simpler than the MLP proposed in earlier model PRD versions. Weights derived from Component 1 feature importances — no separate training data needed.
    
    | Requirement | Backend responsibility | Status |
    | --- | --- | --- |
    | Component 1 feature importances | XGBoost `.feature_importances_` stored in `session_scores.feature_importances` | ✅ |
    | Component 1 scores | `session_scores.structural_scores` JSON blob | ✅ |
    | Component 2 scores | `session_scores.prompt_quality_scores` JSON blob | ✅ |
    | Component 3 session-level score | `session_scores.review_scores.session_level` | ✅ |
    | Weighted average computation | `scoring.py aggregate_scores()` | ✅ Implemented |
    | Overall label thresholds | `< 2.5 → over_reliant`, `2.5–3.5 → balanced`, `> 3.5 → strategic` | ✅ |
    | Fallback weights (no Component 1 artifact) | Equal weights across three components | ✅ |
    | Synthetic session validation | `seed.py` generates labeled sessions for threshold validation | ⚠️ `seed.py` must emit all v4 event types and `chunk_decisions` |
    
    ---
    
    ## 5. LLM Judge — Claude
    
    Runs async after synchronous scoring. Uses `ANTHROPIC_API_KEY` — explicitly separate from `GEMINI_API_KEY` used for the AI assistant.
    
    | Requirement | Model PRD spec | Backend source | Status |
    | --- | --- | --- | --- |
    | Component 1 scores + importances | XGBoost outputs | `session_scores.structural_scores`, `session_scores.feature_importances` | ✅ |
    | Worst-scoring prompt from Component 2 | Lowest per-prompt score | `session_scores.prompt_quality_scores` — per-prompt array | ✅ |
    | Lowest review moment from Component 3 | Min per-chunk score | `chunk_decisions` WHERE score is minimum AND `decision = accepted` | ✅ Directly queryable |
    | Re-prompt sequence for narrative | Longest run of prompt-after-failure | `events` sequential scan | ✅ |
    | Session metadata | Time, phase breakdown, task | `sessions` + phase analytics | ✅ |
    | Session excerpts (3–5 events) | Selected diagnostic events | `GET /session/:id/trace` + selection logic in `scoring.py` | ✅ |
    | Separate Gemini judge call | Not the assistant call — separate system prompt | `llm.py` — same `GeminiClient`, dedicated `judge_call()` method with rubric-focused system prompt | ✅ Single client, two call patterns |
    | Judge output storage | Narrative + chain-of-thought | `session_scores.llm_narrative`, `session_scores.judge_chain_of_thought` | ✅ |
    | Async execution | Does not block `POST /session/end` response | Background thread | ⚠️ Must implement async dispatch in `scoring.py` — simplest is `threading.Thread` for hackathon |
    
    ---
    
    ## 6. Event Schema Compatibility Check
    
    Full mapping of Model PRD event schema to v4 backend.
    
    | Model PRD field | v4 backend location | v1 | v2 | v3 | v4 |
    | --- | --- | --- | --- | --- | --- |
    | `timestamp` | `events.timestamp` | ❌ | ✅ | ✅ | ✅ |
    | `session_id` | `events.session_id` | ❌ | ✅ | ✅ | ✅ |
    | `actor` | `events.actor` | ❌ | ✅ | ✅ | ✅ |
    | `event_type` | `events.event_type` | ❌ | ✅ 8 types | ✅ 11 types | ✅ 11 types |
    | `content` | `events.content` | ❌ | ✅ | ✅ | ✅ |
    | `metadata.file` | `events.metadata` JSON | ❌ | ✅ | ✅ | ✅ |
    | `metadata.exit_code` | `events.metadata` JSON | ❌ | ✅ | ✅ | ✅ |
    | `metadata.edit_delta` | `events.metadata` JSON | ❌ | ✅ | ✅ | ✅ |
    | `metadata.panel` | `events.metadata` JSON | ❌ | ✅ | ✅ | ✅ |
    | `metadata.cursor_position` | `events.metadata` JSON | ❌ | ✅ | ✅ | ✅ |
    | `metadata.suggestion_id` | `events.metadata` JSON | ❌ | ❌ | ✅ | ✅ |
    | `metadata.chunk_index` | `events.metadata` JSON | ❌ | ❌ | ✅ | ✅ |
    | `metadata.decision` | `events.metadata` JSON | ❌ | ❌ | ✅ | ✅ |
    | `metadata.time_on_chunk_ms` | `events.metadata` JSON | ❌ | ❌ | ✅ | ✅ |
    | CUPS: `acceptance_rate` | `chunk_decisions` | ❌ | ❌ | ✅ | ✅ |
    | CUPS: `deliberation_time` | `chunk_decisions.time_on_chunk_ms` | ❌ | ❌ | ✅ | ✅ |
    | CUPS: `post_acceptance_edit_rate` | `chunk_decisions.final_code` vs `proposed_code` | ❌ | ❌ | ✅ | ✅ |
    
    ---
    
    ## 7. Scoring Pipeline — Data Flow
    
    Shows exactly which tables feed which pipeline stages at session end.
    
    ```
    POST /session/end
            │
            ├── Component 1 (XGBoost or heuristic)
            │       reads: events (all types), editor_events (edit_delta), chunk_decisions
            │       produces: structural_scores{}, feature_importances{}
            │
            ├── Component 2 (LightGBM or heuristic)
            │       reads: events WHERE event_type = 'prompt', ai_interactions
            │       produces: prompt_quality_scores{}
            │
            ├── Component 3 (heuristic, always)
            │       reads: chunk_decisions (proposed_code, final_code, decision)
            │       produces: review_scores{ per_interaction[], session_level }
            │
            ├── Aggregation layer
            │       reads: outputs of Components 1, 2, 3
            │       reads: feature_importances from Component 1
            │       produces: weighted_score, overall_label
            │
            └── WRITE session_scores row (all of the above, atomically)
                    │
                    └── [async] Claude judge
                            reads: session_scores, events (selected excerpts)
                            produces: llm_narrative, judge_chain_of_thought
                            UPDATES session_scores (two fields only)
    ```
    
    ---
    
    ## 8. Frontend Instrumentation Checklist — v4
    
    | Event | Frontend trigger | Endpoint | Priority | Notes |
    | --- | --- | --- | --- | --- |
    | `prompt` | User sends message | `POST /ai/chat` | 🔴 Critical | Auto-logged server-side alongside `response` |
    | `suggestion_shown` | After receiving hunks from `/suggestions` | `POST /suggestions` | 🔴 Critical | Send `original_content` + `proposed_content` |
    | `chunk_accepted` | User clicks Accept | `POST /suggestions/:id/chunks/:idx/decide` | 🔴 Critical | `final_code = proposed_code` |
    | `chunk_rejected` | User clicks Reject | `POST /suggestions/:id/chunks/:idx/decide` | 🔴 Critical | `final_code = original_code` |
    | `chunk_modified` | User edits green text then accepts | `POST /suggestions/:id/chunks/:idx/decide` | 🔴 Critical | `final_code = edited version` |
    | `edit` | Editor content changes | `POST /events/editor` (2s debounce) | 🔴 Critical | For manual edits outside suggestion flow |
    | `execute` | User runs code in terminal | `POST /events/execute` | 🔴 Critical | Must include `exit_code` — required for Component 1 |
    | `file_open` | User opens file | `POST /events/file { action: "open" }` | 🟠 High | Needed for exploration metrics |
    | `file_close` | User closes file tab | `POST /events/file { action: "close" }` | 🟠 High | Needed for dwell time |
    | `panel_focus` | User clicks into any panel | `POST /events/panel` | 🟠 High | Fire on every focus change, no debounce |
    | Chunk timing | Track `shown_at` → decide click per chunk | Sent in decide request body | 🔴 Critical | Chunk 0: `decided_at − shown_at`. Chunk N: `decided_at − prev_decided_at` |
    
    ---
    
    ## 9. Build Priority Order for Tonight — v4
    
    | Priority | Work item | Unblocks | Est. time |
    | --- | --- | --- | --- |
    | 1 | Add all 8 tables to `models.py` + `db.py init` (incl. fully-defined `session_scores`) | Everything | 30 min |
    | 2 | Implement `diff.py` — unified diff + hunk parser | Suggestions endpoint | 45 min |
    | 3 | Implement dual Gemini + Claude clients in `llm.py` | AI chat + judge | 20 min |
    | 4 | Implement `POST /ai/chat` with Gemini + dual-write | Component 2 data | 30 min |
    | 5 | Implement `POST /suggestions` with hunk parsing + dual-write | Component 3, frontend render | 45 min |
    | 6 | Implement `POST /suggestions/:id/chunks/:idx/decide` + dual-write | Core instrumentation | 30 min |
    | 7 | Implement `POST /events/editor` with `edit_delta` + dual-write | Editor logging | 25 min |
    | 8 | Implement `POST /events/execute` | Component 1 (re-prompt, verification) | 15 min |
    | 9 | Implement `POST /events/panel` + `POST /events/file` | Component 1 (time distribution, exploration) | 20 min |
    | 10 | Implement `GET /session/:id/trace` | Model pipeline ingestion | 15 min |
    | 11 | Implement `scoring.py` — Component 3 heuristic + fallback for 1 & 2 | Scoring pipeline (unblocked before model training) | 60 min |
    | 12 | Implement scoring pipeline trigger in `POST /session/end` + async judge dispatch | End-to-end score at session close | 30 min |
    | 13 | Implement `GET /analytics/session/:id` + `GET /analytics/overview` | Dashboard | 45 min |
    | 14 | Implement `POST /analytics/session/:id/score` (manual re-score) | Dev tooling | 15 min |
    | 15 | Update `seed.py` for all v4 event types + chunk decisions | Testing, synthetic data gen | 30 min |
    
    **Total estimate: ~7.5 hours.** Items 1–12 are the hard floor for a complete scored demo (~5.5 hours). Items 13–15 complete the dashboard and testing infrastructure.
    
    > **Minimum viable demo (items 1–11, ~5 hours):** Working Cursor diff editor, full event logging, Component 3 heuristic scoring, fallback heuristics for Components 1 and 2. Enough to produce a `session_scores` row and demonstrate behavioral differentiation at session end. Add trained model artifacts later to replace fallbacks without any schema changes.
    > 
    
    ---
    
    ## 10. Key Design Decisions Locked in v4
    
    These decisions are intentional and should not be revisited tonight without good reason.
    
    | Decision | Rationale |
    | --- | --- |
    | Gemini for both assistant and judge | Single API key, single client in `llm.py`, two distinct call patterns (assistant system prompt vs. judge rubric prompt). Free tier covers both at hackathon scale. |
    | Component 3 always heuristic, never a trained model | Heuristic is calibrated from CUPS — not arbitrary. Trained classifier is the upgrade path post-hackathon, not a requirement tonight. |
    | Aggregation via weighted average, not MLP | MLP requires 300+ labeled sessions. Weighted average from Component 1 importances is principled and ships tonight. |
    | `chunk_decisions` replaces `insertion_events` | Rejection is now observable. Modification rate is explicit. Passive acceptance is a one-line query. All three are improvements over the Insert button model. |
    | Scoring runs synchronously at session end | Ensures `session_scores` is populated before any dashboard request. Keeps the backend simple — no task queue needed. Judge is the only async piece. |
    | `final_code` is always actual code, never a flag | Enables Component 3 to compute edit distance without any additional lookups. Enforced by API validation. |

[PRD - BACKEND](https://www.notion.so/PRD-BACKEND-30e9d6d92077808690cbe90c4b5e497b?pvs=21)

[PRD - FRONTEND](https://www.notion.so/PRD-FRONTEND-30e9d6d920778027aafde4dc70537472?pvs=21)

[implementation-plan](https://www.notion.so/implementation-plan-30e9d6d9207780db8db5cd29a26925e2?pvs=21)

# AI-Assisted Coding Interview Assessment Platform

## Overall PRD

**Concept · Market · Competitors · Product Strategy · Success Metrics**

> This document covers product concept, market context, and strategic framing. Separate PRDs exist for Model, Backend, and Frontend.
> 

---

## 1. Concept

Technical interviews at major companies have moved away from isolated algorithm problems. The new format gives candidates a real multi-file codebase, a feature request or bug, and expects them to use AI tools to solve it within ~60 minutes. Companies now need to assess not just whether a candidate can produce working code, but how they work with AI — decomposition, prompting quality, critical review of AI output, and debugging behavior.

> **The shift is structural, not temporary.** Meta, Canva, and others have publicly documented this change. HackerRank now auto-enables AI assistants for all candidates. Companies have changed the format but have no standardized, defensible way to score it. They are currently eyeballing behavioral dimensions with no tooling support.
> 

This platform gives companies the infrastructure to run AI-assisted OAs with consistent, quantified behavioral scoring — grounded in real session data rather than gut feel.

### Core Differentiator

Every other platform evaluates what a candidate produced. This platform evaluates how they worked — the session trace, not just the output. The behavioral scoring model is the core IP.

| Field | Detail |
| --- | --- |
| Product type | B2B assessment toolkit — session environment, behavioral scoring, and hiring signals for recruiting teams |
| Primary customer | Engineering hiring teams at companies running AI-assisted OAs |
| Primary output | Quantified behavioral scores + functional correctness + recruiter-facing candidate report |
| Session length | ~60 minutes, matching real interview format |
| GTM wedge | Candidate-facing practice platform to build session data and validate scoring before enterprise sales |

---

## 2. Problem

### The Format Has Changed

| Company | What Changed |
| --- | --- |
| Meta | Piloted AI-enabled OAs in late 2025. One extended problem divided into stages — extend a codebase, debug, add a feature. Candidates evaluated on AI collaboration quality. |
| Canva | Replaced CS fundamentals with AI-Assisted Coding. Problems are complex, ambiguous, realistic. Candidates use their preferred AI tools. Evaluation includes how they directed the AI. |
| HackerRank | AI assistant now auto-enabled for all candidates. Rubric has expanded to include AI collaboration dimensions alongside correctness. |
| General trend | The interview is no longer a test of memorized algorithms. It is a test of how candidates work — decomposition, delegation, verification, debugging — with AI as a collaborator. |

### The Scoring Gap

Companies have changed the format but not the scoring infrastructure. The result:

- Behavioral assessment is inconsistent across interviewers and cohorts
- No standardized rubric exists for AI collaboration quality
- Session interactions are not logged or reviewed — only the final output is evaluated
- Hiring decisions on behavioral dimensions are subjective and legally harder to defend
- No benchmark exists for what "good" AI-assisted coding looks like at a given level

There is no platform that provides companies a structured environment to run these assessments and a scoring model to evaluate them consistently.

---

## 3. Market

### Primary Customer — Hiring Teams

| Segment | Description |
| --- | --- |
| Primary | Engineering recruiting and hiring teams at mid-to-large tech companies that have adopted or are evaluating AI-assisted OA formats |
| Secondary | Staffing agencies and technical recruiting firms running OAs on behalf of clients |
| Tertiary | Bootcamps and universities preparing students for the new format — institutional B2B |

### Secondary Customer — Candidates (GTM Wedge)

Candidates are not the primary revenue target but the practice platform serves as the go-to-market entry point. It generates real session data, validates scoring quality at scale, and builds brand awareness with engineers before selling to the companies that hire them. Candidate-facing product comes first; enterprise product follows once scoring is validated.

### Market Size

Rough sizing — not audited:

- ~300,000 software engineering OAs conducted per month in the US at companies with structured technical assessments
- Enterprise technical assessment market (HackerRank, Codility, CoderPad) estimated at ~$500M ARR combined
- If 30–40% of companies shift to AI-assisted format within 2 years, the addressable slice needing new scoring infrastructure is significant and currently unserved
- Enterprise ACV for technical assessment tools: $15,000–150,000/year depending on volume — meaningfully higher than consumer pricing

### Market Timing

The window is narrow. The format shift is happening now but the tooling ecosystem has not caught up. HackerRank has the AI assistant but not the behavioral scoring. Within 12–18 months they or a well-funded startup will build it. The moat is scoring model quality, rubric legitimacy, and session data volume — all of which compound over time.

---

## 4. Competitive Landscape

| Platform | Format | AI Assistant | Behavioral Eval | Gap |
| --- | --- | --- | --- | --- |
| HackerRank | OA + some feature tasks | Partial | No | Has AI assistant and enterprise distribution — but scores output only, no session-level behavioral eval |
| CoderPad | Live interview IDE | No | No | Interviewer tool, no AI, no scoring model |
| Codility | Algorithm OAs | No | No | Old format entirely, no AI collab dimension |
| LeetCode | Algorithm problems | No | No | Candidate-facing only, wrong format, no enterprise scoring |
| Greenhouse / Lever | ATS with assessment integrations | No | No | Infrastructure layer only, depends on assessment tools for scoring |
| **This Platform** | Feature impl, real codebases | **Yes** | **Yes** | — |

### Competitive Assessment

HackerRank is the primary threat — they have enterprise relationships, an embedded AI assistant, and the distribution to move fast. Their current gap is that they evaluate output, not process. Closing that gap requires a behavioral scoring model and session logging infrastructure they do not have today. That is the window.

CoderPad is an IDE for live interviews, not an async OA platform. Codility and similar tools are stuck in the old format. None have invested in behavioral scoring.

> **The defensible position is scoring model quality and rubric legitimacy — not the session environment, which is replicable. The harder HackerRank finds it to match behavioral scoring depth, the stronger the moat.**
> 

---

## 5. Product Strategy

### GTM Sequence

**Stage 1 — Candidate practice platform (hackathon / early)**
Build the session environment and scoring model. Distribute to candidates for free or low cost. Collect real session data. Validate that behavioral scores are consistent and meaningful. This is the data flywheel.

**Stage 2 — Enterprise OA platform**
Once scoring is validated, sell to hiring teams as a managed OA service: configurable problem library, candidate session environment, behavioral and functional scoring, recruiter-facing reports. Pricing on assessment volume.

**Stage 3 — Assessment intelligence layer**
Aggregate scoring data across companies (anonymized) to benchmark candidate performance by level, role, and company type. Sell benchmarking and calibration as an add-on.

### Hackathon MVP

Validates the core loop: candidate solves a real codebase task with an embedded AI, session is scored behaviorally and functionally, report is generated.

| Component | Scope |
| --- | --- |
| Problem library | 5–10 curated SWE-bench Lite instances, Python, pre-configured Docker environments |
| AI assistant | Some LLM (Gemini Flash?) API embedded in IDE, all interactions logged with timestamps |
| Behavioral scoring | LLM-as-judge with structured rubric over session trace, chain-of-thought output |
| Functional scoring | Automated test run against SWE-bench test suite |
| Candidate report | Per-dimension scores, specific session examples, overall label |
| Session phases | Orientation → Implementation → Verification, each timed |

### Post-Hackathon Roadmap

**Phase 2 — Model Quality**

- Replace LLM-as-judge with fine-tuned Phi-3 mini classifier trained on collected session data
- Add contrastive training pairs — same task, different behavioral profiles
- Human rater study to validate scoring consistency before enterprise claims

**Phase 3 — Enterprise Features**

- Recruiter dashboard — candidate comparison across sessions, cohort-level scoring
- Configurable problem library — companies bring their own tasks or select from curated sets
- Role-based rubric weighting — different dimensions weighted for IC vs. lead roles
- ATS integration (Greenhouse, Lever, Workday)

**Phase 4 — Assessment Intelligence**

- Anonymized benchmarking — how a candidate scores vs. hired engineers at similar companies
- Calibration tooling — companies tune rubric weights against their own historical hiring outcomes

---

## 6. Key Assumptions

| Assumption | Confidence | How to Validate |
| --- | --- | --- |
| Companies will pay for behavioral scoring on top of existing OA tools | Medium | Discovery calls with 5 engineering hiring managers before building enterprise features |
| Behavioral scoring is consistent enough to be defensible in hiring decisions | Medium | Human rater study — 3 raters score same sessions, compare to model. Target >0.75 Cohen's kappa |
| SWE-bench tasks are representative of real interview tasks | High | Cross-reference with Meta/Canva problem descriptions; collect hiring manager feedback |
| Candidate practice platform generates enough session data to validate scoring within 3 months | Medium | Depends on distribution; need ~500 completed sessions for meaningful calibration |
| HackerRank does not ship behavioral scoring in the next 6 months | Medium-Low | Monitor closely; differentiate on scoring depth and rubric transparency |
| AI-assisted OA format becomes majority format within 2 years | Medium | Track adoption; interview engineers at target companies quarterly |

---

## 7. Success Metrics

### Hackathon

- Core loop completable end-to-end
- Behavioral score differentiates clearly between an over-reliant and a strategic session on the same task
- Output is specific enough that a recruiter could act on it

### Candidate Platform (3 months)

| Metric | Target |
| --- | --- |
| Session completion rate | > 70% of started sessions reach submission |
| Behavioral score consistency | LLM judge agreement with human raters > 0.75 Cohen's kappa |
| Sessions collected | > 500 completed sessions for model calibration |
| Repeat session rate | > 40% of users attempt a second session within 7 days |

### Enterprise (6–12 months)

| Metric | Target |
| --- | --- |
| Design partner companies | 3–5 companies running live OAs on the platform |
| Assessments run | > 200 real candidate assessments |
| Recruiter satisfaction | > 4/5 on report usefulness |
| ACV | > $20,000 per company |

---

## 8. Scope of This Document

This PRD covers product concept, market context, competitive positioning, and strategy. The following are covered in separate documents:

| Document | Covers |
| --- | --- |
| Model PRD | Behavioral scoring architecture, datasets, training pipeline, evaluation methodology, LLM judge design, fine-tuning strategy |
| Backend PRD | Session logging schema, API design, Docker environment orchestration, test runner, data storage, scoring pipeline |
| Frontend PRD | IDE interface, AI assistant integration, session phases UI, candidate report display, recruiter dashboard |

---

## 9. Open Questions

- **Rubric transparency** — open-source the behavioral rubric to build trust with hiring teams and candidates, or keep it proprietary. Transparency likely wins enterprise trust; opacity protects IP.
- **Data ownership** — who owns session logs when run by an enterprise customer: candidate, company, or platform. Needs a clear policy before any enterprise agreements.
- **IDE approach** — full browser-based IDE vs. embedded Monaco/VS Code with backend execution environment.
- **Pricing model** — per-assessment credits vs. seat-based subscription vs. platform fee. Per-assessment aligns incentives best for early enterprise customers.

## Shortcomings

Edit distance in model 3 can’t tell if just change variable names