from ..core.task import Task
import asyncio
import datetime
import time
from dataclasses import dataclass
from ..core.logging import logger


@dataclass
class WaitFor(Task):
    """A task that waits for a specified amount of time.

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
        total_seconds = self.hours * 3600 + self.minutes * 60 + self.seconds
        start_time = time.time()
        end_time = start_time + total_seconds
        logger.info(f"[{self.name}] Waiting for {total_seconds} seconds")

        while time.time() < end_time:
            remaining_time = end_time - time.time()
            if int(remaining_time) % 300 == 0:
                yield f"{datetime.timedelta(seconds=remaining_time):i} remaining"
            else:
                yield None
            await asyncio.sleep(1)


@dataclass
class WaitUntil(Task):
    """Wait until hh:mm (next occurrence)"""

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

        logger.info(f"[{self.name}] Waiting until {target_time.strftime('%H:%M')}")

        while datetime.datetime.now() < target_time:
            remaining_time = (target_time - datetime.datetime.now()).total_seconds()
            if int(remaining_time) % 300 == 0:
                yield f"{datetime.timedelta(seconds=remaining_time):i} remaining"
            else:
                yield None
            await asyncio.sleep(1)
