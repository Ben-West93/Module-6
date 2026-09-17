# L7 — Python Learning Journey (Streamlit)

An interactive Streamlit app that demonstrates the Streamlit re-run model using
six widget types. Every widget's returned value immediately drives what the page
displays — no callbacks or event handlers.

## Files

| File | Purpose |
| --- | --- |
| `solution.py` | The complete Streamlit app. |
| `test_app.py` | Pytest suite covering the app with Streamlit's `AppTest` harness. |
| `README.md` | This file. |

## Requirements

- Python 3.9+
- `streamlit` (developed against 1.64)
- `pytest` (only needed to run the tests)

```bash
pip install streamlit pytest
```

## Running the app

```bash
streamlit run solution.py
```

Streamlit prints a local URL (default <http://localhost:8501>); open it in a
browser. Stop the server with `Ctrl+C`.

## What the app does

| # | Widget | Returns | Drives |
| --- | --- | --- | --- |
| 1 | `st.slider` | `int` (0–52 weeks) | A Beginner / Intermediate / Advanced label shown via `st.metric`, plus an `st.progress` bar for the 52-week journey. |
| 2 | `st.selectbox` | `str` (one of 7 topics) | A topic-specific tip looked up from a dict and shown with `st.info`. |
| 3 | `st.radio` | `str` (one of 4 styles) | A study recommendation matched to the chosen learning style. |
| 4 | `st.multiselect` | `list[str]` (9 tools available) | A checkmark list laid out across up to 3 `st.columns`, or an `st.warning` when nothing is selected. |
| 5 | `st.text_input` | `str` | Four project ideas built from the keyword. The shuffle is seeded from the keyword itself, so the same keyword always yields the same ideas while different keywords vary. |
| 6 | `st.checkbox` | `bool` | An `st.success` summary combining every value above. |

### Level thresholds

- `weeks < 6` → Beginner
- `6 <= weeks < 24` → Intermediate
- `weeks >= 24` → Advanced

## Input handling

- The keyword is `.strip()`ped, so whitespace-only input is treated as empty and
  shows the "enter a keyword" prompt instead of generating blank ideas.
- Idea templates use `str.format(kw=...)` on a fixed template string rather than
  interpolating user text into a format spec, so braces or quotes typed into the
  keyword box cannot break formatting.
- An empty tool selection is handled explicitly in both the toolkit section and
  the summary ("none selected yet").

## Running the tests

```bash
pytest test_app.py
```

26 tests currently pass. They cover:

- The app executing with no exception at default values.
- All six widget types rendering exactly once.
- Slider boundary values (0, 5, 6, 23, 24, 52) mapping to the correct level.
- Every topic option rendering a tip, and every learning style rendering.
- The empty-multiselect warning, and no warning when all tools are selected.
- Text input edge cases: empty, whitespace-only, 300 characters, non-ASCII, a
  `<script>` tag, quotes and braces, an embedded newline, and a percent sign.
- Idea generation being stable for a repeated keyword and varying across
  different keywords.
- The summary hiding when the checkbox is cleared, and reflecting every widget
  value when it is shown.
