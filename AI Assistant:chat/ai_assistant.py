"""
L12 — AI Chat Interface
=======================
Run with:
    streamlit run ai_assistant.py

A Streamlit chat interface with streaming responses.

Core features (from the assignment)
    1. Sidebar: API key input (password), system prompt, model selector,
       Clear button, live message count
    2. Chat history kept in st.session_state as a list of
       {"role": ..., "content": ...} dicts
    3. Full history re-rendered every run with st.chat_message()
    4. st.chat_input() for new user messages
    5. mock_stream() — a keyword-driven generator, so the app works with
       no API key at all
    6. st.write_stream() renders the generator token by token and returns
       the assembled string

Extras
    - Copy and Regenerate controls under each assistant reply
    - Token + estimated cost counter in the sidebar
    - Configurable history window (how many turns get sent to the model)
    - Avatars and timestamps on every message
    - Stop button that halts a response mid-stream and keeps the partial text

Why history "persists"
    Streamlit re-runs this whole script top-to-bottom on every interaction.
    Nothing on screen survives a re-run; only st.session_state does. The
    render loop below redraws every stored message from scratch, which is
    what makes the conversation look continuous.
"""

import time
from datetime import datetime

import streamlit as st

# ── Constants ──────────────────────────────────────────────────────────────
MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
DEFAULT_SYSTEM_PROMPT = "You are a helpful, concise assistant."
STREAM_DELAY = 0.04  # seconds between mock tokens

USER_AVATAR = "🧑‍💻"
ASSISTANT_AVATAR = "🤖"
AVATARS = {"user": USER_AVATAR, "assistant": ASSISTANT_AVATAR}

# USD per 1M tokens (input, output). Published list prices; estimates only.
#
# NOTE: the sidebar figure prices the conversation as it currently stands —
# each message counted once. Real billing is higher, because every turn re-sends
# the whole history window as input tokens, so a long chat pays for the same
# early messages again and again. Read the number as "how big is this
# conversation", not "what have I spent".
PRICING = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-3.5-turbo": (0.50, 1.50),
}

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Chat Assistant",
    page_icon="💬",
    layout="centered",
)

# ── Session state ──────────────────────────────────────────────────────────
# Every key is initialised before it is read, so the first run is safe.
DEFAULT_STATE = {
    "messages": [],        # [{"role", "content", "time"}, ...]
    "api_key": "",
    "streaming": False,    # True while a reply is being generated
    "partial": "",         # text streamed so far this turn
    "stop": False,         # set by the Stop button
    "regenerate": False,   # set by the Regenerate button
    "notice": "",          # sticky warning (e.g. API fallback), survives re-runs
}
for key, default in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Recover from an interrupted stream ─────────────────────────────────────
# Pressing Stop (or refreshing) re-runs the script and kills the generator
# mid-flight, so the assistant turn was never appended. Salvage whatever was
# streamed instead of losing the turn.
if st.session_state.streaming:
    salvaged = st.session_state.partial.strip()
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": (salvaged + "\n\n_⏹️ stopped_") if salvaged else "_⏹️ stopped_",
            "time": datetime.now().strftime("%H:%M"),
        }
    )
    st.session_state.streaming = False
    st.session_state.partial = ""
    st.session_state.stop = False


# ── Token counting ─────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_encoder():
    """Load tiktoken once, or return None so we fall back to an estimate."""
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def count_tokens(text: str) -> int:
    """Token count for a string; ~4 chars per token if tiktoken is absent."""
    text = text or ""
    encoder = get_encoder()
    if encoder is None:
        return max(1, round(len(text) / 4)) if text else 0
    try:
        return len(encoder.encode(text))
    except Exception:
        return max(1, round(len(text) / 4)) if text else 0


def usage_summary(system_prompt: str, model: str) -> dict:
    """Token totals and a rough USD cost for the conversation so far."""
    prompt_tokens = count_tokens(system_prompt)
    completion_tokens = 0
    for message in st.session_state.messages:
        tokens = count_tokens(message.get("content", ""))
        if message.get("role") == "assistant":
            completion_tokens += tokens
        else:
            prompt_tokens += tokens

    in_rate, out_rate = PRICING.get(model, (0.0, 0.0))
    cost = (prompt_tokens * in_rate + completion_tokens * out_rate) / 1_000_000
    return {
        "prompt": prompt_tokens,
        "completion": completion_tokens,
        "total": prompt_tokens + completion_tokens,
        "cost": cost,
        "exact": get_encoder() is not None,
    }


# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")

    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=st.session_state.api_key,
        help="Leave blank to use built-in mock responses.",
        placeholder="sk-...",
    )
    st.session_state.api_key = (api_key or "").strip()

    system_prompt = st.text_area(
        "System prompt",
        value=DEFAULT_SYSTEM_PROMPT,
        height=100,
        help="Sets the assistant's behaviour. Used when an API key is supplied.",
    )

    model = st.selectbox("Model", MODELS, index=0)

    history_turns = st.slider(
        "History window (turns sent)",
        min_value=1,
        max_value=20,
        value=10,
        help="Only the most recent N exchanges are sent to the model, which "
             "keeps long conversations from blowing up context and cost.",
    )

    st.divider()

    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.session_state.partial = ""
        st.session_state.streaming = False
        st.session_state.regenerate = False
        st.session_state.notice = ""
        st.rerun()

    # Both slots are filled at the bottom of the script, after this run's
    # messages have been appended, so the numbers are never a turn stale.
    message_count_slot = st.empty()
    usage_slot = st.empty()

# ── Page title ─────────────────────────────────────────────────────────────
st.title("💬 AI Chat Assistant")

if not st.session_state.api_key:
    st.info(
        "No API key set — running in **mock mode**. "
        "Add an OpenAI key in the sidebar to talk to a real model.",
        icon="ℹ️",
    )

# Filled at the bottom of the script. Warnings raised mid-run would be wiped
# by the re-run that ends a turn, so they live in session_state instead.
notice_slot = st.empty()


# ── Mock response generator ────────────────────────────────────────────────
# NOTE: lookup is a plain substring scan in insertion order, first match wins,
# so ORDER MATTERS here. "fastapi" has to sit above "api" or every FastAPI
# question would get the generic API answer. The short keys stay greedy even
# so: "hi" matches inside "what is this", and "error" inside "terror". That is
# acceptable for canned demo answers — but if you add a key, put the specific
# term above the general one and avoid anything shorter than three characters.
MOCK_RESPONSES = {
    "python": (
        "Python is a high-level, readable language that leans on indentation "
        "instead of braces. It ships with a deep standard library, so most "
        "small jobs need no third-party packages at all."
    ),
    "streamlit": (
        "Streamlit turns a plain Python script into a web app. It re-runs the "
        "whole script on every interaction, and anything you want to survive "
        "that re-run has to live in st.session_state."
    ),
    "fastapi": (
        "FastAPI is an async Python web framework built on type hints. It "
        "validates requests with Pydantic and generates interactive OpenAPI "
        "docs at /docs for free."
    ),
    "sql": (
        "SQL is the query language for relational databases. Start with "
        "SELECT, WHERE and JOIN, then add indexes once you can measure which "
        "queries are actually slow."
    ),
    "api": (
        "An API is a contract between two programs. Check the status code "
        "before you touch the body, and wrap every call in try/except so a "
        "dropped connection cannot take your app down."
    ),
    "error": (
        "Read the traceback from the bottom up: the last line names the "
        "exception, and the frame just above it points at your own code. "
        "Reproduce it in the smallest script you can before you start fixing."
    ),
    "hello": (
        "Hello! I'm running in mock mode, so my answers come from a small "
        "keyword table rather than a real model. Try asking about Python, "
        "Streamlit, FastAPI, SQL, APIs or errors."
    ),
    "hi": (
        "Hi there! Ask me about Python, Streamlit, FastAPI, SQL, APIs or "
        "debugging errors and I'll give you a canned answer."
    ),
    "help": (
        "I can talk about Python, Streamlit, FastAPI, SQL, APIs and debugging. "
        "Add an OpenAI key in the sidebar if you want real answers instead of "
        "these scripted ones."
    ),
}

DEFAULT_MOCK_RESPONSE = (
    "That's a good question. I'm running in mock mode right now, so I only "
    "have scripted answers for a few keywords — try Python, Streamlit, "
    "FastAPI, SQL, APIs or errors, or add an OpenAI API key in the sidebar "
    "for real responses."
)


def mock_response_text(user_message: str) -> str:
    """Pick a canned answer by keyword. Always returns a non-empty string."""
    text = (user_message or "").lower()
    for keyword, response in MOCK_RESPONSES.items():
        if keyword in text:
            return response
    return DEFAULT_MOCK_RESPONSE


def mock_stream(user_message: str):
    """Yield a canned response one word at a time to fake streaming."""
    response = mock_response_text(user_message)
    for word in response.split():
        yield word + " "
        time.sleep(STREAM_DELAY)


# ── Real model responses (used only when an API key is supplied) ───────────
def trimmed_history(turns: int) -> list:
    """The last `turns` exchanges, as plain role/content dicts for the API."""
    window = st.session_state.messages[-(turns * 2):] if turns else []
    return [{"role": m["role"], "content": m["content"]} for m in window]


def openai_stream(api_key: str, model: str, system_prompt: str, history: list):
    """
    Open a streaming chat completion and yield text chunks.

    Raises on failure (missing package, bad key, network error) so the caller
    can fall back to mock mode instead of crashing the app.
    """
    from openai import OpenAI  # imported lazily: the app runs without it

    client = OpenAI(api_key=api_key)
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}] + history,
        stream=True,
    )

    def chunks():
        for chunk in stream:
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            piece = getattr(choices[0].delta, "content", None)
            if piece:
                yield piece

    return chunks()


