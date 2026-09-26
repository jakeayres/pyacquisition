"""Units of measurements and calculated columns, for display (milestone 3)."""

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment, Measurement, RollingMean, Sum
from pyacquisition.core.config_parser import ConfigParser, InvalidMeasurementError
from pyacquisition.instruments import Clock


def reading():
    return 1.0


# -------------------------------------------------------------- measurements
def test_a_measurement_has_no_unit_unless_given_one():
    assert Measurement("x", reading).unit is None
    assert Measurement("T", reading, unit="K").unit == "K"


def test_an_empty_unit_is_no_unit():
    assert Measurement("x", reading, unit="  ").unit is None


@pytest.mark.parametrize("unit", [5, 1.0, ["K"], True])
def test_a_unit_that_is_not_text_is_refused(unit):
    with pytest.raises(TypeError, match="the unit of measurement 'T' must be text"):
        Measurement("T", reading, unit=unit)


def test_a_unit_is_not_passed_to_the_query():
    def query(scale=1.0):
        return scale

    measurement = Measurement("x", query, unit="V", scale=2.0)

    assert measurement.run() == 2.0


# -------------------------------------------------------------- calculations
def test_a_calculation_can_be_given_units(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)

    experiment.add_calculation(lambda row: {"power": 1.0}, units={"power": "W"})

    assert experiment._calculations.units == {"power": "W"}


def test_the_built_in_calculations_take_a_unit():
    assert Sum("a", "b", name="total", unit="A").units == {"total": "A"}
    assert RollingMean("v", window=3, unit="V").units == {"v_mean3": "V"}
    assert RollingMean("v", window=3).units == {}


def test_a_calculation_unit_that_is_not_text_is_refused(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)

    with pytest.raises(TypeError, match="the unit of column 'power' must be text"):
        experiment.add_calculation(lambda row: {}, units={"power": 3})
    with pytest.raises(TypeError, match="units must be a dict"):
        experiment.add_calculation(lambda row: {}, units="W")


# -------------------------------------------------------------- TOML
def write(tmp_path, measurement):
    config = tmp_path / "rig.toml"
    config.write_text(
        f'[experiment]\nroot_path = "{tmp_path.as_posix()}"\n[gui]\nrun = false\n'
        '[instruments]\nclock = {instrument = "Clock"}\n'
        f"[measurements]\ntime = {measurement}\n"
    )
    return str(config)


def test_a_unit_can_be_given_in_toml(tmp_path):
    config = write(tmp_path, '{instrument = "clock", method = "time", unit = "s"}')

    experiment = Experiment.from_config(config)

    assert experiment.measurements["time"].unit == "s"


def test_a_toml_unit_that_is_not_text_is_refused(tmp_path):
    config = write(tmp_path, '{instrument = "clock", method = "time", unit = 1}')

    with pytest.raises(InvalidMeasurementError, match="unit is not text"):
        ConfigParser.parse(config)


# -------------------------------------------------------------- the endpoint
def columns(experiment) -> list:
    experiment._register_endpoints(experiment._api_server)
    return (
        TestClient(experiment._api_server.app).get("/experiment/columns").json()["data"]
    )


def test_the_columns_endpoint_describes_every_known_column(tmp_path):
    class Rig(Experiment):
        def setup(self):
            clock = Clock("clock")
            self.add_instrument(clock)
            self.add_measurement(Measurement("time", clock.time, unit="s"))
            self.add_measurement(Measurement("n", reading))
            self.add_calculation(RollingMean("time", window=2, unit="s"))
            self.add_calculation(lambda row: {"double": 2.0}, units={"double": "s"})
            self.add_calculation(lambda row: {"unlisted": 1.0})

    experiment = Rig(root_path=str(tmp_path), gui=False)
    experiment.setup()

    assert columns(experiment) == [
        {"name": "time", "kind": "measurement", "source": "clock.time", "unit": "s"},
        {"name": "n", "kind": "measurement", "source": "", "unit": None},
        {"name": "time_mean2", "kind": "calculation", "source": "", "unit": "s"},
        {"name": "double", "kind": "calculation", "source": "", "unit": "s"},
    ]
