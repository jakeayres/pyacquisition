from ..instruments import SR_830
from ..scribe import Scribe


import asyncio
from dataclasses import dataclass






@dataclass
class LockinFrequencySweep:

    scribe: Scribe
    lockin: SR_830
    min_value: float
    max_value: float
    pause: float = 1


    def string(self):
        f'Lockin Frequency Sweep from {self.min_value} to {self.max_value}'


    async def run(self):
        await asyncio.sleep(self.pause)

        frequency = self.min_value
        self.lockin.set_frequency(frequency)

        self.scribe.next_file('Sweep up', new_chapter=True)
        await asyncio.sleep(self.pause)
        while frequency < self.max_value:
            await asyncio.sleep(self.pause)
            frequency += 1
            self.lockin.set_frequency(frequency)
            yield ''

        self.scribe.next_file('Ended', new_chapter=False)

