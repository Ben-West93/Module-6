"""
L8 — Personal Stats Dashboard  (SOLUTION)
==========================================
Run with:
    streamlit run my_dashboard.py

A wide-layout dashboard with sidebar controls, a metrics row, tabs,
and an expander.

Feature checklist:
    1. st.set_page_config(layout="wide")                      ✔ Step 1
    2. Sidebar with 2+ control widgets                        ✔ Step 3
    3. 3-column metrics row using st.metric() with deltas     ✔ Step 5
    4. 2 tabs: "Overview" and "Details"                       ✔ Step 6
    5. 1 expander with extra content                          ✔ Step 7
    6. Data is hardcoded                                      ✔ Step 2

When to use tabs vs expanders:
    Tabs      → mutually exclusive views (Overview vs Details)
    Expanders → optional detail that most users won't need
"""

import pandas as pd
import streamlit as st

# ── Step 1: Page config ────────────────────────────────────────────────────
# Must be the FIRST Streamlit call in the script.
st.set_page_config(
    page_title="Personal Stats Dashboard",
    page_icon="📊",
    layout="wide",
)


# ── Step 2: Hardcoded data ────────────────────────────────────────────────
DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

WEEKLY_STUDY = {
    "Mon": 1.5,
    "Tue": 2.0,
    "Wed": 1.0,
    "Thu": 2.5,
    "Fri": 0.5,
    "Sat": 3.0,
    "Sun": 2.0,
}

# Same shape as WEEKLY_STUDY so the two weeks can be compared directly.
PREV_WEEK_STUDY = {
    "Mon": 1.0,
    "Tue": 1.5,
    "Wed": 1.5,
    "Thu": 1.0,
    "Fri": 1.0,
    "Sat": 2.0,
    "Sun": 1.0,
}

MODULES = {
    "Module 1: Python Basics": {
        "score": 88,
        "status": "Complete",
        "hours": 9.5,
        "exercises_done": 12,
        "exercises_total": 12,
    },
    "Module 2: Data Structures": {
        "score": 92,
        "status": "Complete",
        "hours": 11.0,
        "exercises_done": 10,
        "exercises_total": 10,
    },
    "Module 3: SQL & Databases": {
        "score": 79,
        "status": "Complete",
        "hours": 14.0,
        "exercises_done": 8,
        "exercises_total": 8,
    },
    "Module 4: APIs & FastAPI": {
        "score": 85,
        "status": "Complete",
        "hours": 16.5,
        "exercises_done": 14,
        "exercises_total": 14,
    },
    "Module 5: Testing": {
        "score": 81,
        "status": "In Progress",
        "hours": 6.0,
        "exercises_done": 5,
        "exercises_total": 9,
    },
    "Module 6: Streamlit": {
        "score": 0,
        "status": "Not Started",
        "hours": 0.0,
        "exercises_total": 8,
        "exercises_done": 0,
    },
}

SKILLS = {
    "Python": 90,
    "SQL": 75,
    "FastAPI": 82,
    "Testing": 68,
    "Streamlit": 40,
    "Git": 77,
}

CHART_TYPES = ["Bar", "Line", "Area"]


# ── Helpers ───────────────────────────────────────────────────────────────
def render_chart(frame: pd.DataFrame, chart_type: str) -> None:
    """Draw `frame` using the chart style the user picked in the sidebar.

    Falls back to a bar chart if an unknown chart type somehow arrives,
    so a bad value can never crash the page.
    """
    if frame.empty:
        st.info("No data to chart yet.")
        return

    if chart_type == "Line":
        st.line_chart(frame)
    elif chart_type == "Area":
        st.area_chart(frame)
    else:
        st.bar_chart(frame)


def completion_pct(module: dict) -> float:
    """Percent of exercises finished, guarded against a zero total."""
    total = module.get("exercises_total", 0)
    done = module.get("exercises_done", 0)
    if not total:
        return 0.0
    return round(100 * done / total, 1)


def format_delta(current: float, previous: float, unit: str) -> str:
    """Signed change string, e.g. '+2.5 hrs' or '-1.0 hrs'."""
    return f"{current - previous:+.1f} {unit}"


# ── Derived values ────────────────────────────────────────────────────────
this_week_hours = sum(WEEKLY_STUDY.values())
last_week_hours = sum(PREV_WEEK_STUDY.values())

scored_modules = [m for m in MODULES.values() if m["status"] != "Not Started"]
avg_score = (
    round(sum(m["score"] for m in scored_modules) / len(scored_modules), 1)
    if scored_modules
    else 0.0
)

modules_complete = sum(1 for m in MODULES.values() if m["status"] == "Complete")
total_modules = len(MODULES)


