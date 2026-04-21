"""Standalone demo for :class:`scada_widgets.ScadaIndicatorMatrix`.

Showcases the mapping protocol added to the matrix (Fluent Python ch. 12) -
``matrix[name] = IndicatorState.RUNNING`` replaces the old ``update_system_state``.
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget

from scada_ui_kit import IndicatorState, ScadaIndicatorMatrix


def main() -> int:
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("Indicator Matrix Test")
    window.setStyleSheet("background-color: #1E1E1E;")

    layout = QVBoxLayout(window)
    matrix = ScadaIndicatorMatrix(columns=3)

    for name in ("PUMP 1", "PUMP 2", "VALVE A", "VALVE B", "MAIN FAN", "BACKUP"):
        matrix.add_indicator(name)

    matrix["PUMP 1"] = IndicatorState.RUNNING
    matrix["PUMP 2"] = IndicatorState.RUNNING
    matrix["VALVE B"] = IndicatorState.WARNING
    matrix["BACKUP"] = IndicatorState.FAULT

    layout.addWidget(matrix)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
