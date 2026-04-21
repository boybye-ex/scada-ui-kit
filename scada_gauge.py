"""Standalone demo for :class:`scada_widgets.ScadaRadialGauge`.

Kept DRY - the widget definition lives in ``scada_widgets`` and this file only
exercises it (Fluent Python "don't repeat yourself" ethos).
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QSlider, QVBoxLayout, QWidget

from scada_ui_kit import ScadaRadialGauge


def main() -> int:
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("SCADA Radial Gauge Test")
    window.setStyleSheet("background-color: #1E1E1E;")

    layout = QVBoxLayout(window)
    gauge = ScadaRadialGauge(title="MAIN COMPRESSOR", unit="PSI")
    layout.addWidget(gauge)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(0, 100)
    slider.valueChanged.connect(lambda v: setattr(gauge, "value", v))
    layout.addWidget(slider)

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
