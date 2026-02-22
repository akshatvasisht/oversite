# MadData — Backend Implementation Plan

> **Stack:** Python 3.11 · Flask · SQLite · SQLAlchemy
> **Server:** `localhost:8000`
> **Rule:** No step advances until its test gate passes.

---

## Status Tracker

| Step | Task | Status |
|------|------|--------|
| 1 | Schema + DB init (`models.py`, `db.py`) | ✅ Done |
| 2 | Session + file routes (`routes/session.py`, `routes/files.py`, auth stub) | 🔄 In progress |
| 3 | `diff.py` — unified diff + hunk parser | ⬜ Pending |
| 4 | `llm.py` — Gemini client (assistant + judge) | ⬜ Pending |
| 5 | `POST /ai/chat` — Gemini proxy + dual-write | ⬜ Pending |
| 6 | `POST /suggestions` — store original/proposed snapshots + dual-write | ⬜ Pending |
| 7 | `POST /suggestions/:id/resolve` — store final_content, set resolved flags | ⬜ Pending |
| 8 | `POST /events/editor` — edit delta + dual-write | ⬜ Pending |
| 9 | `POST /events/execute` + `POST /events/panel` + `POST /events/file` | ⬜ Pending |
| 10 | `GET /session/:id/trace` | ⬜ Pending |
| 11 | `scoring.py` — Component 3 heuristic + fallbacks for 1 & 2 | ⬜ Pending |
| 12 | Wire scoring pipeline into `POST /session/end` + async judge | ⬜ Pending |
| 13 | `GET /analytics/session/:id` + `GET /analytics/overview` | ⬜ Pending |
| 14 | `POST /analytics/session/:id/score` — manual re-score | ⬜ Pending |
| 15 | `seed.py` — synthetic sessions for all 3 profiles | ⬜ Pending |

**Minimum viable demo:** Steps 1–12 (~5.5 hrs). Steps 13–15 complete the dashboard and testing.

---

## Hour 0–1 | Foundation ✅

**Goal:** All 8 tables created, `db.py init` works, app boots.

- [x] `models.py` — all 8 SQLAlchemy models with correct columns
- [x] `db.py` — `init_db()`, `get_db()` session factory
- [x] `app.py` — Flask factory, CORS, env loading, health endpoint
- [x] `requirements.txt` — all dependencies
- [x] `python3 db.py` — all tables created

**Test gate — `test_schema.py`:** ✅ Passing

---

## Hour 1–2 | Core Endpoints I (Session + Files)

**Goal:** Session lifecycle + file management working.

### `routes/session.py`
- [ ] `POST /session/start` — insert into `sessions` with `phase = orientation`, return `{ session_id, started_at }`
- [ ] `POST /session/end` — set `ended_at`, **stub scoring** for now (returns 200, pipeline wired later in Step 12)
- [ ] `PATCH /session/phase` — update `sessions.phase`, dual-write `panel_focus` event to `events`
- [ ] `GET /session/:id/trace` — return all events `ORDER BY timestamp ASC`, parse `metadata` JSON

### `routes/files.py`
- [ ] `POST /files` — insert into `files`, dual-write `file_open` event, write initial `editor_events` snapshot (`edit_delta = null`)
- [ ] `POST /files/:id/save` — compute `edit_delta` via `diff.py`, insert `editor_events` with `trigger = save`, dual-write `edit` event
- [ ] `POST /events/file` — dual-write `file_open` or `file_close` event

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

> ⚠️ **Handoff to Frontend-B by Hour 2 end:** `POST /auth/login` stub — hardcode `admin`/`admin` → `{ userId, role: "admin" }`, anything else → `{ userId, role: "candidate" }`.

---

## Hour 2–3 | Core Endpoints II + `diff.py` ⭐

**Goal:** `diff.py` fully tested; Gemini proxy + event endpoints working.

### `diff.py` — Do this first, test extensively before moving on

