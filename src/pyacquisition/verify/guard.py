"""A guard between an instrument and its resource, that only lets reads through.

This is the last line of defence. However a check or an instrument method
misbehaves, nothing that is not a read reaches the device unless the session has
opened a window for writes, which it only does for a check that was allowed.

Whether a message is a read is decided by patterns, because it cannot be told
from the decorators: `Mercury_IPS` sends `A1` (go to setpoint) and `J...` (set
the field) through `query()`. By default a read is a message containing `?`, and
an instrument's spec adds the reads of its own protocol, for example `^R\\d+$`.
"""

import re
from contextlib import contextmanager


class SafetyViolation(RuntimeError):
    """Something tried to send a message that is not a read, outside a write window."""


class GuardedResource:
    """Wraps a resource, and refuses any message that is not a read.

    Args:
        inner: The resource to protect.
        read_patterns: Regular expressions for messages that are reads, besides
            those containing `?`.
    """

    def __init__(self, inner, read_patterns=()):
        self._inner = inner
        self._reads = [re.compile(r"\?")] + [re.compile(p) for p in read_patterns]
        self.allow_writes = False
        self.log = []  # every message that reached the instrument, in order
        self.blocked = []  # every message that was refused

    def is_read(self, message):
        text = str(message).strip()
        return any(pattern.search(text) for pattern in self._reads)

    def _permit(self, message):
        if self.allow_writes or self.is_read(message):
            self.log.append(str(message).strip())
            return
        self.blocked.append(str(message).strip())
        raise SafetyViolation(
            f"blocked {str(message).strip()!r}: it is not a read and writes are not allowed"
        )

    @contextmanager
    def writes_allowed(self):
        """Lets any message through for the duration of the block."""
        previous = self.allow_writes
        self.allow_writes = True
        try:
            yield
        finally:
            self.allow_writes = previous

    def mark(self):
        """A position in the log, to ask later what was sent since."""
        return len(self.log)

    def since(self, mark):
        return list(self.log[mark:])

    def write(self, message, *args, **kwargs):
        self._permit(message)
        return self._inner.write(message, *args, **kwargs)

    def query(self, message, *args, **kwargs):
        self._permit(message)
        return self._inner.query(message, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._inner, name)
