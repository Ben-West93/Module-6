"""
L7 — Streamlit Exploration App
===========================================
Run with:
    streamlit run solution.py

An interactive app called "Python Learning Journey" that uses 6 widget types
and shows content that changes based on widget values.

KEY CONCEPT — The re-run model:
    Every time a user interacts with a widget, Streamlit re-executes the
    ENTIRE script from top to bottom. This means:
      • Widget functions (st.slider, st.selectbox, etc.) both RENDER the
        widget AND RETURN the current value in the same call.
      • Just use the returned value immediately — no event handlers needed.
      • Write code like a normal top-to-bottom Python script.

Widgets used:
    st.slider()       — returns a number (int or float)
    st.selectbox()    — returns one item from a list
    st.radio()        — returns one item from a list (shown as radio buttons)
    st.multiselect()  — returns a list of selected items
    st.text_input()   — returns a string
    st.checkbox()     — returns True or False
"""

import random

import streamlit as st

# ── Page configuration ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Python Learning Journey",
    page_icon="🐍",
    layout="centered",
)

st.title("🐍 Python Learning Journey")
st.caption("Adjust the widgets to explore your progress and learning path.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Widget 1 — st.slider
# ═══════════════════════════════════════════════════════════════════════════
st.subheader("1. Experience Level")

TOTAL_WEEKS = 52

weeks = st.slider(
    "How many weeks have you been coding?",
    min_value=0,
    max_value=TOTAL_WEEKS,
    value=8,
    step=1,
)

if weeks < 6:
    level_label = "Beginner"
elif weeks < 24:
    level_label = "Intermediate"
else:
    level_label = "Advanced"

st.metric(label="Your level", value=level_label, delta=f"{weeks} weeks")

# Visual sense of progress through a one-year journey.
st.progress(weeks / TOTAL_WEEKS, text=f"{weeks} of {TOTAL_WEEKS} weeks")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Widget 2 — st.selectbox
# ═══════════════════════════════════════════════════════════════════════════
st.subheader("2. Current Topic")

tips = {
    "Variables & Data Types": "Remember that Python names are labels bound to objects — "
    "assigning a list to a second name does not copy it.",
    "Control Flow": "Prefer a clear `if/elif/else` chain over deeply nested conditions; "
    "return early to keep functions flat.",
    "Functions": "Never use a mutable default argument like `def f(items=[])` — "
    "use `None` and build the list inside the function.",
    "Data Structures": "Reach for a dict when you need fast lookups by key, and a set "
    "when you only care about membership and uniqueness.",
    "File I/O": "Always use `with open(...) as f:` so the file closes even if an "
    "exception is raised partway through.",
    "APIs & Requests": "Check `response.status_code` before touching `response.json()`, "
    "and wrap the call in `try/except` so a network error can't crash the app.",
    "Databases & SQL": "Use parameterised queries (`?` placeholders) instead of "
    "f-strings — that's what keeps SQL injection out of your code.",
}

topic = st.selectbox(
    "Which topic are you working on right now?",
    options=list(tips.keys()),
    index=0,
)

st.info(f"**Tip for {topic}:** {tips[topic]}")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Widget 3 — st.radio
# ═══════════════════════════════════════════════════════════════════════════
st.subheader("3. Learning Style")

resources = {
    "Reading docs": "Work straight from the official Python docs and the library's own "
    "reference pages — then write a two-line summary of each section in your own words.",
    "Watching videos": "Pick one structured course and finish it before starting another. "
    "Pause after each lesson and retype the example from memory.",
    "Building projects": "Ship something small end to end every week. A finished 50-line "
    "tool teaches more than a half-built 500-line one.",
    "Pair programming": "Find a study partner and alternate driver/navigator every 20 "
    "minutes. Explaining your reasoning out loud exposes the gaps fastest.",
}

style = st.radio(
    "How do you learn best?",
    options=["Reading docs", "Watching videos", "Building projects", "Pair programming"],
    horizontal=True,
)

st.write(f"**Recommended approach:** {resources[style]}")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Widget 4 — st.multiselect
# ═══════════════════════════════════════════════════════════════════════════
st.subheader("4. Tools & Libraries You Use")

selected_tools = st.multiselect(
    "Which tools and libraries have you used so far?",
    options=[
        "pandas",
        "requests",
        "FastAPI",
        "Streamlit",
        "SQLite",
        "SQLAlchemy",
        "pytest",
        "Flask",
        "NumPy",
    ],
    default=["requests", "Streamlit"],
)

if selected_tools:
    st.write(f"You're working with **{len(selected_tools)}** tool(s):")
    # Lay the checkmarks out in up to 3 columns instead of one long list.
    column_count = min(3, len(selected_tools))
    columns = st.columns(column_count)
    for index, tool in enumerate(selected_tools):
        columns[index % column_count].write(f"✅ {tool}")
else:
    st.warning("No tools selected yet — pick at least one to see your toolkit.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Widget 5 — st.text_input
# ═══════════════════════════════════════════════════════════════════════════
st.subheader("5. Project Idea Generator")

project_keyword = st.text_input(
    "Enter a keyword you're interested in",
    placeholder="e.g. weather, fitness, recipes",
)

keyword = project_keyword.strip()

IDEA_TEMPLATES = [
    "A {kw} tracker that stores entries in SQLite and shows a weekly summary.",
    "A command-line {kw} logger that saves records to a CSV file.",
    "A FastAPI service exposing {kw} data with full CRUD endpoints.",
    "A Streamlit dashboard that charts your {kw} history over time.",
    "A {kw} reminder tool that emails you a digest once a week.",
    "A small {kw} REST client that pulls from a public API and caches results.",
    "A pytest-covered {kw} module you can import into a bigger project.",
]

if keyword:
    # Seed the shuffle from the keyword itself so ideas stay stable while the
    # user types elsewhere, but a new keyword produces a different set.
    rng = random.Random(keyword.casefold())
    ideas = rng.sample(IDEA_TEMPLATES, k=4)

    st.write(f"**Project ideas built around “{keyword}”:**")
    for i, template in enumerate(ideas, start=1):
        st.write(f"{i}. {template.format(kw=keyword)}")
else:
    st.write("👆 Enter a keyword above to generate project ideas.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Widget 6 — st.checkbox
# ═══════════════════════════════════════════════════════════════════════════
st.subheader("6. Progress Summary")

show_summary = st.checkbox("Show my personalised learning summary", value=True)

if show_summary:
    tools_text = ", ".join(selected_tools) if selected_tools else "none selected yet"
    keyword_text = keyword if keyword else "not chosen yet"

    st.success(
        f"""**Your Learning Journey**

- **Experience:** {weeks} week(s) of coding — {level_label}
- **Current topic:** {topic}
- **Learning style:** {style}
- **Toolkit:** {tools_text}
- **Project keyword:** {keyword_text}

Keep going — steady weekly practice on {topic} is what moves you to the next level."""
    )
else:
    st.write("Tick the box above to see your personalised summary.")
