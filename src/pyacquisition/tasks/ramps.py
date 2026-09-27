"""How far along a ramp is, for a task's progress (see `Task.set_progress`)."""


def ramp_progress(start: float, now: float, target: float, per_second: float):
    """How far a ramp from `start` to `target` has got at `now`, from 0 to 1,
    and the seconds left at `per_second` (None if the rate isn't above zero).

    Args:
        start (float): Where the ramp began.
        now (float): Where it is.
        target (float): Where it is going.
        per_second (float): How fast it goes, in units a second.

    Returns:
        tuple: (fraction, remaining seconds or None).
    """
    span = target - start
    fraction = 1.0 if span == 0 else (now - start) / span
    fraction = max(0.0, min(1.0, fraction))
    remaining = abs(target - now) / per_second if per_second > 0 else None
    return fraction, remaining
