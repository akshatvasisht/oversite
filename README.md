![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)
![React](https://img.shields.io/badge/React-19.2-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.4-007ACC?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5.0-646CFF?logo=vite&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-Pro-8E75B2?logo=google-gemini&logoColor=white)
![Git LFS](https://img.shields.io/badge/Git_LFS-3.4-black?logo=git-lfs&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0-EB214C?logo=xgboost&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.4-F7931E?logo=scikit-learn&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3.0-07405E?logo=sqlite&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-8.0-0A9EDC?logo=pytest&logoColor=white)
![Vitest](https://img.shields.io/badge/Vitest-1.0-729B1B?logo=vitest&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

# OverSite

**AI allowed. Usage reported.**

OverSite is an online assessment (OA) platform for technical hiring—similar to CodeSignal or HackerRank—with a key difference: **candidates can use AI during the assessment**, and the platform **reports on how they use it**. Recruiters get both correctness and behavioral insights: how candidates prompt the AI, review suggestions, and verify their work.

Candidates code in a browser-based IDE with an embedded AI assistant. Sessions are scored for behavioral signals (e.g. over-reliant vs. strategic AI use) and summarized in recruiter-facing reports. OverSite is built for the reality that AI-assisted coding is the norm—assess and hire for how people work with AI, not in spite of it.

## Overview

### Core Functionality

* **IDE & session environment:** VS Code–like workspace (Monaco editor, file explorer, terminal) with phased flows (Orientation → Implementation → Verification). Candidates open a problem, edit code, run tests, and use an in-panel AI chat—all in the browser.
* **Real-time telemetry:** Editor events (edits, deltas), execute events (terminal runs, exit codes), panel focus, and AI suggestion accept/reject/modify decisions are logged with timestamps. Cursor-style diff UI captures how candidates use AI suggestions before committing.
* **Behavioral scoring pipeline:** Multi-component scoring runs at session end: Component 1 (XGBoost/heuristic) on structural behavior (acceptance rate, deliberation time, verification frequency); Component 2 on prompt quality; Component 3 on critical review of AI output. Scores are aggregated into an overall label (e.g. over_reliant, balanced, strategic) and an LLM judge (Gemini) produces a narrative for recruiters.

### How It Works

1. **Input / Ingestion:** Candidates sign in and start a session for a given problem. The frontend sends session start, then streams editor events (debounced), execute events, panel focus, file open/close, and AI chat turns. Suggestion chunks are sent with accept/reject/modify decisions and timing.
2. **Processing / Validation:** The backend persists events and AI interactions in SQLite. On session end, the scoring engine reads full event history and chunk decisions, runs feature extraction (e.g. from `model/features`), applies XGBoost (or fallback heuristics) and Component 2/3 logic, then aggregates into a weighted score and label. An async Gemini judge call adds a human-readable narrative.
3. **Execution / State Update:** Session state, files, events, AI suggestions, and final `session_scores` (scores, narrative, feature importances) are stored. Admin can trigger manual re-score or view analytics.
4. **Output / Response:** Recruiters and admins use the admin dashboard to see session list, per-session scores, and the LLM narrative. The candidate-facing UI shows assessment list and the IDE for the active session.

---

## Impact & Performance

* **Fallback mode:** When ML artifacts are unavailable (no Git LFS), `SCORING_FALLBACK_MODE=true` uses heuristic-based behavioral patterns so the full flow works without XGBoost models.
* **Session lifecycle:** Single session from start to submit is designed for ~60-minute assessments; scoring runs synchronously at session end so the dashboard has scores immediately; only the LLM judge runs asynchronously.

## Applications / Use Cases

* **Technical hiring & OAs:** Run take-home or timed coding assessments with an embedded AI assistant; evaluate both correctness and how candidates use AI (decomposition, prompting, verification, critical review).
* **Behavioral differentiation:** Produce consistent, defensible behavioral labels and narratives (e.g. over_reliant vs. strategic) from real session data instead of post-hoc interviewer judgment.
* **Recruiter dashboards:** Admin view of all sessions, per-candidate score detail, and LLM-generated narratives to support hiring decisions.

<details>
  <summary><b>View Screenshots</b></summary>
  <!-- Add screenshots here -->
</details>

## Documentation

* **[SETUP.md](docs/SETUP.md):** Installation, environment configuration, and startup instructions.
* **[ARCHITECTURE.md](docs/ARCHITECTURE.md):** System design, data flow, glossary, and design decisions.
* **[API.md](docs/API.md):** REST (JSON) API and session/auth reference.
* **[TESTING.md](docs/TESTING.md):** Testing guidelines.
* **[STYLE.md](docs/STYLE.md):** Coding standards, testing guidelines, and repository conventions.

## License

See **[LICENSE](LICENSE)** file for details.
