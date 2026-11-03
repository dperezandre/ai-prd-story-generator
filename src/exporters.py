"""Exporters: PRD Markdown, Azure DevOps CSV and Jira CSV (formats checked against official docs)."""
import csv
import html
import io

from src.models import Language, PipelineResult, Priority, Story

AZURE_COLUMNS = ["Work Item Type", "Title 1", "Title 2", "Description",
                 "Acceptance Criteria", "Priority", "Story Points", "Tags"]
JIRA_COLUMNS = ["Issue Id", "Issue Type", "Summary", "Description", "Priority", "Parent", "Labels"]

_AZURE_PRIORITY: dict[Priority, str] = {"Must": "1", "Should": "2", "Could": "3", "Won't": "4"}
_JIRA_PRIORITY: dict[Priority, str] = {"Must": "Highest", "Should": "High", "Could": "Medium", "Won't": "Low"}
_MOSCOW_SLUG: dict[Priority, str] = {"Must": "must", "Should": "should", "Could": "could", "Won't": "wont"}

_STORIES_HEADING = {"en": "User stories", "pt-BR": "Histórias de usuário"}
_CRITERIA_HEADING = {"en": "Acceptance criteria", "pt-BR": "Critérios de aceite"}


def _cell(value: str) -> str:
    """Neutralise spreadsheet formula injection."""
    return "'" + value if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


def _write(columns: list[str], rows: list[dict[str, str]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_cell(row.get(c, "")) for c in columns])
    return buf.getvalue()


def _epics(result: PipelineResult) -> dict[str, list[Story]]:
    grouped: dict[str, list[Story]] = {}
    for story in result.stories:
        grouped.setdefault(story.epic, []).append(story)
    return grouped


def _scenario_blocks(story: Story, language: Language) -> list[str]:
    return [sc.to_gherkin(language).removeprefix("# language: pt\n") for sc in story.scenarios]


def _html_paragraph(text: str) -> str:
    return "<p>" + html.escape(text, quote=False).replace("\n", "<br>") + "</p>"


def azure_devops_csv(result: PipelineResult) -> str:
    rows: list[dict[str, str]] = []
    for epic, stories in _epics(result).items():
        rows.append({"Work Item Type": "Epic", "Title 1": epic})
        for s in stories:
            rows.append({
                "Work Item Type": "User Story",
                "Title 2": s.title,
                "Description": _html_paragraph(s.to_text(result.language)),
                "Acceptance Criteria": "".join(
                    _html_paragraph(b) for b in _scenario_blocks(s, result.language)),
                "Priority": _AZURE_PRIORITY[s.priority],
                "Story Points": str(s.points),
                "Tags": "MoSCoW-" + _MOSCOW_SLUG[s.priority].capitalize(),
            })
    return _write(AZURE_COLUMNS, rows)


def jira_csv(result: PipelineResult) -> str:
    rows: list[dict[str, str]] = []
    next_id = 1
    for epic, stories in _epics(result).items():
        epic_id = str(next_id)
        next_id += 1
        rows.append({"Issue Id": epic_id, "Issue Type": "Epic", "Summary": epic})
        for s in stories:
            blocks = _scenario_blocks(s, result.language)
            description = s.to_text(result.language)
            if blocks:
                description += f"\n\n{_CRITERIA_HEADING[result.language]}:\n\n" + "\n\n".join(blocks)
            rows.append({
                "Issue Id": str(next_id), "Issue Type": "Story", "Summary": s.title,
                "Description": description, "Priority": _JIRA_PRIORITY[s.priority],
                "Parent": epic_id, "Labels": "moscow-" + _MOSCOW_SLUG[s.priority],
            })
            next_id += 1
    return _write(JIRA_COLUMNS, rows)


def prd_markdown(result: PipelineResult) -> str:
    if result.prd is None:
        return ""
    parts = [result.prd.to_markdown(result.language).rstrip()]
    if result.stories:
        parts.append(f"## {_STORIES_HEADING[result.language]}")
        for s in result.stories:
            lines = [f"### {s.id} — {s.title}", "", f"{s.to_text(result.language)}",
                     "", f"{s.epic} · {s.priority} · {s.points} pts"]
            blocks = _scenario_blocks(s, result.language)
            if blocks:
                header = "# language: pt\n" if result.language == "pt-BR" else ""
                lines += ["", f"**{_CRITERIA_HEADING[result.language]}**", "",
                          "```gherkin\n" + header + "\n\n".join(blocks) + "\n```"]
            parts.append("\n".join(lines))
    return "\n\n".join(parts) + "\n"
