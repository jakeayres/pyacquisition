from ..core import Task
from dataclasses import dataclass


@dataclass
class PauseMeasurements(Task):
    """Pause the measurements

    No rows are measured or written until they are resumed, by
    `ResumeMeasurements` or the top bar's button. The queue carries on. If they
    are already paused, it does nothing.
    """

    @property
    def description(self) -> str:
        return "Pausing the measurements"

    async def run(self, experiment):
        if experiment._rack.paused:
            self.log("The measurements are already paused.")
        else:
            experiment._rack.pause()


@dataclass
class ResumeMeasurements(Task):
    """Resume the measurements

    Measuring and writing rows starts again. If the measurements are already
    running, it does nothing.
    """

    @property
    def description(self) -> str:
        return "Resuming the measurements"

    async def run(self, experiment):
        if experiment._rack.paused:
            experiment._rack.resume()
        else:
            self.log("The measurements are already running.")


@dataclass
class SetMeasurementPeriod(Task):
    """Set the time between measurements

    The measurements are taken every `period` seconds from then on, or as often
    as measuring allows, if it takes longer.

    Attributes:
        period (float): The time between measurements, in seconds (above zero).
    """

    period: float

    def __post_init__(self):
        super().__post_init__()
        if not self.period > 0:
            raise ValueError(f"The period must be above zero, not {self.period}.")

    @property
    def description(self) -> str:
        return f"Measuring every {self.period} s"

    async def run(self, experiment):
        experiment._rack.period = self.period
        self.log(f"Measuring every {self.period} s.")
