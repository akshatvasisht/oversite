# MadData — 10-Hour Implementation Plan

> **Stack:** Python/Flask/SQLite (Backend) · React/Monaco (Frontend) · XGBoost + LightGBM (Model) · Gemini Flash (LLM)
> **Team:** 1× Model · 1× Backend · 1× Frontend-A (IDE/session) · 1× Frontend-B (Admin/auth)
> **Test discipline:** No phase advances until its test suite passes. Blocking dependencies are explicit.

---

## Parallel Track Overview

```
Hour  │ MODEL (M)           │ BACKEND (B)          │ FRONTEND-A (FA)       │ FRONTEND-B (FB)
──────┼─────────────────────┼──────────────────────┼───────────────────────┼───────────────────────
 0–1  │ Data prep + EDA     │ Schema + db init     │ Project scaffold      │ Project scaffold
 1–2  │ CUPS preprocessing  │ Core endpoints I     │ Monaco editor shell   │ Login + auth flow
 2–3  │ WildChat filtering  │ Core endpoints II    │ File explorer         │ Questions list page
 3–4  │ Component 1 train   │ AI proxy + suggest.  │ AI chat panel         │ Admin dashboard
 4–5  │ Component 2 train   │ Scoring engine I     │ Diff overlay UI       │ Score detail view
 5–6  │ Component 3 calib.  │ Scoring engine II    │ Terminal panel        │ Integration + wiring
 6–7  │ Aggregation layer   │ Analytics endpoints  │ Submit flow           │ Polish + edge cases
 7–8  │ Integration + eval  │ seed.py + E2E tests  │ Event instrumentation │ Cross-role testing
 8–9  │ LLM judge prompt    │ Bug fixes + hardening│ Phase UI + polish     │ Bug fixes
 9–10 │ Final validation    │ Demo prep            │ Demo prep             │ Demo prep
```

---

## Pre-Start Checklist (T−30 min, everyone)

- [x] Agree: Gemini throughout — **no Claude/Anthropic references anywhere in code or config**. Judge = Gemini with a rubric system prompt.
- [x] Confirm env vars: `GEMINI_API_KEY`, `FLASK_SECRET_KEY`, `DATABASE_URL`
- [x] Create shared `.env.example` and commit before splitting off
- [x] Stand up shared Git repo; agree on branch strategy (feature branches, merge to `main` only when tests pass)
- [x] Backend on `localhost:8000`, Frontend on `localhost:3000` — locked, no deviations
- [x] Share a Postman/Bruno collection or agree on a curl-based test tool

---

## Hour 0–1 | Foundation

### MODEL — Data Prep & EDA
**Goal:** Datasets loaded, proxy label logic understood, training skeleton exists.

- [x] Load CUPS dataset (`microsoft/coderec_programming_states`) via HuggingFace
- [x] EDA: plot distributions of `acceptance_rate`, `deliberation_time`, `post_acceptance_edit_rate`
- [x] Define proxy label thresholds: `strategic` = low blind acceptance + high pause + post-edit modification; `over_reliant` = inverse; `balanced` = middle
- [x] Load WildChat, filter to multi-turn coding sessions (code block presence + ≥3 turns)
- [x] Check class balance — if >4:1 ratio on CUPS labels, note for class weighting in XGBoost

**Test gate:** Print class distribution for both datasets. Labels exist, no NaNs, distribution is not degenerate. ✅

---

### BACKEND — Schema + DB Init
**Goal:** All 8 tables created, `db.py init` works, app boots.

- [ ] Write `models.py` — all 8 SQLAlchemy models: `sessions`, `files`, `events`, `ai_interactions`, `ai_suggestions`, `chunk_decisions`, `editor_events`, `session_scores`
- [ ] Write `db.py` — `init_db()`, `get_db()` session factory
- [ ] Write `app.py` skeleton — Flask factory, blueprint stubs, CORS, env loading
- [ ] Write `requirements.txt` — flask, flask-cors, sqlalchemy, google-generativeai, python-dotenv, xgboost, lightgbm, joblib, scikit-learn
- [ ] Run `python db.py init` — verify all tables present via sqlite3

**Test gate — `test_schema.py`:**
```python
def test_all_tables_exist():
    tables = inspect(engine).get_table_names()
    required = [
        'sessions','files','events','ai_interactions',
        'ai_suggestions','chunk_decisions','editor_events','session_scores'
    ]
    assert all(t in tables for t in required)
```
✅ Must pass before Hour 1.

---

### FRONTEND-A — Project Scaffold
**Goal:** React app boots, Monaco renders, routing exists.

- [ ] `npx create-react-app maddata --template typescript` (or Vite)
- [ ] Install: `@monaco-editor/react`, `axios`, `react-router-dom`
- [ ] Route skeleton: `/session/:id` → `SessionPage` placeholder
- [ ] Verify Monaco renders with a hardcoded Python string
- [ ] Create `api.ts` — axios instance pointing at `localhost:8000/api/v1`, `X-Session-ID` header interceptor

**Test gate:** App loads at `localhost:3000`, Monaco editor visible at `/session/test`. ✅

---

### FRONTEND-B — Project Scaffold
**Goal:** Same app, auth routing works.

