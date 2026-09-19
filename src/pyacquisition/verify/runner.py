"""Runs plans against an inventory, connecting each instrument when it is first needed."""

from .checks import coverage, plan
from .inventory import Unreachable, open_session
from .model import Report, Result, Status
from .spec import load_spec


class Bench:
    """The instruments of an inventory, opened on first use and closed together.

    Closing puts every instrument that was written to back in its safe state,
    so use it as a context manager, or call `close` in a `finally`.

    Args:
        policy (Policy): What the run may do.
        dry_run (bool): Contact nothing, and list what would be sent.
    """

    def __init__(self, policy, dry_run=False):
        self.policy = policy
        self.dry_run = dry_run
        self.report = Report(dry_run=dry_run)
        self._sessions = {}
        self._unreachable = {}
        self._plans = {}

    def plan(self, entry):
        """The checks for an instrument, and its coverage, without connecting to it."""
        if entry.name not in self._plans:
            spec = load_spec(entry.cls)
            checks = plan(entry.cls, spec)
            self._plans[entry.name] = checks
            self.report.instruments.setdefault(entry.name, {}).update(
                {"class": entry.cls.__name__, **coverage(entry.cls, checks)}
            )
        return self._plans[entry.name]

    def run(self, entry, check):
        """Runs one check on an instrument, connecting to it first if need be.

        Returns:
            Result: What happened. An instrument that cannot be reached skips.
        """
        session = self._session(entry)
        if session is None:
            result = Result(
                instrument=entry.name,
                check=check.id,
                level=check.level,
                hazard=check.hazard,
                status=Status.SKIPPED,
                detail=f"not reachable: {self._unreachable[entry.name]}",
            )
        else:
            result = session.run(check)
            if session.identity:
                self.report.instruments[entry.name]["identity"] = session.identity
        self.report.add(result)
        return result

    def run_entry(self, entry):
        """Runs every check in an instrument's plan."""
        for check in self.plan(entry):
            self.run(entry, check)

    def _session(self, entry):
        if entry.name in self._unreachable:
            return None
        if entry.name not in self._sessions:
            self.plan(entry)
            try:
                self._sessions[entry.name] = open_session(
                    entry, self.policy, dry_run=self.dry_run
                )
            except Unreachable as reason:
                self._unreachable[entry.name] = str(reason)
                return None
        return self._sessions[entry.name]

    def close(self):
        """Puts every instrument in its safe state and closes it."""
        for name, session in self._sessions.items():
            problems = session.close()
            if problems:
                self.report.instruments[name]["close_problems"] = problems
        self._sessions.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


def verify(entries, policy, *, dry_run=False):
    """Plans and runs every check for every instrument, and reports.

    Returns:
        Report: The results, one per check.
    """
    with Bench(policy, dry_run) as bench:
        for entry in entries:
            bench.run_entry(entry)
    return bench.report
