from pathlib import Path

import pytest

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
FILES = ["01_prd.md", "02_stories.md", "03_invest_review.md", "04_gherkin.md"]
HEADINGS = {
    "en": ["# Persona", "# Task", "# Rules", "# Output format", "# Examples"],
    "pt-BR": ["# Persona", "# Tarefa", "# Regras", "# Formato de saída", "# Exemplos"],
}
OUTPUT_KEYS = {
    "01_prd.md": ["title", "problem", "personas", "goals", "success_metrics", "scope_in",
                  "scope_out", "requirements", "risks", "assumptions", "open_questions"],
    "02_stories.md": ["stories", "id", "epic", "as_a", "i_want", "so_that", "priority",
                      "points", "prd_ref"],
    "03_invest_review.md": ["reviews", "story_id", "scores", "independent", "negotiable",
                            "valuable", "estimable", "small", "testable", "verdict",
                            "rewrite", "scores_after"],
    "04_gherkin.md": ["scenarios", "name", "given", "when", "then"],
}


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
@pytest.mark.parametrize("file", FILES)
def test_prompt_has_required_sections_and_json_keys(lang, file):
    path = PROMPTS / lang / file
    assert path.exists(), path
    text = path.read_text(encoding="utf-8")
    for heading in HEADINGS[lang]:
        assert heading in text, f"{path}: missing {heading}"
    out = text.split(HEADINGS[lang][3], 1)[1].split(HEADINGS[lang][4], 1)[0]
    for key in OUTPUT_KEYS[file]:
        assert f'"{key}"' in out, f"{path}: output format lacks {key}"


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
def test_review_prompt_defines_small_threshold(lang):
    text = (PROMPTS / lang / "03_invest_review.md").read_text(encoding="utf-8")
    assert "8" in text