- [ ] Same scaffold as FA (shared repo, same app)
- [ ] Install: same deps + `react-hook-form`
- [ ] Routes: `/login`, `/questions`, `/admin`, `/admin/:candidateId`
- [ ] Write `AuthContext` — stores `{ userId, role, sessionId }`, `isAuthenticated`
- [ ] Route guards: unauthenticated → `/login`; candidate hitting `/admin` → `/questions`

**Test gate:** Navigate to `/admin` unauthenticated → redirects to `/login`. Mock login → `/admin` placeholder renders. ✅

---

## Hour 1–2 | Core Data + Core Endpoints I

### MODEL — CUPS Preprocessing
**Goal:** Feature vector extractable from CUPS, train/val split ready.

- [x] Extract all 15 Component 1 features from CUPS telemetry into a flat DataFrame
- [x] Apply proxy label logic — verify rough thirds across 3 classes
- [x] 80/20 train/val split, stratified by label
- [x] Write `features.py` — `extract_c1_features(session_events_df) -> np.array`. **This function signature is the contract with backend.**
- [x] Unit test on a synthetic 10-event session

**Test gate — `test_features.py`:**
```python
def test_c1_feature_vector_shape():
    dummy_events = make_dummy_events()
    vec = extract_c1_features(dummy_events)
    assert vec.shape == (15,)
    assert not np.isnan(vec).any()
```
✅

---

### BACKEND — Core Endpoints I (Session + Files)
**Goal:** Session lifecycle + file management endpoints working.

- [ ] `routes/session.py`:
  - `POST /session/start` — create session, return `session_id`
  - `POST /session/end` — set `ended_at`, **stub** scoring (returns 200, no pipeline yet)
  - `PATCH /session/phase` — update phase, dual-write `panel_focus` event
  - `GET /session/:id/trace` — return all events ordered by timestamp ASC
- [ ] `routes/files.py`:
  - `POST /files` — insert into `files`, dual-write `file_open` event, write initial `editor_events` snapshot
  - `POST /files/:id/save` — compute delta, insert `editor_events`
  - `POST /events/file` — dual-write `file_open` or `file_close`

**Test gate — `test_session_endpoints.py`:**
```python
def test_session_lifecycle():
    r = client.post('/api/v1/session/start', json={'username':'alice','project_name':'test'})
    sid = r.json['session_id']
    assert sid
    r2 = client.post('/api/v1/session/end', json={'final_phase':'verification'},
                     headers={'X-Session-ID': sid})
    assert r2.status_code == 200

def test_file_creation_dual_writes():
    sid = create_session()
    r = client.post('/api/v1/files',
        json={'filename':'sol.py','initial_content':'# start'},
        headers={'X-Session-ID': sid})
    assert r.json['file_id']
    events = query_events(sid)
    assert any(e.event_type == 'file_open' for e in events)
```
✅

---

### FRONTEND-A — Monaco Editor Shell
**Goal:** Editor loads, content editable, tabs work.

- [ ] `MonacoEditorWrapper.tsx` — wraps `@monaco-editor/react`, props: `{ fileId, content, language, onChange }`
- [ ] `FileExplorer.tsx` — list of files, click to switch active file
- [ ] `useSession` hook — manages `{ sessionId, files, activeFileId, activeContent }`
- [ ] On mount: `POST /session/start` → store `sessionId` in context
- [ ] On file select: `POST /files` if new, render content in Monaco

**Test gate:** Load `/session/test`, click a filename, Monaco switches content. No console errors. ✅

---

### FRONTEND-B — Login + Auth Flow
**Goal:** Login posts to backend stub, token stored, role redirect works.

- [ ] `LoginPage.tsx` — username + password form, calls `POST /auth/login`
- [ ] On success: store role in `AuthContext`, redirect to `/questions` (candidate) or `/admin` (admin)
- [ ] Logout clears context, redirects to `/login`

> **⚠️ Handoff needed from Backend by Hour 2:** `POST /auth/login` stub returning `{ userId, role }` — hardcode `admin`/`admin` → admin role, anything else → candidate.

**Test gate:** Login as `testuser1` → lands on `/questions`. Login as `admin` → lands on `/admin`. Logout → `/login`. ✅

---

## Hour 2–3 | WildChat Prep + Core Endpoints II

### MODEL — WildChat Filtering + Component 2 Feature Design
**Goal:** WildChat coding subset ready, per-prompt features extractable.

- [ ] Filter WildChat: multi-turn coding conversations with ≥1 code block + ≥3 turns
- [ ] Compute per-prompt weak supervision labels: `re_prompt_rate` (next turn corrects/redirects), `turns_to_resolution`
- [ ] Write `prompt_features.py` — `extract_c2_features(prompt_text, next_turn_text) -> dict` covering: length, code block presence, function name references, specificity signals (constraint language, scoped verbs, named identifiers), re-prompt indicator
- [ ] Spot-check 20 samples manually — do high-quality prompts score higher on your features?

**Test gate — `test_prompt_features.py`:**
```python
def test_specific_prompt_scores_higher():
    vague = "fix this function"
    specific = "The `calculate_discount` fn on line 42 returns None when rate=0. Modify it to default to 0."
    v = extract_c2_features(vague, "")
    s = extract_c2_features(specific, "")
    assert s['has_function_name'] >= v['has_function_name']
    assert s['prompt_length'] > v['prompt_length']
    assert s['has_code_context'] >= v['has_code_context']
```
✅

