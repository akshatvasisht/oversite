# Environment Setup Instructions

## Prerequisites
* **Python 3.9+**
* **Node.js 18+**
* **npm** or **yarn**
* **Git**
* **Git LFS** (Large File Storage) - Required for fetching ML models.

## Installation

### 1. Repository Setup
```bash
git clone <repo-url>
cd oversite
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

### 4. Fetching ML Models (Git LFS)
The scoring engine requires pre-trained XGBoost models. Fetch them from the remote:
```bash
git lfs pull
```

#### Git LFS vs. Fallback Mode
*   **LFS Enabled:** After running `git lfs pull`, the backend will use verified ML models stored in `model/models/`.
*   **Fallback Mode:** If Git LFS artifacts are unavailable, set `SCORING_FALLBACK_MODE=true` in your `.env`. The backend will bypass ML inference and use **heuristic-based behavioral patterns** to generate scores. This is recommended for local development without the full data science artifacts.

## Running the Application

### 1. Start Backend
```bash
cd backend
python app.py
```

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

The application is accessible at `http://localhost:5173`.

## Developer Workflow

### Running Tests
* **Backend Suite:** `cd backend && python -m pytest`
* **Frontend Suite:** `cd frontend && npm test`
* **Smoke Test:** `python demo_smoke_test.py` (E2E happy path).

## Troubleshooting Matrix

| Symptom | Probable Cause | Resolution |
| :--- | :--- | :--- |
| **Model failed to load** | Missing ML artifacts | Run `git lfs pull` or set `SCORING_FALLBACK_MODE=true`. |
| **SQLite: database locked** | Concurrent DB access | Close other instances of `app.py` or SQL browsers. |
| **CORS Error** | Backend not on port 8000 | Ensure backend is running and `VITE_API_URL` is correct. |
| **Import: No module 'model'** | Improper PYTHONPATH | Install in editable mode: `pip install -e .` from root. |
| **AI Chat: 502 Error** | Invalid API Key | Verify `GEMINI_API_KEY` in `.env`. |

---
