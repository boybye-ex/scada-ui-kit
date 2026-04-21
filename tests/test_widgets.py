"""Unit tests for the public API surface of ``scada_ui_kit``.

Every test touches one of the Fluent Python idioms the library is built on:

* the ``.value`` and ``.state`` properties and their clamping / validation,
* the sequence protocol on :class:`ScadaStripChart` (``__len__``, ``__iter__``,
  ``__getitem__``),
* the mapping protocol on :class:`ScadaIndicatorMatrix` (``__contains__``,
  ``__getitem__``, ``__setitem__``, ``__iter__``, ``__len__``),
* the observer pattern on :class:`ScadaToggle` (``toggled`` Qt signal),
* the ``IntEnum`` back-compat contract on :class:`IndicatorState`.

Widgets are registered with ``qtbot.addWidget`` so pytest-qt disposes of them
after each test, avoiding leaked ``QWidget`` references across the suite.
"""

from __future__ import annotations

import pytest
from PyQt6.QtCore import Qt

from scada_ui_kit import (
    IndicatorState,
    ScadaIndicatorMatrix,
    ScadaRadialGauge,
    ScadaStripChart,
    ScadaToggle,
)


def test_radial_gauge_clamps_to_range(qtbot):
    """``gauge.value`` setter must clamp out-of-range assignments."""
    gauge = ScadaRadialGauge(min_val=0, max_val=100)
    qtbot.addWidget(gauge)

    gauge.value = 150
    assert gauge.value == 100

    gauge.value = -50
    assert gauge.value == 0


def test_strip_chart_buffer_rollover(qtbot):
    """The fixed-length ``deque`` must evict oldest samples on overflow."""
    chart = ScadaStripChart(max_points=5, min_val=0, max_val=100)
    qtbot.addWidget(chart)

    for sample in range(10):
        chart.add_value(sample)

    assert len(chart) == 5
    assert list(chart) == [5, 6, 7, 8, 9]
    assert chart[-1] == 9


def test_strip_chart_rejects_tiny_buffer(qtbot):
    """``max_points < 2`` is a programmer error; surface it at construction."""
    with pytest.raises(ValueError):
        ScadaStripChart(max_points=1)


def test_matrix_mapping_protocol(qtbot):
    """The matrix must behave like a real ``Mapping[str, ScadaIndicator]``."""
    matrix = ScadaIndicatorMatrix(columns=2)
    qtbot.addWidget(matrix)

    matrix.add_indicator("PUMP_1")

    assert "PUMP_1" in matrix
    assert len(matrix) == 1

    matrix["PUMP_1"] = IndicatorState.WARNING
    assert matrix["PUMP_1"].state == IndicatorState.WARNING


def test_matrix_iteration_preserves_insertion_order(qtbot):
    """``__iter__`` must yield names in the order they were added."""
    matrix = ScadaIndicatorMatrix(columns=3)
    qtbot.addWidget(matrix)

    names = ("COOLANT", "CORE_TEMP", "CONTAINMENT", "VENTILATION")
    for name in names:
        matrix.add_indicator(name)

    assert tuple(matrix) == names


def test_indicator_state_accepts_raw_ints(qtbot):
    """``IndicatorState`` is an ``IntEnum``; raw int assignments must work."""
    matrix = ScadaIndicatorMatrix(columns=1)
    qtbot.addWidget(matrix)
    matrix.add_indicator("CORE_TEMP")

    # Raw int 3 corresponds to IndicatorState.FAULT.
    matrix["CORE_TEMP"] = 3
    assert matrix["CORE_TEMP"].state == IndicatorState.FAULT
    assert int(matrix["CORE_TEMP"].state) == 3


def test_toggle_click_emits_signal(qtbot):
    """A left-click must flip ``is_active`` and emit ``toggled(True)``."""
    toggle = ScadaToggle()
    qtbot.addWidget(toggle)

    assert toggle.is_active is False

    with qtbot.waitSignal(toggle.toggled, timeout=1000) as blocker:
        qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton)

    assert blocker.args == [True]
    assert toggle.is_active is True


def test_toggle_bool_reflects_state(qtbot):
    """``bool(toggle)`` is the canonical truthiness hook for an actuator."""
    toggle = ScadaToggle()
    qtbot.addWidget(toggle)

    assert not toggle

    toggle.is_active = True
    assert toggle
