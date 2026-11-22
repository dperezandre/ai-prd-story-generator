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


# ---- HTTP client -----------------------------------------------------------------------------

import base64  # noqa: E402
import json  # noqa: E402

import httpx  # noqa: E402

from src.azure_devops import AzureDevOpsClient, AzureDevOpsError  # noqa: E402

PAT = "s3cr3t-pat-value"
TYPES = {"value": [{"name": "Epic"}, {"name": "Task"}, {"name": "User Story"}]}
FIELDS = {"value": [{"referenceName": f} for f in (
    "System.Title", "Microsoft.VSTS.Common.AcceptanceCriteria", "Microsoft.VSTS.Common.Priority",
    "Microsoft.VSTS.Scheduling.StoryPoints")]}


class Recorder:
    def __init__(self, handler):
        self.requests: list[httpx.Request] = []
        self._handler = handler

    def __call__(self, request):
        self.requests.append(request)
        return self._handler(request)

    def body(self, index=-1):
        return json.loads(self.requests[index].content)


def client_for(handler, **kw):
    rec = Recorder(handler)
    return AzureDevOpsClient("contoso", "Shop", PAT, transport=httpx.MockTransport(rec), **kw), rec


def respond(status=200, data=None, headers=None, text=None):
    if text is not None:
        return httpx.Response(status, text=text, headers=headers or {"content-type": "text/html"})
    return httpx.Response(status, json=data if data is not None else {}, headers=headers)


def an_item(**kw):
    base = dict(title="Story", description_html="<p>d</p>", acceptance_html="<p>ac</p>", priority=2,
                points=5, tags=["MoSCoW-Should", "Referral"], tasks=[])
    base.update(kw)
    return PushItem(**base)


def test_story_type_prefers_user_story_then_pbi():
    client, rec = client_for(lambda r: respond(data=TYPES))
    assert client.story_type() == "User Story"
    assert "/contoso/Shop/_apis/wit/workitemtypes" in str(rec.requests[0].url)
    assert "api-version=7.1" in str(rec.requests[0].url)
    scrum = {"value": [{"name": "Task"}, {"name": "Product Backlog Item"}, {"name": "Bug"}]}
    client, _ = client_for(lambda r: respond(data=scrum))
    assert client.story_type() == "Product Backlog Item"


def test_story_type_without_known_type_is_validation_error():
    client, _ = client_for(lambda r: respond(data={"value": [{"name": "Task"}]}))
    with pytest.raises(AzureDevOpsError) as err:
        client.story_type()
    assert err.value.kind == "validation"


def test_available_fields_reads_reference_names():
    client, rec = client_for(lambda r: respond(data=FIELDS))
    assert "Microsoft.VSTS.Scheduling.StoryPoints" in client.available_fields("User Story")
    assert "/workitemtypes/User%20Story/fields" in str(rec.requests[0].url)


def create_story_request(available, item=None, **kw):
    client, rec = client_for(lambda r: respond(data={"id": 41}), **kw)
    story_id = client.create_story(item or an_item(), "User Story", available)
    return story_id, rec


def ops_by_path(rec):
    return {op["path"]: op["value"] for op in rec.body() if op["op"] == "add"}


def test_create_story_sends_fields_and_json_patch_content_type():
    story_id, rec = create_story_request(
        {"Microsoft.VSTS.Common.AcceptanceCriteria", "Microsoft.VSTS.Common.Priority",
         "Microsoft.VSTS.Scheduling.StoryPoints"})
    request = rec.requests[0]
    assert story_id == 41 and request.method == "POST"
    assert "/contoso/Shop/_apis/wit/workitems/$User%20Story" in str(request.url)
    assert request.headers["content-type"] == "application/json-patch+json"
    ops = ops_by_path(rec)
    assert ops["/fields/System.Title"] == "Story" and ops["/fields/System.Description"] == "<p>d</p>"
    assert ops["/fields/Microsoft.VSTS.Common.AcceptanceCriteria"] == "<p>ac</p>"
    assert ops["/fields/Microsoft.VSTS.Common.Priority"] == 2
    assert ops["/fields/Microsoft.VSTS.Scheduling.StoryPoints"] == 5
    assert ops["/fields/System.Tags"] == "MoSCoW-Should; Referral"


def test_create_story_sends_only_available_fields():
    _, rec = create_story_request(set())
    paths = set(ops_by_path(rec))
    assert paths == {"/fields/System.Title", "/fields/System.Description", "/fields/System.Tags"}


def test_create_story_uses_effort_when_no_story_points():
    _, rec = create_story_request({"Microsoft.VSTS.Scheduling.Effort"})
    ops = ops_by_path(rec)
    assert ops["/fields/Microsoft.VSTS.Scheduling.Effort"] == 5
    assert "/fields/Microsoft.VSTS.Scheduling.StoryPoints" not in ops


