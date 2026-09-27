from ..core import Task
import datetime
from dataclasses import dataclass

# How often the time left is reported, in seconds.
REPORT_EVERY = 300
# How often the progress is updated for the interface, in seconds.
TICK = 1.0


async def _pass(task, seconds, tick):
    """Sleeps for `seconds` of the task's running time, a `TICK` at a time,
    calling `tick(step)` after each one, so the progress can follow."""
    left = seconds
    while left > 0:
        step = min(TICK, left)
        await task.sleep(step)
        left -= step
        tick(step)


@dataclass
class WaitFor(Task):
    """A task that waits for a specified amount of time.

    The time does not pass while the task is paused, so it is the time that the
    task spends running.

    Attributes:
        hours (int): The number of hours to wait. Default is 0.
        minutes (int): The number of minutes to wait. Default is 0.
        seconds (int): The number of seconds to wait. Default is 0.

    Class Attributes:
        name (str): The name of the task.
        help (str): A brief description of the task.
    """

    hours: int = 0
    minutes: int = 0
    seconds: int = 0

    @property
    def description(self) -> str:
        return f"Wait for {self.hours} hours, {self.minutes} minutes, and {self.seconds} seconds."

    async def run(self, experiment):
        total = remaining = self.hours * 3600 + self.minutes * 60 + self.seconds
        self.log(f"Waiting for {remaining} seconds")
        waited = 0.0

        def tick(step):
            nonlocal waited
            waited += step
            self.set_progress(waited / total, remaining=total - waited)

        if total > 0:
            self.set_progress(0, remaining=total)
        while remaining > 0:
            # wait until the next multiple of five minutes is left, and report it
            step = min(remaining, remaining % REPORT_EVERY or REPORT_EVERY)
            await _pass(self, step, tick)
            remaining -= step
            if remaining > 0:
                self.log(f"{datetime.timedelta(seconds=int(remaining))} remaining")


@dataclass
class WaitUntil(Task):
    """Wait until hh:mm (next occurrence)

    The clock keeps running while the task is paused, so it waits until that time
    however long it was paused for.
    """

    hour: int = 0
    minute: int = 0

    @property
    def description(self) -> str:
        return f"Wait until {self.hour}:{self.minute}."

    async def run(self, experiment):
        now = datetime.datetime.now()
        target_time = now.replace(
            hour=self.hour, minute=self.minute, second=0, microsecond=0
        )

        # If the target time is earlier than the current time, move it to the next day
        if target_time <= now:
            target_time += datetime.timedelta(days=1)

        self.log(f"Waiting until {target_time.strftime('%H:%M')}")
        total = (target_time - datetime.datetime.now()).total_seconds()

        def tick(step=0):
            # By the clock, which runs on while the task is paused.
            left = max(0.0, (target_time - datetime.datetime.now()).total_seconds())
            self.set_progress(1 - left / total, remaining=left)

        tick()
        while True:
            remaining = (target_time - datetime.datetime.now()).total_seconds()
            if remaining <= 0:
                break
            await _pass(self, min(remaining, REPORT_EVERY), tick)
            remaining = (target_time - datetime.datetime.now()).total_seconds()
            if remaining > 0:
                self.log(f"{datetime.timedelta(seconds=int(remaining))} remaining")