```python
def compute_edit_delta(old: str, new: str) -> str:
    """Returns unified diff string. Used for edit_delta in editor_events."""

def parse_hunks(original: str, proposed: str) -> list[Hunk]:
    """
    Diffs original vs proposed, returns ordered list of Hunk objects.
    Each Hunk: { index, original_code, proposed_code, start_line, end_line, char_count_proposed }
    Returns [] if no diff.
    """
```

**`diff.py` test gate (must pass before writing suggestions endpoint):**
```python
def test_diff_hunk_parsing():
    original = "def foo():\n    return 1\n"
    proposed = "def foo():\n    x = 2\n    return x\n"
    hunks = parse_hunks(original, proposed)
    assert len(hunks) == 1
    assert hunks[0].start_line == 2
    assert 'x = 2' in hunks[0].proposed_code

def test_identical_content_produces_no_hunks():
    assert parse_hunks("abc", "abc") == []

def test_multi_hunk_parsing():
    # Two separate change blocks → two hunks
    ...

def test_edit_delta_is_valid_unified_diff():
    delta = compute_edit_delta("a = 1\n", "a = 2\n")
    assert '@@' in delta
    assert '-a = 1' in delta
    assert '+a = 2' in delta
```

### `llm.py`
- [ ] `GeminiClient` class with:
  - `assistant_call(prompt, history, system_prompt) -> str`
  - `judge_call(scores, excerpts, system_prompt) -> str` — same `GEMINI_API_KEY`, separate system prompt
- [ ] Load `GEMINI_API_KEY` from env, fail loudly if missing

### `routes/ai.py`
- [ ] `POST /ai/chat` — call Gemini, insert `ai_interactions`, dual-write `prompt` (actor=user) + `response` (actor=ai) events, return `{ interaction_id, response, has_code_changes, shown_at }`
- [ ] If Gemini fails → return 502, write **neither** row

### `routes/events.py`
- [ ] `POST /events/execute` — dual-write `execute` event with `metadata.exit_code`
- [ ] `POST /events/panel` — dual-write `panel_focus` event, fire on every focus change
- [ ] `POST /events/editor` — compute `edit_delta` via `diff.py`, insert `editor_events`, dual-write `edit` event. 2s debounce enforced by frontend, not backend.

**Test gate — `test_ai_and_events.py`:**
```python
def test_ai_chat_dual_writes(mock_gemini):
    r = client.post('/api/v1/ai/chat',
        json={'prompt':'hello','file_id':fid}, headers=h)
    assert r.json['interaction_id']
    types = [e.event_type for e in query_events(sid)]
    assert 'prompt' in types and 'response' in types
```

> ⚠️ **Handoff to Frontend-B by Hour 3 start:** `GET /questions` stub — hardcode 2–3 question objects: `[{ questionId, title, company, status }]`.

---

## Hour 3–4 | Suggestions Endpoints ⭐ Most Critical

**Goal:** Full side-by-side suggestion flow working end-to-end.

> **Architecture note:** Users interact with the full suggestion (side-by-side view), not individual hunks. `parse_hunks` is **never called at request time** — it runs offline in the scoring pipeline after session end. `chunk_decisions` is populated by the scoring pipeline, not by real-time frontend events.

### `routes/suggestions.py`

**`POST /suggestions`**
- Body: `{ interaction_id, file_id, original_content, proposed_content }`
- Validate: if `proposed_content == original_content` → 400
- Insert `ai_suggestions` row (`hunks_count` left null, computed offline)
- Write `editor_events` snapshot with `trigger = post_suggestion` as pre-decision baseline
- Dual-write `suggestion_shown` event
- Return: `{ suggestion_id, shown_at, original_content, proposed_content }`

**`POST /suggestions/:suggestion_id/resolve`**
- Body: `{ final_content: str, all_accepted: bool, any_modified: bool }`
- Validate suggestion exists + belongs to session → 404
- Validate not already resolved → 409
- Set `ai_suggestions.resolved_at`, `all_accepted`, `any_modified`
- Write `editor_events` snapshot with `trigger = suggestion_resolved`, `content = final_content`
- Dual-write `suggestion_resolved` event
- **All in one transaction**
- Return: `{ resolved_at }`

