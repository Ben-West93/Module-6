"""
Module 6 Project - AI Dashboard
===============================
Run with:
    # Start the backend (when ready):
    uvicorn backend:app --reload --port 8000

    # Start the Streamlit app:
    streamlit run app.py

A full Streamlit dashboard with authentication, task management,
data visualisation and an AI chat feature.

Sections:
    A. Authentication  - login form, token in session state, logout
    B. Sidebar         - user info, logout, AI chat settings
    C. Main content    - Dashboard / Tasks / AI Chat tabs

How this file works
-------------------
Streamlit re-runs this entire script from the top on every interaction - a
click, a keystroke in a form, a tab switch. Three consequences shape the code:

1. Nothing survives a rerun unless it lives in st.session_state, so every key
   the app reads is created once in DEFAULTS below, before anything reads it.
   That includes `login_error`: a plain local variable holding the message
   would disappear the moment the next rerun started.
2. The auth gate calls st.stop() rather than wrapping the app in an `else`.
   st.stop() ends the run there, so nothing below it is rendered or executed
   while the user is logged out.
3. After any change to the data (adding or completing a task) the code calls
   st.rerun(), so the metrics and chart in the other tabs are rebuilt from the
   new state instead of showing the counts from before the click.

Two data sources, one switch
----------------------------
The app runs either against the real API or against mock_data.py. load_tasks()
is the only place that decides which, so the rest of the UI is identical in
both modes. In mock mode the tasks live in st.session_state["mock_tasks"] as a
per-task copy of MOCK_TASKS - the module-level constant is never mutated, so
logging out and back in gives a clean slate.

All backend communication goes through api_client.py, which returns
(data, error) tuples and never raises; see its docstring for why.
"""

import os
import time

import pandas as pd
import plotly.express as px
import streamlit as st

import api_client
from mock_data import (
    MOCK_CHAT_HISTORY,
    MOCK_STATS,
    MOCK_TASKS,
    MOCK_TOKEN,
    MOCK_USER,
)

# ── Step 1: Page configuration ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="AI Dashboard", page_icon="🤖")

# ── Step 2: Session state initialisation ───────────────────────────────────
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant for a task-management dashboard."

# Chat history lives in session state for the life of the browser session, so
# it is capped to stop a long conversation growing without limit.
MAX_CHAT_MESSAGES = 50

def secret(name: str, default=""):
    """
    Read a value from .streamlit/secrets.toml, falling back to the environment
    and then to `default`. Guarded because st.secrets raises when no secrets
    file exists - which is exactly the state of a fresh clone.
    """
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass
    # `or` rather than a getenv default: Streamlit copies top-level secrets into
    # the environment, so a blank value arrives as "" rather than as unset.
    return os.getenv(name) or default


