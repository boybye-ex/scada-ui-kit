# SCADA UI Kit

[![CI](https://github.com/boybye-ex/scada-ui-kit/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/boybye-ex/scada-ui-kit/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/scada-ui-kit.svg?label=pypi)](https://pypi.org/project/scada-ui-kit/)
[![Python versions](https://img.shields.io/pypi/pyversions/scada-ui-kit.svg)](https://pypi.org/project/scada-ui-kit/)
[![Wheel](https://img.shields.io/pypi/wheel/scada-ui-kit.svg)](https://pypi.org/project/scada-ui-kit/#files)
[![License](https://img.shields.io/pypi/l/scada-ui-kit.svg)](./LICENSE)
[![Changelog](https://img.shields.io/badge/changelog-keep%20a%20changelog-orange.svg)](./CHANGELOG.md)

A robust, enterprise-grade industrial UI widget library for **PyQt6**, engineered for
performance, deep customisation, and a smooth developer experience. The codebase is
written to *Fluent Python* (2e) idioms: rich data-model methods, property-based APIs,
`deque`-backed buffers, `IntEnum` state codes, Qt-signal observers, and fully typed
public interfaces (PEP 561).

## Features

- **`ScadaRadialGauge`** - dark-mode radial gauge with a configurable alert threshold
  that turns the needle red above 80% of range. Assign to `.value` and the widget
  repaints itself.
- **`ScadaStripChart`** - real-time scrolling telemetry chart backed by a fixed-length
  `collections.deque` for **O(1)** appends and automatic eviction of the oldest sample.
  Iterable and subscriptable like a normal sequence.
- **`ScadaIndicator` + `ScadaIndicatorMatrix`** - multi-state LED indicators laid out in
  a grid. The matrix implements the full **mapping protocol**, so you can write
  `matrix["COOLANT"] = IndicatorState.RUNNING`, iterate with `for name in matrix`, and
  check membership with `"COOLANT" in matrix`.
- **`ScadaToggle`** - heavy-duty actuator switch that emits `toggled(bool)` so you can
  wire control inputs straight to your indicator matrix or business logic.
- **`IndicatorState` enum** - `OFFLINE`, `RUNNING`, `WARNING`, `FAULT`. It's an
  `IntEnum`, so raw integers still work for back-compat.
- **Typed** - every public symbol ships with type hints and a PEP 561 `py.typed` marker,
  so `mypy` and `pyright` pick up the annotations out of the box.

## Installation

From the project root:

```bash
pip install .
```

Or, for local development with live code reloads:

```bash
pip install -e .
```

PyQt6 is pulled in automatically as a dependency.

## Quick Start

```python
import sys
from PyQt6.QtWidgets import QApplication
from scada_ui_kit import ScadaRadialGauge

app = QApplication(sys.argv)
gauge = ScadaRadialGauge(title="REACTOR PRESSURE", unit="PSI", min_val=0, max_val=150)
gauge.value = 87        # property assignment - triggers the repaint automatically
gauge.show()
sys.exit(app.exec())
```

### Mapping-style status updates

```python
from scada_ui_kit import IndicatorState, ScadaIndicatorMatrix

matrix = ScadaIndicatorMatrix(columns=2)
for name in ("COOLANT", "CORE TEMP", "CONTAINMENT", "VENTILATION"):
    matrix.add_indicator(name)

matrix["COOLANT"] = IndicatorState.RUNNING
matrix["VENTILATION"] = IndicatorState.WARNING

assert "COOLANT" in matrix
for system in matrix:                         # __iter__ yields indicator names
    print(system, matrix[system].state)       # __getitem__ returns the widget
```

### Toggle with observer wiring

```python
from scada_ui_kit import IndicatorState, ScadaToggle

pump = ScadaToggle()
pump.toggled.connect(
    lambda on: matrix.__setitem__(
        "COOLANT",
        IndicatorState.RUNNING if on else IndicatorState.OFFLINE,
    )
)
```

## Running the demos

The repository ships with five runnable scripts at the project root. Once the package
is installed (`pip install -e .`):

```bash
python main_dashboard.py   # unified dashboard with all widgets and a live feed
python scada_gauge.py      # slider-driven gauge demo
python scada_chart.py      # sine-wave + noise strip chart
python scada_matrix.py     # indicator matrix showcase
python scada_toggle.py     # toggle wired to a live status label
```

## Requirements

- Python **3.10+**
- PyQt6 **6.0+**

## Building distribution artifacts

The repo ships a small helper that produces an sdist and a wheel in `./dist/`
and validates them with `twine check` before any upload.

```bash
pip install -e .[build]      # installs the `build` + `twine` tools locally
python build_package.py      # clean -> build -> twine check -> summary
```

Useful flags:

```bash
python build_package.py --clean-only   # just wipe dist/ and build/
python build_package.py --no-clean     # keep previous artifacts
python build_package.py --no-check     # skip the twine validation pass
```

A successful run prints something like:

```text
[build] artifacts ready in ./dist/:
    scada_ui_kit-0.1.0-py3-none-any.whl                         12.3 KB
    scada_ui_kit-0.1.0.tar.gz                                   10.1 KB
```

The wheel is a single, self-contained file you can distribute to users - they
install it with `pip install scada_ui_kit-0.1.0-py3-none-any.whl`.

## Bumping the version

The package version lives in **one place**: `__version__` in
`scada_ui_kit/__init__.py`. `pyproject.toml` resolves it dynamically at build
time via setuptools' `attr` directive, so drift is impossible by construction.

```bash
python bump_version.py patch        # 0.1.0 -> 0.1.1  (bug fix)
python bump_version.py minor        # 0.1.0 -> 0.2.0  (back-compatible feature)
python bump_version.py major        # 0.1.0 -> 1.0.0  (breaking change)
python bump_version.py 2.7.3        # explicit SemVer set
python bump_version.py patch -n     # dry-run: print the new version and exit
```

### Git automation

```bash
python bump_version.py patch -c     # write + 'git add' + 'git commit'
python bump_version.py patch -c -t  # also create an annotated 'vX.Y.Z' tag
```

Safety checks that run before anything is written:

- If `--commit` or `--tag` is requested, `git rev-parse --is-inside-work-tree`
  verifies we're actually in a repo.
- If `--tag` is requested, `git tag --list vX.Y.Z` must be empty (no clobber).
- The commit is scoped with `git commit -- scada_ui_kit/__init__.py` so any
  unrelated already-staged changes don't get swept into the release commit.

After a successful `--commit -t`, push with:

```bash
git push && git push origin vX.Y.Z
```

### Typical release flow

```bash
# 1. Move [Unreleased] entries in CHANGELOG.md under a new [X.Y.Z] heading
# 2. Bump, commit, and tag (all three in one go)
python bump_version.py patch -c -t        # write, commit, tag
python build_package.py                   # sdist + wheel + twine check
python publish.py                         # TestPyPI (safe default)
python publish.py --production            # real PyPI, with y/N prompt
git push && git push origin vX.Y.Z        # share the release commit/tag
```

## Publishing to PyPI / TestPyPI

Once the artifacts in `dist/` are validated, `publish.py` uploads them with
sensible safety defaults:

```bash
python publish.py                    # uploads to TestPyPI (safe default)
python publish.py --production       # uploads to real PyPI; asks for 'yes'
python publish.py --production -y    # non-interactive production upload (CI)
python publish.py --skip-existing    # idempotent: already-uploaded files are a no-op
```

Authentication is delegated to `twine`, so any of the standard mechanisms work:

- `TWINE_USERNAME` / `TWINE_PASSWORD` environment variables (recommended for
  CI; set `TWINE_USERNAME=__token__` and `TWINE_PASSWORD=<your PyPI API token>`).
- A `~/.pypirc` file with `[pypi]` and `[testpypi]` sections.
- The system keyring, if configured.

Safety features baked into the script:

- `twine check` runs before any upload so malformed metadata is caught locally.
- Production uploads require both `--production` **and** an explicit `yes`
  confirmation (or `--yes` for automation).
- Non-interactive environments (no TTY) without `--yes` are refused outright
  for production, preventing accidents in cron jobs and CI triggers.

## License

MIT