# ── Step 3: Sidebar controls ──────────────────────────────────────────────
with st.sidebar:
    st.header("Dashboard Controls")

    focus_module = st.selectbox(
        "Focus module",
        options=list(MODULES.keys()),
        index=len(MODULES) - 1,
        help="Pick the module to highlight in the Details tab.",
    )

    chart_type = st.radio(
        "Chart type",
        options=CHART_TYPES,
        index=0,
        horizontal=True,
        help="How the study-hours chart is drawn.",
    )

    compare_last_week = st.checkbox(
        "Compare against last week",
        value=True,
        help="Overlay last week's hours on the Overview chart.",
    )

    st.divider()
    st.caption("Data is hardcoded for this exercise.")


# ── Step 4: Page title ────────────────────────────────────────────────────
st.title("📊 Personal Stats Dashboard")
st.caption(
    f"Study habits and course progress · focus: {focus_module} · "
    f"{modules_complete} of {total_modules} modules complete"
)


# ── Step 5: Metrics row ───────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Study Hours (this week)",
        f"{this_week_hours:.1f} hrs",
        format_delta(this_week_hours, last_week_hours, "hrs vs last week"),
    )

with col2:
    st.metric(
        "Average Score",
        f"{avg_score:.1f}%",
        "+3.2 pts vs last module",
    )

with col3:
    st.metric(
        "Modules Complete",
        f"{modules_complete} / {total_modules}",
        "+1 this month",
    )


# ── Step 6: Tabs ──────────────────────────────────────────────────────────
tab_overview, tab_details = st.tabs(["📈 Overview", "📋 Details"])

with tab_overview:
    st.subheader("Study Hours by Day")

    hours_frame = pd.DataFrame({"This week": WEEKLY_STUDY}).reindex(DAY_ORDER)
    if compare_last_week:
        hours_frame["Last week"] = pd.Series(PREV_WEEK_STUDY).reindex(DAY_ORDER)

    render_chart(hours_frame, chart_type)

    busiest_day = max(WEEKLY_STUDY, key=WEEKLY_STUDY.get)
    st.caption(
        f"Busiest day: {busiest_day} ({WEEKLY_STUDY[busiest_day]:.1f} hrs) · "
        f"daily average: {this_week_hours / len(WEEKLY_STUDY):.1f} hrs"
    )

    st.subheader("Skill Confidence")
    skills_frame = pd.DataFrame({"Confidence": SKILLS})
    render_chart(skills_frame, chart_type)

with tab_details:
    st.subheader("Module Progress")

    progress_rows = []
    for name, module in MODULES.items():
        progress_rows.append(
            {
                "Module": name,
                "Status": module["status"],
                "Score": module["score"] if module["status"] != "Not Started" else None,
                "Hours": module["hours"],
                "Exercises": f"{module['exercises_done']}/{module['exercises_total']}",
                "Complete %": completion_pct(module),
            }
        )

    progress_frame = pd.DataFrame(progress_rows)
    st.dataframe(progress_frame, hide_index=True)

    st.subheader(f"Focus: {focus_module}")
    focus = MODULES[focus_module]
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        st.metric("Status", focus["status"])
    with fcol2:
        st.metric("Hours Logged", f"{focus['hours']:.1f} hrs")
    with fcol3:
        st.metric(
            "Exercises",
            f"{focus['exercises_done']}/{focus['exercises_total']}",
        )

    st.progress(
        min(max(completion_pct(focus) / 100, 0.0), 1.0),
        text=f"{completion_pct(focus):.0f}% of exercises submitted",
    )

    # ── Step 7: Expander ──────────────────────────────────────────────────
    with st.expander("Raw Data & Methodology", expanded=False):
        st.markdown("**Raw data**")
        st.json(
            {
                "weekly_study_hours": WEEKLY_STUDY,
                "previous_week_hours": PREV_WEEK_STUDY,
                "modules": MODULES,
                "skills": SKILLS,
            }
        )

        st.markdown(
            """
**How these numbers are calculated**

- **Study Hours (this week)** — sum of `WEEKLY_STUDY`. The delta is this
  week's total minus last week's total, so a positive number means more
  time studying.
- **Average Score** — mean score across modules that have actually been
  started; modules marked *Not Started* are excluded so an unstarted
  module doesn't drag the average to zero.
- **Modules Complete** — count of modules whose status is exactly
  *Complete*. *In Progress* does not count.
- **Complete %** — `exercises_done / exercises_total`, guarded against a
  zero total so an empty module returns 0% instead of raising.
- **Skill Confidence** — self-reported 0–100, not computed from scores.

All values are hardcoded for this exercise; nothing is read from a
database or an API.
"""
        )
