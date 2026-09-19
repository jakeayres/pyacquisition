import math
import pytest
from pyacquisition import Measurement
from pyacquisition.instruments import instrument_map
from pyacquisition.instruments.software import SignalGenerator


class FakeClock:
    def __init__(self):
        self.now = 1000.0  # the zero must not matter

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def gen(clock):
    return SignalGenerator("gen", time_source=clock)


def at(gen, clock, t, name, **kwargs):
    """The waveform `t` seconds after the generator was created."""
    clock.now = 1000.0 + t
    return getattr(gen, name)(**kwargs)


@pytest.mark.parametrize(
    "t, expected", [(0, 0), (0.25, 1), (0.5, 0), (0.75, -1), (1, 0)]
)
def test_sine(gen, clock, t, expected):
    assert at(gen, clock, t, "sine") == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("t, expected", [(0, 1), (0.25, 0), (0.5, -1), (0.75, 0)])
def test_cosine(gen, clock, t, expected):
    assert at(gen, clock, t, "cosine") == pytest.approx(expected, abs=1e-12)


def test_frequency_amplitude_and_offset(gen, clock):
    # 2 Hz has its peak at t = 0.125
    value = at(gen, clock, 0.125, "sine", frequency=2, amplitude=3, offset=10)
    assert value == pytest.approx(13)


def test_phase_is_in_degrees(gen, clock):
    assert at(gen, clock, 0, "sine", phase=90) == pytest.approx(1)
    assert at(gen, clock, 0, "sine", phase=-90) == pytest.approx(-1)
    assert at(gen, clock, 0, "cosine", phase=90) == pytest.approx(0, abs=1e-12)


def test_square(gen, clock):
    assert at(gen, clock, 0.0, "square", amplitude=2) == 2
    assert at(gen, clock, 0.49, "square", amplitude=2) == 2
    assert at(gen, clock, 0.5, "square", amplitude=2) == -2
    assert at(gen, clock, 0.99, "square", amplitude=2) == -2
    assert at(gen, clock, 1.0, "square", amplitude=2) == 2


def test_square_duty_and_offset(gen, clock):
    assert at(gen, clock, 0.2, "square", duty=0.25, offset=5) == 6
    assert at(gen, clock, 0.3, "square", duty=0.25, offset=5) == 4
    assert at(gen, clock, 0.3, "square", duty=1) == 1
    assert at(gen, clock, 0.0, "square", duty=0) == -1


@pytest.mark.parametrize(
    "t, expected", [(0, 0), (0.125, 0.5), (0.25, 1), (0.5, 0), (0.75, -1), (1, 0)]
)
def test_triangle(gen, clock, t, expected):
    assert at(gen, clock, t, "triangle") == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize(
    "t, expected",
    [(0, 0), (0.25, 0.5), (0.4999, 0.9998), (0.5, -1), (0.75, -0.5), (1, 0)],
)
def test_sawtooth(gen, clock, t, expected):
    assert at(gen, clock, t, "sawtooth") == pytest.approx(expected, abs=1e-9)


def test_waveforms_are_periodic(gen, clock):
    for name in ["sine", "cosine", "square", "triangle", "sawtooth"]:
        first = at(gen, clock, 0.3, name, frequency=2)
        later = at(gen, clock, 0.3 + 5 * 0.5, name, frequency=2)
        assert later == pytest.approx(first), name


def test_chirp_phase(gen, clock):
    # 1 Hz to 3 Hz over 2 s: cycles = t + t**2 / 2
    kwargs = dict(start_frequency=1, end_frequency=3, duration=2)
    assert at(gen, clock, 0, "chirp", **kwargs) == pytest.approx(0, abs=1e-12)
    assert at(gen, clock, 0.5, "chirp", **kwargs) == pytest.approx(
        math.sin(2 * math.pi * 0.625)
    )
    assert at(gen, clock, 1, "chirp", **kwargs) == pytest.approx(0, abs=1e-9)


def test_chirp_repeats(gen, clock):
    kwargs = dict(start_frequency=1, end_frequency=3, duration=2)
    assert at(gen, clock, 2.5, "chirp", **kwargs) == pytest.approx(
        at(gen, clock, 0.5, "chirp", **kwargs)
    )


def test_damped_sine(gen, clock):
    # a quarter period is 1 s at 0.25 Hz, and decay_time is 1 s
    value = at(gen, clock, 1, "damped_sine", frequency=0.25, decay_time=1, offset=2)
    assert value == pytest.approx(2 + math.exp(-1))
    assert at(gen, clock, 0, "damped_sine", phase=90) == pytest.approx(1)


def test_restart(gen, clock):
    clock.now = 1000.6
    assert gen.elapsed_time() == pytest.approx(0.6)
    assert gen.restart() == 0
    assert gen.elapsed_time() == 0
    clock.now = 1000.85
    assert gen.sine() == pytest.approx(math.sin(2 * math.pi * 0.25))


@pytest.mark.parametrize(
    "name, kwargs",
    [
        ("square", dict(duty=-0.1)),
        ("square", dict(duty=1.1)),
        ("chirp", dict(duration=0)),
        ("damped_sine", dict(decay_time=0)),
    ],
)
def test_invalid_parameters_are_rejected(gen, name, kwargs):
    with pytest.raises(ValueError):
        getattr(gen, name)(**kwargs)


def test_every_query_works_with_its_defaults(gen):
    names = {"sine", "cosine", "square", "triangle", "sawtooth", "chirp", "damped_sine"}
    assert names | {"elapsed_time"} <= set(gen.queries)
    for name in names:
        assert isinstance(gen.queries[name](), float)


def test_uses_real_time_by_default():
    gen = SignalGenerator("gen")
    assert 0 <= gen.elapsed_time() < 1


def test_works_as_a_measurement(gen):
    measurement = Measurement("wave", gen.sine, frequency=0.1, amplitude=2)
    assert abs(measurement.run()) <= 2


def test_is_available_from_config():
    assert instrument_map["SignalGenerator"] is SignalGenerator
