"""
L9 — Stateful Quiz App  (quiz_app.py)
===================================
Run with:
    streamlit run quiz_app.py

A 5-question multiple-choice quiz that tracks state across re-runs using
st.session_state.

Session state lifecycle:
    1. INITIALIZE — set defaults once with the pattern:
         if "key" not in st.session_state:
             st.session_state.key = default_value
    2. READ   — use st.session_state.key anywhere
    3. UPDATE — assign st.session_state.key = new_value
    4. RESET  — reassign all keys to defaults (Restart button)

State keys
----------
current_q    : int   — position in `order` (0-4), not the question's own index
score        : int   — number correct this attempt
answered     : bool  — has the current question been submitted?
selected     : str   — the radio's current value
show_results : bool  — results screen instead of quiz screen
order        : list  — question indices in the shuffled order for this attempt
opt_order    : dict  — question index -> its options, shuffled for this attempt
responses    : list  — one record per finished question (for the review)
history      : list  — one record per completed attempt; survives Restart
"""

import random

import streamlit as st

# ── Step 1: Quiz data ──────────────────────────────────────────────────────
QUESTIONS = [
    {
        "question": "What does st.session_state do in a Streamlit app?",
        "options": [
            "It caches expensive function results between users",
            "It stores values that survive re-runs of the script",
            "It saves data permanently to a database file",
            "It controls the page layout and theme",
        ],
        "answer": "It stores values that survive re-runs of the script",
        "explanation": (
            "Streamlit re-runs the whole script top-to-bottom on every widget "
            "interaction. Plain variables are rebuilt each time; st.session_state "
            "is a dict-like store that persists for the duration of the browser "
            "session."
        ),
    },
    {
        "question": "Why is the `if \"key\" not in st.session_state:` guard used before "
                    "assigning a default value?",
        "options": [
            "It makes the assignment run faster",
            "It is required syntax for every session_state key",
            "It stops the default from overwriting the stored value on each re-run",
            "It converts the value to a string automatically",
        ],
        "answer": "It stops the default from overwriting the stored value on each re-run",
        "explanation": (
            "Without the guard, the script would reset the value back to its "
            "default on every re-run, so the score would never climb above 0."
        ),
    },
    {
        "question": "What does st.rerun() do?",
        "options": [
            "Restarts the Streamlit server process",
            "Clears st.session_state and reloads defaults",
            "Immediately stops the current run and starts the script over",
            "Re-runs only the widget that was clicked",
        ],
        "answer": "Immediately stops the current run and starts the script over",
        "explanation": (
            "st.rerun() aborts the current execution and re-runs the script from "
            "the top with session_state intact — handy right after updating state "
            "so the page reflects the change straight away."
        ),
    },
    {
        "question": "If a widget is given key=\"answer\", where does its current value live?",
        "options": [
            "In st.session_state[\"answer\"]",
            "In a hidden file next to the script",
            "Only in the variable the widget returns",
            "In the URL query string",
        ],
        "answer": "In st.session_state[\"answer\"]",
        "explanation": (
            "A keyed widget writes its value into st.session_state under that key, "
            "so you can read it anywhere in the script — not just from the widget's "
            "return value."
        ),
    },
    {
        "question": "What is the effect of calling st.stop()?",
        "options": [
            "It halts the rest of the script for that run",
            "It shuts down the Streamlit app for all users",
            "It pauses the script until a button is pressed",
            "It disables every widget on the page",
        ],
        "answer": "It halts the rest of the script for that run",
        "explanation": (
            "st.stop() ends the current run early. Here it keeps the quiz screen "
            "from rendering underneath the results screen."
        ),
    },
]

TOTAL_QS = len(QUESTIONS)

# Simple keys and their defaults. `order`, `opt_order` and `history` are
# handled separately because they are built, not constant.
DEFAULTS = {
    "current_q": 0,
    "score": 0,
    "answered": False,
    "selected": None,
    "show_results": False,
    "responses": [],
}


def build_shuffle():
    """Return (question order, per-question option order) for a new attempt."""
    order = list(range(TOTAL_QS))
    random.shuffle(order)
    opt_order = {}
    for q_idx in order:
        options = list(QUESTIONS[q_idx]["options"])
        random.shuffle(options)
        opt_order[q_idx] = options
    return order, opt_order


def reset_quiz() -> None:
    """RESET — put every per-attempt key back to its default and reshuffle.

    `history` is deliberately left alone so past attempts survive a restart.
    The radio widgets are keyed `q_0` ... `q_4` and Streamlit keeps those keys
    in session_state too; they are removed as well, otherwise a restarted quiz
    would show the previous attempt's selections still filled in.
    """
    for key, default in DEFAULTS.items():
        st.session_state[key] = list(default) if isinstance(default, list) else default
    st.session_state.order, st.session_state.opt_order = build_shuffle()
    for i in range(TOTAL_QS):
        st.session_state.pop(f"q_{i}", None)


def record(q_idx: int, chosen, skipped: bool) -> None:
    """Store one finished question for the end-of-quiz review."""
    st.session_state.responses.append(
        {
            "q_idx": q_idx,
            "chosen": chosen,
            "correct": (not skipped) and chosen == QUESTIONS[q_idx]["answer"],
            "skipped": skipped,
        }
    )


