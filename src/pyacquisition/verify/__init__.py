"""Verifying that instrument classes work with the physical device connected.

The engine plans checks from an instrument class and the TOML spec beside it,
runs them under strict safety rules, and returns a structured report. Front
ends: a pytest layer (`tests/hardware`) and `python -m pyacquisition.verify`.
"""

from .checks import coverage, plan
from .guard import GuardedResource, SafetyViolation
from .inventory import Entry, Unreachable, build_session, load_inventory, open_session
from .model import Hazard, Report, Result, SpecError, Status
from .runner import Bench, verify
from .session import Policy, Session
from .spec import Spec, load_spec, parse_spec

__all__ = [
    "Bench",
    "Entry",
    "GuardedResource",
    "Hazard",
    "Policy",
    "Report",
    "Result",
    "SafetyViolation",
    "Session",
    "Spec",
    "SpecError",
    "Status",
    "Unreachable",
    "build_session",
    "coverage",
    "load_inventory",
    "load_spec",
    "open_session",
    "parse_spec",
    "plan",
    "verify",
]
