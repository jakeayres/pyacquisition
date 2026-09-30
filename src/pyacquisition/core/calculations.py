from .broadcaster import Broadcaster
from .consumer import Consumer
from .logging import logger
from .measurement import check_unit
from collections import deque
import asyncio


NAN = float("nan")


def _units(units: dict) -> dict:
    """The units that are given, checked, leaving out the columns without one."""
    checked = {
        column: check_unit(unit, f"the unit of column '{column}'")
        for column, unit in units.items()
    }
    return {column: unit for column, unit in checked.items() if unit}


def _number(value):
    """
    Returns the value as it is, or NaN if it is missing.

    A measurement that fails before it has ever produced a value is `None`.
    """
    return NAN if value is None else value


class Calculation:
    """
    Base class for calculations that need a name, or that keep state between rows.

    A calculation is anything that can be called with a row of data (a dict of
    column name to value) and returns a dict of new columns to add to it. A plain
    function or lambda does this too and needs no base class. Subclass this to
    keep state between rows, such as a rolling window, and set `columns` to the
    names of the columns the calculation produces. That lets `NaN` be recorded in
    those columns if the calculation fails.

    Attributes:
        columns (tuple[str, ...]): The names of the columns this calculation adds.
        units (dict[str, str]): The unit of each column that has one, for display.
    """

    columns: tuple = ()
    units: dict = {}  # replaced, never changed, by the subclasses that set units

    def __call__(self, row: dict) -> dict:
        """
        Calculates new columns from a row of data.

        Args:
            row (dict): The row so far, including the columns added by any
                calculations before this one.

        Returns:
            dict: The new columns and their values.
        """
        raise NotImplementedError("Subclasses must implement __call__().")


class Sum(Calculation):
    """
    The sum of two or more columns.

    Example:
        ```python
        experiment.add_calculation(Sum("a", "b", name="total"))
        ```

    In a TOML config:

        [calculations.total]
        calculation = "Sum"
        inputs = ["a", "b"]
    """

    # Its keys in a config's [calculations] section, besides `calculation` and
    # `unit`, and the kind of value each takes (see `check_config`).
    config_keys = {"inputs": "columns"}

    @classmethod
    def from_config(cls, name: str, inputs: list, unit: str | None = None) -> "Sum":
        return cls(*inputs, name=name, unit=unit)

    def __init__(
        self, *inputs: str, name: str | None = None, unit: str | None = None
    ) -> None:
        """
        Args:
            *inputs (str): The columns to add together.
            name (str | None): The name of the new column. Defaults to the input
                names joined with `+`.
            unit (str | None): The unit of the new column, for display.
        """
        if not inputs:
            raise ValueError("Sum needs at least one column.")
        self.inputs = inputs
        self.name = name or "+".join(inputs)
        self.columns = (self.name,)
        self.units = _units({self.name: unit})

    def __call__(self, row: dict) -> dict:
        return {self.name: sum(_number(row[column]) for column in self.inputs)}


class RollingMean(Calculation):
    """
    The mean of the last `window` values of a column.

    The new column is `NaN` until `window` values have been seen. A `NaN` in the
    input stays in the average until it has left the window.

    Example:
        ```python
        experiment.add_calculation(RollingMean("voltage", window=10))
        ```

    In a TOML config:

        [calculations.voltage_smooth]
        calculation = "RollingMean"
        column = "voltage"
        window = 10
    """

    # Its keys in a config's [calculations] section (see Sum.config_keys).
    config_keys = {"column": "column", "window": "count"}

    @classmethod
    def from_config(
        cls, name: str, column: str, window: int, unit: str | None = None
    ) -> "RollingMean":
        return cls(column, window, name=name, unit=unit)

    def __init__(
        self,
        column: str,
        window: int,
        name: str | None = None,
        unit: str | None = None,
    ) -> None:
        """
        Args:
            column (str): The column to average.
            window (int): The number of values to average over.
            name (str | None): The name of the new column. Defaults to
                `<column>_mean<window>`.
            unit (str | None): The unit of the new column, for display.
        """
        if not isinstance(window, int) or window < 1:
            raise ValueError("window must be a whole number of at least 1.")
        self.column = column
        self.window = window
        self.name = name or f"{column}_mean{window}"
        self.columns = (self.name,)
        self.units = _units({self.name: unit})
        self._values = deque(maxlen=window)

    def __call__(self, row: dict) -> dict:
        self._values.append(_number(row[self.column]))
        if len(self._values) < self.window:
            return {self.name: NAN}
        return {self.name: sum(self._values) / self.window}


