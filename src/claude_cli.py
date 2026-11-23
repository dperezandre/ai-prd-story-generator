"""Run the po-spec-review skill through the local Claude Code CLI (subscription login).

No API key is involved. The runner is injectable so tests never start a real process.
"""
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator


class ClaudeCliError(Exception):
    """kind: not_found (no executable), auth (logged out), failed (anything else)."""

    def __init__(self, message: str, kind: str = "failed"):
        super().__init__(message)
        self.kind = kind


@dataclass
class Event:
    kind: str  # "text" or "result"
    text: str


@dataclass
class ReviewResult:
    text: str
    stories: dict
    pdf: bytes


REVIEW_PROMPT = (
    "Use a skill po-spec-review na especificação em {spec_name}, que está nesta pasta. "
    "Rode sem fazer perguntas ao usuário. Além da resposta, grave nesta pasta o JSON das histórias "
    "(o mesmo da skill, com tasks) em stories.json e o PDF das histórias em historias.pdf. "
    "Não envie nada ao Azure DevOps."
)

_AUTH_WORDS = ("authenticate", "oauth", "login", "log in")


def find_claude(path_env: str | None = None, home: Path | None = None) -> Path:
    found = shutil.which("claude", path=path_env)
    if found:
        return Path(found)
    base = (home or Path.home()) / ".local" / "bin"
    for name in ("claude.exe", "claude"):
        if (base / name).is_file():
            return base / name
    raise ClaudeCliError("Claude Code not found", kind="not_found")


def build_command(exe: Path, prompt: str) -> list[str]:
    return [str(exe), "-p", prompt, "--output-format", "stream-json", "--verbose",
            "--permission-mode", "acceptEdits", "--allowedTools", "Read", "Write", "Bash"]


def parse_events(lines: Iterable[str]) -> Iterator[Event]:
    for raw in lines:
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(data, dict):
            continue
        if data.get("type") == "assistant":
            for block in (data.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                    yield Event("text", block["text"])
        elif data.get("type") == "result":
            text = str(data.get("result") or "")
            if data.get("is_error"):
                kind = "auth" if any(w in text.lower() for w in _AUTH_WORDS) else "failed"
                raise ClaudeCliError(text or "Claude Code failed", kind=kind)
            yield Event("result", text)


def default_runner(cmd: list[str], cwd: Path) -> Iterator[str]:
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace")
    try:
        assert proc.stdout is not None
        yield from proc.stdout
    finally:
        proc.stdout and proc.stdout.close()
        proc.wait()


def review_spec(data: bytes, filename: str, on_event: Callable[[Event], None] | None = None,
                runner=default_runner, exe: Path | None = None) -> ReviewResult:
    exe = exe or find_claude()
    suffix = Path(filename).suffix.lower()
    if suffix not in (".pdf", ".txt", ".md"):
        suffix = ".txt"
    spec_name = f"spec{suffix}"
    workdir = Path(tempfile.mkdtemp(prefix="spec-review-"))
    try:
        (workdir / spec_name).write_bytes(data)
        cmd = build_command(exe, REVIEW_PROMPT.format(spec_name=spec_name))
        texts: list[str] = []
        got_result = False
        try:
            for event in parse_events(runner(cmd, workdir)):
                if event.kind == "text":
                    texts.append(event.text)
                else:
                    got_result = True
                if on_event:
                    on_event(event)
        except ClaudeCliError:
            raise
        except OSError as err:
            raise ClaudeCliError(f"could not run Claude Code: {err}") from err
        if not got_result:
            raise ClaudeCliError("Claude Code ended without a result")
        stories_path, pdf_path = workdir / "stories.json", workdir / "historias.pdf"
        missing = [p.name for p in (stories_path, pdf_path) if not p.is_file()]
        if missing:
            raise ClaudeCliError("the review did not produce: " + ", ".join(missing))
        try:
            stories = json.loads(stories_path.read_text(encoding="utf-8"))
        except ValueError as err:
            raise ClaudeCliError("stories.json is not valid JSON") from err
        return ReviewResult("\n\n".join(texts), stories, pdf_path.read_bytes())
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
