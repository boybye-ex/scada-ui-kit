"""Standalone demo for :class:`scada_widgets.ScadaStripChart`.

Uses a generator as the sample source (Fluent Python ch. 17).
"""

from __future__ import annotations

import math
import random
import sys
from collections.abc import Iterator

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget

from scada_ui_kit import ScadaStripChart


def sensor_stream(amplitude: float = 30.0, noise: float = 5.0) -> Iterator[float]:
    step = 0
    while True:
        yield math.sin(step * 0.1) * amplitude + random.uniform(-noise, noise)
        step += 1


def main() -> int:
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("SCADA Strip Chart Test")
    window.setStyleSheet("background-color: #1E1E1E;")
    window.resize(600, 300)

    layout = QVBoxLayout(window)
    chart = ScadaStripChart(max_points=100, min_val=-50, max_val=50)
    layout.addWidget(chart)

    samples = sensor_stream()
    timer = QTimer()
    timer.timeout.connect(lambda: chart.add_value(next(samples)))
    timer.start(50)

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