def response_generator(prompt: str, model: str, system_prompt: str, turns: int):
    """Return a generator of response text, preferring the real API."""
    if not st.session_state.api_key:
        return mock_stream(prompt)

    try:
        generator = openai_stream(
            api_key=st.session_state.api_key,
            model=model,
            system_prompt=system_prompt,
            history=trimmed_history(turns),
        )
        st.session_state.notice = ""
        return generator
    except ImportError:
        st.session_state.notice = (
            "The `openai` package isn't installed — falling back to mock mode. "
            "Install it with `pip install openai`."
        )
    except Exception as exc:  # bad key, rate limit, network, etc.
        st.session_state.notice = (
            f"API request failed ({exc}) — falling back to mock mode."
        )

    return mock_stream(prompt)


def tracked(generator):
    """Record each chunk in session_state so a stopped stream keeps its text."""
    # See the note on answer() below: this is what makes Stop non-destructive.
    for chunk in generator:
        st.session_state.partial += str(chunk)
        yield chunk


def answer(prompt: str) -> None:
    """
    Stream one assistant reply into its own bubble and store it.

    NOTE on stopping: Streamlit has no way to cancel a running generator.
    Clicking Stop just queues a re-run, which tears down this script at the
    next Streamlit call and abandons the generator mid-iteration — the code
    below this point never executes, so the reply is never appended. That is
    why tracked() mirrors every chunk into session_state as it arrives: the
    recovery block at the top of the script picks up that partial text on the
    next run and stores the turn. Without it, Stop would silently lose the
    whole response. The same mechanism covers a browser refresh mid-stream.
    """
    st.session_state.streaming = True
    st.session_state.partial = ""
    st.session_state.stop = False

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        stop_slot = st.empty()
        # Clicking this triggers a re-run, which kills the generator; the
        # recovery block at the top of the script saves the partial text.
        stop_slot.button("⏹️ Stop", key=f"stop_{len(st.session_state.messages)}")

        try:
            generator = response_generator(prompt, model, system_prompt, history_turns)
            full_response = st.write_stream(tracked(generator))
        except Exception as exc:  # a stream that dies mid-flight
            full_response = f"⚠️ Something went wrong while responding: {exc}"
            st.markdown(full_response)

        stop_slot.empty()

    # st.write_stream returns a str for text chunks, but a list if the
    # generator ever yields non-text — normalise before storing.
    if isinstance(full_response, list):
        full_response = "".join(str(part) for part in full_response)
    full_response = (full_response or "").strip()

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": full_response,
            "time": datetime.now().strftime("%H:%M"),
        }
    )
    st.session_state.streaming = False
    st.session_state.partial = ""


# ══════════════════════════════════════════════════════════════════════════
# RENDER CHAT HISTORY
# ──────────────────────────────────────────────────────────────────────────
# This loop redraws ALL stored messages on every re-run. The messages only
# appear to persist because they live in session_state, not on the page.
for index, message in enumerate(st.session_state.messages):
    role = message["role"]
    with st.chat_message(role, avatar=AVATARS.get(role)):
        st.markdown(message["content"])

        stamp = message.get("time")
        if stamp:
            st.caption(stamp)

        if role == "assistant":
            columns = st.columns([1, 1, 6])
            with columns[0]:
                copy = st.toggle("📋", key=f"copy_{index}", help="Show raw text to copy")
            with columns[1]:
                is_last = index == len(st.session_state.messages) - 1
                if is_last and st.button("🔄", key=f"regen_{index}", help="Regenerate"):
                    st.session_state.messages.pop()
                    st.session_state.regenerate = True
                    st.rerun()
            if copy:
                st.code(message["content"] or "", language=None)


# ── Regenerate the last reply ──────────────────────────────────────────────
if st.session_state.regenerate:
    st.session_state.regenerate = False
    last_user = next(
        (m for m in reversed(st.session_state.messages) if m["role"] == "user"), None
    )
    if last_user:
        answer(last_user["content"])
        st.rerun()


# ── Chat input ─────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask me anything…"):
    prompt = prompt.strip()

    if prompt:
        # 1. Store and 2. render the user's message.
        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
                "time": datetime.now().strftime("%H:%M"),
            }
        )
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)

        # 3. Stream the reply, then 4. store it.
        answer(prompt)

        # Re-run so the finished turn is drawn by the history loop above,
        # with its timestamp, Copy toggle and Regenerate button.
        st.rerun()


# ── Sidebar counters (written last so they reflect this run) ───────────────
count = len(st.session_state.messages)
message_count_slot.caption(f"{count} message{'' if count == 1 else 's'} in history")

usage = usage_summary(system_prompt, model)
approx = "" if usage["exact"] else " (estimated)"
usage_slot.caption(
    f"{usage['total']:,} tokens{approx} · ~${usage['cost']:.4f} at {model} rates"
)

if st.session_state.notice:
    notice_slot.warning(st.session_state.notice, icon="⚠️")