**`GET /suggestions/:suggestion_id`**
- Return `ai_suggestions` row

**Test gate — `test_suggestions.py`:**
```python
def test_post_suggestion_returns_suggestion_id(client):
    sid = make_session(client)
    fid = make_file(client, sid).get_json()['file_id']
    r = client.post('/api/v1/suggestions',
        json={'file_id': fid, 'original_content': 'a', 'proposed_content': 'b'},
        headers={'X-Session-ID': sid})
    assert r.status_code == 201
    assert 'suggestion_id' in r.get_json()

def test_identical_content_returns_400(client):
    r = post_suggestion(client, sid, fid, same, same)
    assert r.status_code == 400

def test_resolve_suggestion_success(client):
    sid, fid, suggestion_id = make_suggestion(client)
    r = client.post(f'/api/v1/suggestions/{suggestion_id}/resolve',
        json={'final_content': 'b', 'all_accepted': True, 'any_modified': False},
        headers={'X-Session-ID': sid})
    assert r.status_code == 200
    assert 'resolved_at' in r.get_json()

def test_resolve_already_resolved_returns_409(client):
    sid, fid, suggestion_id = make_suggestion(client)
    resolve(client, sid, suggestion_id)
    r = resolve(client, sid, suggestion_id)
    assert r.status_code == 409
```

> ⚠️ **Handoff to Frontend-A by Hour 4 end:** `POST /ai/chat`, `POST /suggestions`, `POST /suggestions/:id/resolve` all working.

---

## Hour 4–5 | Scoring Engine I

> ⚠️ **Sync with Model team at Hour 4–5:** Share feature vector JSON schema — `{ "features": ["verification_frequency", "reprompt_ratio", ...] }`. Names and order must match exactly between `features.py` (model) and `scoring.py` (backend). Do NOT write `extract_c1_features` before this sync.

### `scoring.py`

- [ ] `load_models()` — load `component1_xgboost.joblib`, `component2_lgbm.joblib` via `joblib`. Return `None` per component if artifact absent. Check `SCORING_FALLBACK_MODE` env var.
- [ ] `extract_c1_features(session_id, db) -> np.array` — 15-feature vector from `events`, `chunk_decisions`, `editor_events`
- [ ] `run_component1(session_id, db) -> dict` — returns `{ structural_scores: {...}, feature_importances: {...} }`. Fallback to rule-based heuristics if no artifact.
- [ ] `extract_c2_features(session_id, db) -> list[dict]` — per-prompt feature dicts from all `prompt` events
- [ ] `run_component2(session_id, db) -> dict` — returns `{ prompt_quality_scores: {...}, per_prompt: [...] }`. Fallback if no artifact.

**Component 1 feature vector (15 features, order locked after sync):**
| Feature | Source |
|---|---|
| `verification_frequency` | `execute` count / session minutes |
| `reprompt_ratio` | Failed `execute` → `prompt` within 60s / failures |
| `time_in_editor` | Duration from `panel_focus = editor` events |
| `time_in_chat` | Duration from `panel_focus = chat` events |
| `time_in_filetree` | Duration from `panel_focus = filetree` events |
| `orientation_time` | Session start → first `edit` timestamp |
| `iteration_count` | `edit → execute` cycle count |
| `test_lines_written` | `def test_` matches in `edit_delta` insertions |
| `file_open_count` | Unique `file_open` events before first `edit` |
| `dwell_time_per_file` | Mean `file_open → file_close` duration |
| `prompt_count` | Total `prompt` events |
| `prompt_rate` | Prompt count / session minutes |
| `acceptance_rate` | Offline: `parse_hunks(original, final)` overlap with `parse_hunks(original, proposed)` per suggestion |
| `deliberation_time` | `suggestion.resolved_at − suggestion.shown_at` (total time on suggestion) |
| `post_acceptance_edit_rate` | `SequenceMatcher(proposed_content, final_content).ratio()` per suggestion |

