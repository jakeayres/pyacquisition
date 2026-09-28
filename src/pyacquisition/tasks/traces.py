from dataclasses import dataclass
from typing import ClassVar

from ..core import Task


@dataclass
class AcquireTrace(Task):
    """Take a trace now

    Registered by itself when the experiment has traces. It takes one of the
    named trace, waits for it (a slow sweep's whole time), and fails if it
    can't be taken, which pauses the queue.

    Attributes:
        trace (str): The trace to take, by its name.
    """

    input_choices: ClassVar[dict] = {"trace": lambda experiment: list(experiment.traces)}

    trace: str

    @property
    def description(self) -> str:
        return f"Taking a {self.trace} trace"

    async def run(self, experiment):
        if self.trace not in experiment.traces:
            raise ValueError(
                f"There is no trace called {self.trace!r}: there is "
                f"{', '.join(map(repr, experiment.traces)) or 'none'}."
            )
        record = await experiment.traces[self.trace].acquire()
        if record is None:
            raise RuntimeError(f"The {self.trace} trace couldn't be taken: see the log.")
        self.log(f"Took {self.trace} trace {record.index}.")
