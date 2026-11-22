"""Preview and push stories and their tasks to Azure DevOps.

Usage: python -m scripts.azure_push stories.json --org <organization> --project <project> [--yes]

The token comes from the AZDO_PAT environment variable (Work Items: read and write). Without --yes
this only prints what would be created and sends nothing. The input is either a PipelineResult JSON
or the po-spec-review skill's JSON (stories with title, description, acceptance_criteria and tasks).
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Mapping

import httpx

from src.azure_devops import (AzureDevOpsClient, Ledger, PushItem, items_from_result,
                              items_from_stories_json, normalize_organization, plan, push)
from src.models import PipelineResult


def _load_items(path: Path) -> list[PushItem]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "idea" in data:
        return items_from_result(PipelineResult.model_validate(data))
    return items_from_stories_json(data)


def _print_plan(lines) -> None:
    for line in lines:
        print(f"[{line.status}] {line.story_title}")
        for title in line.task_titles:
            print(f"      - {title}")
        if line.warning:
            print(f"      ! {line.warning}")
    stories = len(lines)
    tasks = sum(len(line.task_titles) for line in lines)
    print(f"{stories} stories, {tasks} tasks.")


def main(argv: list[str] | None = None, transport: httpx.BaseTransport | None = None,
         environ: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Push stories and tasks to Azure DevOps.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--org", required=True, help="organization name or dev.azure.com URL")
    parser.add_argument("--project", required=True)
    parser.add_argument("--area", help="area path (default: project root)")
    parser.add_argument("--iteration", help="iteration path (default: project root)")
    parser.add_argument("--ledger", type=Path, help="where to remember what was sent (default: next to the input)")
    parser.add_argument("--yes", action="store_true", help="send; without it only a preview is printed")
    parser.add_argument("--force", action="store_true", help="ignore the ledger and create everything again")
    args = parser.parse_args(argv)
    environ = os.environ if environ is None else environ

    try:
        items = _load_items(args.input)
        organization = normalize_organization(args.org)
        ledger_path = args.ledger or args.input.with_name(f"{args.input.stem}.azdo-ledger.json")
        ledger = Ledger.load(ledger_path, organization, args.project.strip())
    except (OSError, ValueError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2

    _print_plan(plan(items, ledger))
    if not args.yes:
        print("Preview only: nothing was sent. Run again with --yes to create these work items.")
        return 0

    token = environ.get("AZDO_PAT", "").strip()
    if not token:
        print("Error: set the AZDO_PAT environment variable to a personal access token "
              "with Work Items read and write.", file=sys.stderr)
        return 2
    try:
        client = AzureDevOpsClient(organization, args.project, token, transport=transport,
                                   area=args.area, iteration=args.iteration)
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2
    report = push(client, items, ledger, confirmed=True, force=args.force)
    print(f"Created {report.created_stories} stories and {report.created_tasks} tasks; "
          f"{report.skipped} skipped (already sent).")
    for url in report.urls:
        print(url)
    if report.error:
        print(f"Error: {report.error}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
