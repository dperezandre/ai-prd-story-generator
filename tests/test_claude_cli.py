import json
from pathlib import Path

import pytest

from src import claude_cli
from src.claude_cli import ClaudeCliError, Event


def _line(**kw):
    return json.dumps(kw)


def test_find_claude_uses_home_fallback(tmp_path):
    exe = tmp_path / ".local" / "bin" / "claude.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    assert claude_cli.find_claude(path_env="", home=tmp_path) == exe


def test_find_claude_not_found(tmp_path):
    with pytest.raises(ClaudeCliError) as err:
        claude_cli.find_claude(path_env="", home=tmp_path)
    assert err.value.kind == "not_found"


def test_build_command_is_headless():
    cmd = claude_cli.build_command(Path("claude.exe"), "faça X")
    assert cmd[cmd.index("-p") + 1] == "faça X"
    assert "stream-json" in cmd and "--verbose" in cmd


def test_parse_events_text_and_result():
    lines = [
        _line(type="assistant", message={"content": [{"type": "text", "text": "olá"}]}),
        _line(type="result", is_error=False, result="fim"),
    ]
    assert list(claude_cli.parse_events(lines)) == [Event("text", "olá"), Event("result", "fim")]


def test_parse_events_auth_error_raises():
    lines = [_line(type="result", is_error=True,
                   result="Failed to authenticate: OAuth session expired and could not be refreshed")]
    with pytest.raises(ClaudeCliError) as err:
        list(claude_cli.parse_events(lines))
    assert err.value.kind == "auth"


def test_parse_events_other_error_is_failed():
    with pytest.raises(ClaudeCliError) as err:
        list(claude_cli.parse_events([_line(type="result", is_error=True, result="boom")]))
    assert err.value.kind == "failed" and "boom" in str(err.value)


def test_parse_events_skips_garbage():
    lines = ["not json", "", _line(type="result", is_error=False, result="ok")]
    assert list(claude_cli.parse_events(lines)) == [Event("result", "ok")]


# --- review_spec ---

STORIES = {"document": "d", "stories": [{"title": "t", "description": "d",
                                         "acceptance_criteria": ["c"], "tasks": [{"title": "x"}]}]}
OK_LINES = [
    _line(type="assistant", message={"content": [{"type": "text", "text": "revisão"}]}),
    _line(type="result", is_error=False, result="ok"),
]


def _fake(lines=OK_LINES, write=True, seen=None, boom=None):
    def runner(cmd, cwd):
        if seen is not None:
            seen["cwd"] = cwd
            seen["files"] = sorted(p.name for p in cwd.iterdir())
            seen["bytes"] = {p.name: p.read_bytes() for p in cwd.iterdir()}
        if write:
            (cwd / "stories.json").write_text(json.dumps(STORIES), encoding="utf-8")
            (cwd / "historias.pdf").write_bytes(b"%PDF-fake")
        if boom:
            raise boom
        yield from lines
    return runner


def test_review_spec_returns_text_stories_pdf():
    events = []
    res = claude_cli.review_spec(b"spec", "a.pdf", on_event=events.append,
                                 runner=_fake(), exe=Path("claude.exe"))
    assert res.text == "revisão" and res.stories == STORIES and res.pdf == b"%PDF-fake"
    assert [e.kind for e in events] == ["text", "result"]


def test_review_spec_writes_spec_with_suffix():
    seen = {}
    claude_cli.review_spec(b"conteudo", "Minha Spec.PDF", runner=_fake(seen=seen), exe=Path("c"))
    assert seen["bytes"] == {"spec.pdf": b"conteudo"}


def test_review_spec_cleans_temp_dir_on_success_and_failure():
    seen = {}
    claude_cli.review_spec(b"x", "a.txt", runner=_fake(seen=seen), exe=Path("c"))
    assert not seen["cwd"].exists()
    seen2 = {}
    with pytest.raises(ClaudeCliError):
        claude_cli.review_spec(b"x", "a.txt", runner=_fake(seen=seen2, boom=OSError("x")), exe=Path("c"))
    assert not seen2["cwd"].exists()


def test_review_spec_missing_outputs_fails():
    with pytest.raises(ClaudeCliError) as err:
        claude_cli.review_spec(b"x", "a.txt", runner=_fake(write=False), exe=Path("c"))
    assert "stories.json" in str(err.value) and "historias.pdf" in str(err.value)


def test_review_spec_no_result_event_fails():
    with pytest.raises(ClaudeCliError):
        claude_cli.review_spec(b"x", "a.txt", runner=_fake(lines=OK_LINES[:1]), exe=Path("c"))


def test_review_spec_auth_error_propagates():
    bad = [_line(type="result", is_error=True, result="Failed to authenticate: OAuth session expired")]
    with pytest.raises(ClaudeCliError) as err:
        claude_cli.review_spec(b"x", "a.txt", runner=_fake(lines=bad), exe=Path("c"))
    assert err.value.kind == "auth"
