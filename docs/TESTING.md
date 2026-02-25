# Testing Guidelines

## Strategy
OverSite IDE uses a multi-layered testing strategy to ensure reliability across the platform. We prioritize **Integration Tests** for backend API endpoints and **Unit Tests** for shared logic in the `model/` package.

### Test Types
* **Backend Suite (Pytest):** Covers route controllers, database logic, and feature extraction.
* **Frontend Suite (Vitest):** Validates React components and custom hooks (e.g., `useSession`, `useAuth`).
* **Shared Logic (Pytest):** Validates the unified feature extraction in `model/tests/`.
* **E2E Smoke Tests:** Verifies the full session lifecycle from start to score submission.

## Running Tests

### Backend (Python)
```bash
cd backend
python -m pytest
```

### Frontend (Vitest)
```bash
cd frontend
npm test
```

### Smoke Test (E2E)
Verifies the happy path from the CLI:
```bash
# Ensure server is running
python demo_smoke_test.py
```

## Mocking & Isolation

### Mocking Gemini AI
To avoid external dependencies and API costs during testing, use the `MagicMock` pattern for `GeminiClient`. See `backend/tests/test_ai_endpoints.py` for examples.
* **Integration Tests:** Use a test database (`test_oversite.db`) by setting `DB_URL` in the environment.
* **Fallback Mode:** Setting `SCORING_FALLBACK_MODE=true` allows testing the scoring pipeline without requiring ML artifacts.

## CI/CD Standards
* All tests must pass before merging.
* Critical path tests (session start/end) must maintain 100% coverage.
* Commits should not break the `demo_smoke_test.py` workflow.

## Troubleshooting Tests

### Issue: `ImportError: No module named 'services'`
**Fix:** Run tests as a module from the `backend/` directory: `python -m pytest`.

### Issue: `sqlite3.OperationalError: database is locked`
**Fix:** Ensure no other process (like the main server) is holding a lock on the test database. Use a unique DB file for isolated test runs.

### Issue: `ReferenceError: document is not defined` (Frontend)
**Fix:** Ensure Vitest is running with the `jsdom` environment (configured in `vite.config.ts`).

---
