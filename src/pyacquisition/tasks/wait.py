from ..core import Task
import datetime
from dataclasses import dataclass

# How often the time left is reported, in seconds.
REPORT_EVERY = 300


@dataclass
class WaitFor(Task):
    """A task that waits for a specified amount of time.

    The time does not pass while the task is paused, so it is the time that the
    task spends running.

    Attributes:
        hours (int): The number of hours to wait. Defult is 0.
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
        remaining = self.hours * 3600 + self.minutes * 60 + self.seconds
        self.log(f"Waiting for {remaining} seconds")

        while remaining > 0:
            # wait until the next multiple of five minutes is left, and report it
            step = min(remaining, remaining % REPORT_EVERY or REPORT_EVERY)
            await self.sleep(step)
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

        while True:
            remaining = (target_time - datetime.datetime.now()).total_seconds()
            if remaining <= 0:
                break
            await self.sleep(min(remaining, REPORT_EVERY))
            remaining = (target_time - datetime.datetime.now()).total_seconds()
            if remaining > 0:
                self.log(f"{datetime.timedelta(seconds=int(remaining))} remaining")