---

### BACKEND — Core Endpoints II (AI Proxy + Events)
**Goal:** Gemini proxy working; prompt/response dual-written; execute/panel/editor events logging.

- [ ] Write `llm.py` — `GeminiClient` with:
  - `assistant_call(prompt, history, system_prompt) -> str`
  - `judge_call(scores, excerpts, system_prompt) -> str` — separate system prompt, same `GEMINI_API_KEY`
- [ ] `routes/ai.py` — `POST /ai/chat`: call Gemini, insert `ai_interactions`, dual-write `prompt` + `response` events, return `{ interaction_id, response, has_code_changes, shown_at }`
- [ ] `routes/events.py`:
  - `POST /events/execute` — dual-write `execute` event with `exit_code`
  - `POST /events/panel` — dual-write `panel_focus` event
  - `POST /events/editor` — compute `edit_delta` via `diff.py`, insert `editor_events`, dual-write `edit` event

**⭐ Write `diff.py` now.** `compute_edit_delta(old, new) -> str` and `parse_hunks(original, proposed) -> list[Hunk]`. Test extensively before moving on.

**Test gate — `test_ai_and_events.py`:**
```python
def test_ai_chat_dual_writes(mock_gemini):
    r = client.post('/api/v1/ai/chat',
        json={'prompt':'hello','file_id':fid}, headers=h)
    assert r.json['interaction_id']
    types = [e.event_type for e in query_events(sid)]
    assert 'prompt' in types and 'response' in types

def test_diff_hunk_parsing():
    original = "def foo():\n    return 1\n"
    proposed = "def foo():\n    x = 2\n    return x\n"
    hunks = parse_hunks(original, proposed)
    assert len(hunks) == 1
    assert hunks[0].start_line == 2
    assert 'x = 2' in hunks[0].proposed_code

def test_identical_content_produces_no_hunks():
    assert parse_hunks("abc", "abc") == []
```
✅ All `diff.py` tests must pass before the suggestions endpoint is written.

---

### FRONTEND-A — Autosave + File Switching
**Goal:** Explorer complete, autosave wired to backend.

- [ ] File explorer highlights active file, supports switching
- [ ] `useAutosave` hook — 2s debounce, calls `POST /events/editor` on content change
- [ ] File switch triggers immediate save of previous file before loading next
- [ ] Monaco: Python syntax highlighting, line numbers on, minimap off

**Test gate:** Open 3 files, edit each — `POST /events/editor` fires within 2s of stopping typing for each. Check network tab. ✅

---

### FRONTEND-B — Questions List Page
**Goal:** Candidate sees assigned questions with correct status badges.

- [ ] `QuestionsPage.tsx` — fetches `GET /questions` (backend stub: hardcoded list)
- [ ] `QuestionCard.tsx` — company name, title, status badge, Start/Resume button
- [ ] Submitted cards: button disabled
- [ ] Start → navigate to `/session/:questionId`

> **⚠️ Handoff needed from Backend by Hour 3:** `GET /questions` stub returning `[{ questionId, title, company, status }]`.

**Test gate:** Page renders 2+ question cards. Clicking Start navigates to session route. Submitted card button is disabled. ✅

---

## Hour 3–4 | Component 1 Training + Suggestions Endpoint

### MODEL — Component 1 Training
**Goal:** XGBoost trained, feature importances extracted, artifact saved.

- [ ] Train XGBoost on CUPS feature vectors + proxy labels (reasonable defaults: `n_estimators=200`, `max_depth=5`)
- [ ] Extract `.feature_importances_` — normalize to sum to 1
- [ ] `joblib.dump(model, 'models/component1_xgboost.joblib')`
- [ ] `json.dump(importances, open('models/c1_importances.json','w'))`
- [ ] Evaluate on val set — target accuracy ≥0.65 (acceptable given proxy labels)

**Test gate — `test_component1.py`:**
```python
def test_c1_model_loads_and_predicts():
    model = joblib.load('models/component1_xgboost.joblib')
    pred = model.predict(np.zeros((1, 15)))
    assert pred[0] in ['over_reliant', 'balanced', 'strategic']

def test_c1_val_accuracy():
    acc = evaluate_c1(val_X, val_y)
    assert acc >= 0.65
```
✅

---

### BACKEND — Suggestions Endpoints ⭐ Most critical backend task
**Goal:** Full Cursor-style diff flow working end-to-end.

- [ ] `routes/suggestions.py`:
  - `POST /suggestions` — take `{ interaction_id, file_id, original_content, proposed_content }`, run `parse_hunks()`, insert `ai_suggestions`, dual-write `suggestion_shown`, write pre-decision `editor_events` snapshot. Return `{ suggestion_id, shown_at, hunks[] }`. Validate: `proposed == original` → 400.
  - `POST /suggestions/:id/chunks/:idx/decide` — validate chunk exists + not decided; insert `chunk_decisions`; dual-write `chunk_accepted/rejected/modified`; if last hunk: set `resolved_at`, `all_accepted`, `any_modified`. **One transaction.**
  - `GET /suggestions/:id` — return suggestion + all decisions

