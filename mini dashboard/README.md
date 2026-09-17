# L6 — Mini Dashboard

A small task manager: a FastAPI JSON API and a single-file HTML dashboard that talks to it.

## Files

| File | What it is |
|---|---|
| `mini_api.py` | FastAPI backend. In-memory task list persisted to `tasks.json`. |
| `dashboard.html` | The frontend. Plain HTML/CSS/JS, no build step, no dependencies. |
| `tasks.json` | Created automatically on the first write. Delete it to reset to the seed tasks. |
| `README.md` | This file. |

## Setup

```bash
pip install fastapi uvicorn
uvicorn mini_api:app --reload --port 8000
```

The API is then at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

## Running the frontend

Open `dashboard.html` through a local web server rather than double-clicking it, so the
page has a real `http://` origin:

```bash
python -m http.server 5500
```

Then visit `http://localhost:5500/dashboard.html`. The backend allows all origins via
`CORSMiddleware`, so any local port works.

Opening the file directly with `file://` will work in some browsers and be blocked in
others — a local server avoids the question entirely.

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| `GET` | `/` | — | `200` — a short status message |
| `GET` | `/tasks` | — | `200` — list of tasks |
| `POST` | `/tasks` | `{"title": "..."}` | `201` — the created task |
| `PATCH` | `/tasks/{id}/complete` | — | `200` — the task, now `done: true` |
| `PATCH` | `/tasks/{id}` | `{"done": false}` and/or `{"title": "..."}` | `200` — the updated task |
| `DELETE` | `/tasks/{id}` | — | `204` — no body |

### Task shape

```json
{ "id": 1, "title": "Read the FastAPI docs", "done": false, "created_at": "2026-03-01" }
```

### Errors

| Status | When |
|---|---|
| `404` | The `{id}` in the path does not exist. Body: `{"detail": "Task 42 not found."}` |
| `422` | Missing/empty/wrong-typed `title`, a non-integer `{id}`, or a `PATCH /tasks/{id}` with no fields to update. |

## Frontend features

- **Stats bar** — total, done, and pending counts. Always reflects every task, not the active filter.
- **Task list** — one row per task, loaded on page load.
- **Add form** — posts a new title as JSON, then refreshes.
- **Checkbox toggle** — marks a task done or back to pending.
- **Delete button** — removes a task.
- **Filter tabs** — All / Pending / Done, filtered in the browser with no extra requests.
- **Refresh button and timestamp** — shows when the list was last fetched.
- **Error banner** — one red message area for network failures and API errors, cleared on the next success.

## Implementation notes

- **Shared request helper.** Every call goes through `apiRequest()`, which checks
  `response.ok`, pulls FastAPI's `detail` field out of error bodies, and turns a network
  failure into a readable "is the server running?" message.
- **Verification, not just display.** Mutations compare the server's response to what was
  sent — the POST checks the returned title, the toggle checks `id` and `done`, the delete
  re-reads the list to confirm the task is gone.
- **Optimistic updates.** Toggling and deleting change the local copy and redraw
  immediately, then roll back to a snapshot if the request fails.
- **Escaping.** Titles render via `textContent`, so HTML in a task title is displayed as
  text rather than executed.
- **Persistence.** Every mutation writes `tasks.json`. A missing, corrupt, or non-list file
  falls back to the seed tasks instead of crashing at import.
- **`response_model`.** Routes declare a `Task` response model, so `/docs` shows real
  response schemas instead of a bare `200`.
