# Coding Standards & Style Guide

## 1. General Principles

### 1.1 Professionalism & Tone
* **Objective Language:** All documentation and comments must use objective, technical language.
* **Techncial Constraints:** Describe technical constraints rather than environmental ones.
    * *Incorrect:* "Running on my hackathon laptop."
    * *Correct:* "Defaulting to CPU inference for wider hardware compatibility."

### 1.2 Intent over Implementation
* **Why, Not What:** Comments should explain *why* a decision was made. Do not narrate the code execution logic step-by-step.
* **No Meta-Commentary:** Do not leave "thinking traces," internal debates, or editing notes in the codebase.
    * *Forbidden:* `// I tried X but it failed, so I'm doing Y...`
    * *Allowed:* `// Uses Y to ensure thread safety during high-load.`

## 2. Python Guidelines (Backend)

### 2.1 Docstrings
* **Format:** Use Google Style docstrings.
* **Structure:** Clearly separate the description, arguments (**Args**), and return values (**Returns**).

**Bad Example:**
```python
def process_score(data):
    """1. Get data. 2. Run model. 3. Return result."""
```

**Good Example:**
```python
def process_score(session_id: str) -> Dict[str, Any]:
    """
    Triggers the scoring pipeline for a completed interview session.

    Args:
        session_id: UUID string of the session to analyze.

    Returns:
        A dictionary containing Component scores (C1, C2, C3) and importance metrics.

    Raises:
        ValueError: If the session does not exist or is not marked as ended.
    """
```

### 2.2 Shared Logic
* Any logic used by both Training and Serving (e.g., feature extraction) MUST reside in the `model/` package.

## 3. Frontend Guidelines (TSX / React / Vite)

### 3.1 Documentation Standards
* **JSDoc:** Use standard JSDoc format (`/** ... */`) for exported functions, hooks, and complex component props.

**Example:**
```typescript
/**
 * Interactive Monaco Editor wrapper.
 * Handles debounced telemetry logging of incremental code changes.
 */
export default function CodeEditor({ fileId, initialContent }: EditorProps) {
  // ...
}
```

### 3.2 Code Style
* **Interfaces:** Define explicit interfaces for all component props.
* **Hooks:** Prefer custom hooks (e.g., `useSession.ts`) to keep UI components focused on rendering.

## 4. Testing & Ops

### 4.1 Testing Standards
* **Framework:** Use `pytest` (backend) and `vitest` (frontend).
* **Mocking:** All external dependencies (Gemini, third-party APIs) MUST be mocked in automated suites.
* **Naming:** Test files prefixed with `test_`, test functions prefixed with `test_`.

### 4.2 Scripting Guidelines
* Ensure scripts in `backend/scripts/` are executable and include a shebang (`#!/usr/bin/env python3`).
* Scripts should provide clear print statements indicating the current step.

---
