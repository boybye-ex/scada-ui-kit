"""Build distribution artifacts for ``scada-ui-kit``.

Produces an sdist (``.tar.gz``) and a wheel (``.whl``) in ``./dist/`` by
shelling out to the standard PyPA ``build`` tool, then validates them with
``twine check`` so metadata issues are caught before any upload.

Usage::

    python build_package.py                 # clean, build, check
    python build_package.py --no-clean      # keep existing dist/ artifacts
    python build_package.py --clean-only    # remove dist/ and build/ and exit
    python build_package.py --no-check      # skip twine check

Follows Fluent Python idioms: ``pathlib`` for file-system work (ch. 18-ish),
``subprocess.run(..., check=True)`` with explicit error handling, ``argparse``
for first-class CLI arguments, and type-annotated pure helpers.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).resolve().parent
DIST_DIR: Final[Path] = ROOT / "dist"
BUILD_DIR: Final[Path] = ROOT / "build"
CLEANABLE_DIRS: Final[tuple[Path, ...]] = (DIST_DIR, BUILD_DIR)


class BuildError(RuntimeError):
    """Raised when a subprocess step fails."""


def log(message: str) -> None:
    print(f"[build] {message}", flush=True)


def run(cmd: Sequence[str]) -> None:
    """Run ``cmd``, streaming its output; raise :class:`BuildError` on failure."""
    log("$ " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise BuildError(
            f"command failed with exit code {result.returncode}: {' '.join(cmd)}"
        )


def clean(targets: Iterable[Path]) -> None:
    for target in targets:
        if target.exists():
            log(f"removing {target.relative_to(ROOT)}")
            shutil.rmtree(target)
    for egg_info in ROOT.glob("*.egg-info"):
        log(f"removing {egg_info.relative_to(ROOT)}")
        shutil.rmtree(egg_info)


def ensure_tool(module: str, hint: str) -> None:
    """Fail fast with a helpful message if an expected module is missing."""
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise BuildError(
            f"required tool '{module}' is not installed. "
            f"Install it with: {hint}"
        )


def build() -> None:
    ensure_tool("build", hint="pip install build")
    run([sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(DIST_DIR)])


def twine_check() -> None:
    ensure_tool("twine", hint="pip install twine")
    artifacts = sorted(DIST_DIR.glob("*"))
    if not artifacts:
        raise BuildError(f"no artifacts found in {DIST_DIR}")
    run([sys.executable, "-m", "twine", "check", *map(str, artifacts)])


def summarize() -> None:
    artifacts = sorted(DIST_DIR.glob("*"))
    if not artifacts:
        log("no artifacts produced")
        return
    log("artifacts ready in ./dist/:")
    for path in artifacts:
        size_kb = path.stat().st_size / 1024
        print(f"    {path.name:<60} {size_kb:>8.1f} KB")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="keep any existing dist/ and build/ directories",
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="remove dist/ and build/ and exit without building",
    )
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="skip the final 'twine check' validation pass",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        if not args.no_clean or args.clean_only:
            clean(CLEANABLE_DIRS)

        if args.clean_only:
            log("clean complete")
            return 0

        build()

        if not args.no_check:
            twine_check()

        summarize()
    except BuildError as err:
        log(f"FAILED: {err}")
        return 1

    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
