"""
L11 — Streamlit + FastAPI: Frontend
================================================
Run with (after starting the backend):
    streamlit run frontend.py

A Streamlit frontend for the task API.

Features:
    1. Login *and* registration forms (token stored in session state)
    2. Sidebar showing the logged-in user + logout button
    3. Metrics row (total / done / pending)
    4. Filter dropdown: All / Pending / Done
    5. Per-task Complete, Reopen and Delete buttons
    6. Add task form
    7. Error handling for connection errors, timeouts and expired sessions
    8. Auth gate: login screen without a token, app with one

Configuration:
    TASK_API_BASE — API base URL (default: http://localhost:8000)
"""

import os

import streamlit as st
import requests

API_BASE = os.getenv("TASK_API_BASE", "http://localhost:8000").rstrip("/")

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Task Manager", page_icon="✅", layout="centered")

# ── Session state ──────────────────────────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "filter" not in st.session_state:
    st.session_state.filter = "All"


# ══════════════════════════════════════════════════════════════════════════
# CENTRALISED API CLIENT
# ══════════════════════════════════════════════════════════════════════════
def api_call(method: str, path: str, **kwargs):
    """Make a request to the API.

    Returns (data, error): exactly one of the two is None. Every network call
    in this app goes through here, so auth headers, status-code checks and
    connection failures are handled in one place.
    """
    headers = dict(kwargs.pop("headers", {}) or {})
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        response = requests.request(
            method,
            API_BASE + path,
            headers=headers,
            timeout=10,
            **kwargs,
        )
    except requests.exceptions.ConnectionError:
        return None, (
            f"Cannot connect to the API at {API_BASE}. Is the backend running? "
            "Start it with: uvicorn backend:app --reload --port 8000"
        )
    except requests.exceptions.Timeout:
        return None, "The API took too long to respond. Please try again."
    except requests.exceptions.RequestException as exc:
        return None, f"Request failed: {exc}"

    if response.status_code == 401:
        # Missing, expired or invalid token — force a fresh login.
        st.session_state.token = None
        st.session_state.username = None
        return None, "Session expired or invalid credentials. Please log in again."

    if not response.ok:
        return None, f"API error {response.status_code}: {api_detail(response)}"

    if response.status_code == 204 or not response.content:
        return {}, None

    try:
        return response.json(), None
    except ValueError:
        return None, "The API returned a response that was not valid JSON."


def api_detail(response) -> str:
    """Pull FastAPI's `detail` out of an error body, falling back to raw text."""
    try:
        body = response.json()
    except ValueError:
        return response.text
    detail = body.get("detail", body) if isinstance(body, dict) else body
    if isinstance(detail, list):  # 422 validation errors
        return "; ".join(item.get("msg", str(item)) for item in detail)
    return str(detail)


def store_session(data: dict) -> None:
    st.session_state.token = data["access_token"]
    st.session_state.username = data["username"]


# ══════════════════════════════════════════════════════════════════════════
# AUTH GATE
# ══════════════════════════════════════════════════════════════════════════
if st.session_state.token is None:
    st.title("✅ Task Manager")
    st.caption("Log in or create an account. Demo account: `demo` / `demo`")

    login_tab, register_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")

        if submitted:
            if not username or not password:
                st.error("Please enter both a username and a password.")
            else:
                data, error = api_call(
                    "POST",
                    "/auth/token",
                    json={"username": username, "password": password},
                )
                if error:
                    st.error(error)
                else:
                    store_session(data)
                    st.rerun()

    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("Choose a username")
            new_password = st.text_input("Choose a password", type="password")
            confirm = st.text_input("Confirm password", type="password")
            registered = st.form_submit_button("Create account")

        if registered:
            if not new_username or not new_password:
                st.error("Please fill in every field.")
            elif new_password != confirm:
                st.error("The two passwords do not match.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                data, error = api_call(
                    "POST",
                    "/auth/register",
                    json={"username": new_username, "password": new_password},
                )
                if error:
                    st.error(error)
                else:
                    store_session(data)
                    st.rerun()

    st.stop()


# ══════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("✅ Task Manager")
    st.divider()
    st.write(f"Logged in as **{st.session_state.username}**")
    st.caption(f"API: {API_BASE}")
    if st.button("Log out", use_container_width=True):
        st.session_state.token = None
        st.session_state.username = None
        st.rerun()

st.title("My Tasks")

# ── Load tasks ─────────────────────────────────────────────────────────────
tasks, error = api_call("GET", "/tasks")
if error:
    st.error(error)
    tasks = []

# ── Metrics ────────────────────────────────────────────────────────────────
total = len(tasks)
done = sum(1 for task in tasks if task["done"])
pending = total - done

col1, col2, col3 = st.columns(3)
col1.metric("Total", total)
col2.metric("Done", done)
col3.metric("Pending", pending)

st.divider()

# ── Add task form ──────────────────────────────────────────────────────────
with st.form("add_task_form", clear_on_submit=True):
    new_title = st.text_input("New task", placeholder="What needs doing?")
    add_clicked = st.form_submit_button("Add task")

if add_clicked:
    if not new_title.strip():
        st.error("Please enter a task title.")
    else:
        created, error = api_call("POST", "/tasks", json={"title": new_title})
        if error:
            st.error(error)
        # Verify what came back matches what was sent before celebrating.
        elif created.get("title") == new_title.strip() and created.get("done") is False:
            st.toast(f"Added: {created['title']}", icon="✅")
            st.rerun()
        else:
            st.warning(f"Task created, but the API returned unexpected data: {created}")

st.divider()

# ── Filter ─────────────────────────────────────────────────────────────────
choice = st.selectbox("Show", ["All", "Pending", "Done"], key="filter")
if choice == "Pending":
    visible = [task for task in tasks if not task["done"]]
elif choice == "Done":
    visible = [task for task in tasks if task["done"]]
else:
    visible = tasks

# ── Task list ──────────────────────────────────────────────────────────────
if not tasks:
    st.info("No tasks yet. Add your first one above.")
elif not visible:
    st.info(f"No {choice.lower()} tasks.")

for task in visible:
    title_col, status_col, action_col, delete_col = st.columns([4, 2, 2, 1])

    with title_col:
        if task["done"]:
            st.markdown(f"~~{task['title']}~~")
        else:
            st.markdown(task["title"])

    with status_col:
        if task["done"]:
            st.success("Done")
        else:
            st.warning("Pending")

    with action_col:
        if task["done"]:
            if st.button("Reopen", key=f"reopen_{task['id']}", use_container_width=True):
                updated, error = api_call("PATCH", f"/tasks/{task['id']}/uncomplete")
                if error:
                    st.error(error)
                elif updated.get("done") is False:
                    st.toast(f"Reopened: {task['title']}", icon="↩️")
                    st.rerun()
                else:
                    st.warning(f"The API did not reopen task {task['id']}.")
        else:
            if st.button("Complete", key=f"complete_{task['id']}", use_container_width=True):
                updated, error = api_call("PATCH", f"/tasks/{task['id']}/complete")
                if error:
                    st.error(error)
                elif updated.get("done") is True:
                    st.toast(f"Completed: {task['title']}", icon="🎉")
                    st.rerun()
                else:
                    st.warning(f"The API did not mark task {task['id']} as done.")

    with delete_col:
        if st.button("🗑️", key=f"delete_{task['id']}", help="Delete this task"):
            _, error = api_call("DELETE", f"/tasks/{task['id']}")
            if error:
                st.error(error)
            else:
                st.toast(f"Deleted: {task['title']}", icon="🗑️")
                st.rerun()
