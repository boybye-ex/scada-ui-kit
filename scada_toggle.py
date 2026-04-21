"""Standalone demo for :class:`scada_widgets.ScadaToggle`.

Also demonstrates the new ``toggled(bool)`` Qt signal (Fluent Python ch. 10 -
observer pattern through first-class callables).
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from scada_ui_kit import ScadaToggle


def main() -> int:
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("Actuator Toggle Test")
    window.setStyleSheet("background-color: #1E1E1E;")

    layout = QVBoxLayout(window)

    header = QLabel("MAIN WATER PUMP")
    header.setStyleSheet("color: white; font-family: Consolas; font-size: 14px;")
    header.setAlignment(Qt.AlignmentFlag.AlignCenter)

    status = QLabel("STATE: OFF")
    status.setStyleSheet("color: #7F8C8D; font-family: Consolas; font-size: 12px;")
    status.setAlignment(Qt.AlignmentFlag.AlignCenter)

    toggle = ScadaToggle()
    toggle.toggled.connect(lambda on: status.setText(f"STATE: {'ON' if on else 'OFF'}"))

    layout.addWidget(header)
    layout.addWidget(toggle, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(status)

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