**Test gate — `test_scoring_components.py`:**
```python
def test_c1_features_from_seeded_session():
    seed_minimal_session(db)
    feats = extract_c1_features(test_sid, db)
    assert feats.shape == (15,)
    assert not np.isnan(feats).any()

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

---

## Hour 5–6 | Scoring Engine II + Session End Pipeline

**Goal:** Full pipeline runs at `POST /session/end`; `session_scores` row written.

### Component 3 — Critical Review Detector (always heuristic, no artifact)

```python
from difflib import SequenceMatcher

def review_score(proposed_code: str, final_code: str, decision: str) -> int:
    if decision == "rejected":
        return 5  # Strongest critical review signal
    similarity = SequenceMatcher(None, proposed_code, final_code).ratio()
    modification_rate = 1 - similarity
    if modification_rate < 0.05:  return 1  # Verbatim paste
    if modification_rate < 0.15:  return 2  # Cosmetic changes
    if modification_rate < 0.35:  return 3  # Moderate modification
    if modification_rate < 0.60:  return 4  # Substantial review
    return 5                                 # Significant independent work

def run_component3(session_id, db) -> dict:
    # For each ai_suggestion in session:
    #   snapshot_final = editor_events WHERE trigger='suggestion_resolved' AND suggestion_id=...
    #   hunks = parse_hunks(suggestion.original_content, suggestion.proposed_content)
    #   populate chunk_decisions rows offline from diff of hunks vs snapshot_final
    #   score each chunk via review_score()
    # session_level = min(per_chunk scores)
    # Return { per_interaction: [{interaction_id, score}], session_level: float }
```

### Aggregation Layer

```python
def aggregate_scores(c1_scores, c2_scores, c3_scores, feature_importances) -> tuple[float, str]:
    # feature_importances from XGBoost, normalized to sum to 1
    # Fallback: equal weights if no importances (no Component 1 artifact)
    structural_weight = sum(feature_importances.get("structural_dims", [1/3]))
    prompt_weight = sum(feature_importances.get("prompt_dims", [1/3]))
    review_weight = 1 - structural_weight - prompt_weight

    weighted = (
        structural_weight * mean(c1_scores.values()) +
        prompt_weight * mean(c2_scores.values()) +
        review_weight * c3_scores["session_level"]
    )

    if weighted < 2.5:    label = "over_reliant"
    elif weighted <= 3.5: label = "balanced"
    else:                 label = "strategic"

    return weighted, label
```

### Wire pipeline into `POST /session/end`

```
1. run_component1(session_id, db)    ← sync
2. run_component2(session_id, db)    ← sync
3. run_component3(session_id, db)    ← sync
4. aggregate_scores(...)             ← sync
5. Write session_scores row          ← atomic
6. threading.Thread → judge_call()   ← async, updates llm_narrative when done
```

- Any unresolved suggestion hunks → auto-reject before scoring runs
- `session_scores` must be written before `POST /session/end` returns
- `llm_narrative` is NULL until async judge completes — that's acceptable

**Test gate — `test_scoring_pipeline.py`:**
```python
def test_full_pipeline_on_seeded_session():
    seed_rich_session(db)
    r = client.post('/api/v1/session/end',
        json={'final_phase':'verification'}, headers=h)
    assert r.status_code == 200

    scores = db.query(SessionScore).filter_by(session_id=sid).first()
    assert scores is not None
    assert scores.overall_label in ['over_reliant', 'balanced', 'strategic']
    assert 1.0 <= scores.weighted_score <= 5.0
    assert scores.structural_scores is not None
    assert scores.prompt_quality_scores is not None
    assert scores.review_scores is not None
    # llm_narrative may be null (async) — acceptable
