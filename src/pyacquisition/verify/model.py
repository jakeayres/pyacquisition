"""The vocabulary of the verification engine: hazards, statuses and results."""

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum


class Hazard(Enum):
    """What a check can do to the instrument, from least to most.

    Every check carries one, and a run only performs the checks it allows.
    """

    READ_ONLY = "read-only"  # only asks questions
    REVERSIBLE = "reversible"  # changes a setting and puts it back
    HAZARDOUS = "hazardous"  # can act on the outside world: outputs, heaters...

    @property
    def rank(self):
        return list(Hazard).index(self)

    @classmethod
    def parse(cls, text):
        for hazard in cls:
            if hazard.value == text:
                return hazard
        raise ValueError(
            f"unknown hazard {text!r}, expected one of {[h.value for h in cls]}"
        )


class Status(Enum):
    PASSED = "pass"
    FAILED = "FAIL"
    SKIPPED = "skip"
    DRY_RUN = "dry"  # not run: the commands that would have been sent are listed


class SpecError(ValueError):
    """A verification spec that is malformed or does not fit its instrument."""


class Skip(Exception):
    """Raised by a check that cannot run, with the reason."""


class CheckFailed(Exception):
    """Raised by a check that ran and found something wrong."""


@dataclass
class Result:
    instrument: str
    check: str
    level: int
    hazard: Hazard
    status: Status
    detail: str = ""
    sent: list = field(default_factory=list)

    def to_dict(self):
        return {
            "instrument": self.instrument,
            "check": self.check,
            "level": self.level,
            "hazard": self.hazard.value,
            "status": self.status.name.lower(),
            "detail": self.detail,
            "sent": self.sent,
        }


@dataclass
class Report:
    """Everything a verification run found."""

    results: list = field(default_factory=list)
    instruments: dict = field(default_factory=dict)
    dry_run: bool = False

    def add(self, result):
        self.results.append(result)

    @property
    def failed(self):
        return [r for r in self.results if r.status is Status.FAILED]

    @property
    def ok(self):
        return not self.failed

    def counts(self):
        counts = Counter(r.status for r in self.results)
        return {status.name.lower(): counts.get(status, 0) for status in Status}

    def to_dict(self):
        return {
            "dry_run": self.dry_run,
            "counts": self.counts(),
            "instruments": self.instruments,
            "results": [r.to_dict() for r in self.results],
        }

    def text(self, verbose=False):
        """The report as text. Commands sent are shown for a dry run, or `verbose`."""
        lines = []
        if self.dry_run:
            lines.append(
                "DRY RUN: no instrument was contacted, results are not evidence"
            )
        for name in dict.fromkeys(r.instrument for r in self.results):
            info = self.instruments.get(name, {})
            title = f"{name} ({info['class']})" if "class" in info else name
            if info.get("identity"):
                title += f"  {info['identity']}"
            lines.append("")
            lines.append(title)
            for result in (r for r in self.results if r.instrument == name):
                line = f"  {result.status.value:<5} {result.hazard.value:<10} {result.check}"
                if result.detail and result.status is not Status.PASSED:
                    line += f"  -- {result.detail}"
                lines.append(line)
                if result.sent and (verbose or self.dry_run):
                    lines.extend(f"          > {message}" for message in result.sent)
            untested = info.get("untested")
            if untested:
                lines.append(f"  not covered ({len(untested)}): {', '.join(untested)}")
            for method in info.get("set_registered_as_query", ()):
                lines.append(
                    f"  WARNING {method} is registered as a query but is named like a setter"
                )
            for problem in info.get("close_problems", ()):
                lines.append(f"  WARNING {problem}")
        counts = self.counts()
        lines.append("")
        lines.append(
            "summary: "
            + ", ".join(f"{n} {status}" for status, n in counts.items() if n)
        )
        return "\n".join(lines)