Timing rules (enforced client-side, validated server-side):
- Chunk 0: `time_on_chunk_ms = decided_at − suggestion.shown_at`
- Chunk N: `time_on_chunk_ms = decided_at − previous_chunk.decided_at`
- Server clamps: `max(100, min(300_000, value))`

**Test gate — `test_suggestions.py`:**
```python
def test_full_chunk_decide_flow():
    suggestion = post_suggestion(original, proposed)
    sid = suggestion['suggestion_id']
    hunks = suggestion['hunks']
    assert len(hunks) > 0

    r = client.post(f'/api/v1/suggestions/{sid}/chunks/0/decide',
        json={'decision':'accepted',
              'final_code': hunks[0]['proposed_code'],
              'time_on_chunk_ms': 5000}, headers=h)
    assert r.status_code == 200

    decision = db.query(ChunkDecision).filter_by(
        suggestion_id=sid, chunk_index=0).first()
    assert decision.decision == 'accepted'
    assert decision.final_code == hunks[0]['proposed_code']

def test_already_decided_chunk_returns_409():
    # Decide chunk 0, then decide it again
    decide_chunk(sid, 0)
    r = decide_chunk(sid, 0)
    assert r.status_code == 409

def test_identical_content_returns_400():
    r = post_suggestion(same, same)
    assert r.status_code == 400

def test_modified_decision_stores_edited_code():
    r = client.post(f'/api/v1/suggestions/{sid}/chunks/0/decide',
        json={'decision':'modified',
              'final_code':'def foo():\n    return 99\n',
              'time_on_chunk_ms': 12000}, headers=h)
    decision = db.query(ChunkDecision)...
    assert decision.decision == 'modified'
    assert '99' in decision.final_code
```
✅ **All 4 tests must pass before Hour 5.**

---

### FRONTEND-A — AI Chat Panel
**Goal:** Candidate can send prompts, see responses, `POST /suggestions` auto-called when `has_code_changes`.

- [ ] `AIChatPanel.tsx` — message thread, input box, send button
- [ ] On send: `POST /ai/chat` with `{ prompt, file_id, conversation_history }`
- [ ] Render response with timestamp in thread
- [ ] Loading spinner during Gemini request
- [ ] If `has_code_changes: true`: extract proposed code from response (code block detection), call `POST /suggestions` automatically, store returned `suggestion_id` + `hunks` in component state

**Test gate:** Type a prompt, send, see AI response in chat. When response contains a code block, `POST /suggestions` fires automatically. No double submissions on fast clicks. ✅

---

### FRONTEND-B — Admin Dashboard
**Goal:** Admin sees interviewee table with correct columns.

- [ ] `AdminDashboard.tsx` — fetches `GET /analytics/overview`
- [ ] `IntervieweeTable.tsx` — Name, Company, Status, Score, Date Submitted
- [ ] Click completed row → navigate to `/admin/:candidateId`
- [ ] Incomplete rows: no link, grayed score cell

**Test gate:** Dashboard renders with mocked data. Clicking a completed row navigates. Clicking incomplete row does nothing. ✅

---

## Hour 4–5 | Component 2 Training + Scoring Engine I

### MODEL — Component 2 Training
**Goal:** LightGBM prompt quality scorer trained, per-prompt scores computable.

- [ ] Build feature matrix from WildChat filtered subset
- [ ] Train LightGBM; evaluate on held-out WildChat conversations
- [ ] `joblib.dump(model, 'models/component2_lgbm.joblib')`
- [ ] Write `score_prompts(prompt_list) -> list[float]` — callable by backend scoring pipeline
- [ ] **Optional:** load CodeBERT embeddings and concatenate — skip if >30min

**Test gate — `test_component2.py`:**
```python
def test_c2_model_loads():
    model = joblib.load('models/component2_lgbm.joblib')
    feats = extract_c2_features("fix this", "")
    score = model.predict([list(feats.values())])
    assert 1.0 <= float(score) <= 5.0

def test_specific_prompt_scores_higher_than_vague():
    v = score_single_prompt("fix this function")
    s = score_single_prompt(
        "The `calculate_discount` fn on line 42 returns None when rate=0. Modify it to default to 0."
    )
    assert s > v
```
✅

---

### BACKEND — Scoring Engine I (Feature Extraction + Components 1 & 2)

> **⚠️ Sync point with Model (Hour 4–5):** Share a JSON schema file — `{ "features": ["verification_frequency", "reprompt_ratio", ...] }` — both sides must use identical names and order. Do this before writing `extract_c1_features` in `scoring.py`.

- [ ] Write `scoring.py` — `load_models()` at startup, graceful fallback if artifacts absent
- [ ] `extract_c1_features(session_id, db) -> np.array` — queries `events`, `chunk_decisions`, `editor_events`, builds 15-feature vector matching `features.py` exactly
- [ ] `run_component1(session_id, db) -> dict` — returns `structural_scores` + `feature_importances`
- [ ] `extract_c2_features(session_id, db) -> list[dict]` — queries all `prompt` events
- [ ] `run_component2(session_id, db) -> dict` — returns `prompt_quality_scores`

