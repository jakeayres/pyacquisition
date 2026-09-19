"""The checks the engine can run, and how they are planned for an instrument class.

A check has a level, a hazard and a `writes` flag. Building the plan needs only
the class and its spec, never the device, so a run can be planned, listed and
collected by pytest before anything is connected.

Levels:
    0  identity    `*IDN?` names the expected model
    1  read smoke  every getter runs and returns what it promises
    2  round trip  a setting is written, read back, and restored
"""

import re
from enum import Enum
from itertools import product

from .model import CheckFailed, Hazard, Skip
from .spec import (
    bind,
    check_type,
    hints_of,
    marked_methods,
    params_of,
    roundtrip_shape,
    same,
)

_MAX_ARGUMENT_SETS = 64


def _label(value):
    return value.name if hasattr(value, "name") else repr(value)


def _describe(kwargs):
    return ", ".join(f"{name}={_label(value)}" for name, value in kwargs.items())


class Check:
    """One thing to verify. `execute` returns a detail, or raises `Skip` or `CheckFailed`."""

    level = 1
    hazard = Hazard.READ_ONLY
    writes = False  # whether it may send anything that is not a read
    is_identity = False

    def __init__(self, id):
        self.id = id
        self.methods = frozenset()

    @property
    def pytest_id(self):
        return re.sub(r"[^\w.\[\]=,-]+", "_", self.id)

    def execute(self, session):
        raise NotImplementedError

    def __repr__(self):
        return f"<{type(self).__name__} {self.id}>"


class IdentityCheck(Check):
    level = 0
    is_identity = True

    def __init__(self, expected):
        super().__init__("identity")
        self.expected = expected
        self.methods = frozenset({"identify"})

    def execute(self, session):
        if not self.expected:
            # nothing to compare with, so there is no need to ask a device that
            # may not even answer *IDN?
            raise Skip("the spec declares no [identity] to compare with")
        reply = str(session.read("identify"))
        session.identity = reply.strip()
        if session.dry_run:
            raise Skip("dry run: the reply is not compared")
        missing = [word for word in self.expected if word.upper() not in reply.upper()]
        if missing:
            raise CheckFailed(
                f"the instrument answered {reply.strip()!r}, which lacks {missing}: "
                "is this the right device?"
            )
        return reply.strip()


class SafeStateCheck(Check):
    """Puts the instrument in its safe state and confirms it got there."""

    level = 2
    hazard = Hazard.REVERSIBLE
    writes = True

    def __init__(self, spec):
        super().__init__("safe_state")
        self.methods = frozenset(c.call for c in (*(spec.steps or ()), *spec.verify))

    def execute(self, session):
        # the session has already reached and verified the safe state to get here
        return "safe state reached" + (" and verified" if session.spec.verify else "")


class ReadCheck(Check):
    """Calls a getter and checks that its reply is what it promises."""

    def __init__(self, method, kwargs, rule, returns, reason=None):
        suffix = f"[{_describe(kwargs)}]" if kwargs else ""
        super().__init__(f"read.{method}{suffix}")
        self.method, self.kwargs, self.rule = method, kwargs or {}, rule
        self.returns, self.reason = returns, reason
        self.hazard = rule.hazard if rule else Hazard.READ_ONLY
        self.methods = frozenset({method})

    def execute(self, session):
        if self.rule and self.rule.skip:
            raise Skip(self.rule.skip)
        if self.reason:
            raise Skip(self.reason)
        if self.method in session.skip:
            raise Skip("skipped for this instrument by the inventory")
        if self.rule:
            missing = set(self.rule.requires) - session.capabilities
            if missing:
                raise Skip(
                    f"needs {sorted(missing)}, which the inventory does not list"
                )

        value = session.read(self.method, **self.kwargs)
        problem = check_type(value, self.returns)
        if problem:
            raise CheckFailed(problem)
        if self.rule and self.rule.range:
            low, high = self.rule.range
            if not low <= value <= high:
                raise CheckFailed(
                    f"{value!r} is outside the expected range {low} to {high}"
                )
        return f"-> {value!r}"[:100]