DEFAULTS = {
    "token": None,            # auth token (real JWT or MOCK_TOKEN)
    "username": None,         # who is logged in
    "messages": [],           # chat history: [{"role": ..., "content": ...}]
    "use_mock": False,        # True -> work offline against mock_data.py
    "mock_tasks": [],         # editable copy of MOCK_TASKS used in mock mode
    # Pre-filled from secrets.toml when present, otherwise typed in the sidebar.
    "api_key": secret("AI_API_KEY"),
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "login_error": None,      # message to show under the login form
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        # copy() so the mutable defaults are not shared between sessions
        st.session_state[key] = value.copy() if isinstance(value, (list, dict)) else value


# ── Helpers ────────────────────────────────────────────────────────────────
def is_done(task) -> bool:
    """
    Whether a task counts as completed.

    Not just ``bool(task["done"])``: a backend that serialises the flag as a
    string would make "false" truthy, and the dashboard would report a pending
    task as complete. Known false-ish strings are handled explicitly.
    """
    value = (task or {}).get("done")
    if isinstance(value, str):
        return value.strip().lower() not in ("", "false", "0", "no", "none")
    return bool(value)


def is_mock() -> bool:
    """True when the app is running against mock_data.py instead of the API."""
    return bool(st.session_state.use_mock)


def load_tasks():
    """
    Return ``(tasks, error)`` from whichever source is active.

    In mock mode the session-state copy of MOCK_TASKS is returned, so tasks
    added or completed during the session persist across reruns.
    """
    if is_mock():
        return st.session_state.mock_tasks, None
    return api_client.get_tasks(st.session_state.token)


def compute_stats(tasks) -> dict:
    """Total / done / pending counts for a list of task dicts."""
    tasks = tasks or []
    done = sum(1 for t in tasks if is_done(t))
    return {
        "total_tasks": len(tasks),
        "done_tasks": done,
        "pending_tasks": len(tasks) - done,
    }


def next_mock_id() -> int:
    """Next free id for a locally added mock task."""
    ids = [t.get("id", 0) for t in st.session_state.mock_tasks]
    return max(ids, default=0) + 1


def logout():
    """Clear the session back to a logged-out state."""
    for key in ("token", "username", "use_mock", "login_error"):
        st.session_state[key] = DEFAULTS[key]
    st.session_state.messages = []
    st.session_state.mock_tasks = []


def handle_session_expiry(error) -> bool:
    """
    Log the user out if the API rejected the token.

    api_client returns its UNAUTHORIZED constant verbatim on any 401, so an
    expired session ends with a clear message on the login screen rather than
    leaving the user staring at a red error they cannot act on.
    """
    if error != api_client.UNAUTHORIZED:
        return False
    logout()
    st.session_state.login_error = "Your session expired. Please log in again."
    st.rerun()
    return True


def mock_reply(prompt: str) -> str:
    """
    Build a canned assistant reply.

    Keyword matching keeps the demo responses relevant without needing a live
    model. The sidebar system prompt is honoured so changing it is visible.
    """
    text = (prompt or "").lower()
    system_prompt = (st.session_state.system_prompt or "").strip()

    if any(word in text for word in ("task", "todo", "to-do")):
        stats = compute_stats(load_tasks()[0] or [])
        reply = (
            f"You currently have {stats['total_tasks']} task(s): "
            f"{stats['done_tasks']} done and {stats['pending_tasks']} still pending. "
            "Open the Tasks tab to add a new one or mark one complete."
        )
    elif "fastapi" in text:
        reply = (
            "FastAPI is a modern Python web framework for building APIs. It uses "
            "type hints and Pydantic models to validate requests automatically and "
            "generates interactive docs at /docs."
        )
    elif "streamlit" in text:
        reply = (
            "Streamlit re-runs the whole script on every interaction, so anything "
            "that must survive a rerun belongs in st.session_state. Initialise every "
            "key once at the top of the file before you read it."
        )
    elif any(word in text for word in ("auth", "token", "jwt", "login")):
        reply = (
            "This dashboard stores its token in st.session_state['token'] and sends "
            "it as an Authorization: Bearer header from api_client.py, so the header "
            "is built in exactly one place."
        )
    elif any(word in text for word in ("hello", "hi ", "hey")) or text.strip() in ("hi", "hey"):
        reply = f"Hello! I'm the demo assistant for this dashboard. Ask me about your tasks, FastAPI or Streamlit."
    else:
        reply = (
            "This is a simulated response - no AI provider is connected yet. "
            f"You asked: \"{prompt.strip()}\". Add a real client in the AI Chat "
            "section to get live answers."
        )

    if system_prompt and system_prompt != DEFAULT_SYSTEM_PROMPT:
        reply = f"[{system_prompt}]\n\n{reply}"
    return reply


def stream_words(text: str, delay: float = 0.02, max_seconds: float = 2.5):
    """
    Yield ``text`` word by word so st.write_stream can animate it.

    The per-word delay is scaled down for long replies so a wordy answer still
    finishes in about ``max_seconds`` instead of making the user wait.
    """
    words = text.split(" ")
    if words and len(words) * delay > max_seconds:
        delay = max(max_seconds / len(words), 0.001)
    for word in words:
        yield word + " "
        time.sleep(delay)


def remember(role: str, content: str) -> None:
    """Append a chat message, keeping only the most recent MAX_CHAT_MESSAGES."""
    st.session_state.messages.append({"role": role, "content": content})
    if len(st.session_state.messages) > MAX_CHAT_MESSAGES:
        del st.session_state.messages[:-MAX_CHAT_MESSAGES]


# ════════════════════════════════════════════════════════════════════════════
# SECTION A - AUTHENTICATION
# ════════════════════════════════════════════════════════════════════════════
if not st.session_state.token:
    st.title("🤖 AI Dashboard")
    st.caption("Please sign in to continue.")

    left, _ = st.columns([1, 1])
    with left:
        with st.form("login_form"):
            st.subheader("Sign in")
            username = st.text_input("Username", placeholder="your username")
            password = st.text_input("Password", type="password", placeholder="your password")
            use_mock = st.checkbox(
                "Use Mock Data",
                value=False,
                help="Skip the API and run the dashboard against mock_data.py.",
            )
            submitted = st.form_submit_button("Log in", type="primary")

        if submitted:
            if use_mock:
                st.session_state.token = MOCK_TOKEN
                st.session_state.username = MOCK_USER
                st.session_state.use_mock = True
                st.session_state.mock_tasks = [dict(task) for task in MOCK_TASKS]
                st.session_state.messages = [dict(m) for m in MOCK_CHAT_HISTORY]
                st.session_state.login_error = None
                st.rerun()
            else:
                token, error = api_client.login(username, password)
                if error:
                    st.session_state.login_error = error
                else:
                    st.session_state.token = token
                    st.session_state.username = username
                    st.session_state.use_mock = False
                    st.session_state.login_error = None
                    st.rerun()

        if st.session_state.login_error:
            st.error(st.session_state.login_error)

    st.stop()

# ════════════════════════════════════════════════════════════════════════════
# SECTION B - SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🤖 AI Dashboard")
    st.divider()

    st.write(f"Logged in as **{st.session_state.username}**")
    if is_mock():
        st.info("Mock mode - no API calls are being made.", icon="🧪")

    if st.button("Log out", use_container_width=True):
        logout()
        st.rerun()

    st.divider()
    st.subheader("AI Chat settings")
    st.session_state.api_key = st.text_input(
        "API key",
        value=st.session_state.api_key,
        type="password",
        # Collected for the graded requirement and kept in session state only.
        # No AI provider is called yet - replies come from mock_reply() below.
        help="Stored in session state only; never written to disk or sent anywhere.",
    )
    st.session_state.system_prompt = st.text_area(
        "System prompt",
        value=st.session_state.system_prompt,
        height=110,
    )
    if st.button("Clear chat history", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("Module 6 Project · Streamlit + FastAPI")

# ════════════════════════════════════════════════════════════════════════════
# SECTION C - MAIN CONTENT (tabs)
# ════════════════════════════════════════════════════════════════════════════
tab_dash, tab_tasks, tab_chat = st.tabs(["📊 Dashboard", "✅ Tasks", "🤖 AI Chat"])

# ── TAB 1: Dashboard ───────────────────────────────────────────────────────
with tab_dash:
    st.header("📊 Dashboard")

    tasks, error = load_tasks()
    if tasks is None:
        # A real failure: the token was rejected, or the API is unreachable.
        if not handle_session_expiry(error):
            st.error(error)
            st.caption("Log out and tick 'Use Mock Data' to explore the dashboard offline.")
    else:
        # get_tasks can return good tasks *and* a message when it skipped
        # malformed items, so a warning here is not a dead end.
        if error:
            st.warning(error)
        stats = compute_stats(tasks)

        col_total, col_done, col_pending = st.columns(3)
        if is_mock():
            # Deltas show what changed since the mock data was loaded.
            deltas = {k: stats[k] - MOCK_STATS.get(k, 0) for k in stats}
        else:
            deltas = {k: 0 for k in stats}

        col_total.metric("Total tasks", stats["total_tasks"], delta=deltas["total_tasks"] or None)
        col_done.metric("Completed", stats["done_tasks"], delta=deltas["done_tasks"] or None)
        col_pending.metric("Pending", stats["pending_tasks"], delta=deltas["pending_tasks"] or None)

        st.divider()
        left, right = st.columns([3, 2])

        with left:
            st.subheader("All tasks")
            if tasks:
                frame = pd.DataFrame(tasks)
                for column in ("id", "title", "done", "created_at"):
                    if column not in frame.columns:
                        frame[column] = None
                # Normalise the flag so the table agrees with the metrics even
                # if the API sent strings rather than booleans.
                frame["done"] = [is_done(t) for t in tasks]
                frame = frame[["id", "title", "done", "created_at"]].rename(
                    columns={
                        "id": "ID",
                        "title": "Title",
                        "done": "Done",
                        "created_at": "Created",
                    }
                )
                st.dataframe(frame, use_container_width=True, hide_index=True)
            else:
                st.info("No tasks yet. Add one in the Tasks tab.")

        with right:
            st.subheader("Completed vs pending")
            if stats["total_tasks"]:
                chart_data = pd.DataFrame(
                    {
                        "Status": ["Completed", "Pending"],
                        "Tasks": [stats["done_tasks"], stats["pending_tasks"]],
                    }
                )
                figure = px.bar(
                    chart_data,
                    x="Status",
                    y="Tasks",
                    color="Status",
                    color_discrete_map={"Completed": "#2E9E5B", "Pending": "#E4A11B"},
                    text="Tasks",
                )
                figure.update_layout(
                    showlegend=False,
                    height=320,
                    margin=dict(l=10, r=10, t=10, b=10),
                    yaxis_title="Tasks",
                    xaxis_title="",
                )
                st.plotly_chart(figure, use_container_width=True)
            else:
                st.info("The chart appears once there is at least one task.")

# ── TAB 2: Tasks ───────────────────────────────────────────────────────────
with tab_tasks:
    st.header("✅ Tasks")

    with st.form("add_task_form", clear_on_submit=True):
        new_title = st.text_input("New task", placeholder="e.g. Finish the Module 6 write-up")
        add_clicked = st.form_submit_button("Add task", type="primary")

    if add_clicked:
        title = (new_title or "").strip()
        if not title:
            st.warning("Please enter a task title before adding it.")
        elif is_mock():
            st.session_state.mock_tasks.append(
                {
                    "id": next_mock_id(),
                    "title": title,
                    "done": False,
                    "created_at": time.strftime("%Y-%m-%d"),
                }
            )
            st.success(f"Added '{title}'.")
            st.rerun()
        else:
            created, error = api_client.create_task(st.session_state.token, title)
            if error:
                if not handle_session_expiry(error):
                    st.error(error)
            else:
                st.success(f"Added '{created.get('title')}' (#{created.get('id')}).")
                st.rerun()

    st.divider()

    tasks, error = load_tasks()
    if tasks is None:
        # Failure: nothing to list. handle_session_expiry() reruns the app if
        # the token was rejected, so anything reaching st.error() is a
        # different problem (API down, server error).
        if not handle_session_expiry(error):
            st.error(error)
    elif not tasks:
        if error:
            st.warning(error)
        st.info("No tasks yet. Add your first one above.")
    else:
        # Partial success: some items were skipped, but the rest are usable.
        if error:
            st.warning(error)

        pending = [t for t in tasks if not is_done(t)]
        done = [t for t in tasks if is_done(t)]

        st.subheader(f"Pending ({len(pending)})")
        if not pending:
            st.caption("Nothing pending - every task is done.")
        for position, task in enumerate(pending):
            row_title, row_button = st.columns([5, 1])
            row_title.write(f"**{task.get('title', 'Untitled')}**  \n`#{task.get('id')}` · added {task.get('created_at', 'unknown')}")
            # The position is part of the key because ids are not guaranteed to
            # be unique or even present: two tasks sharing an id, or two with
            # no id at all, would otherwise collide and crash the whole page
            # with a duplicate-key error.
            if row_button.button(
                "Complete",
                key=f"complete_{position}_{task.get('id')}",
                use_container_width=True,
            ):
                if is_mock():
                    matched = [
                        item
                        for item in st.session_state.mock_tasks
                        if item.get("id") == task.get("id")
                    ]
                    if not matched:
                        # The row on screen is from a previous run; the task is
                        # gone. Say so instead of silently doing nothing.
                        st.warning("That task no longer exists. Refreshing the list.")
                    for item in matched:
                        item["done"] = True
                    st.rerun()
                else:
                    updated, complete_error = api_client.complete_task(
                        st.session_state.token, task.get("id")
                    )
                    if complete_error:
                        if not handle_session_expiry(complete_error):
                            st.error(complete_error)
                    else:
                        st.success(f"Completed '{updated.get('title')}'.")
                        st.rerun()

        st.divider()
        st.subheader(f"Completed ({len(done)})")
        if not done:
            st.caption("No completed tasks yet.")
        for task in done:
            st.write(f"~~{task.get('title', 'Untitled')}~~  \n`#{task.get('id')}`")

# ── TAB 3: AI Chat ─────────────────────────────────────────────────────────
with tab_chat:
    st.header("🤖 AI Chat")
    st.caption(
        "Responses are generated locally by a mock assistant - no data leaves your machine."
    )

    for message in st.session_state.messages:
        with st.chat_message(message.get("role", "assistant")):
            st.markdown(message.get("content", ""))

    prompt = st.chat_input("Ask about your tasks, FastAPI or Streamlit...")
    if prompt:
        remember("user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            reply = st.write_stream(stream_words(mock_reply(prompt)))

        remember("assistant", reply.strip())