**Test gate — `test_scoring_components.py`:**
```python
def test_c1_features_from_seeded_session():
    seed_minimal_session(db)
    feats = extract_c1_features(test_sid, db)
    assert feats.shape == (15,)
    assert feats[FEAT_IDX['verification_frequency']] == pytest.approx(expected_vf, rel=0.05)

def test_c1_fallback_mode():
    os.environ['SCORING_FALLBACK_MODE'] = 'true'
    scores = run_component1(test_sid, db)
    assert all(1 <= v <= 5 for v in scores['structural_scores'].values())

def test_c2_per_prompt_scores_populated():
    seed_session_with_prompts(db)
    scores = run_component2(test_sid, db)
    assert 'per_prompt' in scores
    assert len(scores['per_prompt']) > 0
```
✅

---

### FRONTEND-A — Diff Overlay UI ⭐ Most complex frontend task
**Goal:** Monaco renders green/red diff decorations per hunk; Accept/Reject buttons work.

- [ ] On receiving `{ suggestion_id, hunks }`:
  - Apply Monaco decorations: green highlight for additions, red for removals, per hunk
  - Render Accept/Reject as overlay widgets at each hunk position
- [ ] Accept → `POST /suggestions/:id/chunks/:idx/decide` with `{ decision: 'accepted', final_code: proposed_code, time_on_chunk_ms }`
- [ ] Reject → same endpoint, `decision: 'rejected'`, `final_code: original_code`
- [ ] Modified → user edits green text inline, then Accept → `decision: 'modified'`, `final_code: edited`
- [ ] After all hunks decided → clear all decorations, update file content to final state
- [ ] Track `shown_at` per suggestion + `decided_at` per chunk for `time_on_chunk_ms` computation

**Test gate:** Trigger a suggestion via chat. Green diff appears. Accept first hunk → decoration clears, content updates. Reject second hunk → reverts to original. No stale decorations remain after all hunks decided. ✅

---

### FRONTEND-B — Score Detail View
**Goal:** Admin sees full behavioral report for a candidate.

- [ ] `ScoreDetailPage.tsx` — fetches `GET /analytics/session/:sessionId`
- [ ] `ScoreSummary.tsx` — overall label badge (color-coded), weighted score
- [ ] `RubricBreakdown.tsx` — 12 dimensions, 1–5 scores, color gradient
- [ ] `NarrativeReport.tsx` — renders `llm_narrative`; shows "Generating report..." skeleton if null; polls every 5s until populated (max 3 retries)
- [ ] Back button → `/admin`

**Test gate:** Navigate to `/admin/:candidateId` with mocked response. All panels render. Null `llm_narrative` shows skeleton with poll behavior. ✅

---

## Hour 5–6 | Component 3 + Scoring Engine II

### MODEL — Component 3 Calibration + Aggregation Layer
**Goal:** Heuristic thresholds validated; aggregation layer differentiates profiles.

- [ ] Implement `component3_score(proposed_code, final_code, decision) -> int` with thresholds from PRD
- [ ] Validate thresholds against CUPS post-acceptance edit rate distribution — check 0.05/0.15/0.35/0.60 cover distribution percentiles meaningfully
- [ ] Write `aggregate_scores(c1, c2, c3, feature_importances) -> (float, str)`
- [ ] Generate 20 synthetic sessions (5 each profile) via prompted Gemini; run pipeline on them
- [ ] **Contrastive test:** for each task, strategic must score higher than over_reliant

**Test gate — `test_aggregation.py`:**
```python
def test_contrastive_discrimination():
    results = []
    for strategic, overreliant in test_pairs:  # 10 pairs
        s_score, _ = aggregate_scores(*score_session(strategic))
        o_score, _ = aggregate_scores(*score_session(overreliant))
        results.append(s_score > o_score)
    assert sum(results) >= 8  # 8 of 10

def test_label_thresholds():
    assert run_with_score(2.0)[1] == 'over_reliant'
    assert run_with_score(3.0)[1] == 'balanced'
    assert run_with_score(4.0)[1] == 'strategic'
```
✅

---

### BACKEND — Scoring Engine II (Component 3 + Aggregation + Session End)
**Goal:** Full pipeline runs at `POST /session/end`; `session_scores` row written.

- [ ] `run_component3(session_id, db) -> dict` — queries `chunk_decisions`, applies heuristic
- [ ] `aggregate_scores(c1, c2, c3, importances) -> (float, str)` — fallback to equal weights if no importances
- [ ] Wire full pipeline into `POST /session/end`:
  1. `run_component1` (sync)
  2. `run_component2` (sync)
  3. `run_component3` (sync)
  4. `aggregate_scores` (sync)
  5. Write `session_scores` row atomically
  6. Dispatch async `threading.Thread` → Gemini judge → updates `llm_narrative` when done
- [ ] Write `judge_prompt_builder(session_scores, events, db) -> str` — selects 3–5 diagnostic excerpts

