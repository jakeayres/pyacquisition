from ..core.task import Task
import asyncio
import datetime
import time
from dataclasses import dataclass
from ..core.logging import logger


@dataclass
class WaitFor(Task):
    
    hours: int
    minutes: int
    seconds: int
    
    
    name = "Wait For"
    help = "Wait for a specified amount of time."
    
    
    @property
    def description(self) -> str:
        return f"Wait for {self.hours} hours, {self.minutes} minutes, and {self.seconds} seconds."
        
    
    async def run(self):
        
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
    
    
    hour: int
    minute: int
    
    name = "Wait Until"
    help = "Wait until a specified time (24hr)."
    
    @property
    def description(self) -> str:
        return f"Wait until {self.hour}:{self.minute}."
    
    
    async def run(self):
        now = datetime.datetime.now()
        target_time = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)

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