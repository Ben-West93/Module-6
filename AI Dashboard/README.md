# Module 6 Project — AI Dashboard

A Streamlit dashboard that combines everything from Module 6: token-based
authentication, task management against a REST API, data visualisation, and an
AI chat interface — with a mock-data mode so the whole UI works offline.

## Features

- **Authentication** — login form, token held in `st.session_state`, logout button
- **Mock mode** — tick *Use Mock Data* on the login form to run the whole app
  against `mock_data.py` with no backend
- **Dashboard tab** — total / completed / pending metrics, a task table, and a
  Plotly bar chart of completed vs pending
- **Tasks tab** — add-task form and per-task Complete buttons, with API errors
  surfaced as messages instead of stack traces
- **AI Chat tab** — persistent chat history, `st.chat_input`, and word-by-word
  streaming via `st.write_stream`
- **Layout** — wide page, sidebar (user info, logout, AI settings), three tabs

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create your local secrets file from the template:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   Both values are optional — without this file the app uses
   `http://localhost:8000` and an empty AI key. `secrets.toml` is gitignored and
   is never committed; the `.example` is what lives in the repo.

3. Start the backend:
   ```bash
   uvicorn backend:app --reload --port 8000
   ```
   Interactive API docs: <http://localhost:8000/docs>

4. In a second terminal, run the app:
   ```bash
   streamlit run app.py
   ```

5. Log in with one of the demo accounts:

   | Username | Password |
   |----------|----------|
   | `demo_user` | `demo1234` |
   | `ben` | `module6` |

   Or tick **Use Mock Data** on the login form to explore the dashboard with no
   backend running at all. If the backend lives somewhere other than
   `http://localhost:8000`, change `API_BASE` in `api_client.py`.

## Files

| File | Purpose |
|------|---------|
| `backend.py` | FastAPI backend — JWT auth and in-memory tasks |
| `app.py` | Main Streamlit app — auth gate, sidebar, and the three tabs |
| `api_client.py` | All backend communication: shared request helper + four API functions |
| `mock_data.py` | Sample tasks, stats, user and chat history for offline development |
| `requirements.txt` | Python dependencies |
| `README.md` | This file |
| `.streamlit/secrets.toml.example` | Template for local settings — copy to `secrets.toml` |
| `.gitignore` | Keeps bytecode, virtualenvs and `secrets.toml` out of the repo |

`app.py` talks only to `api_client.py`, so `backend.py` can be swapped for any
server exposing the endpoints below.

## API endpoints expected by `api_client.py`

| Function | Request | Success response |
|----------|---------|------------------|
| `login(username, password)` | `POST /auth/token` with `{"username", "password"}` | `{"access_token": "..."}` |
| `get_tasks(token)` | `GET /tasks` | list of task objects (or `{"tasks": [...]}`) |
| `create_task(token, title)` | `POST /tasks` with `{"title"}` | the created task, including `id` |
| `complete_task(token, task_id)` | `PATCH /tasks/{task_id}/complete` | the updated task, with `done: true` |

Every protected request sends `Authorization: Bearer <token>`. A task object
looks like `{"id": 1, "title": "...", "done": false, "created_at": "2026-03-10"}`.

## Error handling

Each function returns a `(data, error)` tuple — never a raw response — so the UI
never reads a body before the status code has been checked. `api_client._request`
handles connection refused, timeouts, non-2xx statuses, and bodies that are not
valid JSON in one place. Responses are also verified rather than trusted:
`create_task` compares the returned title with the title that was sent, and
`complete_task` checks that the returned task is the requested one and is
actually marked done.

The UI is defensive about what a backend may send. Items in the task list that
are not task objects are dropped and reported as a warning rather than crashing
the page; `done` is normalised, so a flag sent as the string `"false"` is not
counted as complete; Complete-button keys include the row position, so
duplicate or missing task ids cannot collide; and a 401 from any call logs the
user out with an explanation instead of leaving a dead-end error on screen.

## Backend notes

`backend.py` is a teaching backend kept to a single file. Tasks live in memory
and are stored per user, so restarting uvicorn (or letting `--reload` restart
it) resets everything to the seed data. Passwords are PBKDF2-SHA256 hashed at
import time from the plaintext in `USERS`, and the signing key defaults to a
development constant — both are readable on purpose so the demo logins work out
of the box, and both are the first things to change for anything real. Set
`AI_DASHBOARD_SECRET` and `AI_DASHBOARD_TOKEN_MINUTES` in the environment to
override them; a TTL of 1 minute is a quick way to watch the dashboard's
auto-logout on token expiry.

One deviation worth knowing: `/auth/token` accepts a JSON body rather than
OAuth2 form encoding, because that is what `api_client.login()` sends.

## Configuration

`API_BASE` and `AI_API_KEY` are read from `.streamlit/secrets.toml` if it
exists, then from environment variables of the same name, then from built-in
defaults. A fresh clone with no secrets file runs fine.

## Notes

- Session state keys are all initialised at the top of `app.py` before anything
  reads them.
- The AI chat replies are generated locally by `mock_reply()` in `app.py`; the
  sidebar API key field is stored in session state only and no external AI
  service is called.