**Test gate — `test_scoring_pipeline.py`:**
```python
def test_full_pipeline_on_seeded_session():
    seed_rich_session(db)
    r = client.post('/api/v1/session/end',
        json={'final_phase':'verification'}, headers=h)
    assert r.status_code == 200

    scores = db.query(SessionScores).filter_by(session_id=sid).first()
    assert scores is not None
    assert scores.overall_label in ['over_reliant', 'balanced', 'strategic']
    assert 1.0 <= scores.weighted_score <= 5.0
    assert scores.structural_scores is not None
    assert scores.prompt_quality_scores is not None
    assert scores.review_scores is not None
    # llm_narrative may be null (async) — that's acceptable
```
✅ **This is the hardest backend gate. Must pass before Hour 7.**

---

### FRONTEND-A — Terminal Panel
**Goal:** Terminal shows output, Run fires execute event.

- [ ] `TerminalPanel.tsx` — output log (monospace), run command input, Run button, Clear button
- [ ] Run → `POST /events/execute` with `{ command, exit_code, output }`
- [ ] Exit 0 → green "✓ Passed". Non-zero → red "✗ Failed"
- [ ] Output auto-scrolls to bottom

**Test gate:** Type `python solution.py`, click Run, see output. `POST /events/execute` fires with correct `exit_code` in network tab. ✅

---

### FRONTEND-B — Full Integration Pass
**Goal:** All pages wired to real backend endpoints; no hardcoded mock data.

- [ ] Replace all stubs with real API calls: `GET /questions`, `GET /analytics/overview`, `GET /analytics/session/:id`, `POST /auth/login`
- [ ] Loading + error states on all pages
- [ ] Verify `X-Session-ID` header sent on all session-scoped requests
- [ ] AI API failure → show retry button in chat panel
- [ ] Network drop handling → reconnect modal

**Test gate:** Full candidate flow end-to-end with a live backend: login → questions → start session → submit → status = Submitted. Full admin flow: login → dashboard → click candidate → see scores. ✅

---

## Hour 6–7 | Analytics + Submit Flow

### MODEL — Integration Testing with Backend
**Goal:** Artifacts load correctly in backend; feature extraction matches training.

- [ ] Copy `models/component1_xgboost.joblib`, `models/component2_lgbm.joblib`, `models/c1_importances.json` to `backend/models/`
- [ ] Run `test_scoring_components.py` with `SCORING_FALLBACK_MODE=false` — must use real artifacts
- [ ] Verify `feature_importances` in `session_scores` is populated and sums to ~1.0
- [ ] Run aggregation on 5 synthetic sessions — verify labels are sensible
- [ ] Fix any feature name/order mismatch between `features.py` and `scoring.py`

**Test gate:**
```python
def test_real_artifacts_load():
    os.environ['SCORING_FALLBACK_MODE'] = 'false'
    models = load_models()
    assert models['component1'] is not None
    assert models['component2'] is not None

def test_no_fallback_on_complete_pipeline():
    seed_rich_session(db)
    trigger_scoring(sid)
    scores = db.query(SessionScores).filter_by(session_id=sid).first()
    assert json.loads(scores.fallback_components) == []
```
✅

---

### BACKEND — Analytics Endpoints
**Goal:** Dashboard + session detail return correct data shapes.

- [ ] `routes/analytics.py`:
  - `GET /analytics/session/:id` — live metrics + `session_scores` cache
  - `GET /analytics/overview` — aggregate across completed sessions, support `?completed_only=true`
  - `POST /analytics/session/:id/score` — manual re-score trigger
- [ ] Implement all live metrics: `chunk_acceptance_rate`, `passive_acceptance_rate`, `time_on_chunk_avg_ms`, `verification_frequency`, `reprompt_ratio`, `time_by_panel`, `orientation_duration_s`, `iteration_depth`, `prompt_count_by_phase`

**Test gate — `test_analytics.py`:**
```python
def test_session_analytics_structure():
    seed_rich_session(db)
    trigger_scoring(sid)
    r = client.get(f'/api/v1/analytics/session/{sid}', headers=h)
    data = r.json
    for key in ['chunk_acceptance_rate','verification_frequency',
                'overall_label','structural_scores','prompt_quality_scores']:
        assert key in data

def test_overview_filters_correctly():
    seed_n_sessions(3, completed=True)
    seed_n_sessions(1, completed=False)
    r = client.get('/api/v1/analytics/overview?completed_only=true')
    assert len(r.json['sessions']) == 3
```
✅

---

### FRONTEND-A — Submit Flow + Panel Instrumentation
**Goal:** Submit ends session cleanly; panel focus events logged.

- [ ] `SubmitModal.tsx` — "Are you sure?" + warning, Confirm/Cancel
- [ ] Confirm → `POST /session/end` → redirect to `/questions` with status updated to Submitted
- [ ] Panel focus tracking: `POST /events/panel` on every click into editor/chat/terminal/filetree
- [ ] Phase progress bar in top bar (update on `PATCH /session/phase`)

**Test gate:** Click Submit → modal appears. Confirm → session ends, redirected to questions, card shows "Submitted". Events table has `panel_focus` events for editor and chat. ✅

---

### FRONTEND-B — Polish + Edge Cases
**Goal:** All UX edge cases handled; no unhandled rejections.

- [ ] Empty state on AdminDashboard if no sessions
- [ ] ScoreDetailPage: show spinner if `weighted_score` is null (scoring in progress)
- [ ] Narrative polling: max 3 retries at 5s intervals, then "Report unavailable — try refreshing"
- [ ] Toast notifications: AI API failure, save success, submit confirmation
- [ ] Verify layout holds at 1280px viewport

