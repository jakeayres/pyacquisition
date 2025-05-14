import time
import asyncio
from .logging import logger
from .measurement import Measurement
from .broadcaster import Broadcaster
from .instrument import Instrument


class Rack(Broadcaster):
    """
    A class that represents a rack of instruments.
    """

    def __init__(self, period: float = 0.25) -> None:
        super().__init__()

        self._period = period
        self.instruments = {}
        self.measurements = {}
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._shutdown_event = asyncio.Event()

    async def measure(self) -> dict:
        """
        Executes all measurements in the rack and broadcasts the results.

        Returns:
            dict: A dictionary of results from the measurements.
        """
        result = {k: v.run() for k, v in self.measurements.items()}
        await self.broadcast(result)

    async def setup(self):
        """
        Sets up the rack by initializing the instruments and measurements.
        """
        logger.debug("[Rack] setup started")
        logger.debug("[Rack] setup completed")

    async def run(self, experiment=None) -> None:
        """
        Asynchronously runs the measurements at the specified period.
        """

        while True:
            try:
                await self._pause_event.wait()

                if self._shutdown_event.is_set():
                    break

                t0 = time.time()
                await self.measure()
                t1 = time.time()
                await asyncio.sleep(max(0, self.period - (t1 - t0)))
            except Exception as e:
                logger.error(f"Error in rack run loop: {e}")
                await asyncio.sleep(self.period)

    async def teardown(self):
        """
        Cleans up the rack by stopping all measurements and instruments.
        """
        logger.debug("[Rack] teardown started")
        logger.debug("[Rack] teardown completed")

    async def shutdown(self):
        """
        Shuts down the rack and all its instruments.
        """
        self._shutdown_event.set()

    def pause(self):
        """
        Pauses the measurements.
        """
        self._pause_event.clear()
        logger.info("Measurements paused.")

    def resume(self):
        """
        Resumes the measurements.
        """
        self._pause_event.set()
        logger.info("Measurements resumed.")

    @property
    def period(self) -> float:
        """
        Returns the period for the measurements.

        Returns:
            float: The period for the measurements.

        Examples:
            >>> rack = Rack()
            >>> print(rack.period)  # Access the period property
            >>> rack.period = 0.5  # Set a new period
        """
        return self._period

    @period.setter
    def period(self, value: float) -> None:
        """
        Sets the period for the measurements.

        Args:
            value (float): The new period for the measurements.
        """
        if value <= 0:
            raise ValueError("Period must be a positive number.")
        self._period = value
        logger.info(f"Measurement period set to {self._period} seconds.")

    def add_instrument(self, instrument: Instrument) -> None:
        """
        Adds an instrument to the rack.

        Args:
            instrument (Instrument): The instrument to be added.
        """
        self.instruments[instrument._uid] = instrument
        logger.debug(f"Instrument {instrument._uid} added to the rack.")

    def remove_instrument(self, name: str) -> None:
        """
        Removes an instrument from the rack.

        Args:
            name (str): The name of the instrument to be removed.
        """
        if name in self.instruments:
            del self.instruments[name]
            logger.debug(f"Instrument {name} removed from the rack.")
        else:
            logger.warning(f"Instrument {name} not found in the rack.")

    def add_measurement(self, measurement: Measurement) -> None:
        """
        Adds a measurement to the rack.

        Args:
            measurement (Measurement): The measurement to be added.
        """
        if not isinstance(measurement, Measurement):
            raise TypeError("Expected an instance of Measurement.")
        self.measurements[measurement._name] = measurement
        logger.debug(f"Measurement {measurement._name} added to the rack.")

    def remove_measurement(self, name: str) -> None:
        """
        Removes a measurement from the rack.

        Args:
            name (str): The name of the measurement to be removed.
        """
        if name in self.measurements:
            del self.measurements[name]
            logger.debug(f"Measurement {name} removed from the rack.")
        else:
            logger.warning(f"Measurement {name} not found in the rack.")

    def _register_endpoints(self, api_server):
        """
        Registers endpoints to the FastAPI app.
        """

        for instrument in self.instruments.values():
            instrument.register_endpoints(api_server)

        @api_server.app.get("/rack/list_instruments", tags=["rack"])
        async def list_instruments():
            return {
                "status": "success",
                "instruments": {
                    name: instrument.name
                    for name, instrument in self.instruments.items()
                },
            }

        @api_server.app.get("/rack/list_measurements", tags=["rack"])
        async def list_measurements():
            return {
                "status": "success",
                "measurements": {
                    name: measurement._name
                    for name, measurement in self.measurements.items()
                },
            }

        @api_server.app.get("/rack/pause/", tags=["rack"])
        async def pause():
            """
            Pauses the measurements.
            """
            if not self._pause_event.is_set():
                return {
                    "status": "success",
                    "message": "Measurements are already paused.",
                }
            self.pause()
            return {"status": "success", "message": "Measurements paused."}

        @api_server.app.get("/rack/resume/", tags=["rack"])
        async def resume():
            """
            Resumes the measurements.
            """
            if self._pause_event.is_set():
                return {
                    "status": "success",
                    "message": "Measurements are already running.",
                }
            self.resume()
            return {"status": "success", "message": "Measurements resumed."}

        @api_server.app.get("/rack/period/set/", tags=["rack"])
        async def set_period(period: float):
            """
            Sets the period for the measurements.
            """
            self.period = period
            return {"status": "success", "period": self.period}

        @api_server.app.get("/rack/period/get/", tags=["rack"])
        async def get_period():
            """
            Gets the period for the measurements.
            """
            return {"status": "success", "period": self.period}
