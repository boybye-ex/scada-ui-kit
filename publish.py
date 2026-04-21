"""Publish ``scada-ui-kit`` to TestPyPI or PyPI.

Safety-first workflow:

1. Verifies ``twine`` is importable (``importlib.util.find_spec``).
2. Discovers built artifacts in ``./dist/`` (``*.whl`` + ``*.tar.gz`` only -
   any stray files are ignored).
3. Runs ``twine check`` against those artifacts before touching the network.
4. Defaults to **TestPyPI**; production uploads require ``--production`` *and*
   an interactive ``y/N`` confirmation (``--yes`` skips the prompt for CI).
5. Delegates credential handling to ``twine`` so ``TWINE_USERNAME`` /
   ``TWINE_PASSWORD``, ``.pypirc``, and keyring all work unchanged.

Usage::

    python publish.py                 # dry-run-ish: pushes to TestPyPI
    python publish.py --production    # asks for y/N, then uploads to real PyPI
    python publish.py --production -y # non-interactive production upload (CI)

Written to match the idioms already established in ``build_package.py``:
``from __future__ import annotations``, module-level ``Final`` paths, a tiny
``log()`` helper, a custom exception, and a ``parse_args()`` / ``main()``
split (Fluent Python ch. 8, 15, 18).
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).resolve().parent
DIST_DIR: Final[Path] = ROOT / "dist"
ARTIFACT_GLOBS: Final[tuple[str, ...]] = ("*.whl", "*.tar.gz")

TESTPYPI_URL: Final[str] = "https://test.pypi.org/legacy/"
PYPI_URL: Final[str] = "https://upload.pypi.org/legacy/"


class PublishError(RuntimeError):
    """Raised when a publish step fails."""


def log(message: str) -> None:
    print(f"[publish] {message}", flush=True)


def run(cmd: Sequence[str]) -> None:
    log("$ " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise PublishError(
            f"command failed with exit code {result.returncode}: {' '.join(cmd)}"
        )


def ensure_tool(module: str, hint: str) -> None:
    """Fail fast with a helpful message if ``module`` isn't importable."""
    if importlib.util.find_spec(module) is None:
        raise PublishError(
            f"required tool '{module}' is not installed. "
            f"Install it with: {hint}"
        )


def discover_artifacts() -> list[Path]:
    """Return the sorted list of publishable artifacts in ``./dist/``."""
    if not DIST_DIR.is_dir():
        raise PublishError(
            f"{DIST_DIR} does not exist. Run 'python build_package.py' first."
        )
    artifacts = sorted(
        {path for pattern in ARTIFACT_GLOBS for path in DIST_DIR.glob(pattern)}
    )
    if not artifacts:
        raise PublishError(
            f"no .whl or .tar.gz files in {DIST_DIR}. "
            f"Run 'python build_package.py' first."
        )
    return artifacts


def confirm_production(skip_prompt: bool) -> None:
    """Interactive safety gate. Honours ``--yes`` for unattended runs."""
    log(f"target index: {PYPI_URL}  (PRODUCTION)")
    if skip_prompt:
        log("--yes supplied; skipping confirmation prompt")
        return
    if not sys.stdin.isatty():
        raise PublishError(
            "refusing to upload to PRODUCTION PyPI from a non-interactive "
            "session without --yes"
        )
    answer = input("[publish] Type 'yes' to proceed with production upload: ")
    if answer.strip().lower() != "yes":
        raise PublishError("production upload cancelled by user")


def upload(
    artifacts: Sequence[Path],
    *,
    production: bool,
    skip_existing: bool,
) -> None:
    repository = "pypi" if production else "testpypi"
    # In a TTY we want verbose progress; in CI we want twine to hard-fail
    # rather than prompt for a missing password.
    interaction_flag = "--verbose" if sys.stdin.isatty() else "--non-interactive"
    cmd: list[str] = [
        sys.executable,
        "-m",
        "twine",
        "upload",
        "--repository",
        repository,
        interaction_flag,
    ]
    if skip_existing:
        cmd.append("--skip-existing")
    cmd.extend(str(path) for path in artifacts)
    try:
        run(cmd)
    except PublishError as err:
        raise PublishError(
            f"twine upload failed ({err}). Common causes:\n"
            f"    (a) HTTP 403 'Invalid authentication' - wrong or missing "
            f"token for this index; PyPI and TestPyPI use separate accounts "
            f"and separate tokens.\n"
            f"    (b) HTTP 400 'File already exists' - this name+version is "
            f"already on the target index; bump the version or re-run with "
            f"--skip-existing if that's expected.\n"
            f"    (c) network / DNS failure.\n"
            f"Twine's full response is printed above this summary."
        ) from err


def summarize(artifacts: Sequence[Path]) -> None:
    log("artifacts discovered:")
    for path in artifacts:
        size_kb = path.stat().st_size / 1024
        print(f"    {path.name:<60} {size_kb:>8.1f} KB")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--production",
        action="store_true",
        help="upload to the real PyPI index (defaults to TestPyPI)",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="skip the interactive confirmation prompt (for CI pipelines)",
    )
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="skip the preflight 'twine check' pass",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help=(
            "pass --skip-existing to twine so files already published at the "
            "target index are treated as a no-op instead of an error. Useful "
            "for safely re-running after a partial or aborted upload."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        ensure_tool("twine", hint="pip install -e .[build]")

        artifacts = discover_artifacts()
        summarize(artifacts)

        if not args.no_check:
            run([sys.executable, "-m", "twine", "check", *map(str, artifacts)])

        if args.production:
            confirm_production(skip_prompt=args.yes)
        else:
            log(f"target index: {TESTPYPI_URL}  (TestPyPI, safe default)")

        upload(
            artifacts,
            production=args.production,
            skip_existing=args.skip_existing,
        )

    except PublishError as err:
        log(f"FAILED: {err}")
        return 1
    except KeyboardInterrupt:
        log("aborted by user")
        return 130

    log("publish sequence complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