**Test gate:** All error states render. No unhandled promise rejections. Console clean on both flows. ✅

---

## Hour 7–8 | E2E Integration + Seed Data

### ALL TEAMS — Integration Sprint
**Stop new features. Fix integration bugs across team boundaries.**

#### Backend + Model
- [ ] Write `seed.py` — generates 3 sessions (over_reliant, balanced, strategic) with all v4 event types + `chunk_decisions`
- [ ] Run full pipeline on seeded sessions — verify `over_reliant` session scores < 2.5, `strategic` > 3.5
- [ ] Fix any `session_scores` write failures
- [ ] Verify `llm_narrative` populates after ~10–15s async delay
- [ ] Threading safety check: 3 concurrent `POST /session/end` — no SQLite locking errors

**Test gate — `test_e2e_backend.py`:**
```python
def test_seeded_profiles_score_correctly():
    seed_all_profiles()
    for profile, expected_label in [
        ('over_reliant', 'over_reliant'),
        ('strategic', 'strategic'),
    ]:
        sid = get_seeded_session_id(profile)
        trigger_scoring(sid)
        scores = db.query(SessionScores).filter_by(session_id=sid).first()
        assert scores.overall_label == expected_label
```
✅

#### Frontend-A + Frontend-B
- [ ] Full candidate flow: login → start → prompt → diff overlay → accept/reject → terminal run → submit → back to questions
- [ ] Full admin flow: login → dashboard → click candidate → scores → narrative populated after poll
- [ ] Fix any CORS errors, 401s from missing session ID header, broken redirects, stale Monaco decorations

**Test gate — manual E2E checklist:**
```
[ ] Candidate: login → questions → session → prompt → diff overlay → accept → reject → run terminal → submit → questions (Submitted status)
[ ] Admin: login → dashboard → click completed candidate → scores visible → narrative visible within 15s
[ ] No console errors on either flow
[ ] Network tab: all requests return 200 except expected 409 on double-decide
```
✅

---

## Hour 8–9 | LLM Judge + Hardening

### MODEL — LLM Judge Prompt Engineering
**Goal:** Narratives are specific, actionable, and calibrated. Tested on real sessions.

- [ ] Write `judge_system_prompt.txt` — rubric definitions, output format instructions (summary + per-dimension + suggestions)
- [ ] Write `judge_user_prompt_template.txt` — slots for scores, excerpts, metadata
- [ ] Add variable-rename caveat: "Edit distance cannot detect variable renaming. Treat Component 3 scores with appropriate uncertainty on short chunks."
- [ ] Test on 3–5 complete sessions from `seed.py`
- [ ] Iterate prompt until narratives:
  - Reference specific session events (actual prompt text or chunk reference)
  - Don't call a 3.2 score "excellent"
  - Produce 2–3 genuinely actionable suggestions

**Test gate (qualitative — human review):**
- Over-reliant narrative mentions: passive acceptance, low review, over-delegation ✅
- Strategic narrative mentions: targeted prompts, code modification, verification ✅
- Both contain ≥1 specific session example ✅

---

### BACKEND — Hardening + Auth
**Goal:** No 500s on expected inputs; edge cases handled.

- [ ] `POST /auth/login` — check against hardcoded test accounts, return `{ userId, role, token }`
- [ ] `time_on_chunk_ms` server-side clamp: `max(100, min(300_000, value))`
- [ ] `POST /session/end` on already-ended session → 400
- [ ] Empty session scoring (0 prompts, 0 chunks, 0 executes) → graceful fallback, not crash
- [ ] Dual-write transaction rollback test

**Test gate — `test_edge_cases.py`:**
```python
def test_empty_session_scores_without_crash():
    sid = start_session()
    end_session(sid)  # no events in between
    scores = db.query(SessionScores).filter_by(session_id=sid).first()
    assert scores is not None
    assert scores.overall_label is not None

def test_double_session_end_returns_400():
    sid = start_and_end_session()
    r = client.post('/api/v1/session/end', headers={'X-Session-ID': sid})
    assert r.status_code == 400

def test_dual_write_rolls_back_on_db_error(monkeypatch):
    # Patch second write to raise, verify neither row exists
    ...
```
✅

---

### FRONTEND-A — Phase UI + Polish
**Goal:** IDE feels complete and professional.

- [ ] Phase progress bar: Orientation → Implementation → Verification; updates on phase change
- [ ] Timer in top right — counts up from 0:00
- [ ] Autosave indicator: "Saving..." on debounce trigger, "Saved ✓" after 200 response
- [ ] `Cmd+Enter` / `Ctrl+Enter` to send chat prompt
- [ ] Session restore on refresh: re-fetch file content from backend on mount (persist `sessionId` in localStorage)

**Test gate:** Phase bar updates. Timer counts up. Refresh page → file content restored. ✅

---

### FRONTEND-B — Bug Fixes + Cross-Role Testing
**Goal:** Zero role confusion bugs; all states handled.

