"""A session runs checks against one instrument, under the safety rules.

Before a check that writes is allowed to run, every one of these has to hold:

1. its hazard is enabled by the run (`--reversible`, `--hazardous`) and by the
   instrument's own limit in the inventory,
2. the spec declares a `[safe_state]`,
3. the instrument has passed its identity check, so nothing is written to a
   device that has not shown what it is,
4. the safe state has been reached and, where the spec says how, verified.

The safe state is entered again after every check that writes, whatever
happened in it, and once more when the session closes. A failure to reach it
stops every later check that writes.
"""

from .guard import SafetyViolation
from .model import CheckFailed, Hazard, Result, Skip, Status
from .spec import bind, canned, coerce, hints_of, same


class SafeStateError(RuntimeError):
    """The instrument could not be put in, or confirmed to be in, its safe state."""


class Policy:
    """How much a run is allowed to do.

    Args:
        max_hazard (Hazard): The most hazardous checks that may run. Read-only
            unless a run asks for more.
    """

    def __init__(self, max_hazard=Hazard.READ_ONLY):
        self.max_hazard = max_hazard

    def allows(self, hazard, instrument_limit=None):
        limit = self.max_hazard.rank
        if instrument_limit is not None:
            limit = min(limit, instrument_limit.rank)
        return hazard.rank <= limit

    def why_not(self, hazard, instrument_limit=None):
        if instrument_limit is not None and hazard.rank > instrument_limit.rank:
            return f"this instrument is limited to {instrument_limit.value} checks by the inventory"
        flag = "--hazardous" if hazard is Hazard.HAZARDOUS else "--reversible"
        return f"{hazard.value} checks are not enabled: run with {flag}"


class _DryRun:
    """Stands in for an instrument on a dry run, whose replies mean nothing.

    Every method still runs, so the commands it would send are recorded, but a
    reply that cannot be parsed is replaced by a stand-in value.
    """

    def __init__(self, instrument):
        self._instrument = instrument

    def __getattr__(self, name):
        attribute = getattr(self._instrument, name)
        if not callable(attribute):
            return attribute
        returns = hints_of(attribute).get("return")

        def call(*args, **kwargs):
            try:
                return attribute(*args, **kwargs)
            except SafetyViolation:
                raise
            except Exception:  # noqa: BLE001 - a stand-in reply may not parse
                return canned(returns)

        return call