```

---

## Hour 6–7 | Analytics Endpoints

**Goal:** Dashboard + session detail return correct data shapes.

### `routes/analytics.py`

**`GET /analytics/session/:session_id`**

Live metrics (always computed):
| Metric | Source |
|---|---|
| `chunk_acceptance_rate` | `decision=accepted` / total chunks (computed offline by scoring pipeline) |
| `chunk_rejection_rate` | `decision=rejected` / total chunks |
| `chunk_modification_rate` | `decision=modified` / total chunks |
| `suggestion_time_avg_ms` | Mean `resolved_at − shown_at` per suggestion |
| `verification_frequency` | `execute` count / session minutes |
| `reprompt_ratio` | Failed execute → prompt within 60s / failures |
| `time_by_panel` | Duration between consecutive `panel_focus` events |
| `orientation_duration_s` | Session start → first `edit` |
| `iteration_depth` | `edit → execute` cycle count |
| `prompt_count_by_phase` | COUNT grouped by `ai_interactions.phase` |

Cached model scores (from `session_scores` when available): `overall_label`, `weighted_score`, `structural_scores`, `prompt_quality_scores`, `review_scores`, `llm_narrative`, `judge_chain_of_thought`, `fallback_components`, `scores_available`.

**`GET /analytics/overview`**
- Aggregate across completed sessions
- Filters: `?project_name=X`, `?min_duration=N`, `?completed_only=true`
- Returns per-session summary rows + cohort averages

**`POST /analytics/session/:session_id/score`**
- Manually trigger re-scoring (overwrites existing `session_scores` row)
- Returns `{ score_id, computed_at, overall_label, fallback_components }`

> ⚠️ **Handoff to Frontend-B by Hour 7 end:** `GET /analytics/session/:id` full response schema confirmed.

**Test gate — `test_analytics.py`:**
```python
def test_session_analytics_structure():
    seed_rich_session(db)
    trigger_scoring(sid)
    r = client.get(f'/api/v1/analytics/session/{sid}', headers=h)
    for key in ['chunk_acceptance_rate','verification_frequency',
                'overall_label','structural_scores','prompt_quality_scores']:
        assert key in r.json

def test_overview_filters_correctly():
    seed_n_sessions(3, completed=True)
    seed_n_sessions(1, completed=False)
    r = client.get('/api/v1/analytics/overview?completed_only=true')
    assert len(r.json['sessions']) == 3
```

---

## Hour 7–8 | `seed.py` + E2E Tests

**Goal:** Synthetic sessions for all 3 profiles; full pipeline verified end-to-end.

### `seed.py`
- [ ] Generate 3 sessions: `over_reliant`, `balanced`, `strategic`
- [ ] Each session must include all v4 event types: `edit`, `execute`, `prompt`, `response`, `file_open`, `file_close`, `panel_focus`, `suggestion_shown`, `chunk_accepted`, `chunk_rejected`, `chunk_modified`
- [ ] Each session must include realistic `chunk_decisions` rows
- [ ] Run full pipeline on each → verify `over_reliant` scores < 2.5, `strategic` > 3.5

**Test gate — `test_e2e_backend.py`:**
```python
def test_seeded_profiles_score_correctly():
    seed_all_profiles()
    for profile, expected_label in [('over_reliant','over_reliant'),('strategic','strategic')]:
        sid = get_seeded_session_id(profile)
        trigger_scoring(sid)
        scores = db.query(SessionScore).filter_by(session_id=sid).first()
        assert scores.overall_label == expected_label
```

---

## Hour 8–9 | Hardening + Auth

**Goal:** No 500s on expected inputs; all edge cases handled.

- [ ] `POST /auth/login` — hardcoded accounts, return `{ userId, role, token }`
- [ ] `POST /session/end` on already-ended session → 400
- [ ] Empty session scoring (0 events) → graceful fallback, no crash
- [ ] `time_on_chunk_ms` server-side clamp enforced
- [ ] Dual-write transaction rollback verified
- [ ] Threading safety: 3 concurrent `POST /session/end` → no SQLite locking errors

**Test gate — `test_edge_cases.py`:**
```python
def test_empty_session_scores_without_crash():
    sid = start_session()
    end_session(sid)
    scores = db.query(SessionScore).filter_by(session_id=sid).first()
    assert scores is not None
    assert scores.overall_label is not None

