"""Telemetry is best-effort: a metrics failure must never discard a valid itinerary."""
import logging
import math
import os
import sqlite3
from . import telemetry

log = logging.getLogger(__name__)


def record(*args, **kwargs):
    try:
        return telemetry.record(*args, **kwargs)
    except (sqlite3.Error, OSError, ValueError, TypeError):
        log.warning("Metrics recording unavailable; primary operation preserved")
        return None


def estimated_cost(answer):
    try:
        rate = float(os.getenv('DIFY_COST_PER_1K', '0'))
        return len(answer) / 4000 * rate if math.isfinite(rate) and rate>=0 else 0.0
    except ValueError:
        return 0.0
