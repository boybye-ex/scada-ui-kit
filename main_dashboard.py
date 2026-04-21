"""Unified SCADA dashboard.

Demonstrates the refactored kit driven by Fluent-Python-style idioms:

* property assignment instead of ``set_*`` methods (ch. 22)
* ``IndicatorState`` enum in place of magic numbers (ch. 11)
* mapping-style writes into ``ScadaIndicatorMatrix`` (ch. 12)
* a generator function as the telemetry source (ch. 17)
* ``@dataclass(frozen=True)`` configuration object (ch. 5)
* Qt signals wiring toggles to status indicators (ch. 10 - observer pattern)
"""

from __future__ import annotations

import math
import random
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Final

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from scada_ui_kit import (
    IndicatorState,
    ScadaIndicatorMatrix,
    ScadaRadialGauge,
    ScadaStripChart,
    ScadaToggle,
)


SECTION_STYLE: Final[str] = (
    "color: #7F8C8D; font-family: Consolas; font-weight: bold; font-size: 16px;"
)
LABEL_STYLE: Final[str] = "color: white; font-family: Consolas;"


@dataclass(frozen=True, slots=True)
class TelemetryConfig:
    """Configuration for the simulated pressure sensor (Fluent Python ch. 5)."""

    center: float = 75.0
    amplitude: float = 60.0
    frequency: float = 0.05
    noise: float = 3.0


def pressure_samples(cfg: TelemetryConfig) -> Iterator[float]:
    """Infinite generator of simulated pressure readings (Fluent Python ch. 17)."""
    step = 0
    while True:
        base = cfg.center + math.sin(step * cfg.frequency) * cfg.amplitude
        yield base + random.uniform(-cfg.noise, cfg.noise)
        step += 1


class ScadaDashboard(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Industrial SCADA Overview")
        self.setStyleSheet("background-color: #1A1A1A;")
        self.resize(1000, 600)

        self._build_ui()
        self._seed_initial_state()
        self._wire_signals()
        self._start_simulation()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        root.addLayout(self._build_left_column(), stretch=3)
        root.addLayout(self._build_right_column(), stretch=2)

    def _build_left_column(self) -> QVBoxLayout:
        column = QVBoxLayout()
        self.main_gauge = ScadaRadialGauge(
            title="REACTOR PRESSURE", unit="PSI", min_val=0, max_val=150
        )
        self.main_chart = ScadaStripChart(max_points=100, min_val=0, max_val=150)
        column.addWidget(self.main_gauge, stretch=2)
        column.addWidget(self.main_chart, stretch=1)
        return column

    def _build_right_column(self) -> QVBoxLayout:
        column = QVBoxLayout()

        column.addWidget(self._section_label("SYSTEM STATUS"))
        self.status_matrix = ScadaIndicatorMatrix(columns=2)
        for system in ("COOLANT", "CORE TEMP", "CONTAINMENT", "VENTILATION"):
            self.status_matrix.add_indicator(system)
        column.addWidget(self.status_matrix, stretch=2)

        column.addWidget(self._section_label("MANUAL OVERRIDES"))
        controls = QHBoxLayout()
        self.pump_toggle, pump_block = self._labelled_toggle("PUMP 1")
        self.valve_toggle, valve_block = self._labelled_toggle("VALVE A")
        controls.addLayout(pump_block)
        controls.addLayout(valve_block)
        column.addLayout(controls, stretch=1)

        return column

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(SECTION_STYLE)
        return label

    @staticmethod
    def _labelled_toggle(name: str) -> tuple[ScadaToggle, QVBoxLayout]:
        block = QVBoxLayout()
        title = QLabel(name)
        title.setStyleSheet(LABEL_STYLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toggle = ScadaToggle()
        block.addWidget(title)
        block.addWidget(toggle, alignment=Qt.AlignmentFlag.AlignCenter)
        return toggle, block

    # ------------------------------------------------------------- Behaviour --

    def _seed_initial_state(self) -> None:
        # Mapping-style writes on ScadaIndicatorMatrix (Fluent Python ch. 12).
        self.status_matrix["COOLANT"] = IndicatorState.RUNNING
        self.status_matrix["CORE TEMP"] = IndicatorState.RUNNING
        self.status_matrix["CONTAINMENT"] = IndicatorState.RUNNING
        self.status_matrix["VENTILATION"] = IndicatorState.WARNING

    def _wire_signals(self) -> None:
        # Observer pattern: a toggle flip drives the status matrix.
        self.pump_toggle.toggled.connect(self._on_pump_toggled)
        self.valve_toggle.toggled.connect(self._on_valve_toggled)

    def _on_pump_toggled(self, is_on: bool) -> None:
        self.status_matrix["COOLANT"] = (
            IndicatorState.RUNNING if is_on else IndicatorState.OFFLINE
        )

    def _on_valve_toggled(self, is_on: bool) -> None:
        self.status_matrix["CONTAINMENT"] = (
            IndicatorState.RUNNING if is_on else IndicatorState.WARNING
        )

    def _start_simulation(self) -> None:
        self._samples = pressure_samples(TelemetryConfig())
        self.simulation_timer = QTimer()
        self.simulation_timer.timeout.connect(self._tick)
        self.simulation_timer.start(50)  # 20 Hz

    def _tick(self) -> None:
        reading = next(self._samples)
        # Property-based API - no more ``set_value`` / ``add_value`` duplication.
        self.main_gauge.value = reading
        self.main_chart.add_value(reading)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dashboard = ScadaDashboard()
    dashboard.show()
    sys.exit(app.exec())
