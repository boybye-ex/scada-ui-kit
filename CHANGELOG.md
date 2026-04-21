# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `CHANGELOG.md` tracking project history in Keep a Changelog format.
- Live status, PyPI, Python, wheel, license, and changelog badges in `README.md`,
  all reading PyPI/GitHub metadata so they never drift from the source of truth.
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) that builds an sdist
  and wheel across Python 3.10 / 3.13 on Ubuntu and Windows, runs
  `twine check`, and uploads the verified artifacts for PR reviewers.

### Fixed

- `bump_version.py` no longer emits a raw `FileNotFoundError` traceback when
  `git` is not on `PATH`; `ensure_git_on_path()` now uses `shutil.which` for a
  clean preflight and a human-readable install-guidance error.

## [0.1.1] - 2026-04-21

### Added

- Root-level `LICENSE` file (MIT) so source distributions include the licence
  text and PyPI surfaces it in the project metadata.

### Changed

- `pyproject.toml` now uses the PEP 639 SPDX `license = "MIT"` string plus
  `license-files = ["LICENSE"]`, replacing the deprecated `{ text = "MIT" }`
  table form and the obsolete `License :: OSI Approved :: MIT License`
  classifier. Requires `setuptools >= 77.0.0`.
- Package version is now dynamically resolved by setuptools from
  `scada_ui_kit.__version__` via `[tool.setuptools.dynamic]`, making
  `scada_ui_kit/__init__.py` the single source of truth for the version
  string. The `pyproject.toml` value is no longer manually edited.

## [0.1.0] - 2026-04-21

### Added

- Initial public release of `scada_ui_kit`.
- `ScadaRadialGauge` — dark-mode radial gauge with a configurable alert
  threshold; value updates via the `.value` property trigger an automatic
  repaint.
- `ScadaStripChart` — real-time scrolling telemetry chart backed by a
  fixed-length `collections.deque` for **O(1)** appends and automatic eviction
  of the oldest sample. Implements `__len__`, `__iter__`, and `__getitem__`.
- `ScadaIndicator` + `ScadaIndicatorMatrix` — multi-state LED indicators laid
  out in a grid. The matrix implements the full mapping protocol
  (`__getitem__`, `__setitem__`, `__contains__`, `__iter__`, `__len__`) so
  systems can be addressed by name.
- `ScadaToggle` — heavy-duty actuator switch that emits `toggled(bool)` for
  observer-pattern wiring into indicator matrices or business logic.
- `IndicatorState` `IntEnum` (`OFFLINE`, `RUNNING`, `WARNING`, `FAULT`) with a
  read-only `MappingProxyType` colour table.
- PEP 561 `py.typed` marker so downstream projects' `mypy` / `pyright` pick up
  the annotations.
- Explicit re-exports from `scada_ui_kit/__init__.py` using the
  `from .scada_widgets import X as X` pattern for strict type-checker visibility.
- Packaging and release tooling: `build_package.py` (sdist + wheel + `twine
  check`), `publish.py` (TestPyPI-by-default with explicit production opt-in),
  and `bump_version.py` (SemVer-validated version bumps with optional
  `--commit` / `--tag` git automation).
- `main_dashboard.py` reference application and per-widget demo scripts.

[Unreleased]: https://github.com/boybye-ex/scada-ui-kit/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/boybye-ex/scada-ui-kit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/boybye-ex/scada-ui-kit/releases/tag/v0.1.0
