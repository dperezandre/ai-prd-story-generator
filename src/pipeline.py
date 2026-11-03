"""Four-step generation pipeline: PRD -> stories -> INVEST review -> Gherkin."""
import json
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from src.models import PRD, Language, PipelineResult, Review, Scenario, Story
from src.providers import LLMProvider, ProviderError

MAX_IDEA_CHARS = 4000
STEPS = ("prd", "stories", "invest", "gherkin")
_PROMPT_FILES = dict(zip(STEPS, ("01_prd.md", "02_stories.md", "03_invest_review.md", "04_gherkin.md")))
DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class PipelineError(Exception):
    """A step failed. `partial` holds everything completed before it."""

    def __init__(self, step: str, message: str, partial: PipelineResult):
        super().__init__(message)
        self.step = step
        self.partial = partial


def parse_json_response(text: str) -> Any:
    """Parse a JSON object from model output, tolerating fences and surrounding prose."""
    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char == "{":
            try:
                return decoder.raw_decode(text, start)[0]
            except ValueError:
                continue
    raise ValueError("No JSON object found in the response.")


class _StoryList(BaseModel):
    stories: list[Story]


class _ReviewList(BaseModel):
    reviews: list[Review]


class _ScenarioMap(BaseModel):
    scenarios: dict[str, list[Scenario]]


def _call_json(provider: LLMProvider, system: str, user: str, model: type[BaseModel]) -> BaseModel:
    """Call the provider, validate JSON against `model`; retry once with the error appended."""
    prompt = user
    for attempt in (1, 2):
        text = provider.complete(system, prompt)
        try:
            return model.model_validate(parse_json_response(text))
        except (ValueError, ValidationError) as err:
            if attempt == 2:
                raise ValueError("The model did not return valid JSON for this step.") from err
            prompt = (f"{user}\n\nYour previous reply was invalid: {str(err)[:500]}\n"
                      "Reply again with ONLY a valid JSON object in the required format.")
    raise AssertionError("unreachable")


def _context(result: PipelineResult) -> str:
    return json.dumps({"prd": result.prd.model_dump(),
                       "stories": [s.model_dump() for s in result.stories]}, ensure_ascii=False)


def run_pipeline(idea: str, language: Language, provider: LLMProvider,
                 on_step: Callable[[str, PipelineResult], None] | None = None,
                 prompts_dir: Path = DEFAULT_PROMPTS_DIR) -> PipelineResult:
    idea = idea.strip()
    if not idea:
        raise ValueError("Please describe the feature idea.")
    if len(idea) > MAX_IDEA_CHARS:
        raise ValueError(f"The idea is too long (max {MAX_IDEA_CHARS} characters).")

    result = PipelineResult(idea=idea, language=language)

    def system_for(step: str) -> str:
        return (prompts_dir / language / _PROMPT_FILES[step]).read_text(encoding="utf-8")

    def done(step: str) -> None:
        if on_step:
            on_step(step, result.model_copy(deep=True))

    def guarded(step: str, fn: Callable[[], None]) -> None:
        try:
            fn()
        except (ProviderError, ValueError) as err:
            raise PipelineError(step, str(err), result.model_copy(deep=True)) from err
        done(step)

    def do_prd() -> None:
        result.prd = _call_json(provider, system_for("prd"), idea, PRD)

    def do_stories() -> None:
        user = result.prd.model_dump_json()
        result.stories = _call_json(provider, system_for("stories"), user, _StoryList).stories

    def do_invest() -> None:
        reviews = _call_json(provider, system_for("invest"), _context(result), _ReviewList).reviews
        by_id = {s.id: i for i, s in enumerate(result.stories)}
        kept: dict[str, Review] = {}
        for review in reviews:
            if review.story_id in by_id and review.story_id not in kept:
                kept[review.story_id] = review
        for sid, review in kept.items():
            if review.rewrite is not None:
                fixed = review.rewrite.model_copy(update={"id": sid, "epic": result.stories[by_id[sid]].epic})
                result.stories[by_id[sid]] = fixed
                review.rewrite = fixed
        result.reviews = list(kept.values())

    def do_gherkin() -> None:
        mapping = _call_json(provider, system_for("gherkin"), _context(result), _ScenarioMap).scenarios
        for story in result.stories:
            story.scenarios = mapping.get(story.id, [])

    guarded("prd", do_prd)
    guarded("stories", do_stories)
    guarded("invest", do_invest)
    guarded("gherkin", do_gherkin)
    return result
