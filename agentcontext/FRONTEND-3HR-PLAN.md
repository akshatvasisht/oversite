# Frontend 3-Hour Plan

## Current State

| Area | Done | Missing |
|------|------|---------|
| Frontend-A | Monaco, FileExplorer, useSession, useAutosave, api.ts | AI chat wiring, suggestions/diff overlay, execute/submit events |
| Frontend-B | Login, AuthContext, route guards, hardcoded questions, admin placeholder | Backend wiring, admin dashboard, score detail page |

---

## Hour 1 — AI Chat Panel (Most Critical Path)

### Block 1 (0:00–0:30) — `AIChatPanel.tsx` component shell

- [ ] Message thread with user/AI bubbles
- [ ] Textarea + Send button
- [ ] Loading spinner during Gemini request
- [ ] `Cmd+Enter` / `Ctrl+Enter` to send
- [ ] Store `conversationHistory` array in local state (passed to `POST /ai/chat`)

### Block 2 (0:30–1:00) — Wire `POST /ai/chat` + auto-create suggestion

- [ ] On send: call `POST /ai/chat` with `{ prompt, file_id, history }`
- [ ] Render AI response in thread with timestamp
- [ ] If `has_code_changes: true`: extract code block from response markdown, call `POST /suggestions` with `{ interaction_id, file_id, original_content, proposed_content }`
- [ ] Store `{ suggestion_id, hunks, shown_at }` in component state
- [ ] Show "Review suggestion below" badge in chat when a suggestion is pending

---

## Hour 2 — Diff Overlay + Execute/Submit (Hardest Task)

### Block 3 (1:00–1:30) — Monaco diff decorations

- [ ] Create `useDiffOverlay` hook (or inline in `MonacoEditorWrapper`)
- [ ] For each hunk: apply green line decorations for additions, red for removals via `editor.deltaDecorations()`
- [ ] Store decoration IDs to dispose later
- [ ] Add overlay widgets at hunk positions with Accept / Reject buttons

### Block 4 (1:30–2:00) — Chunk decide wiring + cleanup

- [ ] Accept → `POST /suggestions/:id/chunks/:idx/decide` with `{ decision: 'accepted', final_code: proposed_code, time_on_chunk_ms }`
- [ ] Reject → same endpoint, `decision: 'rejected'`, `final_code: original_code`
- [ ] After last hunk decided: dispose all decorations, update `activeContent` to final state
- [ ] Track `shown_at` per suggestion and `decided_at` per chunk → compute `time_on_chunk_ms` client-side
- [ ] "User sends new prompt" → auto-resolve any pending suggestion before `POST /ai/chat` fires

---

## Hour 3 — Submit, Events, Admin Dashboard

### Block 5 (2:00–2:30) — Run Code + Submit + Panel Events

- [ ] Wire Run button → `POST /events/execute` with `{ command, exit_code, output }`
- [ ] `SubmitModal.tsx` — "Are you sure?" confirm/cancel → `POST /session/end` → redirect to `/questions`
- [ ] `POST /events/panel` on click into editor, chat, and terminal panes (add `onClick` handlers to each `<section>`)

### Block 6 (2:30–3:00) — Admin Dashboard + Score Detail

- [ ] `AdminDashboard.tsx` — `GET /analytics/overview`, render `IntervieweeTable` with Name, Status, Score, Date
- [ ] Click completed row → navigate to `/admin/:candidateId`
- [ ] `ScoreDetailPage.tsx` — `GET /analytics/session/:id`, render:
  - Score badge (`over_reliant` / `balanced` / `strategic`)
  - `RubricBreakdown` — 12 dimensions as a list with numeric scores
  - `NarrativeReport` — if `llm_narrative` is null, show skeleton + poll every 5s (max 3 retries)

---

## Key Decisions

| Decision | Choice |
|----------|--------|
| Diff overlay approach | Monaco `deltaDecorations` + `addContentWidget` for Accept/Reject — do NOT use Monaco diff editor (separate control) |
| Code block extraction | Simple regex: `/```[\w]*\n([\s\S]*?)```/` — keep it dumb |
| Questions page | Leave hardcoded unless backend has `GET /questions` ready; wire in Block 6 if time allows |
| Auth login | Keep mock login in `AuthContext` for now — handoff item from backend |

---

## Dependency Map

```
Block 1: AIChatPanel shell
    │
    ▼
Block 2: POST /ai/chat + POST /suggestions
    │
    ▼
Block 3: Monaco diff decorations (hunks from suggestion)
    │
    ▼
Block 4: POST /suggestions/:id/chunks/:idx/decide + cleanup
    │
    ▼
Block 5: Run Code + Submit + Panel events
    │
    ▼
Block 6: Admin dashboard + Score detail
```
