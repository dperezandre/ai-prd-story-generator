"""Validated data models shared by the pipeline, exporters and UI."""
from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["pt-BR", "en"]
Priority = Literal["Must", "Should", "Could", "Won't"]

_HEADINGS = {
    "en": {
        "problem": "Problem", "personas": "Personas", "goals": "Goals",
        "success_metrics": "Success metrics", "scope_in": "In scope",
        "scope_out": "Out of scope", "requirements": "Requirements",
        "risks": "Risks", "assumptions": "Assumptions",
        "open_questions": "Open questions",
    },
    "pt-BR": {
        "problem": "Problema", "personas": "Personas", "goals": "Objetivos",
        "success_metrics": "Métricas de sucesso", "scope_in": "Dentro do escopo",
        "scope_out": "Fora do escopo", "requirements": "Requisitos",
        "risks": "Riscos", "assumptions": "Premissas",
        "open_questions": "Perguntas em aberto",
    },
}
_LIST_FIELDS = ["personas", "goals", "success_metrics", "scope_in", "scope_out",
                "requirements", "risks", "assumptions", "open_questions"]

_KEYWORDS = {
    "en": dict(scenario="Scenario", given="Given", when="When", then="Then", and_="And"),
    "pt-BR": dict(scenario="Cenário", given="Dado", when="Quando", then="Então", and_="E"),
}


class PRD(BaseModel):
    title: str
    problem: str
    personas: list[str] = []
    goals: list[str] = []
    success_metrics: list[str] = []
    scope_in: list[str] = []
    scope_out: list[str] = []
    requirements: list[str] = []
    risks: list[str] = []
    assumptions: list[str] = []
    open_questions: list[str] = []

    def to_markdown(self, language: Language) -> str:
        h = _HEADINGS[language]
        parts = [f"# {self.title}", f"## {h['problem']}\n\n{self.problem}"]
        for name in _LIST_FIELDS:
            items = getattr(self, name)
            if items:
                parts.append(f"## {h[name]}\n\n" + "\n".join(f"- {i}" for i in items))
        return "\n\n".join(parts) + "\n"


class Scenario(BaseModel):
    name: str
    given: list[str] = []
    when: list[str] = []
    then: list[str] = []

    def to_gherkin(self, language: Language) -> str:
        k = _KEYWORDS[language]
        lines = [f"{k['scenario']}: {self.name}"]
        for key, steps in (("given", self.given), ("when", self.when), ("then", self.then)):
            for i, step in enumerate(steps):
                lines.append(f"  {k[key] if i == 0 else k['and_']} {step}")
        text = "\n".join(lines)
        return "# language: pt\n" + text if language == "pt-BR" else text


class Story(BaseModel):
    id: str
    epic: str
    title: str
    as_a: str
    i_want: str
    so_that: str
    priority: Priority
    points: int
    prd_ref: str
    scenarios: list[Scenario] = []

    def to_text(self, language: Language) -> str:
        if language == "pt-BR":
            return f"Como {self.as_a}, quero {self.i_want} para {self.so_that}"
        return f"As a {self.as_a}, I want {self.i_want} so that {self.so_that}"


class InvestScores(BaseModel):
    independent: int = Field(ge=0, le=2)
    negotiable: int = Field(ge=0, le=2)
    valuable: int = Field(ge=0, le=2)
    estimable: int = Field(ge=0, le=2)
    small: int = Field(ge=0, le=2)
    testable: int = Field(ge=0, le=2)

    @property
    def total(self) -> int:
        return (self.independent + self.negotiable + self.valuable
                + self.estimable + self.small + self.testable)


class Review(BaseModel):
    story_id: str
    scores: InvestScores
    verdict: Literal["pass", "rewrite"]
    comment: str
    rewrite: Story | None = None
    scores_after: InvestScores | None = None


class PipelineResult(BaseModel):
    idea: str
    language: Language
    prd: PRD | None = None
    stories: list[Story] = []
    reviews: list[Review] = []
