"""Push user stories and their tasks to Azure DevOps through its REST API."""
import base64
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlparse

import httpx

from src.exporters import _MOSCOW_SLUG, _html_paragraph, _scenario_blocks
from src.models import PipelineResult, Priority

_PRIORITY: dict[Priority, int] = {"Must": 1, "Should": 2, "Could": 3, "Won't": 4}

_API_VERSION = "7.1"
_STORY_TYPES = ("User Story", "Product Backlog Item", "Requirement", "Issue")
_TIMEOUT = httpx.Timeout(10.0, read=60.0)
_MAX_RETRY_WAIT = 10.0
_sleep = time.sleep

ErrorKind = Literal["auth", "not_found", "network", "rate_limit", "validation"]


class AzureDevOpsError(Exception):
    """Azure DevOps failure. The message never includes the personal access token."""

    def __init__(self, message: str, kind: ErrorKind):
        super().__init__(message)
        self.kind = kind


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


class AzureDevOpsClient:
    """Minimal Azure DevOps work item client (REST 7.1, personal access token)."""

    def __init__(self, organization: str, project: str, pat: str,
                 transport: httpx.BaseTransport | None = None,
                 area: str | None = None, iteration: str | None = None):
        self.organization = normalize_organization(organization)
        self.project = project.strip()
        if not self.project:
            raise ValueError("The Azure DevOps project is required.")
        if not pat.strip():
            raise ValueError("The Azure DevOps token is required.")
        self._pat = pat.strip()
        self._area = area
        self._iteration = iteration
        credentials = base64.b64encode(f":{self._pat}".encode()).decode()
        self._client = httpx.Client(transport=transport, timeout=_TIMEOUT,
                                    headers={"Authorization": f"Basic {credentials}"})

    # -- helpers ----------------------------------------------------------------------------

    def _project_url(self) -> str:
        return f"https://dev.azure.com/{quote(self.organization)}/{quote(self.project)}"

    def work_item_url(self, work_item_id: int) -> str:
        return f"{self._project_url()}/_workitems/edit/{work_item_id}"

    def _detail(self, resp: httpx.Response) -> str:
        try:
            text = str(resp.json().get("message", ""))
        except (ValueError, AttributeError):
            return ""
        return text.replace(self._pat, "[token]")[:300]

    def _request(self, method: str, path: str, *, body: list | None = None) -> dict:
        url = f"{self._project_url()}/_apis/wit/{path}"
        kwargs: dict = {"params": {"api-version": _API_VERSION}}
        if body is not None:
            kwargs["content"] = json.dumps(body)
            kwargs["headers"] = {"Content-Type": "application/json-patch+json"}
        for attempt in (1, 2):
            try:
                resp = self._client.request(method, url, **kwargs)
            except httpx.TimeoutException:
                raise AzureDevOpsError("Azure DevOps timed out. Try again.", "network") from None
            except httpx.HTTPError:
                raise AzureDevOpsError("Could not reach Azure DevOps. Check your connection.", "network") from None
            if (resp.status_code == 429 or resp.status_code >= 500) and attempt == 1:
                try:
                    wait = float(resp.headers.get("retry-after", "1"))
                except ValueError:
                    wait = 1.0
                _sleep(min(max(wait, 0.0), _MAX_RETRY_WAIT))
                continue
            break
        return self._parse(resp)

    def _parse(self, resp: httpx.Response) -> dict:
        status = resp.status_code
        if status == 203 or (status < 300 and "json" not in resp.headers.get("content-type", "")):
            raise AzureDevOpsError(
                "Azure DevOps rejected the token (it answered with a sign-in page). "
                "Check the token, its expiry and that it has Work Items read and write.", "auth")
        detail = self._detail(resp)
        suffix = f" ({detail})" if detail else ""
        if status in (401, 403):
            raise AzureDevOpsError("Azure DevOps rejected the token or it lacks permission for this "
                                   "project." + suffix, "auth")
        if status == 404:
            raise AzureDevOpsError("Organization or project not found. Check their names." + suffix, "not_found")
        if status == 429:
            raise AzureDevOpsError("Azure DevOps is rate limiting requests. Try again in a moment.", "rate_limit")
        if status >= 500:
            raise AzureDevOpsError(f"Azure DevOps had a server error ({status}). Try again.", "network")
        if status >= 400:
            raise AzureDevOpsError(f"Azure DevOps refused the request{suffix or f' ({status})'}.", "validation")
        return resp.json()

    # -- reads ------------------------------------------------------------------------------

    def story_type(self) -> str:
        names = {t["name"] for t in self._request("GET", "workitemtypes")["value"]}
        for candidate in _STORY_TYPES:
            if candidate in names:
                return candidate
        raise AzureDevOpsError("This project has none of the supported story types "
                               f"({', '.join(_STORY_TYPES)}).", "validation")

    def available_fields(self, work_item_type: str) -> set[str]:
        data = self._request("GET", f"workitemtypes/{quote(work_item_type)}/fields")
        return {f["referenceName"] for f in data["value"]}

    # -- writes -----------------------------------------------------------------------------

    def _path_fields(self) -> list[tuple[str, str]]:
        return [(f, v) for f, v in (("System.AreaPath", self._area),
                                    ("System.IterationPath", self._iteration)) if v]

    def _create(self, work_item_type: str, fields: list[tuple[str, object]], parent_id: int | None = None) -> int:
        body: list[dict] = [{"op": "add", "path": f"/fields/{name}", "value": value} for name, value in fields]
        if parent_id is not None:
            body.append({"op": "add", "path": "/relations/-", "value": {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"https://dev.azure.com/{quote(self.organization)}/_apis/wit/workItems/{parent_id}"}})
        data = self._request("POST", f"workitems/{quote('$' + work_item_type, safe='$')}", body=body)
        return int(data["id"])

    def create_story(self, item: PushItem, story_type: str, available: set[str]) -> int:
        fields: list[tuple[str, object]] = [("System.Title", item.title),
                                            ("System.Description", item.description_html)]
        if item.acceptance_html and "Microsoft.VSTS.Common.AcceptanceCriteria" in available:
            fields.append(("Microsoft.VSTS.Common.AcceptanceCriteria", item.acceptance_html))
        if item.priority is not None and "Microsoft.VSTS.Common.Priority" in available:
            fields.append(("Microsoft.VSTS.Common.Priority", item.priority))
        if item.points is not None:
            for points_field in ("Microsoft.VSTS.Scheduling.StoryPoints", "Microsoft.VSTS.Scheduling.Effort"):
                if points_field in available:
                    fields.append((points_field, item.points))
                    break
        if item.tags:
            fields.append(("System.Tags", "; ".join(item.tags)))
        fields.extend(self._path_fields())
        return self._create(story_type, fields)

    def create_task(self, task: PushTask, parent_id: int) -> int:
        fields: list[tuple[str, object]] = [("System.Title", task.title)]
        if task.description:
            fields.append(("System.Description", task.description))
        fields.extend(self._path_fields())
        return self._create("Task", fields, parent_id=parent_id)


