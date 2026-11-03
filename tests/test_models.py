import pytest
from pydantic import ValidationError

from src.models import PRD, InvestScores, PipelineResult, Scenario, Story


def make_story(**kw):
    base = dict(id="S1", epic="E1", title="t", as_a="user", i_want="x", so_that="y",
                priority="Must", points=3, prd_ref="R1")
    base.update(kw)
    return Story(**base)


def test_scores_reject_out_of_range():
    with pytest.raises(ValidationError):
        InvestScores(independent=3, negotiable=0, valuable=0, estimable=0, small=0, testable=0)


def test_scores_total():
    s = InvestScores(independent=2, negotiable=1, valuable=2, estimable=0, small=1, testable=2)
    assert s.total == 8


def test_gherkin_en():
    sc = Scenario(name="x", given=["a", "a2"], when=["b"], then=["c", "d"])
    assert sc.to_gherkin("en") == (
        "Scenario: x\n  Given a\n  And a2\n  When b\n  Then c\n  And d"
    )


def test_gherkin_pt():
    sc = Scenario(name="x", given=["a"], when=["b"], then=["c", "d"])
    out = sc.to_gherkin("pt-BR")
    assert out.startswith("# language: pt\nCenário: x")
    assert "Dado a" in out and "Quando b" in out and "Então c" in out and "E d" in out


def test_story_text_localized():
    s = make_story()
    assert s.to_text("en") == "As a user, I want x so that y"
    assert s.to_text("pt-BR") == "Como user, quero x para y"


def test_prd_markdown_omits_empty_lists_and_localizes_headings():
    prd = PRD(title="T", problem="P", goals=["g1"])
    en = prd.to_markdown("en")
    pt = prd.to_markdown("pt-BR")
    assert "## Goals" in en and "- g1" in en and "## Risks" not in en
    assert "## Objetivos" in pt and "## Riscos" not in pt


def test_result_roundtrips_json():
    r = PipelineResult(idea="i", language="en", prd=PRD(title="T", problem="P"),
                       stories=[make_story(scenarios=[Scenario(name="n", given=["a"], when=["b"], then=["c"])])])
    assert PipelineResult.model_validate_json(r.model_dump_json()) == r
