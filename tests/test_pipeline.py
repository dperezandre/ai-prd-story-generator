import json

import pytest

from src.models import PipelineResult
from src.pipeline import MAX_IDEA_CHARS, PipelineError, parse_json_response, run_pipeline
from src.providers import ProviderError
from tests.conftest import FakeProvider

PRD = {"title": "Referral", "problem": "P", "goals": ["g"], "requirements": ["The system must X"]}


def story(i, **kw):
    base = dict(id=f"S{i}", epic="E1", title=f"t{i}", as_a="user", i_want="x", so_that="y",
                priority="Must", points=3, prd_ref="r")
    base.update(kw)
    return base


SCORES = dict(independent=2, negotiable=2, valuable=2, estimable=2, small=2, testable=2)
BAD = dict(SCORES, small=0)
SCEN = [{"name": "n", "given": ["a"], "when": ["b"], "then": ["c"]}]


def good_responses():
    return [
        json.dumps(PRD),
        json.dumps({"stories": [story(1), story(2, points=13)]}),
        json.dumps({"reviews": [
            {"story_id": "S1", "scores": SCORES, "verdict": "pass", "comment": "ok"},
            {"story_id": "S2", "scores": BAD, "verdict": "rewrite", "comment": "big",
             "rewrite": story(2, points=5, title="smaller"), "scores_after": SCORES},
        ]}),
        json.dumps({"scenarios": {"S1": SCEN, "S2": SCEN}}),
    ]


def run(responses, idea="an idea", **kw):
    p = FakeProvider(responses)
    return run_pipeline(idea, "en", p, **kw), p


def test_happy_path_runs_four_steps_in_order():
    seen = []
    res, p = run(good_responses(), on_step=lambda step, r: seen.append(step))
    assert seen == ["prd", "stories", "invest", "gherkin"]
    assert len(p.calls) == 4
    assert res.prd.title == "Referral"
    assert [s.id for s in res.stories] == ["S1", "S2"]
    assert all(s.scenarios for s in res.stories)


def test_system_prompts_come_from_language_folder():
    _, p = run(good_responses())
    assert "Product Manager" in p.calls[0][0]
    assert "gatekeeper" in p.calls[2][0]


def test_stories_step_receives_prd_not_idea():
    _, p = run(good_responses(), idea="SECRET-IDEA-TEXT")
    assert p.calls[0][1] == "SECRET-IDEA-TEXT"
    assert "SECRET-IDEA-TEXT" not in p.calls[1][1]
    assert "Referral" in p.calls[1][1]


def test_rewrite_replaces_story_and_keeps_scores():
    res, _ = run(good_responses())
    s2 = next(s for s in res.stories if s.id == "S2")
    assert s2.title == "smaller" and s2.points == 5
    r2 = next(r for r in res.reviews if r.story_id == "S2")
    assert r2.scores.small == 0 and r2.scores_after.small == 2


def test_invalid_json_retries_once_with_error_appended():
    responses = ["not json at all"] + good_responses()
    res, p = run(responses)
    assert res.prd is not None
    assert len(p.calls) == 5
    assert p.calls[1][1].startswith(p.calls[0][1])
    assert "invalid" in p.calls[1][1].lower()


def test_second_invalid_json_raises_pipeline_error_with_partial():
    with pytest.raises(PipelineError) as exc:
        run(["bad", "still bad"])
    assert exc.value.step == "prd"
    assert exc.value.partial.prd is None


def test_fenced_json_is_parsed():
    assert parse_json_response('Here you go:\n```json\n{"a": 1}\n```\nBye') == {"a": 1}
    res, _ = run([f"```json\n{r}\n```" for r in good_responses()])
    assert res.prd.title == "Referral"


@pytest.mark.parametrize("idea", ["", "   \n\t "])
def test_empty_idea_raises_without_calling_provider(idea):
    p = FakeProvider([])
    with pytest.raises(ValueError):
        run_pipeline(idea, "en", p)
    assert p.calls == []


def test_idea_over_max_raises():
    p = FakeProvider([])
    with pytest.raises(ValueError):
        run_pipeline("x" * (MAX_IDEA_CHARS + 1), "en", p)
    assert p.calls == []


def test_provider_error_midway_keeps_completed_steps():
    key = "sk-SECRET"
    responses = good_responses()[:1] + [ProviderError("Groq rate limit reached.", "rate_limit")]
    with pytest.raises(PipelineError) as exc:
        run(responses)
    err = exc.value
    assert err.step == "stories"
    assert err.partial.prd is not None and err.partial.stories == []
    assert key not in str(err)
    assert isinstance(err.partial, PipelineResult)


def test_unknown_ids_ignored_and_missing_story_kept():
    r = good_responses()
    r[2] = json.dumps({"reviews": [
        {"story_id": "S1", "scores": SCORES, "verdict": "pass", "comment": "ok"},
        {"story_id": "S99", "scores": SCORES, "verdict": "pass", "comment": "ghost"}]})
    r[3] = json.dumps({"scenarios": {"S1": SCEN, "S99": SCEN}})
    res, _ = run(r)
    assert [x.story_id for x in res.reviews] == ["S1"]
    assert [s.id for s in res.stories] == ["S1", "S2"]
    s2 = res.stories[1]
    assert s2.scenarios == [] and res.stories[0].scenarios


def test_rewrite_with_wrong_id_still_targets_reviewed_story():
    r = good_responses()
    r[2] = json.dumps({"reviews": [
        {"story_id": "S2", "scores": BAD, "verdict": "rewrite", "comment": "c",
         "rewrite": story(7, title="renamed"), "scores_after": SCORES}]})
    res, _ = run(r)
    assert [s.id for s in res.stories] == ["S1", "S2"]
    assert res.stories[1].title == "renamed"
