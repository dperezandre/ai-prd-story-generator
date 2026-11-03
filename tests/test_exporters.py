import csv
import io

import pytest

from src.exporters import azure_devops_csv, jira_csv, prd_markdown
from src.models import PRD, PipelineResult, Scenario, Story

AZURE_HEADER = ["Work Item Type", "Title 1", "Title 2", "Description",
                "Acceptance Criteria", "Priority", "Story Points", "Tags"]
JIRA_HEADER = ["Issue Id", "Issue Type", "Summary", "Description", "Priority", "Parent", "Labels"]


def story(i, epic="Referral", **kw):
    base = dict(id=f"S{i}", epic=epic, title=f"Story {i}", as_a="customer", i_want="x",
                so_that="y", priority="Must", points=3, prd_ref="r",
                scenarios=[Scenario(name="Rule", given=["a"], when=["b"], then=["c"])])
    base.update(kw)
    return Story(**base)


def result(stories, language="en"):
    return PipelineResult(idea="i", language=language,
                          prd=PRD(title="Feature", problem="P", goals=["g"]), stories=stories)


def rows(text):
    return list(csv.reader(io.StringIO(text, newline="")))


def test_azure_header_exact():
    assert rows(azure_devops_csv(result([story(1)])))[0] == AZURE_HEADER


def test_azure_epic_and_story_rows_use_title_levels():
    data = rows(azure_devops_csv(result([story(1), story(2), story(3, epic="Other")])))
    body = [dict(zip(AZURE_HEADER, r)) for r in data[1:]]
    assert [r["Work Item Type"] for r in body] == ["Epic", "User Story", "User Story", "Epic", "User Story"]
    assert body[0]["Title 1"] == "Referral" and body[0]["Title 2"] == ""
    assert body[1]["Title 2"] == "Story 1" and body[1]["Title 1"] == ""
    assert sum(r["Work Item Type"] == "Epic" for r in body) == 2


def test_azure_priority_points_tags_and_html_acceptance():
    s = story(1, priority="Won't", points=5)
    row = dict(zip(AZURE_HEADER, rows(azure_devops_csv(result([s])))[2]))
    assert row["Priority"] == "4" and row["Story Points"] == "5" and row["Tags"] == "MoSCoW-Wont"
    assert "Scenario: Rule" in row["Acceptance Criteria"] and "<br>" in row["Acceptance Criteria"]
    assert row["Description"].startswith("<p>As a customer")


def test_azure_pt_description_and_gherkin_keywords():
    row = dict(zip(AZURE_HEADER, rows(azure_devops_csv(result([story(1)], "pt-BR")))[2]))
    assert "Como customer" in row["Description"] and "Cenário: Rule" in row["Acceptance Criteria"]


def test_jira_header_and_parent_links_epics_first():
    data = rows(jira_csv(result([story(1), story(2), story(3, epic="Other")])))
    assert data[0] == JIRA_HEADER
    body = [dict(zip(JIRA_HEADER, r)) for r in data[1:]]
    assert [r["Issue Type"] for r in body] == ["Epic", "Story", "Story", "Epic", "Story"]
    ids = [r["Issue Id"] for r in body]
    assert len(set(ids)) == 5
    assert body[1]["Parent"] == body[2]["Parent"] == body[0]["Issue Id"]
    assert body[4]["Parent"] == body[3]["Issue Id"]
    assert body[0]["Parent"] == ""
    assert body[1]["Priority"] == "Highest" and body[1]["Labels"] == "moscow-must"
    assert "Scenario: Rule" in body[1]["Description"]


@pytest.mark.parametrize("exporter", [azure_devops_csv, jira_csv])
def test_special_characters_roundtrip(exporter):
    title = 'Cobrança, "parcelada"\nem 3x — ação'
    data = rows(exporter(result([story(1, title=title)])))
    assert any(title in cell for r in data for cell in r)


@pytest.mark.parametrize("exporter", [azure_devops_csv, jira_csv])
@pytest.mark.parametrize("lead", ["=", "+", "-", "@"])
def test_formula_injection_is_neutralised(exporter, lead):
    data = rows(exporter(result([story(1, title=f'{lead}HYPERLINK("http://x")')])))
    cells = [c for r in data for c in r if "HYPERLINK" in c]
    assert cells and all(c.startswith("'") for c in cells)


@pytest.mark.parametrize("exporter", [azure_devops_csv, jira_csv])
def test_no_stories_gives_header_only(exporter):
    data = rows(exporter(result([])))
    assert len(data) == 1


def test_html_in_story_text_is_escaped_for_azure():
    row = dict(zip(AZURE_HEADER, rows(azure_devops_csv(result([story(1, i_want="<script>x</script>")])))[2]))
    assert "<script>" not in row["Description"] and "&lt;script&gt;" in row["Description"]


def test_prd_markdown_includes_prd_stories_and_gherkin():
    md = prd_markdown(result([story(1)]))
    assert "# Feature" in md and "## User stories" in md and "Scenario: Rule" in md
    assert "## Histórias de usuário" in prd_markdown(result([story(1)], "pt-BR"))


def test_prd_markdown_without_prd_is_empty():
    assert prd_markdown(PipelineResult(idea="i", language="en")) == ""
