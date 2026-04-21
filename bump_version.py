"""Bump the ``scada-ui-kit`` version and optionally commit + tag the release.

``scada_ui_kit/__init__.py`` is now the single source of truth for the package
version; ``pyproject.toml`` reads it dynamically via setuptools' ``attr``
directive. This script therefore only has one file to edit, which eliminates
the drift problem entirely by construction.

Usage::

    python bump_version.py patch            # 0.1.0 -> 0.1.1  (bug fix)
    python bump_version.py minor            # 0.1.0 -> 0.2.0  (back-compat feature)
    python bump_version.py major            # 0.1.0 -> 1.0.0  (breaking change)
    python bump_version.py 2.7.3            # explicit SemVer set
    python bump_version.py patch -n         # dry-run: show result, write nothing
    python bump_version.py patch -c         # also: git add + commit
    python bump_version.py patch -c -t      # also: git tag vX.Y.Z (implies -c)

Matches the idioms used in ``build_package.py`` / ``publish.py``:
``from __future__ import annotations``, module-level ``Final`` constants,
a ``log()`` helper, a custom exception, a ``parse_args`` / ``main`` split,
and ``subprocess.run`` calls scoped to ``ROOT`` via ``cwd``. Bump dispatch
uses ``match``/``case`` (Fluent Python ch. 18).
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).resolve().parent
INIT_PY: Final[Path] = ROOT / "scada_ui_kit" / "__init__.py"

SEMVER_RE: Final[re.Pattern[str]] = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
# Groups: (prefix)(quote)(version)(quote) - preserves the existing quote style.
VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""^(__version__\s*=\s*)(['"])(\d+\.\d+\.\d+)(['"])""",
    re.MULTILINE,
)


class BumpError(RuntimeError):
    """Raised when a version bump can't be completed safely."""


def log(message: str) -> None:
    print(f"[bump] {message}", flush=True)


# ---------------------------------------------------------------- version I/O --


def read_current_version() -> tuple[str, str, str]:
    """Return ``(content, version, quote_char)`` of the init file."""
    if not INIT_PY.exists():
        raise BumpError(f"cannot find {INIT_PY}")
    content = INIT_PY.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(content)
    if match is None:
        raise BumpError(f"no __version__ assignment found in {INIT_PY.name}")
    return content, match.group(3), match.group(2)


def compute_next(current: str, spec: str) -> str:
    """Return the new version given a bump keyword or explicit ``X.Y.Z``."""
    parts = current.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise BumpError(f"current version {current!r} is not SemVer")
    major, minor, patch = (int(p) for p in parts)

    match spec:
        case "major":
            return f"{major + 1}.0.0"
        case "minor":
            return f"{major}.{minor + 1}.0"
        case "patch":
            return f"{major}.{minor}.{patch + 1}"
        case _:
            if SEMVER_RE.match(spec):
                return spec
            raise BumpError(
                f"expected 'major' / 'minor' / 'patch' or an X.Y.Z version, got {spec!r}"
            )


def rewrite_version(content: str, new_version: str) -> str:
    updated, count = VERSION_PATTERN.subn(
        lambda m: f"{m.group(1)}{m.group(2)}{new_version}{m.group(4)}",
        content,
        count=1,
    )
    if count == 0:
        raise BumpError(f"could not rewrite __version__ in {INIT_PY.name}")
    return updated


# ---------------------------------------------------------------- git helpers --


def run_git(args: Sequence[str], *, capture: bool = True) -> str:
    """Run ``git <args>`` in ROOT; raise :class:`BumpError` on failure.

    ``FileNotFoundError`` from ``subprocess.run`` means ``git`` isn't on the
    ``PATH`` (``WinError 2`` on Windows). We translate it to a friendly
    :class:`BumpError` with install guidance instead of exposing a raw
    traceback to the user.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=capture,
            text=True,
        )
    except FileNotFoundError as err:
        raise BumpError(
            "git executable not found on PATH. Install Git "
            "(https://git-scm.com/download/win on Windows) or ensure "
            "'git' is reachable from the current shell, then retry."
        ) from err
    if result.returncode != 0:
        raise BumpError(
            f"git {' '.join(args)} failed: "
            f"{(result.stderr or result.stdout or '').strip()}"
        )
    return (result.stdout or "").strip()


def ensure_git_on_path() -> None:
    """Verify ``git`` is resolvable before any subprocess call."""
    if shutil.which("git") is None:
        raise BumpError(
            "git executable not found on PATH. Install Git "
            "(https://git-scm.com/download/win on Windows) or ensure "
            "'git' is reachable from the current shell, then retry."
        )


def ensure_git_repo() -> None:
    """Verify the current directory is inside a git working tree."""
    ensure_git_on_path()
    try:
        run_git(["rev-parse", "--is-inside-work-tree"])
    except BumpError as err:
        raise BumpError(
            "this directory is not a git working tree; cannot --commit or --tag"
        ) from err


def ensure_tag_free(tag: str) -> None:
    existing = run_git(["tag", "--list", tag])
    if existing:
        raise BumpError(
            f"tag {tag!r} already exists; delete it with "
            f"'git tag -d {tag}' first, or choose a different version"
        )


# ---------------------------------------------------------------------- CLI --


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "bump",
        help="'major', 'minor', 'patch', or an explicit SemVer like '1.2.3'",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="print the new version and exit without touching any files or git",
    )
    parser.add_argument(
        "-c",
        "--commit",
        action="store_true",
        help="after writing the new version, 'git add' + 'git commit' it",
    )
    parser.add_argument(
        "-t",
        "--tag",
        action="store_true",
        help="create an annotated 'vX.Y.Z' tag; implies --commit",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    do_commit = args.commit or args.tag

    try:
        content, current_version, _quote = read_current_version()
        new_version = compute_next(current_version, args.bump)

        log(f"current version: {current_version}")
        log(f"next version:    {new_version}")

        if new_version == current_version:
            raise BumpError(
                f"no-op bump: target {new_version!r} equals current version"
            )

        if do_commit:
            ensure_git_repo()
            if args.tag:
                ensure_tag_free(f"v{new_version}")

        if args.dry_run:
            log("dry-run: no files written and no git operations performed")
            return 0

        INIT_PY.write_text(rewrite_version(content, new_version), encoding="utf-8")
        log(f"updated {INIT_PY.relative_to(ROOT)} -> {new_version}")

        if do_commit:
            # ``-- <pathspec>`` scopes the commit to only the init file so any
            # unrelated staged changes don't get swept into the release commit.
            run_git(["add", "--", str(INIT_PY)])
            run_git(["commit", "-m", f"Release {new_version}", "--", str(INIT_PY)])
            log(f"committed: 'Release {new_version}'")

            if args.tag:
                tag = f"v{new_version}"
                run_git(["tag", "-a", tag, "-m", f"Release {tag}"])
                log(f"tagged: {tag}")
                log(f"push with: git push && git push origin {tag}")
            else:
                log("push with: git push")

    except BumpError as err:
        log(f"FAILED: {err}")
        return 1

    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
