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
            if int(remaining_time) % 60 == 0:
                yield f"{datetime.timedelta(seconds=remaining_time)} remaining"
            else:
                yield None
            await asyncio.sleep(1)



@dataclass
class WaitUntil(Task):
    
    
    hour: int
    minute: int
    
    name = "Wait Until"
    
    @property
    def description(self) -> str:
        return f"Wait until {self.hour}:{self.minute}."
    
    
    async def run(self):
        
        now = datetime.datetime.now()
        wait_time = datetime.timedelta(hours=self.hour, minutes=self.minute) - datetime.timedelta(hours=now.hour, minutes=now.minute)
        until = now + wait_time
        
        if wait_time < 0:
            yield "Time already passed"
            return
        
        while datetime.datetime.now() < until:
            remaining_time = (until - datetime.datetime.now()).total_seconds()
            if int(remaining_time) % 60 == 0:
                yield f"{datetime.timedelta(seconds=remaining_time)} remaining"
            else:
                yield None
            await asyncio.sleep(1)