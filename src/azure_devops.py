"""Push user stories and their tasks to Azure DevOps through its REST API."""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from src.exporters import _MOSCOW_SLUG, _html_paragraph, _scenario_blocks
from src.models import PipelineResult, Priority

_PRIORITY: dict[Priority, int] = {"Must": 1, "Should": 2, "Could": 3, "Won't": 4}


@dataclass(frozen=True)
class PushTask:
    title: str
    description: str  # HTML, or an empty string


@dataclass(frozen=True)
class PushItem:
    """A story and its tasks, in the neutral shape the push works with. Text fields are HTML."""

    title: str
    description_html: str
    acceptance_html: str
    priority: int | None
    points: int | None
    tags: list[str] = field(default_factory=list)
    tasks: list[PushTask] = field(default_factory=list)


@dataclass(frozen=True)
class PlanLine:
    story_title: str
    task_titles: list[str]
    status: Literal["new", "sent", "partial"]
    warning: str | None = None


def _task_html(description: str) -> str:
    return _html_paragraph(description) if description else ""


def items_from_result(result: PipelineResult) -> list[PushItem]:
    items = []
    for s in result.stories:
        items.append(PushItem(
            title=s.title,
            description_html=_html_paragraph(s.to_text(result.language)),
            acceptance_html="".join(_html_paragraph(b) for b in _scenario_blocks(s, result.language)),
            priority=_PRIORITY[s.priority],
            points=s.points,
            tags=[f"MoSCoW-{_MOSCOW_SLUG[s.priority].capitalize()}", s.epic],
            tasks=[PushTask(t.title, _task_html(t.description)) for t in s.tasks],
        ))
    return items


def items_from_stories_json(data: dict) -> list[PushItem]:
    """Build items from the skill's JSON: stories with title, description, acceptance_criteria and tasks."""
    items = []
    for number, story in enumerate(data.get("stories", []), 1):
        for name in ("title", "description", "acceptance_criteria", "tasks"):
            if name not in story:
                raise ValueError(f"story {number} is missing {name}")
        items.append(PushItem(
            title=story["title"],
            description_html=_html_paragraph(story["description"]),
            acceptance_html="".join(_html_paragraph(c) for c in story["acceptance_criteria"]),
            priority=None,
            points=None,
            tasks=[PushTask(t["title"], _task_html(t.get("description", ""))) for t in story["tasks"]],
        ))
    return items


def normalize_organization(value: str) -> str:
    """Accept a bare name, dev.azure.com/<org>, a full URL or <org>.visualstudio.com."""
    text = value.strip()
    if not text:
        raise ValueError("The Azure DevOps organization is required.")
    if "/" not in text and "." not in text:
        return text
    parsed = urlparse(text if "://" in text else "https://" + text)
    host = parsed.hostname or ""
    if host.endswith(".visualstudio.com"):
        return host.removesuffix(".visualstudio.com")
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        raise ValueError(f"Could not find the organization name in {value!r}.")
    return parts[0]


def item_key(organization: str, project: str, item: PushItem) -> str:
    """Stable id of a story for one organization and project. Same title with different text differs."""
    payload = [organization, project, item.title, item.description_html, item.acceptance_html]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode("utf-8")).hexdigest()


class Ledger:
    """Remembers which stories were already created, so a repeated push never duplicates them.

    With path=None it lives in memory only (the app); otherwise it is a JSON file."""

    def __init__(self, path: Path | None, organization: str, project: str, entries: dict[str, dict]):
        self.path = path
        self.organization = organization
        self.project = project
        self._entries = entries

    @classmethod
    def load(cls, path: Path | None, organization: str, project: str) -> "Ledger":
        entries: dict[str, dict] = {}
        if path is not None and path.exists():
            try:
                entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
            except (ValueError, KeyError, TypeError) as err:
                raise ValueError(f"Could not read the ledger file {path}.") from err
        return cls(path, organization, project, entries)

    def get(self, item: PushItem) -> dict | None:
        entry = self._entries.get(item_key(self.organization, self.project, item))
        if entry is None:
            return None
        return {"story_id": entry["story_id"], "task_ids": list(entry["task_ids"])}

    def record(self, item: PushItem, story_id: int, task_ids: list[int]) -> None:
        self._entries[item_key(self.organization, self.project, item)] = {
            "title": item.title, "story_id": story_id, "task_ids": list(task_ids)}

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"version": 1, "entries": self._entries},
                                        ensure_ascii=False, indent=2), encoding="utf-8")


def plan(items: list[PushItem], ledger: Ledger) -> list[PlanLine]:
    """Preview of what a push would do. Makes no request."""
    lines = []
    for item in items:
        entry = ledger.get(item)
        if entry is None:
            status = "new"
        elif len(entry["task_ids"]) >= len(item.tasks):
            status = "sent"
        else:
            status = "partial"
        lines.append(PlanLine(
            story_title=item.title,
            task_titles=[t.title for t in item.tasks],
            status=status,
            warning=None if item.tasks else "This story has no tasks.",
        ))
    return lines