- [ ] Admin cannot access `/session/:id`
- [ ] Candidate cannot access `/admin`
- [ ] Logout clears `sessionId` from context + localStorage
- [ ] ScoreDetailPage: null `weighted_score` shows spinner, not 0 or NaN
- [ ] Two simultaneous browser tabs (one candidate, one admin) → no interference

**Test gate:** Login as candidate → manually navigate to `/admin` → redirected. Login as admin → `/session/x` → redirected. Two tabs, no cross-contamination. ✅

---

## Hour 9–10 | Final Validation + Demo Prep

### Demo Run (Hour 9:00–9:30) — All Teams

**Run one complete demo as if presenting to judges.**

1. Admin logs in → empty dashboard
2. Candidate (different browser) logs in → starts session
3. Candidate sends 3–4 prompts, accepts/rejects hunks, runs code, submits
4. Admin refreshes dashboard → sees candidate, clicks through to scores
5. Wait for narrative to populate (~15s)
6. Walk through the report out loud — does it make sense given observed behavior?

**Pass criteria:**
- [ ] `session_scores` row exists with all fields populated
- [ ] `overall_label` makes sense given the candidate's behavior during the demo
- [ ] LLM narrative references specific session moments (not generic text)
- [ ] No crashes, no 500s, no console errors

---

### Bug Fix Window (Hour 9:30–10:00)
Fix P0 bugs only. No new features.

**Priority order:**
1. Scoring pipeline crash → fix or force `SCORING_FALLBACK_MODE=true`
2. Diff overlay decorations not clearing → fix Monaco decoration disposal
3. Narrative not populating → check async thread + Gemini judge call; add rule-based fallback
4. Auth redirect loop → fix route guard logic

---

### Final Checklist Before Demo

**Backend:**
- [ ] `SCORING_FALLBACK_MODE=false`, real artifacts loading
- [ ] `session_scores` written on every `POST /session/end`
- [ ] Narrative populates within 15s of session end
- [ ] `GET /analytics/overview` returns all completed sessions

**Model:**
- [ ] Both `.joblib` artifacts in `backend/models/`
- [ ] `c1_importances.json` present
- [ ] Fallback heuristics verified to work if artifacts somehow fail to load

**Frontend:**
- [ ] Full candidate flow zero errors
- [ ] Full admin flow zero errors
- [ ] No hardcoded session IDs or mock data in production paths

---

## Critical Dependency Map

```
BACKEND: diff.py  ──────────────────────────────► BACKEND: POST /suggestions
                                                          │
                                                          ▼
FRONTEND-A: diff overlay  ◄───────────────────── BACKEND: GET /suggestions/:id
         │
         ▼
FRONTEND-A: chunk decide  ──────────────────────► BACKEND: POST /suggestions/:id/chunks/:idx/decide
                                                          │
                                                          ▼
MODEL: features.py contract  ──────────────────► BACKEND: extract_c1_features() in scoring.py
MODEL: component1_xgboost.joblib  ─────────────► BACKEND: run_component1()
MODEL: component2_lgbm.joblib  ─────────────────► BACKEND: run_component2()
                                                          │
                                                          ▼
BACKEND: POST /session/end  ────────────────────► session_scores written
                                                          │
                                                          ▼
BACKEND: GET /analytics/session/:id  ───────────► FRONTEND-B: ScoreDetailPage
```

---

## Handoff SLAs

| From | To | What | By when |
|------|-----|------|---------|
| Backend | Frontend-B | `POST /auth/login` stub | Hour 2 end |
| Backend | Frontend-B | `GET /questions` stub | Hour 3 start |
| Backend | Frontend-A | `POST /ai/chat` + `POST /suggestions` working | Hour 4 end |
| Backend | Frontend-A | `POST /suggestions/:id/chunks/:idx/decide` | Hour 4 end |
| Model + Backend | Both | Feature vector schema JSON (names + order) | Hour 4–5 sync |
| Model | Backend | Both `.joblib` artifacts + `c1_importances.json` | Hour 7 start |
| Backend | Frontend-B | `GET /analytics/session/:id` full schema | Hour 7 end |

---

## Risk Register

| Risk | Likelihood | Owner | Mitigation |
|------|-----------|-------|-----------|
| `diff.py` hunk parsing: wrong line numbers | High | Backend | Spike it at Hour 2, ≥4 unit tests before suggestions endpoint |
| Feature vector mismatch between `features.py` and `scoring.py` | High | Model + Backend | Share JSON schema at Hour 4–5 sync; don't write scoring.py before sync |
| Gemini API rate limit during demo | Medium | Backend | Cache one response as fallback fixture for demo |
| Monaco decorations not clearing after all hunks decided | Medium | Frontend-A | Dispose all editor decorations on suggestion resolve |
| `llm_narrative` never populates | Medium | Backend | Add fallback: if thread fails within 30s, write a rule-based summary |
| SQLite locking under concurrent session ends | Low | Backend | Serialize scoring pipeline with `threading.Lock` |
| Variable rename invisible to Component 3 | Known | Model | Add note to judge prompt; document as known limitation |

---

## Every-2-Hour Sync Protocol

**Hour 2, 4, 6, 8 — 5-minute standup:**
1. What's blocked?
2. Has any API interface changed that affects another team?
3. Are your test gates for this phase passing?

**Rule: Nothing merges to `main` without passing its stated test gate.**
