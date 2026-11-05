"""Install the po-spec-review skill into a Claude skills folder.

Usage: python -m scripts.install_skill            (installs into ~/.claude/skills)
       python -m scripts.install_skill --dest DIR
"""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "po-spec-review"
STANDARD = ROOT / "docs" / "spec-standard.pt-BR.md"


def install(skills_dir: Path) -> Path:
    dest = skills_dir / "po-spec-review"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SKILL_DIR / "SKILL.md", dest / "SKILL.md")
    shutil.copyfile(STANDARD, dest / "standard.pt-BR.md")
    shutil.copytree(SKILL_DIR / "scripts", dest / "scripts", dirs_exist_ok=True)
    return dest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", type=Path, default=Path.home() / ".claude" / "skills")
    print(f"Installed to {install(parser.parse_args().dest)}")


if __name__ == "__main__":
    main()