def test_create_story_omits_priority_points_and_tags_when_item_has_none():
    _, rec = create_story_request(
        {"Microsoft.VSTS.Common.Priority", "Microsoft.VSTS.Scheduling.StoryPoints"},
        item=an_item(priority=None, points=None, tags=[], acceptance_html=""))
    assert set(ops_by_path(rec)) == {"/fields/System.Title", "/fields/System.Description"}


def test_area_and_iteration_paths_are_sent_when_given():
    _, rec = create_story_request(set(), area="Shop\\Team A", iteration="Shop\\Sprint 1")
    ops = ops_by_path(rec)
    assert ops["/fields/System.AreaPath"] == "Shop\\Team A"
    assert ops["/fields/System.IterationPath"] == "Shop\\Sprint 1"


def test_create_task_links_parent_with_hierarchy_reverse():
    client, rec = client_for(lambda r: respond(data={"id": 42}))
    task_id = client.create_task(PushTask("Do it", "<p>x</p>"), parent_id=41)
    assert task_id == 42
    assert "/_apis/wit/workitems/$Task" in str(rec.requests[0].url)
    ops = rec.body()
    link = next(op for op in ops if op["path"] == "/relations/-")
    assert link["value"]["rel"] == "System.LinkTypes.Hierarchy-Reverse"
    assert link["value"]["url"].endswith("/_apis/wit/workItems/41")
    assert ops_by_path(rec)["/fields/System.Title"] == "Do it"


def test_auth_header_is_basic_with_empty_user():
    client, rec = client_for(lambda r: respond(data=TYPES))
    client.story_type()
    expected = "Basic " + base64.b64encode(f":{PAT}".encode()).decode()
    assert rec.requests[0].headers["authorization"] == expected


def test_203_html_response_is_auth_error():
    client, _ = client_for(lambda r: respond(203, text="<html>Sign in</html>"))
    with pytest.raises(AzureDevOpsError) as err:
        client.story_type()
    assert err.value.kind == "auth"


def test_200_with_html_body_is_auth_error():
    client, _ = client_for(lambda r: respond(200, text="<html>Sign in</html>"))
    with pytest.raises(AzureDevOpsError) as err:
        client.story_type()
    assert err.value.kind == "auth"


@pytest.mark.parametrize("status,kind", [(401, "auth"), (403, "auth"), (404, "not_found"), (400, "validation")])
def test_error_status_maps_to_kind(status, kind):
    client, _ = client_for(lambda r: respond(status, data={"message": "nope"}))
    with pytest.raises(AzureDevOpsError) as err:
        client.story_type()
    assert err.value.kind == kind


def test_429_retries_once_then_succeeds(monkeypatch):
    monkeypatch.setattr("src.azure_devops._sleep", lambda s: None)
    replies = iter([respond(429, headers={"retry-after": "0"}), respond(data=TYPES)])
    client, rec = client_for(lambda r: next(replies))
    assert client.story_type() == "User Story"
    assert len(rec.requests) == 2


def test_429_twice_raises_rate_limit(monkeypatch):
    monkeypatch.setattr("src.azure_devops._sleep", lambda s: None)
    client, rec = client_for(lambda r: respond(429, headers={"retry-after": "0"}))
    with pytest.raises(AzureDevOpsError) as err:
        client.story_type()
    assert err.value.kind == "rate_limit" and len(rec.requests) == 2


def test_5xx_retries_once_then_network_error(monkeypatch):
    monkeypatch.setattr("src.azure_devops._sleep", lambda s: None)
    client, rec = client_for(lambda r: respond(503, data={}))
    with pytest.raises(AzureDevOpsError) as err:
        client.story_type()
    assert err.value.kind == "network" and len(rec.requests) == 2


def test_network_error_is_network_kind():
    def boom(request):
        raise httpx.ConnectError("no route")
    client, _ = client_for(boom)
    with pytest.raises(AzureDevOpsError) as err:
        client.story_type()
    assert err.value.kind == "network"


def test_timeout_is_network_kind():
    def slow(request):
        raise httpx.ReadTimeout("slow")
    client, _ = client_for(slow)
    with pytest.raises(AzureDevOpsError) as err:
        client.story_type()
    assert err.value.kind == "network" and "timed out" in str(err.value)


def test_error_messages_never_contain_the_pat():
    client, _ = client_for(lambda r: respond(400, data={"message": f"bad value for {PAT} in field"}))
    with pytest.raises(AzureDevOpsError) as err:
        client.story_type()
    assert PAT not in str(err.value) and "[token]" in str(err.value)


def test_work_item_url_points_to_the_project_board():
    client, _ = client_for(lambda r: respond())
    assert client.work_item_url(41) == "https://dev.azure.com/contoso/Shop/_workitems/edit/41"