# The calculations a TOML config can name in its [calculations] section, by the
# name it uses in `calculation = "..."`, as `instrument_map` does for instruments.
# Each has `config_keys` and `from_config`.
calculation_map = {"Sum": Sum, "RollingMean": RollingMean}


def config_problems(calculations, measured):
    """Every problem with a config's [calculations] section, in file order.

    Args:
        calculations: The section, as `tomllib` reads it.
        measured: The names of the measurements' columns, which come first.

    Yields:
        tuple[tuple, str]: Where each problem is, as keys from inside the
            section (such as `("x_smooth", "window")`), and what it is.
    """
    if not isinstance(calculations, dict):
        yield (), "[calculations] must be a table of calculations"
        return
    columns = list(measured)
    for name, options in calculations.items():
        if not isinstance(options, dict):
            yield (name,), (
                f"Calculation '{name}' must be a table, with `calculation` naming "
                f"one of {', '.join(calculation_map)}"
            )
            continue
        kind = options.get("calculation")
        if kind is None:
            yield (name,), (
                f"Calculation '{name}' needs `calculation`, naming one of "
                f"{', '.join(calculation_map)}"
            )
            continue
        if not isinstance(kind, str) or kind not in calculation_map:
            yield (name, "calculation"), (
                f"Calculation '{name}': there is no calculation called {kind!r}. "
                f"The calculations are {', '.join(calculation_map)}"
            )
            continue
        keys = calculation_map[kind].config_keys
        for key in options:
            if key not in ("calculation", "unit", *keys):
                yield (name, key), (
                    f"Calculation '{name}': unknown key '{key}'. A {kind} takes "
                    f"{', '.join(f'`{k}`' for k in keys)}, and `unit`"
                )
        for key, value_kind in keys.items():
            if key not in options:
                yield (name, key), f"Calculation '{name}': a {kind} needs `{key}`"
            else:
                problem = _value_problem(value_kind, options[key], columns)
                if problem:
                    yield (name, key), f"Calculation '{name}': `{key}` {problem}"
        if "unit" in options and not isinstance(options["unit"], str):
            yield (name, "unit"), (
                f"Calculation '{name}': `unit` must be text, such as \"V\", "
                f"got {options['unit']!r}"
            )
        if name in columns:
            yield (name,), (
                f"Calculation '{name}' has the same name as a column before it"
            )
        columns.append(name)


def _value_problem(kind: str, value, columns: list) -> str | None:
    """What is wrong with a key's value, given the kind it takes, or None."""

    def unknown(column):
        if column in columns:
            return None
        return (
            f"names '{column}', which is not a measurement or a calculation above "
            "this one"
        )

    if kind == "column":
        if not isinstance(value, str):
            return f"must be the name of a column, got {value!r}"
        return unknown(value)
    if kind == "columns":
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(column, str) for column in value)
        ):
            return f'must be a list of one or more columns, such as ["a", "b"], got {value!r}'
        return next(filter(None, map(unknown, value)), None)
    if kind == "count":
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            return f"must be a whole number of at least 1, got {value!r}"
        return None
    raise ValueError(f"unknown kind of value {kind!r}")


def from_config(calculations, measured) -> list[Calculation]:
    """The calculations a config's [calculations] section describes, in order.

    Args:
        calculations: The section, as `tomllib` reads it.
        measured: The names of the measurements' columns.

    Raises:
        ValueError: If the section has a problem (the first, of
            `config_problems`).
    """
    for _, problem in config_problems(calculations, measured):
        raise ValueError(problem)
    return [
        calculation_map[options["calculation"]].from_config(
            name, **{key: value for key, value in options.items() if key != "calculation"}
        )
        for name, options in calculations.items()
    ]