def test_double_session_end_returns_400():
    sid = start_and_end_session()
    r = client.post('/api/v1/session/end', headers={'X-Session-ID': sid})
    assert r.status_code == 400
```

---

## Hour 9–10 | Demo Prep

- [ ] `SCORING_FALLBACK_MODE=false`, real artifacts loading
- [ ] `session_scores` written on every `POST /session/end`
- [ ] `llm_narrative` populates within 15s of session end
- [ ] `GET /analytics/overview` returns all completed sessions
- [ ] Cache one Gemini response as fallback fixture in case of rate limits during demo

---

## Error Handling Reference

| Scenario | Status |
|---|---|
| Missing `X-Session-ID` | 401 |
| Invalid `session_id` | 404 |
| Gemini API error | 502 — write neither `ai_interactions` nor `events` row |
| Gemini judge error | 200 — scoring still written, `llm_narrative` stays null |
| Invalid `chunk_index` | 400 |
| Already-decided chunk | 409 |
| `proposed_content == original_content` | 400 |
| Dual-write failure | 500 — roll back both writes atomically |
| Model artifact missing | 200 — score with heuristic fallback, set `fallback_components` |
| Scoring pipeline failure | 500 — do not write partial `session_scores` row |

---

## Handoff SLAs (Backend → Others)

| To | What | By |
|---|---|---|
| Frontend-B | `POST /auth/login` stub | Hour 2 end |
| Frontend-B | `GET /questions` stub | Hour 3 start |
| Frontend-A | `POST /ai/chat` + `POST /suggestions` working | Hour 4 end |
| Frontend-A | `POST /suggestions/:id/chunks/:idx/decide` | Hour 4 end |
| Frontend-B | `GET /analytics/session/:id` full schema | Hour 7 end |

---

## Backend-Owned Risks

| Risk | Mitigation |
|---|---|
| `diff.py` wrong line numbers | Spike standalone, ≥4 unit tests before touching suggestions route |
| Feature vector mismatch with model team | Share JSON schema at Hour 4–5 sync — do not write `extract_c1_features` before sync |
| Gemini rate limit during demo | Cache one response as fallback fixture |
| `llm_narrative` never populates | Add rule-based fallback: if thread fails within 30s, write summary from scores |
| SQLite locking under concurrent session ends | Serialize scoring pipeline with `threading.Lock` |

---

## Project Structure

```
backend/
├── app.py                  # Flask factory, blueprint registration, CORS
├── base.py                 # SQLAlchemy Base
├── models.py               # All 8 table definitions
├── db.py                   # init_db(), get_db(), engine
├── diff.py                 # compute_edit_delta() + parse_hunks()
├── llm.py                  # GeminiClient — assistant_call() + judge_call()
├── scoring.py              # load_models(), Components 1–3, aggregation, judge dispatch
├── seed.py                 # Synthetic session generator
├── routes/
│   ├── session.py          # /session/start, /end, /phase, /trace
│   ├── files.py            # /files, /files/:id/save, /events/file
│   ├── ai.py               # /ai/chat
│   ├── suggestions.py      # /suggestions, /suggestions/:id/chunks/:idx/decide, /suggestions/:id
│   ├── events.py           # /events/editor, /events/execute, /events/panel
│   └── analytics.py        # /analytics/session/:id, /analytics/overview, /analytics/.../score
├── models/
│   ├── component1_xgboost.joblib      # From model team (optional, fallback if absent)
│   ├── component2_lgbm.joblib         # From model team (optional, fallback if absent)
│   └── component2_codebert_embeddings/
├── .env                    # GEMINI_API_KEY, FLASK_SECRET_KEY, DATABASE_URL
└── requirements.txt
```
