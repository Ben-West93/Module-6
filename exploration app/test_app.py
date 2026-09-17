"""
Tests for the Python Learning Journey Streamlit app.

Run with:
    pytest test_app.py

These use Streamlit's AppTest harness, which executes solution.py the same way
the real server does — including a full re-run after each simulated widget
interaction — and reports any exception the script raised.
"""

import pytest
from streamlit.testing.v1 import AppTest

APP_FILE = "solution.py"


def fresh_app() -> AppTest:
    """Return a freshly executed app with default widget values."""
    app = AppTest.from_file(APP_FILE, default_timeout=30).run()
    assert not app.exception, app.exception
    return app


def test_app_starts_without_error():
    app = fresh_app()
    assert not app.exception


def test_all_six_widget_types_render():
    app = fresh_app()
    assert len(app.slider) == 1
    assert len(app.selectbox) == 1
    assert len(app.radio) == 1
    assert len(app.multiselect) == 1
    assert len(app.text_input) == 1
    assert len(app.checkbox) == 1


@pytest.mark.parametrize(
    "weeks, expected_level",
    [
        (0, "Beginner"),
        (5, "Beginner"),
        (6, "Intermediate"),
        (23, "Intermediate"),
        (24, "Advanced"),
        (52, "Advanced"),
    ],
)
def test_slider_boundaries_map_to_correct_level(weeks, expected_level):
    app = fresh_app()
    app.slider[0].set_value(weeks).run()
    assert not app.exception, app.exception
    assert app.metric[0].value == expected_level
    assert app.metric[0].delta == f"{weeks} weeks"


def test_every_topic_renders_a_tip():
    for option in fresh_app().selectbox[0].options:
        app = fresh_app()
        app.selectbox[0].set_value(option).run()
        assert not app.exception, (option, app.exception)
        assert len(app.info) == 1


def test_every_learning_style_renders():
    for option in fresh_app().radio[0].options:
        app = fresh_app()
        app.radio[0].set_value(option).run()
        assert not app.exception, (option, app.exception)


def test_empty_multiselect_shows_warning():
    app = fresh_app()
    app.multiselect[0].set_value([]).run()
    assert not app.exception, app.exception
    assert len(app.warning) == 1


def test_all_tools_selected_has_no_warning():
    app = fresh_app()
    app.multiselect[0].set_value(app.multiselect[0].options).run()
    assert not app.exception, app.exception
    assert len(app.warning) == 0


@pytest.mark.parametrize(
    "keyword",
    [
        "",
        "   ",
        "weather",
        "a" * 300,
        "Ünïcode ☕",
        "<script>alert(1)</script>",
        "O'Brien \"quoted\" {braces}",
        "line\nbreak",
        "100%",
    ],
)
def test_text_input_edge_cases_do_not_crash(keyword):
    app = fresh_app()
    app.text_input[0].set_value(keyword).run()
    assert not app.exception, (repr(keyword), app.exception)


def test_idea_generation_is_stable_for_the_same_keyword():
    """The seeded shuffle must not reshuffle between identical runs."""
    outputs = []
    for _ in range(2):
        app = fresh_app()
        app.text_input[0].set_value("fitness").run()
        outputs.append([block.value for block in app.markdown])
    assert outputs[0] == outputs[1]


def test_different_keywords_can_produce_different_idea_sets():
    sets = []
    for keyword in ("weather", "recipes", "fitness", "budget"):
        app = fresh_app()
        app.text_input[0].set_value(keyword).run()
        assert not app.exception, app.exception
        # Strip the keyword back out so only the template ordering is compared.
        sets.append(
            tuple(block.value.replace(keyword, "KW") for block in app.markdown)
        )
    assert len(set(sets)) > 1


def test_unchecking_hides_the_summary():
    app = fresh_app()
    app.checkbox[0].set_value(False).run()
    assert not app.exception, app.exception
    assert len(app.success) == 0


def test_summary_reflects_all_widget_values():
    app = fresh_app()
    app.slider[0].set_value(52)
    app.selectbox[0].set_value("File I/O")
    app.radio[0].set_value("Pair programming")
    app.multiselect[0].set_value(["pandas", "pytest"])
    app.text_input[0].set_value("  fitness  ")
    app.checkbox[0].set_value(True)
    app.run()

    assert not app.exception, app.exception
    summary = app.success[0].value
    assert "52 week(s)" in summary
    assert "Advanced" in summary
    assert "File I/O" in summary
    assert "Pair programming" in summary
    assert "pandas, pytest" in summary
    assert "fitness" in summary


def test_summary_handles_empty_tools_and_keyword():
    app = fresh_app()
    app.multiselect[0].set_value([])
    app.text_input[0].set_value("")
    app.run()

    assert not app.exception, app.exception
    summary = app.success[0].value
    assert "none selected yet" in summary
    assert "not chosen yet" in summary