def config_inputs(options: dict) -> list[str]:
    """The columns that a calculation in a config's [calculations] section uses."""
    keys = calculation_map[options["calculation"]].config_keys
    inputs = []
    for key, kind in keys.items():
        if kind == "column":
            inputs.append(options[key])
        elif kind == "columns":
            inputs.extend(options[key])
    return inputs


class Calculations(Broadcaster, Consumer):
    """
    A class to perform calculations on the live data.

    Rows from the rack are passed through each calculation in turn, and the
    result is broadcast to the scribe. Every calculation sees the columns added
    by the ones before it.

    The columns of the first row define the columns of every row after it, so
    that the data file always has the same columns. A calculation that fails
    leaves `NaN` in its columns, and a column that first appears after the first
    row is left out.
    """

    def __init__(self, callbacks=[], async_callbacks=[]):
        """
        Initialize the Calculations.
        """
        self.queue = asyncio.Queue()
        self._subscribers = []
        self._callbacks = []
        self._async_callbacks = []
        self._shutdown_event = asyncio.Event()
        self._calculations = []
        self._columns = None
        self._dropped = set()
        # The columns the calculations are known to add, in order, with the unit
        # of each that has one. A plain function's columns are only known once it
        # has run, unless it is given units.
        self.known_columns = []
        self.units = {}

    def add_calculation(self, calculation, units: dict | None = None) -> None:
        """
        Adds a calculation.

        Calculations run in the order they are added.

        Args:
            calculation (callable): Called with a row (a dict of column name to
                value). Returns a dict of new columns.
            units (dict | None): The unit of each new column that has one, for
                display, such as `{"power": "W"}`. They add to the `units` of a
                `Calculation`.

        Raises:
            TypeError: If the calculation is not callable, or a unit is not text.
        """
        if not callable(calculation):
            raise TypeError(
                "A calculation must be callable, taking a row (a dict) and "
                f"returning a dict of new columns, not {type(calculation).__name__}."
            )
        if units is not None and not isinstance(units, dict):
            raise TypeError(
                'units must be a dict of column name to unit, such as {"power": "W"}'
            )
        added = {**getattr(calculation, "units", {}), **_units(units or {})}
        for column in [*getattr(calculation, "columns", ()), *added]:
            if column not in self.known_columns:
                self.known_columns.append(column)
        self.units.update(added)
        self._calculations.append(calculation)

    def _calculate(self, calculation, row: dict) -> dict:
        """
        Runs one calculation, logging the error and returning `NaN` for its
        columns if it fails.
        """
        try:
            return dict(calculation(row))
        except Exception as e:
            name = getattr(calculation, "__name__", type(calculation).__name__)
            logger.error(f"[Calculations] Error in calculation {name}: {e}")
            return {column: NAN for column in getattr(calculation, "columns", ())}

    def _apply(self, message: dict) -> dict:
        """
        Applies every calculation to a row of data.

        Returns:
            dict: A new row. The message is not changed, because the rack sends
                the same dict to every subscriber.
        """
        if not self._calculations:
            return message

        row = dict(message)
        for calculation in self._calculations:
            row.update(self._calculate(calculation, row))

        if self._columns is None:
            self._columns = list(row)
            return row

        for column in row.keys() - set(self._columns) - self._dropped:
            self._dropped.add(column)
            logger.warning(
                f"[Calculations] Column '{column}' was not in the first row, so it "
                "is left out of the data."
            )
        return {column: row.get(column, NAN) for column in self._columns}

    async def setup(self):
        """
        Setup the calculations.
        """
        logger.debug("[Calculations] Setup started")
        logger.debug("[Calculations] Setup completed")

    async def run(self, experiment) -> None:
        while True:
            try:
                message = await self.consume(timeout=0.1)
                if message is not None:
                    await self.broadcast(self._apply(message))
                if self._shutdown_event.is_set():
                    break
            except Exception as e:
                logger.error(f"Error in calculator run loop: {e}")

    async def teardown(self):
        """
        Teardown the calculations.
        """
        logger.debug("[Calculations] Teardown started")
        logger.debug("[Calculations] Teardown completed")

    async def shutdown(self):
        """
        Shutdown the calculations.
        """
        logger.debug("[Calculations] Shutdown started")
        self._shutdown_event.set()

    def _register_endpoints(self, api_server):
        """
        Register the endpoints for the calculations.
        """
        pass
