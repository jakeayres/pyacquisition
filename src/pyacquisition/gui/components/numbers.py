import math


def is_number(value) -> bool:
    """
    Whether a value can be drawn on a graph: an int or a float. A bool is not,
    because `True` is a state and not a quantity.
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def format_number(value: float, width: int = 12) -> str:
    """
    A number as text in at most `width` characters. It is written with the fewest
    figures that give it back exactly, so `40.0` is `40`, and `1789978454.496` is
    that and not `1789978454.4960001`. If even that is too long, as many figures as
    fit are kept: in 12 characters `0.8405884400988841` is `0.8405884401`, so a
    column of them lines up and shows what is worth reading.

    Args:
        value (float): The number.
        width (int): The most characters to use. Numbers that cannot be shortened to
            fit, such as `1.5e+300` in a very small width, are given three figures.
    """
    if isinstance(value, int):
        text = str(value)
        return text if len(text) <= width else f"{value:.{max(width - 6, 3)}g}"
    if not math.isfinite(value):
        return str(value)

    # `repr` is the shortest text that gives the number back exactly. Any more would
    # only show the noise of a binary fraction: 1790015704.496 is not
    # 1790015704.4960001.
    text = repr(value)
    if text.endswith(".0"):
        text = text[:-2]
    return text if len(text) <= width else _shortened(value, width)


def _shortened(value: float, width: int) -> str:
    """A number that is too long, with as many figures as fit."""
    for figures in range(width, 3, -1):
        text = f"{value:.{figures}g}"
        if len(text) <= width:
            return text
    return f"{value:.3g}"