class RoundTripCheck(Check):
    """Writes each value, reads it back, and restores the original setting."""

    level = 2
    writes = True

    def __init__(self, rt, param, values, selects):
        super().__init__(f"roundtrip.{rt.id}")
        self.rt, self.param, self.values, self.selects = rt, param, values, selects
        self.hazard = rt.hazard
        self.methods = frozenset({rt.setter, rt.getter})

    def execute(self, session):
        rt = self.rt
        skipped = self.methods & session.skip
        if skipped:
            raise Skip(
                f"{sorted(skipped)} skipped for this instrument by the inventory"
            )
        missing = set(rt.requires) - session.capabilities
        if missing:
            raise Skip(f"needs {sorted(missing)}, which the inventory does not list")

        problems, done = [], 0
        for select in self.selects:
            for condition in rt.preconditions:
                holds, got = session.holds(condition)
                if not holds:
                    raise Skip(
                        f"precondition not met: {condition.call} returned {got!r}, "
                        f"expected {condition.equals!r}"
                    )
            original = session.read(rt.getter, **select)
            try:
                for value in self.values:
                    session.write(rt.setter, **select, **{self.param: value})
                    got = session.read(rt.getter, **select)
                    done += 1
                    if not same(got, value, rt.rel, rt.abs):
                        problems.append(
                            f"{_describe(select) + ': ' if select else ''}"
                            f"wrote {_label(value)}, read back {_label(got)}"
                        )
            finally:
                session.write(rt.setter, **select, **{self.param: original})
            restored = session.read(rt.getter, **select)
            if not same(restored, original, rt.rel, rt.abs):
                problems.append(
                    f"{_describe(select) + ': ' if select else ''}"
                    f"RESTORE FAILED: was {_label(original)}, now {_label(restored)}"
                )
        if problems:
            raise CheckFailed("; ".join(problems))
        return f"{done} value(s) written, read back and restored"


# ---------------------------------------------------------------- planning
def _read_cases(cls, name, rule):
    """The argument sets to call a getter with, or the reason it cannot be run."""
    func = getattr(cls, name)
    if rule and rule.args is not None:
        return [bind(func, args, f"[read.{name}]") for args in rule.args], None
    params, hints = params_of(func), hints_of(func)
    if not params:
        return [{}], None

    domains = []
    for param in params:
        annotation = hints.get(param)
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            domains.append(list(annotation))
        elif annotation is bool:
            domains.append([False, True])
        else:
            return None, (
                f"takes {param!r}, which is not an enum: give 'args' in [read.{name}] in the spec"
            )
    cases = [dict(zip(params, combo)) for combo in product(*domains)]
    if len(cases) > _MAX_ARGUMENT_SETS:
        return None, f"{len(cases)} argument combinations: give 'args' in [read.{name}]"
    return cases, None


def plan(cls, spec):
    """Lists the checks for an instrument class, in the order they should run.

    Only methods named `get_...` are read. What a method is registered as says
    nothing about what it does: `Mercury_IPS` registers its setters as queries.
    """
    checks = [IdentityCheck(spec.identity if spec else None)]
    if spec is not None and spec.steps is not None:
        checks.append(SafeStateCheck(spec))

    rules = spec.read if spec else {}
    for name in sorted(marked_methods(cls)):
        if not name.startswith("get_"):
            continue
        rule = rules.get(name)
        returns = hints_of(getattr(cls, name)).get("return")
        cases, reason = _read_cases(cls, name, rule)
        if cases is None:
            checks.append(ReadCheck(name, {}, rule, returns, reason))
        else:
            checks.extend(ReadCheck(name, case, rule, returns) for case in cases)

    if spec is not None:
        for rt in spec.roundtrips.values():
            param, values, selects = roundtrip_shape(rt, cls)
            checks.append(RoundTripCheck(rt, param, values, selects))
    return checks


def coverage(cls, checks):
    """What the plan does not touch.

    Returns:
        dict: `untested`, the registered methods no check calls, and
            `set_registered_as_query`, setters registered as queries.
    """
    marked = marked_methods(cls)
    exercised = set()
    for check in checks:
        exercised |= check.methods
    return {
        "untested": sorted(set(marked) - exercised),
        "set_registered_as_query": sorted(
            name
            for name, func in marked.items()
            if name.startswith("set_") and hasattr(func, "_is_query")
        ),
    }
