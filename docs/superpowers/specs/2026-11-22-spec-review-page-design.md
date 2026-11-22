# Spec review page (local, Claude Code subscription) - design

Approved by the user in chat on 2026-11-22 ("Aprovar").

## Intent
The user pays for Claude Pro, not the API. They want a single localhost page where they upload a business specification (PDF) or paste its text, get the `po-spec-review` review, download the stories PDF, and push stories and tasks to Azure DevOps. It runs through the local Claude Code CLI, which uses their subscription login, with no API key.

## Goals
- One Streamlit page: upload/paste, review with live output, download the stories PDF, Azure preview, and a **separate** confirm button that is the only thing that sends to Azure.
- Reuse the existing `scripts.azure_push` core (`items_from_stories_json`, `Ledger`, `plan`, `push`, `AzureDevOpsClient`).
- Confidential input stays local: the PDF goes to a temp folder deleted at the end; nothing is written into the repo.

## Non-goals
- Convert mode, chat, multiple documents, running anywhere but the user's machine.
- Validating review quality (needs the user's real login).

## Anti-goals
- Sending to Azure without the preview and the explicit confirm button.
- Storing or logging the PAT.
- Silently failing when the CLI is missing or logged out.

## Approaches considered
1. Thin page over `claude -p` (chosen). Smallest work, reuses tested pieces.
2. Page drives each step with one call per step. More control, rewrites skill logic.
3. Embedded chat relaying the skill's questions. Most faithful, most fragile.

## Design
- `src/claude_cli.py`: `find_claude()` (PATH, then `~/.local/bin/claude.exe`), `build_command(...)`, `run_review(prompt, workdir, runner=...)` yielding `Event(kind, text)` parsed from `--output-format stream-json --verbose`, and `ClaudeCliError(kind)` with kinds `not_found`, `auth`, `failed`. The runner is injectable so tests use a fake process.
- Headless prompt asks the skill to run without questions, write `stories.json` and the PDF into the temp folder, and say nothing about Azure.
- `spec_review_page.py` (own Streamlit entry, `streamlit run spec_review_page.py`): workflow above. Azure org/project fields, PAT in a password field, preview button, confirm button disabled until a preview exists for the same org/project and cleared when they change.
- Errors shown plainly: CLI not found; logged out (tell the user to run `claude` and sign in); other failures with the CLI's message.

## Known facts / limits
- Claude Code 2.1.304 lives at `C:\Users\dpere\.local\bin\claude.exe`, not on PATH.
- On 2026-11-22 the CLI answered "OAuth session expired and could not be refreshed": the user must sign in again before the page can work.
- Terms of the Pro plan for this automated use were not verified; the user decides.
- Real reviews were not run by the builder; tests use a fake CLI.
