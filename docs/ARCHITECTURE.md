# Architecture Documentation

This document details the architectural decisions, system components, and data flow for OverSite IDE.

---

## Glossary

* **Candidate:** The user performing the technical interview.
* **EditorEvent:** A record of a single code modification or file action.
* **Interaction:** A single turn in the AI chat panel.
* **Scoring Pipeline:** The backend process that analyzes candidate behavior and code to produce a multi-dimensional score.
* **X-Session-ID:** A unique identifier for an active interview session, used for authentication and logging.

## System Overview
OverSite IDE is built as a **Client-Server** application:
* **Frontend**: A React Single Page Application (SPA) that provides a VS Code-like environment for candidates.
* **Backend**: A Flask REST API that manages session state, logs candidate telemetry, and integrates with Gemini for real-time assistance and scoring.
* **Database**: SQLite (SQLAlchemy) for persistence, storing sessions, events, and AI interactions.

## Directory Structure
```
/root
├── backend/            # Flask server, route controllers, and DB schema
│   ├── routes/         # API endpoints (auth, session, ai, events, etc.)
│   ├── services/       # Business logic (diffing, scoring, model loading)
│   └── tests/          # Pytest suite
├── frontend/           # React application
│   ├── src/
│   │   ├── components/ # UI components (Monaco editor, Chat panel)
│   │   ├── hooks/      # Custom React hooks (useSession, useAuth)
│   │   └── api.ts      # Axios configuration
├── model/              # Unified feature extraction and ML model artifacts
└── problems/           # Static problem definitions and initial file contents
```

## Data Life Cycle

The path from a single keystroke to a behavioral score:

1. **Ingestion (Frontend):** Monaco editor captures `EditorEvents`. These are debounced and sent to the `/events/editor` endpoint as full content snapshots or deltas.
2. **Persistence (Backend):** Each event is timestamped and stored in the `EditorEvents` table, preserving the chronological history of the implementation.
3. **Extraction (Scoring Service):** Upon session submission, the `ScoringEngine` retrieves the full event history. It uses the `model.features` package to extract behavioral signals (e.g., `rate_acceptance`, `freq_verification`).
4. **Inference (ML Scoring):** Extracted features are fed into pre-trained **XGBoost models** (Behavioral and Prompt Quality classifiers) to generate scores.
5. **Synthesis (Gemini Summary):** The final score and the conversation history are sent to **Gemini** to generate a session summary based on the model's feature contributions.

## Data Model (Database Schema)

The persistence layer is managed via SQLAlchemy. Below are the core entities:

### 1. Sessions & Files
* **`Session`**: Tracks the interview lifecycle (`started_at`, `ended_at`, `username`, `project_name`).
* **`File`**: Represents a file in the workspace context, linked to a session.

### 2. Telemetry & AI 
* **`Event`**: High-level telemetry (actors: `system`, `user`; types: `execute`, `panel_focus`). Stores flexible JSON `metadata`.
* **`EditorEvent`**: Fine-grained code modification logs. Stores the full `content` or `edit_delta` for every keystroke group.
* **`AIInteraction`**: Logs prompts and responses between the candidate and Gemini.
* **`AISuggestion`**: Links AI responses to specific code hunks, tracking if they were accepted, rejected, or modified.

### 3. Scoring
* **`SessionScore`**: Stores the output of the scoring pipeline, including the Gemini summary, importance metrics, and raw feature values.

## Detailed Scoring Engine

The scoring engine is divided into three primary components, defined in `backend/services/scoring.py` and `model/features.py`.

### Behavioral Scoring
Analyzes *how* the candidate works. It extracts **16 features** from telemetry, separated by data routing:

**1. The Classifier Path (Model Signal)**
Highly regularized structural signals used for the XGBoost model:
- **`count_prompt_orientation` (Normalized)**: Percentage of prompts spent on docs/setup.
- **`count_prompt_implementation` (Normalized)**: Percentage of prompts spent on writing code.
- **`depth_iteration`**: Cycles of edit -> execute -> debug.

**2. The Evidence Path (Model Evidence)**
Raw telemetry passed directly to Gemini for the session summary (but excluded from the classifier to prevent bias):
- **`duration_deliberation_avg`**: Average time spent reviewing a code suggestion.
- **`rate_post_acceptance_edit`**: Frequency of manual corrections after AI insertion.
- **`deliberation_to_action_ratio`**: Detects "idling" where deliberation time is high but follow-on action is low.

### Prompt Quality
Evaluates the candidate's engineering communication.
* Analyzes prompt intent (e.g., orientation vs. debugging).
* Scores prompts based on specificity, context provision, and goal clarity.

### User Summary
A Gemini-based step that reviews the final code and the candidate's interaction history to produce the session summary.

## Tech Stack & Decision Record

| Category | Technology | Rationale |
| :--- | :--- | :--- |
| **Frontend** | React / Vite | Need for a fast, component-based UI with rich interactive states. |
| **Editor** | Monaco Editor | Industry standard for code editing, familiar to candidates. |
| **Backend** | Flask | Lightweight and flexible for rapid prototyping of REST APIs. |
| **Database** | SQLite | Serverless and simple for hackathon/demo deployments. |
| **AI SDK** | Gemini (Google Gen AI) | State-of-the-art LLM capabilities for code generation and analysis. |
| **ML Libraries** | Scikit-learn / XGBoost | Robust ecosystem for the behavioral scoring engine. |

## Design Constraints & Heuristic Defense

* **Decision: Monolithic Backend**
  * **Rationale:** Prioritized simplicity and ease of deployment for the demo environment. Deferring extraction until specific scaling needs arise.
* **Decision: In-memory Editor State** 
  * **Rationale:** A single-user interview environment does not require real-time collaboration with the interviewer, simplifying the persistence model to periodically synced events. 

* **Decision: Rule-based Critical Review (Levenshtein)**
  * **Rationale:** We use a deterministic rule for Critical Review rather than an LLM call to ensure immediate scoring and to prioritize mathematical evidence of verification (actual edits) over qualitative AI judgment.

## Data Strategy & Lineage

To ensure rigorous evaluation, OverSite maintains a clean separation of data roles:
* **Research Datasets (CUPS/WildChat)**: Used exclusively for model training and establishing behavioral baselines.
* **Synthetic Data**: Procedurally generated session JSONs used only for **Integration Testing and CI/CD validation** of the scoring pipeline. These are not used for training to avoid synthetic bias.

---