@dataclass
class PushReport:
    created_stories: int = 0
    created_tasks: int = 0
    skipped: int = 0
    urls: list[str] = field(default_factory=list)
    error: AzureDevOpsError | None = None


def push(client: AzureDevOpsClient, items: list[PushItem], ledger: Ledger,
         confirmed: bool, force: bool = False) -> PushReport:
    """Create the stories and their tasks. Stops at the first Azure error and reports what was created.

    The ledger is saved after every created work item, so a repeat run only creates what is missing."""
    if not confirmed:
        raise ValueError("The push needs an explicit confirmation.")
    report = PushReport()
    if not items:
        return report
    try:
        story_type = client.story_type()
        available = client.available_fields(story_type)
        for item in items:
            entry = None if force else ledger.get(item)
            if entry is None:
                story_id = client.create_story(item, story_type, available)
                task_ids: list[int] = []
                ledger.record(item, story_id, task_ids)
                ledger.save()
                report.created_stories += 1
                report.urls.append(client.work_item_url(story_id))
            else:
                story_id, task_ids = entry["story_id"], list(entry["task_ids"])
                if len(task_ids) >= len(item.tasks):
                    report.skipped += 1
                    continue
            for task in item.tasks[len(task_ids):]:
                task_ids.append(client.create_task(task, story_id))
                ledger.record(item, story_id, task_ids)
                ledger.save()
                report.created_tasks += 1
    except AzureDevOpsError as err:
        report.error = err
    return report
