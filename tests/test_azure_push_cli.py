import json

import httpx
import pytest

from scripts.azure_push import main
from src.models import PRD, PipelineResult, Scenario, Story, Task
from tests.test_azure_devops import PAT, SKILL_JSON, FakeAzure

ENV = {"AZDO_PAT": PAT}


def result_json():
    story = Story(id="S1", epic="E", title="Story one", as_a="user", i_want="x", so_that="y",
                  priority="Must", points=3, prd_ref="r",
                  scenarios=[Scenario(name="n", given=["a"], when=["b"], then=["c"])],
                  tasks=[Task(title="Task one", description="d"), Task(title="Task two")])
    return PipelineResult(idea="i", language="en", prd=PRD(title="F", problem="P"),
                          stories=[story]).model_dump_json()


def write(tmp_path, text, name="stories.json"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def run(tmp_path, *extra, text=None, transport=None, environ=ENV):
    path = write(tmp_path, text if text is not None else json.dumps(SKILL_JSON))
    argv = [str(path), "--org", "contoso", "--project", "Shop", *extra]
    return main(argv, transport=transport, environ=environ), path


def test_preview_by_default_prints_plan_and_sends_nothing(tmp_path, capsys):
    def explode(request):
        raise AssertionError("preview must not call Azure")
    code, _ = run(tmp_path, transport=httpx.MockTransport(explode))
    out = capsys.readouterr().out
    assert code == 0
    assert "Informar o peso" in out and "Criar o campo" in out and "Testar" in out
    assert "preview" in out.lower() and "--yes" in out


def test_preview_does_not_need_a_token(tmp_path):
    code, _ = run(tmp_path, environ={})
    assert code == 0


def test_yes_pushes_and_prints_urls(tmp_path, capsys):
    azure = FakeAzure()
    code, _ = run(tmp_path, "--yes", transport=httpx.MockTransport(azure))
    out = capsys.readouterr().out
    assert code == 0
    assert [f["/fields/System.Title"] for _, f in azure.created] == ["Informar o peso", "Criar o campo", "Testar"]
    assert "https://dev.azure.com/contoso/Shop/_workitems/edit/101" in out
    assert "1 stories" in out and "2 tasks" in out


def test_missing_pat_exits_2_without_printing_it(tmp_path, capsys):
    code, _ = run(tmp_path, "--yes", environ={})
    captured = capsys.readouterr()
    assert code == 2
    assert "AZDO_PAT" in captured.err and PAT not in captured.out + captured.err


def test_accepts_pipeline_result_and_skill_json(tmp_path, capsys):
    code, _ = run(tmp_path, text=result_json())
    assert code == 0 and "Story one" in capsys.readouterr().out
    code, _ = run(tmp_path)
    assert code == 0 and "Informar o peso" in capsys.readouterr().out


def test_input_without_tasks_exits_2(tmp_path, capsys):
    bad = {"stories": [{k: v for k, v in SKILL_JSON["stories"][0].items() if k != "tasks"}]}
    code, _ = run(tmp_path, text=json.dumps(bad))
    assert code == 2 and "tasks" in capsys.readouterr().err


def test_azure_error_exits_3_and_message_has_no_token(tmp_path, capsys):
    transport = httpx.MockTransport(lambda r: httpx.Response(
        400, json={"message": f"bad {PAT}"}))
    code, _ = run(tmp_path, "--yes", transport=transport)
    captured = capsys.readouterr()
    assert code == 3 and PAT not in captured.out + captured.err


def test_ledger_defaults_next_to_input_and_rerun_skips(tmp_path, capsys):
    azure = FakeAzure()
    transport = httpx.MockTransport(azure)
    code, path = run(tmp_path, "--yes", transport=transport)
    ledger = path.with_name("stories.azdo-ledger.json")
    assert code == 0 and ledger.exists()
    capsys.readouterr()
    code, _ = run(tmp_path, "--yes", transport=transport)
    assert code == 0 and len(azure.created) == 3 and "skipped" in capsys.readouterr().out.lower()


def test_force_resends(tmp_path):
    azure = FakeAzure()
    transport = httpx.MockTransport(azure)
    run(tmp_path, "--yes", transport=transport)
    run(tmp_path, "--yes", "--force", transport=transport)
    assert len(azure.created) == 6


def test_explicit_ledger_path(tmp_path):
    custom = tmp_path / "elsewhere" / "ledger.json"
    code, _ = run(tmp_path, "--yes", "--ledger", str(custom), transport=httpx.MockTransport(FakeAzure()))
    assert code == 0 and custom.exists()


def test_missing_input_file_exits_2(tmp_path, capsys):
    code = main([str(tmp_path / "nope.json"), "--org", "o", "--project", "p"], environ=ENV)
    assert code == 2 and "nope.json" in capsys.readouterr().err
