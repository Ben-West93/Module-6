"""
Module 6 Project - AI Dashboard
API Client
===========
Centralised functions for all backend communication.

All API calls go through these functions so that:
    * The Authorization header is added in one place
    * Error handling is consistent
    * The rest of the app stays clean

Why nothing here raises
-----------------------
Every public function returns a two-tuple ``(data, error)`` instead of raising:
    * On success -> ``(data, None)``
    * On failure -> ``(None, "human readable message")``

That means app.py never has to wrap a call in try/except - it just checks
``error`` and passes the message straight to st.error(). Network failures,
bad status codes and malformed bodies all arrive through the same channel.

Responses are verified, not just displayed: create_task compares the title
that came back with the title that was sent, and complete_task checks that
the task returned is the one asked for and is genuinely marked done. A
backend that silently stores something different is reported as an error
rather than shown to the user as a success.

Public functions:
    login(username, password)      -> (token: str | None,  error: str | None)
    get_tasks(token)               -> (tasks: list | None, error: str | None)
                                      (may return both: see its docstring)
    create_task(token, title)      -> (task: dict | None,  error: str | None)
    complete_task(token, task_id)  -> (task: dict | None,  error: str | None)
"""

import os

import requests


def _resolve_api_base() -> str:
    """
    Where the backend lives, in order of precedence:

        1. .streamlit/secrets.toml  ->  API_BASE = "..."
        2. the API_BASE environment variable
        3. the localhost default below

    st.secrets raises if no secrets file exists, which is the normal case for a
    fresh clone, so the lookup is guarded. Importing streamlit lazily also keeps
    this module usable from a plain script or a test with no Streamlit runtime.
    """
    try:
        import streamlit as st

        configured = st.secrets.get("API_BASE")
        if configured:
            return str(configured).rstrip("/")
    except Exception:
        # No secrets file, no streamlit, or no API_BASE key - fall through.
        pass

    # `or` rather than a getenv default: Streamlit copies top-level secrets into
    # the environment, so a blank API_BASE in secrets.toml arrives here as an
    # empty string rather than as an absent variable.
    return (os.getenv("API_BASE") or "http://localhost:8000").rstrip("/")


API_BASE = _resolve_api_base()

# Seconds to wait before giving up on the backend. Keeps the Streamlit UI
# responsive instead of hanging on a dead server.
TIMEOUT = 10

# Returned verbatim on any 401 so app.py can recognise an expired session and
# log the user out, instead of having to pattern-match on error text.
UNAUTHORIZED = "Session expired or invalid credentials. Please log in again."


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _auth_headers(token: str) -> dict:
    """Build the Authorization header used by every protected endpoint."""
    return {"Authorization": f"Bearer {token}"}


def _error_message(response) -> str:
    """
    Turn a failed response into a readable message.

    FastAPI normally returns {"detail": "..."} on an error, but the body may
    also be a validation-error list or not be JSON at all, so every shape is
    handled defensively.
    """
    try:
        payload = response.json()
    except ValueError:
        payload = None

    detail = None
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message")
    elif isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            detail = first.get("msg")

    if isinstance(detail, list):  # FastAPI 422 validation errors
        parts = [d.get("msg", str(d)) if isinstance(d, dict) else str(d) for d in detail]
        detail = "; ".join(parts)

    if not detail:
        detail = (response.text or "").strip()[:200] or response.reason or "Unknown error"

    return f"HTTP {response.status_code}: {detail}"


