import asyncio
from ..core.relay import Relay
from ..core.logging import logger


class DataFrame(Relay):
    """
    A class that connects to the live stream of data
    and holds a dataframe that other components can access.
    """

    def __init__(self):
        super().__init__()
        self.data = {}
        self.length = 0

        self._maximum_points = 10000
        self._crop_length = 1000

    def clear(self):
        """
        Clear the DataFrame.
        """
        self.data = {}
        self.length = 0

    def crop(self, start: int = None, end: int = None):
        """
        Crop the DataFrame to a specific range.
        """
        if start is None:
            start = 0
        if end is None:
            end = self.length
        cropped_data = {key: value[start:end] for key, value in self.data.items()}
        self.data = cropped_data
        logger.debug(f"DataFrame cropped from {start} to {end}")

    async def run(self, timeout=None):
        """
        Run the DataFrame GUI.
        """
        # Initialize the DataFrame GUI here

        while True:
            try:
                data = await self.relay(timeout=timeout)
                if data is not None:
                    for key, value in data.items():
                        if key not in self.data:
                            self.data[key] = [0] * self.length
                        self.data[key].append(value)
                    self.length += 1

                if self.length > self._maximum_points:
                    self.crop(start=self._crop_length)
                    self.length -= self._crop_length

            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.error(f"Error running DataFrame: {e}")
