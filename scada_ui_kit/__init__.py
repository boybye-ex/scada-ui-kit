"""SCADA UI Kit - industrial PyQt6 widget library.

Public API re-exports below follow PEP 484's ``import X as X`` idiom
(Fluent Python ch. 15) so type checkers treat each symbol as an
intentional public export rather than a "private import".
"""

from __future__ import annotations

from .scada_widgets import IndicatorState as IndicatorState
from .scada_widgets import ScadaIndicator as ScadaIndicator
from .scada_widgets import ScadaIndicatorMatrix as ScadaIndicatorMatrix
from .scada_widgets import ScadaRadialGauge as ScadaRadialGauge
from .scada_widgets import ScadaStripChart as ScadaStripChart
from .scada_widgets import ScadaToggle as ScadaToggle

__version__ = "0.1.0"

__all__ = [
    "IndicatorState",
    "ScadaIndicator",
    "ScadaIndicatorMatrix",
    "ScadaRadialGauge",
    "ScadaStripChart",
    "ScadaToggle",
    "__version__",
]
