import csv
import io
from pathlib import Path

import pytest

from src.demo import DEMO_CASES, load_demo
from src.exporters import azure_devops_csv, jira_csv

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
COMBOS = [(c, lang) for c in DEMO_CASES for lang in ("en", "pt-BR")]


def test_demo_cases_defined_for_both_languages():
    assert set(DEMO_CASES) == {"referral", "abandoned_cart"}
    for texts in DEMO_CASES.values():
        assert set(texts) == {"en", "pt-BR"} and all(texts.values())


@pytest.mark.parametrize("case,lang", COMBOS)
def test_load_demo_returns_complete_result(case, lang):
    r = load_demo(case, lang)
    assert r.language == lang and r.prd is not None
    assert len(r.stories) >= 3
    assert all(s.scenarios for s in r.stories)
    assert any(rv.rewrite is not None and rv.scores_after is not None for rv in r.reviews)
    assert r.idea == DEMO_CASES[case][lang]


def test_load_demo_unknown_case_raises_key_error():
    with pytest.raises(KeyError):
        load_demo("nope", "en")


@pytest.mark.parametrize("case,lang", COMBOS)
def test_example_csvs_match_exporters_and_parse(case, lang):
    r = load_demo(case, lang)
    for suffix, exporter in (("azure", azure_devops_csv), ("jira", jira_csv)):
        with open(EXAMPLES / f"{case}.{lang}.{suffix}.csv", encoding="utf-8", newline="") as fh:
            text = fh.read()
        assert text == exporter(r)
        assert len(list(csv.reader(io.StringIO(text, newline="")))) > 1


@pytest.mark.parametrize("case,lang", COMBOS)
def test_every_example_story_has_two_to_six_tasks_without_estimates(case, lang):
    r = load_demo(case, lang)
    for s in r.stories:
        assert 2 <= len(s.tasks) <= 6, s.id
        for t in s.tasks:
            assert t.title and t.description
            assert not any(w in (t.title + t.description).lower() for w in ("estimate", "estimativa", "story point", "pontos"))
    rewritten = [rv.rewrite for rv in r.reviews if rv.rewrite]
    assert all(rw.tasks for rw in rewritten)
