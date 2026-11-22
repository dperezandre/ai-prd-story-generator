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


# ---- Azure DevOps section --------------------------------------------------------------------

PAT = "s3cr3t-app-pat"


from streamlit.proto.TextInput_pb2 import TextInput  # noqa: E402


class FakeAzureClient:
    """Stands in for AzureDevOpsClient: records what the app asks it to do."""

    instances: list = []
    fail = None

    def __init__(self, organization, project, pat, **kwargs):
        self.organization, self.project, self.pat = organization, project, pat
        self.stories, self.tasks = [], []
        FakeAzureClient.instances.append(self)

    def story_type(self):
        return "User Story"

    def available_fields(self, work_item_type):
        return set()

    def create_story(self, item, story_type, available):
        if FakeAzureClient.fail:
            raise FakeAzureClient.fail
        self.stories.append(item.title)
        return 500 + len(self.stories)

    def create_task(self, task, parent_id):
        self.tasks.append((task.title, parent_id))
        return 900 + len(self.tasks)

    def work_item_url(self, work_item_id):
        return f"https://dev.azure.com/{self.organization}/{self.project}/_workitems/edit/{work_item_id}"


def live_result(monkeypatch):
    import src.azure_devops
    from tests.test_pipeline import good_responses
    FakeAzureClient.instances, FakeAzureClient.fail = [], None
    monkeypatch.setattr(src.azure_devops, "AzureDevOpsClient", FakeAzureClient)
    return live_run(monkeypatch, good_responses())


def fill_azure(at, org="contoso", project="Shop", pat=PAT):
    by_key(at.text_input, "azdo_org").set_value(org).run()
    by_key(at.text_input, "azdo_project").set_value(project).run()
    by_key(at.text_input, "azdo_pat").set_value(pat).run()


def all_text(at):
    pieces = [e.value for group in (at.markdown, at.error, at.success, at.warning, at.info, at.caption)
              for e in group]
    return "\n".join(str(p) for p in pieces)


def test_azure_section_hidden_in_demo_mode():
    at = fresh()
    by_key(at.button, "generate").click().run()
    assert not at.exception
    assert not [e for e in at.text_input if e.key == "azdo_org"]


def test_azure_section_shown_for_live_results_with_password_token_field(monkeypatch):
    at = live_result(monkeypatch)
    assert not at.exception
    assert by_key(at.text_input, "azdo_pat").proto.type == TextInput.PASSWORD
    assert by_key(at.text_input, "azdo_org") and by_key(at.text_input, "azdo_project")


def test_preview_makes_no_request_and_lists_stories_and_tasks(monkeypatch):
    at = live_result(monkeypatch)
    fill_azure(at)
    by_key(at.button, "azdo_preview").click().run()
    assert not at.exception and FakeAzureClient.instances == []
    text = all_text(at)
    assert "t1" in text and "smaller" in text  # S2 is rewritten by the INVEST review


def test_send_button_disabled_until_preview(monkeypatch):
    at = live_result(monkeypatch)
    fill_azure(at)
    assert by_key(at.button, "azdo_send").disabled is True
    by_key(at.button, "azdo_preview").click().run()
    assert by_key(at.button, "azdo_send").disabled is False


def test_send_pushes_stories_and_tasks_and_shows_links(monkeypatch):
    at = live_result(monkeypatch)
    fill_azure(at)
    by_key(at.button, "azdo_preview").click().run()
    by_key(at.button, "azdo_send").click().run()
    assert not at.exception and not at.error
    client = FakeAzureClient.instances[0]
    assert client.pat == PAT and client.organization == "contoso" and client.project == "Shop"
    assert client.stories == ["t1", "smaller"]
    assert client.tasks == [("Build the endpoint", 501), ("Write the tests", 501), ("Build the endpoint", 502)]
    assert "https://dev.azure.com/contoso/Shop/_workitems/edit/501" in all_text(at)


def test_send_twice_does_not_duplicate(monkeypatch):
    at = live_result(monkeypatch)
    fill_azure(at)
    by_key(at.button, "azdo_preview").click().run()
    by_key(at.button, "azdo_send").click().run()
    by_key(at.button, "azdo_send").click().run()
    assert sum(len(c.stories) for c in FakeAzureClient.instances) == 2


def test_azure_error_is_shown_and_token_is_never_displayed(monkeypatch):
    from src.azure_devops import AzureDevOpsError
    at = live_result(monkeypatch)
    FakeAzureClient.fail = AzureDevOpsError("Azure DevOps rejected the token.", "auth")
    fill_azure(at)
    by_key(at.button, "azdo_preview").click().run()
    by_key(at.button, "azdo_send").click().run()
    assert not at.exception
    assert any("rejected the token" in e.value for e in at.error)
    assert PAT not in all_text(at)


def test_missing_fields_show_error_without_calling_azure(monkeypatch):
    at = live_result(monkeypatch)
    by_key(at.button, "azdo_preview").click().run()
    by_key(at.button, "azdo_send").click().run()
    assert not at.exception and FakeAzureClient.instances == []


def test_stories_tab_lists_each_story_tasks_in_demo_mode():
    at = fresh()
    by_key(at.button, "generate").click().run()
    assert not at.exception
    text = "\n".join(str(m.value) for m in at.markdown)
    assert "Gerar um código de indicação único por cliente" in text


def test_azure_preview_shows_the_no_tasks_warning(monkeypatch):
    import json

    import src.azure_devops
    from tests.test_pipeline import good_responses
    replies = good_responses()
    replies[4] = json.dumps({"tasks": {"S1": [{"title": "Only one", "description": "d"}]}})
    FakeAzureClient.instances, FakeAzureClient.fail = [], None
    monkeypatch.setattr(src.azure_devops, "AzureDevOpsClient", FakeAzureClient)
    at = live_run(monkeypatch, replies)
    by_key(at.button, "azdo_preview").click().run()
    assert "no tasks" in all_text(at).lower()