def finish_quiz() -> None:
    """Close out the attempt: log it to history and switch to the results screen."""
    st.session_state.history.append(
        {
            "attempt": len(st.session_state.history) + 1,
            "score": st.session_state.score,
            "total": TOTAL_QS,
            "pct": round(st.session_state.score / TOTAL_QS * 100) if TOTAL_QS else 0,
        }
    )
    st.session_state.show_results = True


def advance(q_idx: int, chosen, skipped: bool) -> None:
    """Record the answer, then move to the next question or to the results."""
    record(q_idx, chosen, skipped)
    if st.session_state.current_q == TOTAL_QS - 1:
        finish_quiz()
    else:
        st.session_state.current_q += 1
        st.session_state.answered = False
        st.session_state.selected = None


# ── Step 2: Session state initialisation ──────────────────────────────────
# Runs ONLY on the first load. On every re-run the keys already exist, so
# the assignment is skipped and the stored values survive.
for key, default in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = list(default) if isinstance(default, list) else default

if "history" not in st.session_state:
    st.session_state.history = []

if "order" not in st.session_state:
    st.session_state.order, st.session_state.opt_order = build_shuffle()

# ── Step 3: Page config ───────────────────────────────────────────────────
st.set_page_config(page_title="L9 Quiz App", page_icon="🧠", layout="centered")
st.title("🧠 Streamlit Session State Quiz")

# ══════════════════════════════════════════════════════════════════════════
# RESULTS SCREEN
# ══════════════════════════════════════════════════════════════════════════
if st.session_state.show_results:
    score = st.session_state.score
    pct = round(score / TOTAL_QS * 100) if TOTAL_QS else 0
    skipped = sum(1 for r in st.session_state.responses if r["skipped"])
    wrong = sum(
        1 for r in st.session_state.responses if not r["correct"] and not r["skipped"]
    )

    st.header("Results")

    col1, col2, col3 = st.columns(3)
    col1.metric("Correct", score)
    col2.metric("Wrong", wrong)
    col3.metric("Skipped", skipped)

    st.metric("Final score", f"{score} / {TOTAL_QS}", f"{pct}%")
    st.progress(pct / 100)

    if pct >= 80:
        st.success(f"Nice work — {score} out of {TOTAL_QS} ({pct}%). You've got this.")
    elif pct >= 50:
        st.warning(f"{score} out of {TOTAL_QS} ({pct}%). Worth another pass.")
    else:
        st.error(f"{score} out of {TOTAL_QS} ({pct}%). Give it another go.")

    # ── Per-question review ───────────────────────────────────────────────
    st.subheader("Review")
    for n, resp in enumerate(st.session_state.responses, start=1):
        q = QUESTIONS[resp["q_idx"]]
        if resp["skipped"]:
            mark, yours = "⏭️", "_Skipped_"
        elif resp["correct"]:
            mark, yours = "✅", resp["chosen"]
        else:
            mark, yours = "❌", resp["chosen"]
        with st.expander(f"{mark} Q{n}. {q['question']}", expanded=not resp["correct"]):
            st.markdown(f"**Your answer:** {yours}")
            st.markdown(f"**Correct answer:** {q['answer']}")
            st.caption(q["explanation"])

    # ── Score history ─────────────────────────────────────────────────────
    history = st.session_state.history
    if len(history) > 1:
        st.subheader("Your attempts")
        st.line_chart({"Score (%)": [h["pct"] for h in history]})
        best = max(h["score"] for h in history)
        st.caption(f"{len(history)} attempts · best so far: {best} / {TOTAL_QS}")

    if st.button("🔄 Restart quiz"):
        reset_quiz()
        st.rerun()

    st.stop()

# ══════════════════════════════════════════════════════════════════════════
# QUIZ SCREEN
# ══════════════════════════════════════════════════════════════════════════
position = st.session_state.current_q
q_index = st.session_state.order[position]
question = QUESTIONS[q_index]
options = st.session_state.opt_order[q_index]

# Progress indicator
st.caption(f"Question {position + 1} of {TOTAL_QS}")
st.progress(position / TOTAL_QS)

st.subheader(question["question"])

choice = st.radio(
    "Choose your answer:",
    options,
    index=None,
    key=f"q_{position}",
    disabled=st.session_state.answered,
)
st.session_state.selected = choice

if not st.session_state.answered:
    left, right = st.columns([1, 1])
    if left.button("✅ Submit answer", use_container_width=True):
        if choice is None:
            st.warning("Pick an answer first, or skip the question.")
        else:
            st.session_state.answered = True
            if choice == question["answer"]:
                st.session_state.score += 1
            st.rerun()
    if right.button("⏭️ Skip question", use_container_width=True):
        advance(q_index, None, skipped=True)
        st.rerun()
else:
    if st.session_state.selected == question["answer"]:
        st.success("Correct!")
    else:
        st.error(f"Not quite — the correct answer is: {question['answer']}")
    st.info(question["explanation"])

    is_last = position == TOTAL_QS - 1
    label = "🏁 Finish quiz" if is_last else "➡️ Next question"
    if st.button(label):
        advance(q_index, st.session_state.selected, skipped=False)
        st.rerun()
        