class Session:
    """Runs checks against one connected instrument.

    Args:
        name (str): What the instrument is called in reports.
        instrument: The instrument, built over `guard`.
        guard (GuardedResource): The guard between the instrument and the device.
        spec (Spec): Its spec, or None.
        policy (Policy): What the run allows.
        max_hazard (Hazard): This instrument's own limit, or None for the run's.
        capabilities: What is attached, for checks that `require` something.
        skip: Methods to leave alone on this instrument.
        dry_run (bool): Whether the device is a stand-in.
    """

    def __init__(
        self,
        name,
        instrument,
        guard,
        spec,
        policy,
        *,
        max_hazard=None,
        capabilities=(),
        skip=(),
        dry_run=False,
    ):
        self.name = name
        self.guard = guard
        self.spec = spec
        self.policy = policy
        self.max_hazard = max_hazard
        self.capabilities = frozenset(capabilities)
        self.skip = frozenset(skip)
        self.dry_run = dry_run
        self.identity = None
        self.instrument = instrument
        self.inst = _DryRun(instrument) if dry_run else instrument
        self.identity_verified = dry_run  # a stand-in has nothing to prove
        self.blocked = None  # why every later check is refused
        self.unsafe = None  # why every later check that writes is refused
        self._touched = False

    # ------------------------------------------------------------ calls
    def read(self, method, **kwargs):
        """Calls a method that only asks questions. The guard refuses anything else."""
        return getattr(self.inst, method)(**kwargs)

    def write(self, method, **kwargs):
        """Calls a method that changes something, with the guard's write window open."""
        with self.guard.writes_allowed():
            return getattr(self.inst, method)(**kwargs)

    def holds(self, condition):
        """Whether a spec condition is true of the instrument, and what it read."""
        func = getattr(type(self.instrument), condition.call)
        kwargs = bind(func, condition.args, condition.call)
        expected = coerce(
            condition.equals, hints_of(func).get("return"), condition.call
        )
        got = self.read(condition.call, **kwargs)
        return same(got, expected, 1e-9), got

    # ------------------------------------------------------------ safe state
    def reach_safe_state(self):
        """Runs the spec's safe-state steps and confirms the instrument is there.

        Raises:
            SafeStateError: If a step fails or a verification does not hold.
        """
        self._touched = True
        try:
            for step in self.spec.steps:
                func = getattr(type(self.instrument), step.call)
                self.write(step.call, **bind(func, step.args, step.call))
            for condition in self.spec.verify:
                holds, got = self.holds(condition)
                if not holds and not self.dry_run:
                    raise SafeStateError(
                        f"{condition.call} returned {got!r}, expected {condition.equals!r}"
                    )
        except SafeStateError:
            raise
        except Exception as error:
            raise SafeStateError(f"{type(error).__name__}: {error}") from error

    # ------------------------------------------------------------ running
    def run(self, check):
        """Runs a check, or says why it was not run.

        Returns:
            Result: What happened, with the commands that were sent.
        """
        mark = self.guard.mark()
        status, detail = self._run(check)
        return Result(
            instrument=self.name,
            check=check.id,
            level=check.level,
            hazard=check.hazard,
            status=status,
            detail=detail,
            sent=self.guard.since(mark),
        )

    def _refusal(self, check):
        """Why a check may not run, or None if it may."""
        if self.blocked:
            return self.blocked
        if not self.policy.allows(check.hazard, self.max_hazard):
            return self.policy.why_not(check.hazard, self.max_hazard)
        if check.writes:
            if self.spec is None or self.spec.steps is None:
                return "the spec has no [safe_state], so nothing may be written"
            if not self.identity_verified:
                return (
                    "the identity was not verified: nothing is written to a device "
                    "that has not shown what it is"
                )
            if self.unsafe:
                return f"disabled after: {self.unsafe}"
        return None

    def _run(self, check):
        reason = self._refusal(check)
        if reason:
            return Status.SKIPPED, reason

        if check.writes:
            try:
                self.reach_safe_state()
            except SafeStateError as error:
                self.unsafe = f"the safe state could not be reached ({error})"
                return Status.FAILED, f"SAFE STATE NOT REACHED: {error}"

        violated = False
        try:
            detail = check.execute(self)
            status = Status.PASSED
        except Skip as skip:
            status, detail = Status.SKIPPED, str(skip)
        except CheckFailed as failure:
            status, detail = Status.FAILED, str(failure)
        except SafetyViolation as violation:
            violated = True
            status, detail = Status.FAILED, f"BLOCKED BY THE GUARD: {violation}"
        except Exception as error:  # noqa: BLE001 - whatever a driver does is a result
            status, detail = Status.FAILED, f"{type(error).__name__}: {error}"

        if check.writes:
            try:
                self.reach_safe_state()
            except SafeStateError as error:
                self.unsafe = (
                    f"the safe state could not be reached after {check.id} ({error})"
                )
                status = Status.FAILED
                detail += f" | SAFE STATE NOT REACHED AFTER THE CHECK: {error}"

        if check.is_identity:
            if status is Status.PASSED:
                self.identity_verified = True
            elif status is Status.FAILED:
                self.blocked = "the identity check failed: this device is not talked to"

        if self.dry_run and not violated and status in (Status.PASSED, Status.FAILED):
            status, detail = Status.DRY_RUN, ""
        return status, detail

    def close(self):
        """Puts the instrument in its safe state if a check touched it, and closes it.

        Returns:
            list[str]: Anything that went wrong doing so.
        """
        problems = []
        if self._touched and not self.dry_run:
            try:
                self.reach_safe_state()
            except SafeStateError as error:
                problems.append(
                    f"{self.name}: SAFE STATE NOT REACHED AT THE END: {error}"
                )
        try:
            self.guard.close()
        except Exception as error:  # noqa: BLE001 - report it, do not raise from cleanup
            problems.append(f"{self.name}: could not close: {error}")
        return problems
