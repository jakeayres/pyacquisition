from ...core.instrument import SoftwareInstrument, mark_query, mark_command
import math
import random


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


class RandomNumberGenerator(SoftwareInstrument):
    """
    A software random number generator with the common probability distributions.

    Every distribution is its own query, and every parameter has a default, so
    `Measurement("noise", rng.gaussian)` works as it is and
    `Measurement("noise", rng.gaussian, sigma=0.1)` changes a parameter.

    Useful for standing in for real hardware while developing an experiment. Give
    a `seed` to get the same numbers on every run.
    """

    name = "Random Number Generator"

    def __init__(self, uid, seed: int | None = None):
        super().__init__(uid)
        self._random = random.Random(seed)

    @mark_command
    def set_seed(self, seed: int) -> int:
        """
        Restarts the generator from a seed, so that the numbers repeat.

        Args:
            seed (int): The seed.

        Returns:
            int: The seed.
        """
        self._random.seed(seed)
        return seed

    # Continuous distributions

    @mark_query
    def uniform(self, low: float = 0.0, high: float = 1.0) -> float:
        """
        Draws from the uniform distribution between `low` and `high`.

        Args:
            low (float): The lower bound.
            high (float): The upper bound.
        """
        return self._random.uniform(low, high)

    @mark_query
    def gaussian(self, mean: float = 0.0, sigma: float = 1.0) -> float:
        """
        Draws from the Gaussian (normal) distribution.

        Args:
            mean (float): The mean.
            sigma (float): The standard deviation. Must not be negative.
        """
        _require(sigma >= 0, "sigma must not be negative.")
        return self._random.normalvariate(mean, sigma)

    @mark_query
    def lognormal(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        """
        Draws from the log-normal distribution.

        The logarithm of the result is Gaussian, with mean `mu` and standard
        deviation `sigma`.

        Args:
            mu (float): The mean of the logarithm.
            sigma (float): The standard deviation of the logarithm. Must not be negative.
        """
        _require(sigma >= 0, "sigma must not be negative.")
        return self._random.lognormvariate(mu, sigma)

    @mark_query
    def exponential(self, rate: float = 1.0) -> float:
        """
        Draws from the exponential distribution, whose mean is `1 / rate`.

        Args:
            rate (float): The rate. Must be positive.
        """
        _require(rate > 0, "rate must be positive.")
        return self._random.expovariate(rate)

    @mark_query
    def gamma(self, shape: float = 1.0, scale: float = 1.0) -> float:
        """
        Draws from the gamma distribution, whose mean is `shape * scale`.

        Args:
            shape (float): The shape. Must be positive.
            scale (float): The scale. Must be positive.
        """
        _require(shape > 0 and scale > 0, "shape and scale must be positive.")
        return self._random.gammavariate(shape, scale)

    @mark_query
    def beta(self, alpha: float = 1.0, beta: float = 1.0) -> float:
        """
        Draws from the beta distribution, which lies between 0 and 1.

        Args:
            alpha (float): The first shape. Must be positive.
            beta (float): The second shape. Must be positive.
        """
        _require(alpha > 0 and beta > 0, "alpha and beta must be positive.")
        return self._random.betavariate(alpha, beta)

    @mark_query
    def chi_squared(self, dof: float = 1.0) -> float:
        """
        Draws from the chi-squared distribution.

        Args:
            dof (float): The degrees of freedom. Must be positive.
        """
        _require(dof > 0, "dof must be positive.")
        return self._random.gammavariate(dof / 2, 2)

    @mark_query
    def student_t(self, dof: float = 1.0) -> float:
        """
        Draws from Student's t-distribution.

        Args:
            dof (float): The degrees of freedom. Must be positive.
        """
        _require(dof > 0, "dof must be positive.")
        z = self._random.normalvariate(0, 1)
        chi_squared = self._random.gammavariate(dof / 2, 2)
        return z / math.sqrt(chi_squared / dof)

    @mark_query
    def cauchy(self, location: float = 0.0, scale: float = 1.0) -> float:
        """
        Draws from the Cauchy (Lorentz) distribution.

        Args:
            location (float): The position of the peak.
            scale (float): The half width at half maximum. Must be positive.
        """
        _require(scale > 0, "scale must be positive.")
        return location + scale * math.tan(math.pi * (self._random.random() - 0.5))

    @mark_query
    def laplace(self, location: float = 0.0, scale: float = 1.0) -> float:
        """
        Draws from the Laplace (double exponential) distribution.

        Args:
            location (float): The position of the peak.
            scale (float): The decay length. Must be positive.
        """
        _require(scale > 0, "scale must be positive.")
        # The difference of two exponentials is Laplace distributed.
        return location + scale * (
            self._random.expovariate(1) - self._random.expovariate(1)
        )

    @mark_query
    def logistic(self, location: float = 0.0, scale: float = 1.0) -> float:
        """
        Draws from the logistic distribution.

        Args:
            location (float): The mean.
            scale (float): The scale. Must be positive.
        """
        _require(scale > 0, "scale must be positive.")
        u = self._random.random()
        while u == 0:
            u = self._random.random()
        return location + scale * math.log(u / (1 - u))

    @mark_query
    def rayleigh(self, sigma: float = 1.0) -> float:
        """
        Draws from the Rayleigh distribution.

        Args:
            sigma (float): The scale. Must be positive.
        """
        _require(sigma > 0, "sigma must be positive.")
        return math.hypot(
            self._random.normalvariate(0, sigma), self._random.normalvariate(0, sigma)
        )

    @mark_query
    def weibull(self, scale: float = 1.0, shape: float = 1.0) -> float:
        """
        Draws from the Weibull distribution.

        Args:
            scale (float): The scale. Must be positive.
            shape (float): The shape. Must be positive.
        """
        _require(scale > 0 and shape > 0, "scale and shape must be positive.")
        return self._random.weibullvariate(scale, shape)

    @mark_query
    def pareto(self, alpha: float = 1.0, scale: float = 1.0) -> float:
        """
        Draws from the Pareto distribution, which is never below `scale`.

        Args:
            alpha (float): The shape. Must be positive.
            scale (float): The minimum value. Must be positive.
        """
        _require(alpha > 0 and scale > 0, "alpha and scale must be positive.")
        return scale * self._random.paretovariate(alpha)

    @mark_query
    def triangular(
        self, low: float = 0.0, mode: float = 0.5, high: float = 1.0
    ) -> float:
        """
        Draws from the triangular distribution.

        Args:
            low (float): The lower bound.
            mode (float): The most likely value. Must be between `low` and `high`.
            high (float): The upper bound.
        """
        _require(low <= mode <= high, "mode must be between low and high.")
        return self._random.triangular(low, high, mode)

    @mark_query
    def von_mises(self, mu: float = 0.0, kappa: float = 1.0) -> float:
        """
        Draws an angle in radians from the von Mises (circular normal) distribution.

        Args:
            mu (float): The mean angle in radians.
            kappa (float): The concentration. Must not be negative. Zero gives a
                uniform angle.
        """
        _require(kappa >= 0, "kappa must not be negative.")
        return self._random.vonmisesvariate(mu, kappa)

    # Discrete distributions

    @mark_query
    def integer(self, low: int = 0, high: int = 100) -> int:
        """
        Draws a whole number between `low` and `high`, both included.

        Args:
            low (int): The lower bound.
            high (int): The upper bound.
        """
        _require(low <= high, "low must not be above high.")
        return self._random.randint(low, high)

    @mark_query
    def bernoulli(self, p: float = 0.5) -> int:
        """
        Draws 1 with probability `p`, and 0 otherwise.

        Args:
            p (float): The probability of 1, between 0 and 1.
        """
        _require(0 <= p <= 1, "p must be between 0 and 1.")
        return int(self._random.random() < p)

    @mark_query
    def binomial(self, n: int = 1, p: float = 0.5) -> int:
        """
        Draws the number of successes in `n` trials, each with probability `p`.

        Args:
            n (int): The number of trials. Must not be negative.
            p (float): The probability of success, between 0 and 1.
        """
        _require(n >= 0, "n must not be negative.")
        _require(0 <= p <= 1, "p must be between 0 and 1.")
        if hasattr(self._random, "binomialvariate"):
            return self._random.binomialvariate(n, p)
        return sum(self._random.random() < p for _ in range(n))

    @mark_query
    def poisson(self, mean: float = 1.0) -> int:
        """
        Draws from the Poisson distribution.

        Large means take longer, because the time grows in proportion to `mean`.

        Args:
            mean (float): The mean number of events. Must not be negative.
        """
        _require(mean >= 0, "mean must not be negative.")
        # Knuth's method. exp(-mean) underflows for large means, so split the
        # mean into parts, since a sum of Poisson draws is itself Poisson.
        count = 0
        while mean > 0:
            part = min(mean, 30.0)
            mean -= part
            limit = math.exp(-part)
            product = self._random.random()
            while product > limit:
                count += 1
                product *= self._random.random()
        return count

    @mark_query
    def geometric(self, p: float = 0.5) -> int:
        """
        Draws the number of trials up to and including the first success (1, 2, 3, ...).

        Args:
            p (float): The probability of success on each trial. Must be above 0
                and at most 1.
        """
        _require(0 < p <= 1, "p must be above 0 and at most 1.")
        if p == 1:
            return 1
        u = self._random.random()
        return max(1, math.ceil(math.log(1 - u) / math.log(1 - p)))
