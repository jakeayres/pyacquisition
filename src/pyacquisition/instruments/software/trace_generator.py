import time

import numpy as np

from ...core.instrument import SoftwareInstrument, mark_command, mark_query, mark_trace
from ...core.trace import TraceData


class TraceGenerator(SoftwareInstrument):
    """A simulated instrument that gives a spectrum: a Lorentzian peak on a
    little noise, over a frequency axis. Its centre and width can be set, and a
    sweep can be made to take time, as a real instrument's does, to try traces
    without hardware.

    Args:
        uid: The instrument's id.
        centre: Where the peak is, on the axis.
        width: The peak's half width at half maximum.
        points: How many points a spectrum has.
        start, stop: The axis's ends.
        noise: The noise's standard deviation, as a fraction of the peak.
        sweep_time: Seconds a sweep takes, from `start_sweep` until
            `sweep_done`.
    """

    name = "Trace Generator"

    def __init__(self, uid, centre: float = 5.0, width: float = 0.5, points: int = 512,
                 start: float = 0.0, stop: float = 10.0, noise: float = 0.02, sweep_time: float = 0.0):
        super().__init__(uid)
        self._centre = centre
        self._width = width
        self._points = points
        self._start = start
        self._stop = stop
        self._noise = noise
        self._sweep_time = sweep_time
        self._started = None  # when the sweep under way started
        self.sweeps_stopped = 0  # how many sweeps were stopped part way

    @mark_command
    def set_centre(self, centre: float) -> None:
        """Set where the peak is, on the axis."""
        self._centre = centre

    @mark_query
    def get_centre(self) -> float:
        """Read where the peak is."""
        return self._centre

    @mark_command
    def set_width(self, width: float) -> None:
        """Set the peak's half width at half maximum."""
        self._width = width

    @mark_command
    def set_sweep_time(self, seconds: float) -> None:
        """Set how long a sweep takes, in seconds."""
        self._sweep_time = seconds

    def start_sweep(self) -> None:
        """Start a sweep."""
        self._started = time.monotonic()

    def sweep_done(self) -> bool:
        """Whether the sweep under way is done."""
        return self._started is not None and time.monotonic() - self._started >= self._sweep_time

    def stop_sweep(self) -> None:
        """Stop the sweep under way."""
        if self._started is not None:
            self.sweeps_stopped += 1
        self._started = None

    @mark_trace(start="start_sweep", ready="sweep_done", stop="stop_sweep", timeout=60)
    def get_spectrum(self) -> TraceData:
        """The spectrum: the peak, with noise, in dB over the frequency axis."""
        self._started = None
        x = np.linspace(self._start, self._stop, self._points)
        peak = 1.0 / (1.0 + ((x - self._centre) / self._width) ** 2)
        values = peak + np.random.normal(0.0, self._noise, self._points)
        return TraceData(
            {"amplitude": values.astype(np.float32)},
            x=(self._start, self._stop),
            x_name="frequency",
            x_unit="Hz",
            unit="V",
        )
