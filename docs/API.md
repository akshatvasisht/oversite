# OverSite IDE API Documentation

## Protocol: REST (JSON)

### Authentication
Most endpoints require an active session context to identify the candidate and question.
* **Header:** `X-Session-ID`
* **Value:** A UUID string obtained from the `/session/start` endpoint.
* **Exceptions:** Admin endpoints (prefixed `/analytics`) require an admin role (mocked via username starting with `admin`).

#### 1. Session & Auth

##### `GET /api/v1/auth/questions`
**Description:** Retrieves available interview blocks for a specific user.
**Query Parameters:** `username` (optional)
**Output (200 OK):**
```json
[
  {
    "id": "q1",
    "title": "Shopping Cart Debugger",
    "status": "pending",
    "files": ["cart.py", "product.py"]
  }
]
```

##### `POST /api/v1/auth/login`
**Description:** Mock login for demo purposes.
**Input:** 
```json
{ "username": "testuser1", "password": "password123" }
```
**Output (200 OK):** 
```json
{ 
  "userId": "u123", 
  "role": "candidate", 
  "token": "mock-session-token" 
}
```

##### `POST /api/v1/session/start`
**Description:** Initializes or rehydrates an interview session.
**Input:** 
```json
{ "username": "testuser1", "project_name": "q1" }
```
**Output (201 Created):** 
```json
{ 
  "session_id": "550e8400-e29b-41d4-a716-446655440000", 
  "started_at": "2023-10-27T10:00:00Z", 
  "files": [], 
  "rehydrated": false 
}
```

##### `POST /api/v1/session/end`
**Description:** Submits the interview and triggers the scoring pipeline.
**Output (200 OK):** 
```json
{ 
  "session_id": "...", 
  "ended_at": "...", 
  "duration_seconds": 1200 
}
```

#### 2. Workspace & AI

##### `POST /api/v1/files`
**Description:** Persists a new file for the current session.
**Input:** 
```json
{ "filename": "test.py", "language": "python", "initial_content": "print('hello')" }
```

##### `POST /api/v1/ai/chat`
**Description:** Interactive prompt with Gemini.
**Input:** 
```json
{ 
  "prompt": "How do I fix the loop?", 
  "file_id": "f456", 
  "history": [], 
  "context": "Active code snippet..." 
}
```
**Output (201 Created):** 
```json
{ 
  "response": "Use a while loop instead...", 
  "has_code_changes": true, 
  "interaction_id": "i789" 
}
```

##### `POST /api/v1/suggestions`
**Description:** Records a multi-hunk code suggestion for later resolution.
**Input:** 
```json
{ 
  "interaction_id": "i789", 
  "file_id": "f456", 
  "original_content": "...", 
  "proposed_content": "..." 
}
```
**Output (201 Created):** 
```json
{ 
  "suggestion_id": "s012", 
  "hunks": [{ "type": "modified", "old": "...", "new": "..." }] 
}
```

##### `POST /api/v1/suggestions/decide`
**Description:** Resolves a specific code hunk decision.
**Input:** 
```json
{ 
  "suggestion_id": "s012", 
  "file_id": "f456", 
  "chunk_index": 0, 
  "decision": "accepted", 
  "final_code": "..." 
}
```

#### 3. Telemetry & Events

##### `POST /api/v1/events/editor`
**Description:** Logs code edits. Debounced on the frontend.
**Input:** `{ "file_id": "...", "content": "full_file_text" }`

##### `POST /api/v1/events/execute`
**Description:** Logs terminal execution results.
**Input:** `{ "exit_code": 0, "output": "...", "file_id": "..." }`

#### 4. Admin & Analytics

##### `GET /api/v1/analytics/overview`
**Description:** Fetches a list of all candidate sessions.
**Output (200 OK):**
```json
{ 
  "sessions": [ 
    { "session_id": "..", "username": "testuser1", "overall_label": "Strong" } 
  ] 
}
```

### Error Handling

| Code | Status | Scenario |
| :--- | :--- | :--- |
| **400** | Bad Request | Missing required fields (e.g., `prompt` in AI chat). |
| **401** | Unauthorized | Invalid or expired `X-Session-ID` header. |
| **403** | Forbidden | Regular user attempting to access `/analytics` endpoints. |
| **404** | Not Found | Reference to a non-existent `file_id` or `session_id`. |
| **502** | Bad Gateway | Gemini API timeout or internal scoring engine crash. |

---