def _request(method: str, path: str, token: str = None, json_body: dict = None):
    """
    Shared request helper used by every function in this module.

    Handles, in one place:
        * building the URL and the Authorization header
        * network failures (connection refused, timeout, bad URL)
        * non-2xx status codes (checked BEFORE the body is used)
        * responses that are not valid JSON

    Returns ``(parsed_json, None)`` or ``(None, error_message)``.
    """
    url = f"{API_BASE}{path}"
    headers = _auth_headers(token) if token else {}

    try:
        response = requests.request(
            method, url, headers=headers, json=json_body, timeout=TIMEOUT
        )
    except requests.exceptions.ConnectionError:
        return None, (
            f"Cannot reach the API at {API_BASE}. "
            "Is the backend running? Tick 'Use Mock Data' to work offline."
        )
    except requests.exceptions.Timeout:
        return None, f"The API did not respond within {TIMEOUT} seconds."
    except requests.exceptions.RequestException as exc:
        return None, f"Request failed: {exc}"

    # Check the status code before touching the body.
    if not response.ok:
        if response.status_code == 401:
            return None, UNAUTHORIZED
        return None, _error_message(response)

    if response.status_code == 204 or not (response.text or "").strip():
        return {}, None

    try:
        return response.json(), None
    except ValueError:
        return None, "The API returned a response that was not valid JSON."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def login(username: str, password: str):
    """
    POST /auth/token with username and password.

    Returns ``(access_token, None)`` on success, or ``(None, error)`` on
    failure - including when the server responds 200 but omits the token.
    """
    # A username of spaces is truthy, so strip before checking. The password
    # is checked but never stripped - leading/trailing spaces may be genuine.
    username = (username or "").strip()
    if not username or not (password or "").strip():
        return None, "Username and password are both required."

    data, error = _request(
        "POST", "/auth/token", json_body={"username": username, "password": password}
    )
    if error:
        return None, error

    if not isinstance(data, dict):
        return None, "Unexpected login response from the API."

    token = data.get("access_token")
    if not token:
        return None, "Login succeeded but no access_token was returned."

    return token, None


def get_tasks(token: str):
    """
    GET /tasks with a Bearer token.

    Returns ``(list_of_tasks, None)`` on success or ``(None, error_message)``
    on failure. One in-between case exists: if the API returns a list that
    contains items which are not task objects, the good tasks are returned
    *together with* a message describing what was skipped - i.e.
    ``(tasks, message)``. Callers should therefore treat ``data is None`` as
    the failure signal, not ``error is not None``.
    """
    if not token:
        return None, "No authentication token available. Please log in."

    data, error = _request("GET", "/tasks", token=token)
    if error:
        return None, error

    # Accept either a bare list or {"tasks": [...]}.
    if isinstance(data, dict):
        data = data.get("tasks", data.get("items"))

    if not isinstance(data, list):
        return None, "Unexpected task list format returned by the API."

    # Drop anything that is not a task object. Without this a payload such as
    # ["task one", 42] reaches the UI and crashes it on the first .get() call.
    tasks = [item for item in data if isinstance(item, dict)]
    if len(tasks) != len(data):
        skipped = len(data) - len(tasks)
        return tasks, f"Ignored {skipped} malformed item(s) returned by the API."

    return tasks, None


def create_task(token: str, title: str):
    """
    POST /tasks with a Bearer token and the JSON body ``{"title": title}``.

    Returns ``(new_task_dict, None)`` or ``(None, error_message)``. The title
    that comes back is compared with the title that was sent, so a silent
    mismatch is reported instead of being displayed as a success.
    """
    if not token:
        return None, "No authentication token available. Please log in."

    title = (title or "").strip()
    if not title:
        return None, "Task title cannot be empty."

    data, error = _request("POST", "/tasks", token=token, json_body={"title": title})
    if error:
        return None, error

    if not isinstance(data, dict) or "id" not in data:
        return None, "The API did not return the created task."

    returned_title = str(data.get("title", "")).strip()
    if returned_title != title:
        return None, (
            f"The API stored a different title than the one sent "
            f"(sent '{title}', received '{returned_title}')."
        )

    return data, None


def complete_task(token: str, task_id: int):
    """
    PATCH /tasks/{task_id}/complete with a Bearer token.

    Returns ``(updated_task_dict, None)`` or ``(None, error_message)``. The
    returned task is verified to actually be marked done before success is
    reported.
    """
    if not token:
        return None, "No authentication token available. Please log in."

    if task_id is None:
        return None, "A task id is required."

    data, error = _request("PATCH", f"/tasks/{task_id}/complete", token=token)
    if error:
        return None, error

    if not isinstance(data, dict) or "id" not in data:
        return None, "The API did not return the updated task."

    if str(data.get("id")) != str(task_id):
        return None, (
            f"The API returned a different task than the one requested "
            f"(asked for #{task_id}, received #{data.get('id')})."
        )

    if not data.get("done"):
        return None, f"Task #{task_id} was not marked as done by the API."

    return data, None
