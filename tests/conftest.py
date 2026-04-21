"""Shared pytest fixtures and test-time configuration.

This module is imported by pytest before any test module is collected, which
is exactly when we need to force the Qt offscreen platform plugin. Without
it, the widget tests fail on Linux CI runners with ``qt.qpa.xcb: could not
connect to display``.

Setting the env var here (rather than in an ``autouse`` fixture) guarantees
it's in place before PyQt6 is ever imported by pytest-qt or by the tests
themselves - imports happen top-of-file, before fixtures run.
"""

from __future__ import annotations

import os

# Use ``setdefault`` so developers can override locally with ``QT_QPA_PLATFORM=xcb``
# or similar when they want to see the widgets on screen while debugging a test.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
