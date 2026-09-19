from ...core.instrument import SoftwareInstrument, mark_query, mark_command
import math
import time


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


class SignalGenerator(SoftwareInstrument):
    """
    A software signal generator that computes waveforms from the time.

    Each query gives the value of the waveform now, measured from when the
    generator was created (or last restarted). Read it on every cycle with
    `Measurement("signal", generator.sine, frequency=0.1)` to record the wave.

    Every waveform takes a `frequency` in Hz, an `amplitude`, a `phase` in degrees
    and an `offset`. The waveforms are all at zero phase at the start of a period,
    where they cross `offset` on the way up, except `square`, which goes high there.
    """

    name = "Signal Generator"

    def __init__(self, uid, time_source=time.monotonic):
        """
        Args:
            uid (str): The id of the instrument.
            time_source (callable): Returns the time in seconds. Only changes
                matter, not the zero. Defaults to `time.monotonic`.
        """
        super().__init__(uid)
        self._time_source = time_source
        self._t0 = time_source()

    def _elapsed(self) -> float:
        return self._time_source() - self._t0

    def _cycles(self, frequency: float, phase: float) -> float:
        """The number of periods completed so far."""
        return frequency * self._elapsed() + phase / 360

    @mark_command
    def restart(self) -> int:
        """
        Restarts the waveforms from time zero.

        Returns:
            int: 0.
        """
        self._t0 = self._time_source()
        return 0

    @mark_query
    def elapsed_time(self) -> float:
        """
        Returns the time in seconds since the generator was created or restarted.

        Returns:
            float: The time in seconds.
        """
        return self._elapsed()

    @mark_query
    def sine(
        self,
        frequency: float = 1.0,
        amplitude: float = 1.0,
        phase: float = 0.0,
        offset: float = 0.0,
    ) -> float:
        """
        Sine wave.

        Args:
            frequency (float): The frequency in Hz.
            amplitude (float): The peak amplitude.
            phase (float): The phase in degrees.
            offset (float): The value added to the wave.
        """
        return offset + amplitude * math.sin(
            2 * math.pi * self._cycles(frequency, phase)
        )

    @mark_query
    def cosine(
        self,
        frequency: float = 1.0,
        amplitude: float = 1.0,
        phase: float = 0.0,
        offset: float = 0.0,
    ) -> float:
        """
        Cosine wave.

        Args:
            frequency (float): The frequency in Hz.
            amplitude (float): The peak amplitude.
            phase (float): The phase in degrees.
            offset (float): The value added to the wave.
        """
        return offset + amplitude * math.cos(
            2 * math.pi * self._cycles(frequency, phase)
        )

    @mark_query
    def square(
        self,
        frequency: float = 1.0,
        amplitude: float = 1.0,
        phase: float = 0.0,
        offset: float = 0.0,
        duty: float = 0.5,
    ) -> float:
        """
        Square wave, which is high for the fraction `duty` of each period.

        Args:
            frequency (float): The frequency in Hz.
            amplitude (float): The height above and below the offset.
            phase (float): The phase in degrees.
            offset (float): The value added to the wave.
            duty (float): The fraction of each period spent high, from 0 to 1.
        """
        _require(0 <= duty <= 1, "duty must be between 0 and 1.")
        fraction = self._cycles(frequency, phase) % 1
        return offset + (amplitude if fraction < duty else -amplitude)

    @mark_query
    def triangle(
        self,
        frequency: float = 1.0,
        amplitude: float = 1.0,
        phase: float = 0.0,
        offset: float = 0.0,
    ) -> float:
        """
        Triangle wave.

        Args:
            frequency (float): The frequency in Hz.
            amplitude (float): The peak amplitude.
            phase (float): The phase in degrees.
            offset (float): The value added to the wave.
        """
        angle = 2 * math.pi * self._cycles(frequency, phase)
        return offset + amplitude * (2 / math.pi) * math.asin(math.sin(angle))

    @mark_query
    def sawtooth(
        self,
        frequency: float = 1.0,
        amplitude: float = 1.0,
        phase: float = 0.0,
        offset: float = 0.0,
    ) -> float:
        """
        Sawtooth wave, which rises through the whole period then drops back.

        Args:
            frequency (float): The frequency in Hz.
            amplitude (float): The peak amplitude.
            phase (float): The phase in degrees.
            offset (float): The value added to the wave.
        """
        fraction = (self._cycles(frequency, phase) + 0.5) % 1
        return offset + amplitude * (2 * fraction - 1)

    @mark_query
    def chirp(
        self,
        start_frequency: float = 1.0,
        end_frequency: float = 10.0,
        duration: float = 10.0,
        amplitude: float = 1.0,
        offset: float = 0.0,
    ) -> float:
        """
        Sine wave whose frequency sweeps linearly from `start_frequency` to
        `end_frequency` over `duration`, then starts the sweep again.

        Args:
            start_frequency (float): The frequency at the start of a sweep, in Hz.
            end_frequency (float): The frequency at the end of a sweep, in Hz.
            duration (float): The length of a sweep in seconds. Must be positive.
            amplitude (float): The peak amplitude.
            offset (float): The value added to the wave.
        """
        _require(duration > 0, "duration must be positive.")
        t = self._elapsed() % duration
        sweep_rate = (end_frequency - start_frequency) / duration
        cycles = start_frequency * t + 0.5 * sweep_rate * t**2
        return offset + amplitude * math.sin(2 * math.pi * cycles)

    @mark_query
    def damped_sine(
        self,
        frequency: float = 1.0,
        decay_time: float = 10.0,
        amplitude: float = 1.0,
        phase: float = 0.0,
        offset: float = 0.0,
    ) -> float:
        """
        Sine wave whose amplitude decays exponentially from the start.

        Args:
            frequency (float): The frequency in Hz.
            decay_time (float): The time in seconds for the amplitude to fall to
                1/e (37%). Must be positive.
            amplitude (float): The amplitude at the start.
            phase (float): The phase in degrees.
            offset (float): The value the wave settles to.
        """
        _require(decay_time > 0, "decay_time must be positive.")
        envelope = math.exp(-self._elapsed() / decay_time)
        angle = 2 * math.pi * self._cycles(frequency, phase)
        return offset + amplitude * envelope * math.sin(angle)
