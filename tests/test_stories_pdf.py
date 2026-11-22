import importlib.util
from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz")

_SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "po-spec-review" / "scripts" / "stories_pdf.py"
_spec = importlib.util.spec_from_file_location("stories_pdf", _SCRIPT)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
write_pdf = _module.write_pdf

DATA = {
    "document": "Cadastro de cliente",
    "stories": [
        {
            "title": "Informar o telefone no cadastro",
            "description": "Como atendente, quero informar o telefone, para contatar o cliente.",
            "acceptance_criteria": [
                "Cenário: Telefone vazio mantém o cadastro atual\n  Dado que o campo Telefone está vazio\n  Quando salvo o cadastro\n  Então o cadastro é salvo sem telefone",
                "[A DEFINIR] formato válido do telefone",
            ],
            "tasks": [
                {"title": "Criar o campo telefone", "description": "Entrega o cenário de telefone vazio"},
                {"title": "Testar o cadastro sem telefone", "description": "Cobre o caminho alternativo"},
            ],
        },
        {
            "title": "Segunda história",
            "description": "Como modelador, quero x, para y.",
            "acceptance_criteria": ["Cenário: a\n  Dado b"],
            "tasks": [{"title": "Fazer x", "description": ""}],
        },
    ],
}


def read_pdf(path):
    with fitz.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def test_pdf_has_title_description_and_criteria_for_each_story(tmp_path):
    out = tmp_path / "stories.pdf"
    write_pdf(DATA, out)
    text = read_pdf(out)
    for expected in ("Cadastro de cliente", "Informar o telefone no cadastro", "Segunda história",
                     "Título", "Descrição", "Critérios de aceite",
                     "Como atendente, quero informar o telefone", "Telefone vazio mantém o cadastro atual",
                     "[A DEFINIR] formato válido do telefone"):
        assert expected in text, expected
    assert text.count("Título") == 2 and text.count("Critérios de aceite") == 2


def test_story_missing_a_field_is_rejected(tmp_path):
    bad = {"document": "x", "stories": [{"title": "t", "description": "d"}]}
    with pytest.raises(ValueError, match="acceptance_criteria"):
        write_pdf(bad, tmp_path / "x.pdf")


def test_pdf_has_tasks_block_for_each_story(tmp_path):
    out = tmp_path / "stories.pdf"
    write_pdf(DATA, out)
    text = read_pdf(out)
    assert text.count("Tasks") == 2
    for expected in ("Criar o campo telefone", "Entrega o cenário de telefone vazio",
                     "Testar o cadastro sem telefone", "Fazer x"):
        assert expected in text, expected
    assert text.index("Critérios de aceite") < text.index("Tasks") < text.index("Segunda história")


def test_story_without_tasks_is_rejected(tmp_path):
    for tasks in (None, []):
        story = dict(DATA["stories"][0])
        if tasks is None:
            story.pop("tasks")
        else:
            story["tasks"] = tasks
        with pytest.raises(ValueError, match="tasks"):
            write_pdf({"document": "x", "stories": [story]}, tmp_path / "x.pdf")
