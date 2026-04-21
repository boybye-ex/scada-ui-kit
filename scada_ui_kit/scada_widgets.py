"""SCADA UI Kit - core widget library.

Refactored to follow idioms from *Fluent Python* (Ramalho, 2e):

* Ch. 1/11 - rich ``__repr__`` and other dunder methods
* Ch. 2    - ``collections.deque(maxlen=...)`` for the rolling strip-chart buffer
* Ch. 3    - ``types.MappingProxyType`` for the read-only state-colour palette
* Ch. 5/11 - ``IntEnum`` for indicator states (back-compat with raw ints)
* Ch. 8/15 - complete type hints, ``Final`` constants, ``from __future__ import annotations``
* Ch. 10   - observer pattern via first-class callables (``pyqtSignal``)
* Ch. 12   - ``ScadaIndicatorMatrix`` implements the mapping protocol
* Ch. 18   - ``painting`` context manager guarantees ``QPainter.end()``
* Ch. 22   - ``@property`` accessors replace ad-hoc ``set_*`` methods
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from enum import IntEnum
from types import MappingProxyType
from typing import Final

from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QGridLayout, QWidget

__all__ = [
    "IndicatorState",
    "STATE_COLORS",
    "ScadaRadialGauge",
    "ScadaStripChart",
    "ScadaIndicator",
    "ScadaIndicatorMatrix",
    "ScadaToggle",
]


# ---------------------------------------------------------------------------
# Module-level constants (Fluent Python ch. 15 - ``Final``)
# ---------------------------------------------------------------------------

FONT_FAMILY: Final[str] = "Consolas"
BORDER_COLOR: Final[QColor] = QColor("#2C3E50")
LABEL_COLOR: Final[QColor] = QColor("#ECF0F1")
ACCENT_CYAN: Final[QColor] = QColor("#00D2FF")
ALERT_RED: Final[QColor] = QColor("#E74C3C")
TRACK_BG: Final[QColor] = QColor("#17202A")
GRID_LINE: Final[QColor] = QColor("#34495E")
LINE_GREEN: Final[QColor] = QColor("#2ECC71")
ALERT_THRESHOLD: Final[float] = 0.8


class IndicatorState(IntEnum):
    """Operational state of a monitored system (Fluent Python ch. 11)."""

    OFFLINE = 0
    RUNNING = 1
    WARNING = 2
    FAULT = 3


# Read-only palette: wrapping a dict in ``MappingProxyType`` gives callers a
# view they cannot mutate (Fluent Python ch. 3).
STATE_COLORS: Final[Mapping[IndicatorState, QColor]] = MappingProxyType(
    {
        IndicatorState.OFFLINE: QColor("#7F8C8D"),
        IndicatorState.RUNNING: QColor("#2ECC71"),
        IndicatorState.WARNING: QColor("#F1C40F"),
        IndicatorState.FAULT: QColor("#E74C3C"),
    }
)


# ---------------------------------------------------------------------------
# Pure helpers (Fluent Python ch. 7 - functions as first-class objects)
# ---------------------------------------------------------------------------

def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@contextmanager
def painting(widget: QWidget) -> Iterator[QPainter]:
    """Context-managed ``QPainter`` (Fluent Python ch. 18).

    Guarantees ``painter.end()`` runs even if the paint routine raises,
    which ``QPainter``'s reliance on ``__del__`` does not.
    """
    painter = QPainter(widget)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        yield painter
    finally:
        painter.end()


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------


class ScadaRadialGauge(QWidget):
    """Industrial radial gauge with colour-coded alert threshold."""

    def __init__(
        self,
        title: str = "PRESSURE",
        unit: str = "PSI",
        min_val: float = 0,
        max_val: float = 100,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self._value: float = self.min_val
        self.setMinimumSize(250, 250)

    # --- Pythonic object protocol ------------------------------------------

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(title={self.title!r}, unit={self.unit!r}, "
            f"range=({self.min_val}, {self.max_val}), value={self._value})"
        )

    # --- Property-based API (Fluent Python ch. 22) -------------------------

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, new_value: float) -> None:
        clamped = _clamp(float(new_value), self.min_val, self.max_val)
        if clamped == self._value:
            return
        self._value = clamped
        self.update()

    @property
    def percent(self) -> float:
        span = self.max_val - self.min_val
        return (self._value - self.min_val) / span if span else 0.0

    # --- Painting -----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: D401 - Qt-required name
        with painting(self) as painter:
            rect = self.rect()
            size = min(rect.width(), rect.height()) - 40
            center_x = rect.width() / 2
            center_y = rect.height() / 2
            arc_rect = QRectF(center_x - size / 2, center_y - size / 2, size, size)

            painter.setPen(QPen(BORDER_COLOR, 18, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(arc_rect, 210 * 16, -240 * 16)

            percent = self.percent
            span_angle = int(-240 * percent * 16)
            color = ALERT_RED if percent > ALERT_THRESHOLD else ACCENT_CYAN
            painter.setPen(QPen(color, 18, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(arc_rect, 210 * 16, span_angle)

            painter.setPen(LABEL_COLOR)
            painter.setFont(QFont(FONT_FAMILY, 24, QFont.Weight.Bold))
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                f"{self._value:.0f}\n{self.unit}",
            )

            painter.setFont(QFont(FONT_FAMILY, 10, QFont.Weight.Bold))
            painter.drawText(
                int(center_x - size / 2),
                int(center_y + size / 2.2),
                int(size),
                30,
                Qt.AlignmentFlag.AlignCenter,
                self.title,
            )


class ScadaStripChart(QWidget):
    """Real-time scrolling telemetry chart backed by a fixed-length ``deque``."""

    def __init__(
        self,
        max_points: int = 100,
        min_val: float = 0,
        max_val: float = 100,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if max_points < 2:
            raise ValueError("max_points must be >= 2")
        self.max_points: Final[int] = max_points
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        # deque(maxlen=...) drops the leftmost element on append automatically
        # (Fluent Python ch. 2, "An Array of Sequences").
        self._data: deque[float] = deque(
            [self.min_val] * max_points, maxlen=max_points
        )
        self.setMinimumSize(300, 150)

    # --- Sequence protocol (Fluent Python ch. 12) --------------------------

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[float]:
        return iter(self._data)

    def __getitem__(self, index: int) -> float:
        return self._data[index]

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(max_points={self.max_points}, "
            f"range=({self.min_val}, {self.max_val}), latest={self._data[-1]:.2f})"
        )

    # --- Data ingestion -----------------------------------------------------

    def add_value(self, val: float) -> None:
        """Append a new sample; the oldest sample is dropped automatically."""
        self._data.append(_clamp(float(val), self.min_val, self.max_val))
        self.update()

    # --- Painting -----------------------------------------------------------

    def paintEvent(self, event) -> None:
        with painting(self) as painter:
            rect = self.rect()
            width = rect.width()
            height = rect.height()

            painter.fillRect(rect, TRACK_BG)

            painter.setPen(QPen(GRID_LINE, 1, Qt.PenStyle.DashLine))
            for i in range(1, 5):
                y = int(height * (i / 5))
                painter.drawLine(0, y, width, y)
            for i in range(1, 10):
                x = int(width * (i / 10))
                painter.drawLine(x, 0, x, height)

            path = QPainterPath()
            span = self.max_val - self.min_val
            x_step = width / (self.max_points - 1)
            for i, val in enumerate(self._data):
                x = i * x_step
                y_percent = (val - self.min_val) / span if span else 0.0
                y = height - (y_percent * height)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            painter.setPen(QPen(LINE_GREEN, 2, Qt.PenStyle.SolidLine))
            painter.drawPath(path)


class ScadaIndicator(QWidget):
    """Single multi-state LED-style indicator."""

    def __init__(self, label: str = "SYSTEM", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.label = label
        self._state: IndicatorState = IndicatorState.OFFLINE
        self.setMinimumSize(80, 100)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(label={self.label!r}, state={self._state.name})"

    @property
    def state(self) -> IndicatorState:
        return self._state

    @state.setter
    def state(self, value: IndicatorState | int) -> None:
        new_state = IndicatorState(int(value))
        if new_state == self._state:
            return
        self._state = new_state
        self.update()

    def paintEvent(self, event) -> None:
        with painting(self) as painter:
            rect = self.rect()
            width = rect.width()

            circle_size = min(width, 50)
            center_x = width / 2
            circle_rect = QRectF(
                center_x - circle_size / 2, 10, circle_size, circle_size
            )

            painter.setBrush(STATE_COLORS[self._state])
            painter.setPen(QPen(BORDER_COLOR, 3))
            painter.drawEllipse(circle_rect)

            painter.setPen(LABEL_COLOR)
            painter.setFont(QFont(FONT_FAMILY, 9, QFont.Weight.Bold))
            painter.drawText(
                0,
                int(circle_size + 15),
                width,
                30,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                self.label,
            )


class ScadaIndicatorMatrix(QWidget):
    """Grid container exposing the :class:`Mapping` protocol (Fluent Python ch. 12).

    Usage::

        matrix = ScadaIndicatorMatrix(columns=2)
        matrix.add_indicator("COOLANT")
        matrix["COOLANT"] = IndicatorState.RUNNING   # mapping-style set
        assert "COOLANT" in matrix                   # __contains__
        for name in matrix:                          # __iter__
            print(name, matrix[name].state)
    """

    def __init__(self, columns: int = 3, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if columns < 1:
            raise ValueError("columns must be >= 1")
        self._columns: Final[int] = columns
        self._grid = QGridLayout()
        self.setLayout(self._grid)
        self._indicators: dict[str, ScadaIndicator] = {}
        self._next_row = 0
        self._next_col = 0

    # --- Mapping protocol ---------------------------------------------------

    def __len__(self) -> int:
        return len(self._indicators)

    def __iter__(self) -> Iterator[str]:
        return iter(self._indicators)

    def __contains__(self, name: object) -> bool:
        return name in self._indicators

    def __getitem__(self, name: str) -> ScadaIndicator:
        return self._indicators[name]

    def __setitem__(self, name: str, state: IndicatorState | int) -> None:
        """``matrix[name] = state`` updates (or adds then updates) an indicator."""
        if name not in self._indicators:
            self.add_indicator(name)
        self._indicators[name].state = IndicatorState(int(state))

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(columns={self._columns}, "
            f"n_indicators={len(self)})"
        )

    # --- Public API ---------------------------------------------------------

    def add_indicator(self, name: str) -> ScadaIndicator:
        """Attach a new indicator to the next available grid slot."""
        if name in self._indicators:
            return self._indicators[name]
        indicator = ScadaIndicator(label=name)
        self._indicators[name] = indicator
        self._grid.addWidget(indicator, self._next_row, self._next_col)
        self._next_col += 1
        if self._next_col >= self._columns:
            self._next_col = 0
            self._next_row += 1
        return indicator

    def update_system_state(
        self, name: str, state: IndicatorState | int
    ) -> None:
        """Back-compat alias; prefer ``matrix[name] = state``."""
        self[name] = state


class ScadaToggle(QWidget):
    """Heavy-duty toggle switch that broadcasts its state via a Qt signal."""

    toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_active: bool = False
        self.setMinimumSize(100, 50)
        self.setMaximumSize(120, 60)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(is_active={self._is_active})"

    def __bool__(self) -> bool:
        return self._is_active

    @property
    def is_active(self) -> bool:
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        new_value = bool(value)
        if new_value == self._is_active:
            return
        self._is_active = new_value
        self.toggled.emit(new_value)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_active = not self._is_active

    def paintEvent(self, event) -> None:
        with painting(self) as painter:
            rect = self.rect()
            width = rect.width()
            height = rect.height()

            track_rect = QRectF(5, 5, width - 10, height - 10)
            thumb_size = height - 18

            if self._is_active:
                track_color = QColor("#27AE60")
                thumb_x = width - thumb_size - 9
                text = "ON"
                text_x = 15
            else:
                track_color = QColor("#555555")
                thumb_x = 9
                text = "OFF"
                text_x = int(width / 2) + 5

            painter.setBrush(track_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(track_rect, height / 2, height / 2)

            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont(FONT_FAMILY, 12, QFont.Weight.Bold))
            painter.drawText(
                text_x,
                5,
                int(width / 2),
                int(height - 10),
                Qt.AlignmentFlag.AlignVCenter,
                text,
            )

            thumb_rect = QRectF(thumb_x, 9, thumb_size, thumb_size)
            painter.setBrush(QColor("#ECF0F1"))
            painter.setPen(QPen(BORDER_COLOR, 2))
            painter.drawEllipse(thumb_rect)
