from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import azure_devops, claude_cli
from src.claude_cli import ClaudeCliError, ReviewResult

PAGE = str(Path(__file__).resolve().parent.parent / "spec_review_page.py")

STORIES = {"document": "Doc", "stories": [
    {"title": "Criar A", "description": "Como X, quero A, para B.",
     "acceptance_criteria": ["Cenário: ok\n  Dado a\n  Quando b\n  Então c"],
     "tasks": [{"title": "Construir A", "description": "d"}, {"title": "Testar A"}]},
    {"title": "Criar B", "description": "Como X, quero B, para C.",
     "acceptance_criteria": ["Cenário: ok2"], "tasks": [{"title": "Construir B"}]},
]}


def by_key(elements, key):
    return next(e for e in elements if e.key == key)


def page():
    at = AppTest.from_file(PAGE, default_timeout=30)
    at.run()
    assert not at.exception
    return at


def reviewed(monkeypatch):
    monkeypatch.setattr(claude_cli, "review_spec",
                        lambda data, name, on_event=None: ReviewResult("Revisão ok", STORIES, b"%PDF-x"))
    at = page()
    by_key(at.text_area, "spec_text").set_value("minha spec").run()
    by_key(at.button, "run_review").click().run()
    assert not at.exception
    return at


def test_page_renders_and_has_no_azure_before_review():
    at = page()
    assert not [k for k in ("azdo_confirm", "azdo_preview") if any(b.key == k for b in at.button)]


def test_empty_input_shows_error():
    at = page()
    by_key(at.button, "run_review").click().run()
    assert at.error


def test_review_shows_pdf_download(monkeypatch):
    at = reviewed(monkeypatch)
    assert len(at.get("download_button")) == 1
    assert not at.error


@pytest.mark.parametrize("kind,word", [("auth", "login"), ("not_found", "não encontrado")])
def test_cli_errors_show_plain_message(monkeypatch, kind, word):
    def boom(*a, **k):
        raise ClaudeCliError("x", kind=kind)
    monkeypatch.setattr(claude_cli, "review_spec", boom)
    at = page()
    by_key(at.text_area, "spec_text").set_value("spec").run()
    by_key(at.button, "run_review").click().run()
    assert not at.exception
    assert word in " ".join(e.value for e in at.error).lower()


def test_confirm_disabled_until_preview(monkeypatch):
    at = reviewed(monkeypatch)
    by_key(at.text_input, "azdo_org").set_value("minhaorg").run()
    by_key(at.text_input, "azdo_project").set_value("Sandbox").run()
    assert by_key(at.button, "azdo_confirm").disabled
    by_key(at.button, "azdo_preview").click().run()
    assert not by_key(at.button, "azdo_confirm").disabled


def test_confirm_disabled_again_when_org_changes(monkeypatch):
    at = reviewed(monkeypatch)
    by_key(at.text_input, "azdo_org").set_value("minhaorg").run()
    by_key(at.text_input, "azdo_project").set_value("Sandbox").run()
    by_key(at.button, "azdo_preview").click().run()
    assert not by_key(at.button, "azdo_confirm").disabled
    by_key(at.text_input, "azdo_project").set_value("Outro").run()
    assert by_key(at.button, "azdo_confirm").disabled


def test_confirm_sends_once_via_push(monkeypatch):
    calls = []

    def fake_push(client, items, ledger, confirmed, force=False):
        calls.append((len(items), confirmed))
        return azure_devops.PushReport(created_stories=2, created_tasks=3)
    monkeypatch.setattr(azure_devops, "push", fake_push)
    at = reviewed(monkeypatch)
    by_key(at.text_input, "azdo_org").set_value("minhaorg").run()
    by_key(at.text_input, "azdo_project").set_value("Sandbox").run()
    by_key(at.text_input, "azdo_pat").set_value("token-de-teste").run()
    by_key(at.button, "azdo_preview").click().run()
    by_key(at.button, "azdo_confirm").click().run()
    assert not at.exception
    assert calls == [(2, True)]
    assert any("2 histórias" in s.value for s in at.success)


def test_confirm_without_token_does_not_push(monkeypatch):
    calls = []
    monkeypatch.setattr(azure_devops, "push", lambda *a, **k: calls.append(1))
    at = reviewed(monkeypatch)
    by_key(at.text_input, "azdo_org").set_value("minhaorg").run()
    by_key(at.text_input, "azdo_project").set_value("Sandbox").run()
    by_key(at.button, "azdo_preview").click().run()
    by_key(at.button, "azdo_confirm").click().run()
    assert not calls and at.error
