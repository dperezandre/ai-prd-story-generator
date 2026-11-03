from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def fresh():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception
    return at


def by_key(elements, key):
    return next(e for e in elements if e.key == key)


def test_demo_mode_generates_all_tabs_and_downloads():
    at = fresh()
    by_key(at.button, "generate").click().run()
    assert not at.exception
    assert len(at.tabs) == 4
    assert len(at.get("download_button")) == 3
    assert not at.error


def test_demo_works_in_english_and_portuguese():
    at = fresh()
    by_key(at.selectbox, "lang").set_value("en").run()
    by_key(at.button, "generate").click().run()
    assert not at.exception and len(at.tabs) == 4
    by_key(at.selectbox, "lang").set_value("pt-BR").run()
    by_key(at.button, "generate").click().run()
    assert not at.exception and len(at.tabs) == 4


def test_live_mode_without_key_shows_error_not_crash():
    at = fresh()
    by_key(at.toggle, "demo").set_value(False).run()
    by_key(at.text_area, "idea").set_value("Some feature idea").run()
    by_key(at.button, "generate").click().run()
    assert not at.exception
    assert len(at.error) == 1
    assert len(at.tabs) == 0


def test_live_mode_with_empty_idea_shows_error():
    at = fresh()
    by_key(at.toggle, "demo").set_value(False).run()
    by_key(at.text_input, "api_key").set_value("k").run()
    by_key(at.text_area, "idea").set_value("   ").run()
    by_key(at.button, "generate").click().run()
    assert not at.exception and len(at.error) == 1


def live_run(monkeypatch, responses):
    import src.providers
    from tests.conftest import FakeProvider
    monkeypatch.setattr(src.providers, "get_provider", lambda *a, **k: FakeProvider(responses))
    at = fresh()
    by_key(at.toggle, "demo").set_value(False).run()
    by_key(at.text_input, "api_key").set_value("k").run()
    by_key(at.text_area, "idea").set_value("A feature idea").run()
    by_key(at.button, "generate").click().run()
    return at


def test_live_mode_success_renders_results(monkeypatch):
    from tests.test_pipeline import good_responses
    at = live_run(monkeypatch, good_responses())
    assert not at.exception and not at.error
    assert len(at.tabs) == 4 and len(at.get("download_button")) == 3


def test_live_mode_failure_midway_shows_error_and_partial_results(monkeypatch):
    from src.providers import ProviderError
    from tests.test_pipeline import good_responses
    at = live_run(monkeypatch, good_responses()[:1] + [ProviderError("Groq rate limit reached.", "rate_limit")])
    assert not at.exception
    assert any("rate limit" in e.value for e in at.error)
    assert len(at.tabs) == 4
