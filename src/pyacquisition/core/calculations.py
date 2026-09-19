from .broadcaster import Broadcaster
from .consumer import Consumer
from .logging import logger
from collections import deque
import asyncio


NAN = float("nan")


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
    """

    columns: tuple = ()

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
        experiment.add_calculation(Sum("a", "b", name="total"))
    """

    def __init__(self, *inputs: str, name: str | None = None) -> None:
        """
        Args:
            *inputs (str): The columns to add together.
            name (str | None): The name of the new column. Defaults to the input
                names joined with `+`.
        """
        if not inputs:
            raise ValueError("Sum needs at least one column.")
        self.inputs = inputs
        self.name = name or "+".join(inputs)
        self.columns = (self.name,)

    def __call__(self, row: dict) -> dict:
        return {self.name: sum(_number(row[column]) for column in self.inputs)}


class RollingMean(Calculation):
    """
    The mean of the last `window` values of a column.

    The new column is `NaN` until `window` values have been seen. A `NaN` in the
    input stays in the average until it has left the window.

    Example:
        experiment.add_calculation(RollingMean("voltage", window=10))
    """

    def __init__(self, column: str, window: int, name: str | None = None) -> None:
        """
        Args:
            column (str): The column to average.
            window (int): The number of values to average over.
            name (str | None): The name of the new column. Defaults to
                `<column>_mean<window>`.
        """
        if not isinstance(window, int) or window < 1:
            raise ValueError("window must be a whole number of at least 1.")
        self.column = column
        self.window = window
        self.name = name or f"{column}_mean{window}"
        self.columns = (self.name,)
        self._values = deque(maxlen=window)

    def __call__(self, row: dict) -> dict:
        self._values.append(_number(row[self.column]))
        if len(self._values) < self.window:
            return {self.name: NAN}
        return {self.name: sum(self._values) / self.window}


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

    def add_calculation(self, calculation) -> None:
        """
        Adds a calculation.

        Calculations run in the order they are added.

        Args:
            calculation (callable): Called with a row (a dict of column name to
                value). Returns a dict of new columns.

        Raises:
            TypeError: If the calculation is not callable.
        """
        if not callable(calculation):
            raise TypeError(
                "A calculation must be callable, taking a row (a dict) and "
                f"returning a dict of new columns, not {type(calculation).__name__}."
            )
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
