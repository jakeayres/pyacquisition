import math
import statistics
import pytest
from pyacquisition import Measurement
from pyacquisition.instruments import instrument_map
from pyacquisition.instruments.software import RandomNumberGenerator

SAMPLES = 20000


@pytest.fixture
def rng():
    return RandomNumberGenerator("rng", seed=12345)


def draw(rng, name, **kwargs):
    return [getattr(rng, name)(**kwargs) for _ in range(SAMPLES)]


def gamma_fn(x):
    return math.gamma(x)


# name, kwargs, theoretical mean, theoretical variance
DISTRIBUTIONS = [
    ("uniform", dict(low=2, high=6), 4, 16 / 12),
    ("gaussian", dict(mean=5, sigma=2), 5, 4),
    (
        "lognormal",
        dict(mu=0, sigma=0.5),
        math.exp(0.125),
        (math.exp(0.25) - 1) * math.exp(0.25),
    ),
    ("exponential", dict(rate=2), 0.5, 0.25),
    ("gamma", dict(shape=3, scale=2), 6, 12),
    ("beta", dict(alpha=2, beta=5), 2 / 7, 10 / 392),
    ("chi_squared", dict(dof=4), 4, 8),
    ("student_t", dict(dof=10), 0, 1.25),
    ("laplace", dict(location=1, scale=2), 1, 8),
    ("logistic", dict(location=1, scale=2), 1, 4 * math.pi**2 / 3),
    ("rayleigh", dict(sigma=2), 2 * math.sqrt(math.pi / 2), 4 * (4 - math.pi) / 2),
    (
        "weibull",
        dict(scale=2, shape=3),
        2 * gamma_fn(1 + 1 / 3),
        4 * (gamma_fn(1 + 2 / 3) - gamma_fn(1 + 1 / 3) ** 2),
    ),
    ("triangular", dict(low=0, mode=1, high=4), 5 / 3, 13 / 18),
    ("integer", dict(low=1, high=6), 3.5, 35 / 12),
    ("bernoulli", dict(p=0.3), 0.3, 0.21),
    ("binomial", dict(n=10, p=0.3), 3, 2.1),
    ("poisson", dict(mean=4), 4, 4),
    ("poisson", dict(mean=100), 100, 100),
    ("geometric", dict(p=0.25), 4, 12),
]


@pytest.mark.parametrize(
    "name, kwargs, mean, variance",
    DISTRIBUTIONS,
    ids=[f"{d[0]}-{i}" for i, d in enumerate(DISTRIBUTIONS)],
)
def test_moments(rng, name, kwargs, mean, variance):
    values = draw(rng, name, **kwargs)
    standard_error = math.sqrt(variance / SAMPLES)
    assert statistics.fmean(values) == pytest.approx(mean, abs=5 * standard_error)
    assert statistics.pvariance(values) == pytest.approx(variance, rel=0.15)


def test_cauchy_has_the_right_median_and_width(rng):
    values = sorted(draw(rng, "cauchy", location=3, scale=2))
    quartiles = statistics.quantiles(values, n=4)
    assert quartiles[1] == pytest.approx(3, abs=0.15)
    assert quartiles[2] - quartiles[0] == pytest.approx(2 * 2, rel=0.1)


def test_pareto_is_never_below_scale_and_has_the_right_mean(rng):
    values = draw(rng, "pareto", alpha=5, scale=2)
    assert min(values) >= 2
    assert statistics.fmean(values) == pytest.approx(2.5, rel=0.05)


def test_von_mises_is_an_angle(rng):
    values = draw(rng, "von_mises", mu=1, kappa=4)
    assert all(0 <= v <= 2 * math.pi for v in values)
    assert math.atan2(
        statistics.fmean(math.sin(v) for v in values),
        statistics.fmean(math.cos(v) for v in values),
    ) == pytest.approx(1, abs=0.05)


def test_discrete_distributions_return_whole_numbers(rng):
    for name in ["integer", "bernoulli", "binomial", "poisson", "geometric"]:
        assert all(type(v) is int for v in draw(rng, name)[:200]), name


def test_geometric_starts_at_one(rng):
    assert min(draw(rng, "geometric", p=0.9)) == 1
    assert rng.geometric(p=1) == 1


def test_edge_cases(rng):
    assert rng.poisson(mean=0) == 0
    assert rng.bernoulli(p=0) == 0
    assert rng.bernoulli(p=1) == 1
    assert rng.binomial(n=0) == 0
    assert rng.integer(low=3, high=3) == 3
    assert rng.gaussian(mean=2, sigma=0) == 2


def test_same_seed_repeats():
    a = RandomNumberGenerator("a", seed=7)
    b = RandomNumberGenerator("b", seed=7)
    assert [a.gaussian() for _ in range(5)] == [b.gaussian() for _ in range(5)]


def test_set_seed_restarts_the_sequence(rng):
    rng.set_seed(99)
    first = [rng.uniform() for _ in range(5)]
    rng.set_seed(99)
    assert [rng.uniform() for _ in range(5)] == first


def test_different_generators_are_independent():
    a = RandomNumberGenerator("a", seed=1)
    b = RandomNumberGenerator("b", seed=1)
    a.uniform()
    a.uniform()
    assert b.uniform() == RandomNumberGenerator("c", seed=1).uniform()


@pytest.mark.parametrize(
    "name, kwargs",
    [
        ("gaussian", dict(sigma=-1)),
        ("lognormal", dict(sigma=-1)),
        ("exponential", dict(rate=0)),
        ("gamma", dict(shape=0)),
        ("gamma", dict(scale=-1)),
        ("beta", dict(alpha=0)),
        ("chi_squared", dict(dof=0)),
        ("student_t", dict(dof=-1)),
        ("cauchy", dict(scale=0)),
        ("laplace", dict(scale=0)),
        ("logistic", dict(scale=0)),
        ("rayleigh", dict(sigma=0)),
        ("weibull", dict(shape=0)),
        ("pareto", dict(alpha=0)),
        ("triangular", dict(low=0, mode=2, high=1)),
        ("von_mises", dict(kappa=-1)),
        ("integer", dict(low=2, high=1)),
        ("bernoulli", dict(p=1.5)),
        ("binomial", dict(n=-1)),
        ("binomial", dict(p=-0.1)),
        ("poisson", dict(mean=-1)),
        ("geometric", dict(p=0)),
    ],
)
def test_invalid_parameters_are_rejected(rng, name, kwargs):
    with pytest.raises(ValueError):
        getattr(rng, name)(**kwargs)


def test_every_query_works_with_its_defaults(rng):
    distributions = {d[0] for d in DISTRIBUTIONS} | {"cauchy", "pareto", "von_mises"}
    assert distributions <= set(rng.queries)
    for name in distributions:
        assert isinstance(rng.queries[name](), (int, float))


def test_works_as_a_measurement(rng):
    measurement = Measurement("noise", rng.gaussian, sigma=0.1)
    assert abs(measurement.run()) < 1


def test_is_available_from_config():
    assert instrument_map["RandomNumberGenerator"] is RandomNumberGenerator
