import pytest

from src.azure_devops import (Ledger, PlanLine, PushItem, PushTask, item_key, items_from_result,
                              items_from_stories_json, normalize_organization, plan)
from src.models import PRD, PipelineResult, Scenario, Story, Task

ORG, PROJECT = "contoso", "Shop"


def story(i, **kw):
    base = dict(id=f"S{i}", epic="Referral", title=f"Story {i}", as_a="customer", i_want="x <b>",
                so_that="y", priority="Must", points=3, prd_ref="r",
                scenarios=[Scenario(name="Rule", given=["a"], when=["b"], then=["c"])],
                tasks=[Task(title=f"Task {i}.1", description="Does <it>"), Task(title=f"Task {i}.2")])
    base.update(kw)
    return Story(**base)


def result(stories, language="en"):
    return PipelineResult(idea="i", language=language, prd=PRD(title="F", problem="P"), stories=stories)


SKILL_JSON = {
    "document": "Spec",
    "stories": [
        {"title": "Informar o peso", "description": "Como modelador, quero x, para y.",
         "acceptance_criteria": ["Cenário: a\n  Dado b", "[A DEFINIR] faixa"],
         "tasks": [{"title": "Criar o campo", "description": "Entrega o cenário a"}, {"title": "Testar"}]},
    ],
}


def test_items_from_result_maps_priority_tags_and_escaped_html():
    item = items_from_result(result([story(1, priority="Won't", points=5)]))[0]
    assert item.title == "Story 1" and item.priority == 4 and item.points == 5
    assert item.tags == ["MoSCoW-Wont", "Referral"]
    assert item.description_html == "<p>As a customer, I want x &lt;b&gt; so that y</p>"
    assert "Scenario: Rule" in item.acceptance_html and "<br>" in item.acceptance_html
    assert item.tasks[0] == PushTask(title="Task 1.1", description="<p>Does &lt;it&gt;</p>")
    assert item.tasks[1].description == ""


def test_items_from_result_pt_description():
    item = items_from_result(result([story(1)], "pt-BR"))[0]
    assert item.description_html.startswith("<p>Como customer")


def test_items_from_stories_json_keeps_tasks_and_omits_priority():
    item = items_from_stories_json(SKILL_JSON)[0]
    assert item.title == "Informar o peso" and item.priority is None and item.points is None
    assert item.tags == []
    assert item.description_html == "<p>Como modelador, quero x, para y.</p>"
    assert item.acceptance_html == "<p>Cenário: a<br>  Dado b</p><p>[A DEFINIR] faixa</p>"
    assert [t.title for t in item.tasks] == ["Criar o campo", "Testar"]
    assert item.tasks[1].description == ""


@pytest.mark.parametrize("missing", ["title", "description", "acceptance_criteria", "tasks"])
def test_stories_json_missing_field_is_rejected(missing):
    bad = {"stories": [{k: v for k, v in SKILL_JSON["stories"][0].items() if k != missing}]}
    with pytest.raises(ValueError, match=missing):
        items_from_stories_json(bad)


def test_item_key_is_stable_and_differs_for_same_title_different_text():
    a, b = items_from_result(result([story(1), story(2, title="Story 1", i_want="other")]))
    assert item_key(ORG, PROJECT, a) == item_key(ORG, PROJECT, a)
    assert item_key(ORG, PROJECT, a) != item_key(ORG, PROJECT, b)
    assert item_key(ORG, PROJECT, a) != item_key("other", PROJECT, a)
    assert item_key(ORG, PROJECT, a) != item_key(ORG, "Other", a)


@pytest.mark.parametrize("raw", ["contoso", "dev.azure.com/contoso", "https://dev.azure.com/contoso",
                                 "https://dev.azure.com/contoso/", " Contoso ".lower()])
def test_normalize_organization_accepts_name_domain_and_url(raw):
    assert normalize_organization(raw) == "contoso"


def test_normalize_organization_accepts_legacy_visualstudio_host():
    assert normalize_organization("https://contoso.visualstudio.com/") == "contoso"


def test_normalize_organization_rejects_empty():
    with pytest.raises(ValueError):
        normalize_organization("  ")


def test_plan_marks_new_sent_and_partial():
    items = items_from_result(result([story(1), story(2), story(3)]))
    ledger = Ledger.load(None, ORG, PROJECT)
    ledger.record(items[1], story_id=10, task_ids=[11, 12])
    ledger.record(items[2], story_id=20, task_ids=[21])
    lines = plan(items, ledger)
    assert [(ln.story_title, ln.status) for ln in lines] == [
        ("Story 1", "new"), ("Story 2", "sent"), ("Story 3", "partial")]
    assert lines[0].task_titles == ["Task 1.1", "Task 1.2"]
    assert isinstance(lines[0], PlanLine) and lines[0].warning is None


def test_plan_warns_story_without_tasks():
    items = items_from_result(result([story(1, tasks=[])]))
    line = plan(items, Ledger.load(None, ORG, PROJECT))[0]
    assert line.warning and "task" in line.warning.lower()


def test_ledger_roundtrip_and_missing_file_is_empty(tmp_path):
    path = tmp_path / "ledger.json"
    empty = Ledger.load(path, ORG, PROJECT)
    item = items_from_result(result([story(1)]))[0]
    assert empty.get(item) is None
    empty.record(item, story_id=7, task_ids=[8, 9])
    empty.save()
    again = Ledger.load(path, ORG, PROJECT)
    assert again.get(item) == {"story_id": 7, "task_ids": [8, 9]}
    assert Ledger.load(path, ORG, "OtherProject").get(item) is None


def test_ledger_without_path_never_touches_disk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ledger = Ledger.load(None, ORG, PROJECT)
    ledger.record(items_from_result(result([story(1)]))[0], 1, [])
    ledger.save()
    assert list(tmp_path.iterdir()) == []


def test_corrupt_ledger_raises_value_error(tmp_path):
    path = tmp_path / "ledger.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="ledger"):
        Ledger.load(path, ORG, PROJECT)
