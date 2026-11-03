"""Regenerate examples/ by running the real pipeline against a provider.

Usage: python -m scripts.generate_examples --provider groq --key-env GROQ_API_KEY
Review and edit the generated files before committing them.
"""
import argparse
import os
from pathlib import Path

from src.demo import DEFAULT_EXAMPLES_DIR, DEMO_CASES
from src.exporters import azure_devops_csv, jira_csv, prd_markdown
from src.models import PipelineResult
from src.pipeline import run_pipeline
from src.providers import get_provider


def write_example_files(result: PipelineResult, case_id: str, out_dir: Path = DEFAULT_EXAMPLES_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{case_id}.{result.language}"
    (out_dir / f"{stem}.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / f"{stem}.prd.md").write_text(prd_markdown(result), encoding="utf-8")
    (out_dir / f"{stem}.azure.csv").write_text(azure_devops_csv(result), encoding="utf-8", newline="")
    (out_dir / f"{stem}.jira.csv").write_text(jira_csv(result), encoding="utf-8", newline="")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True)
    parser.add_argument("--key-env", required=True, help="Environment variable holding the API key")
    parser.add_argument("--model")
    args = parser.parse_args()
    provider = get_provider(args.provider, os.environ[args.key_env], args.model)
    for case_id, texts in DEMO_CASES.items():
        for language, idea in texts.items():
            print(f"Generating {case_id} ({language})...")
            write_example_files(run_pipeline(idea, language, provider), case_id)


if __name__ == "__main__":
    main()
