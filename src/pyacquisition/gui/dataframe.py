from ..core.logging import logger


class DataFrame:
    """
    A class that holds the live stream of data as a dataframe
    that other components can access.
    """

    def __init__(self):
        self.data = {}
        self.length = 0

        self._callbacks = []
        self._maximum_points = 10000
        self._crop_length = 1000

    def add_callback(self, callback: callable):
        """
        Add a callback to be called with each new row of data.
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: callable):
        """
        Remove a callback from the list of callbacks.
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

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

    def update(self, message: dict):
        """
        Append a new row of data and notify the callbacks.
        """
        for key, value in message.items():
            if key not in self.data:
                self.data[key] = [0] * self.length
            self.data[key].append(value)
        self.length += 1

        if self.length > self._maximum_points:
            self.crop(start=self._crop_length)
            self.length -= self._crop_length

        for callback in self._callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Error in DataFrame callback: {e}")
