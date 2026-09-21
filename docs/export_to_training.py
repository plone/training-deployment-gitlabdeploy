"""Copy this repository's reference chapters into a plone/training checkout.

The chapters in docs/docs/tutorials/pipeline/ are the reference
documentation of this repository. The Plone training includes them as a
reference block next to its own narrative chapters. This script produces those
copies, so the repository stays the only place they are edited.

Each copy gets two additions and is otherwise unchanged:

* a MyST label before its title, `deploy-ref-<name>`, so the training's
  own chapters can link to it with {ref}, and
* a note under its title saying where the chapter is maintained.

Usage, from the repository root:

    uv run --no-project python3 docs/export_to_training.py \\
        ~/plone/training/docs/plone-deployment/reference/deploy-demo

The target must be a directory this script created before, or not exist yet.
It refuses anything else, so a wrong path cannot overwrite other chapters.
"""

import subprocess
import sys
from pathlib import Path

REPO_URL = "https://gitlab.com/plone-training1/training-deployment-gitlabdeploy"
SOURCE = Path(__file__).parent / "docs" / "tutorials" / "pipeline"
MARKER = ".exported-from-training-deployment-gitlabdeploy"
PREFIX = "deploy-ref-"


def label_for(path: Path) -> str:
    """index -> overview, 3-manager -> manager, 1-ssh-and-users -> ssh-and-users."""
    if path.stem == "index":
        return PREFIX + "overview"
    return PREFIX + path.stem.split("-", 1)[1]


def revision() -> str:
    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=SOURCE, capture_output=True, text=True, check=True
        ).stdout.strip()

    try:
        rev = git("rev-parse", "--short", "HEAD")
        dirty = git("status", "--porcelain", "--", ".")
        return rev + ("+uncommitted-changes" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def convert(text: str, label: str, rev: str) -> str:
    # Front matter is `---` ... `---`; the label and note go after it.
    assert text.startswith("---\n"), "expected MyST front matter"
    end = text.index("\n---\n", 4) + len("\n---\n")
    front, body = text[:end], text[end:].lstrip("\n")
    assert body.startswith("# "), "expected the title right after the front matter"
    title, rest = body.split("\n", 1)
    note = (
        f"% Exported from training-deployment-gitlabdeploy {rev} by\n"
        "% docs/export_to_training.py. Do not edit this copy; edit the repository.\n\n"
        "```{note}\n"
        "This chapter is part of the reference documentation of the\n"
        f"[training-deployment-gitlabdeploy]({REPO_URL}) repository, and is maintained\n"
        "there.\n"
        "```\n"
    )
    return f"{front}\n({label})=\n\n{title}\n\n{note}{rest}"


def main(target_arg: str) -> None:
    target = Path(target_arg).expanduser().resolve()
    if target.exists():
        if not (target / MARKER).exists():
            sys.exit(
                f"refusing: {target} exists and was not created by this script "
                f"(no {MARKER} file in it)"
            )
        for old in target.glob("*.md"):
            old.unlink()
    else:
        target.mkdir(parents=True)

    rev = revision()
    (target / MARKER).write_text(f"{REPO_URL} {rev}\n")
    for source in sorted(SOURCE.glob("*.md")):
        label = label_for(source)
        (target / source.name).write_text(convert(source.read_text(), label, rev))
        print(f"  {source.name:22} -> ({label})")
    print(f"exported {len(list(SOURCE.glob('*.md')))} chapters at {rev} to {target}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
