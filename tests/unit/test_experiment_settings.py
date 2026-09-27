"""Experiment options are class attributes, arguments or TOML keys, in that order of strength."""

import re
from pathlib import Path

import pytest

from pyacquisition import Experiment
from pyacquisition.core import settings


@pytest.fixture
def root(tmp_path):
    return str(tmp_path)


def write_toml(tmp_path, body):
    path = tmp_path / "rig.toml"
    path.write_text(body)
    return str(path)


# -------------------------------------------------------------- the defaults
def test_every_option_is_a_class_attribute_with_its_default():
    for name, setting in settings.SETTINGS.items():
        assert getattr(Experiment, name) == setting.default


def test_the_defaults_are_the_documented_ones():
    assert Experiment.data_path == "."
    assert Experiment.measurement_period == 0.25
    assert Experiment.api_server_port == 8000
    assert Experiment.gui is True


def test_every_option_can_be_passed_to_the_constructor():
    import inspect

    assert set(inspect.signature(Experiment).parameters) == set(settings.SETTINGS)


# -------------------------------------------------------------- class attributes
def test_a_subclass_sets_options_by_naming_them(root):
    class MyExperiment(Experiment):
        root_path = root
        data_path = "my_data"
        data_delimiter = ";"
        log_file_name = "my.log"
        measurement_period = 0.5
        gui = False

    experiment = MyExperiment()

    assert str(experiment._data_path) == str(experiment._root_path / "my_data")
    assert experiment._log_file_name.name == "my.log"
    assert experiment._rack.period == 0.5
    assert experiment._run_gui is False


def test_options_left_out_keep_their_defaults(root):
    class MyExperiment(Experiment):
        root_path = root
        gui = False

    experiment = MyExperiment()

    assert experiment._rack.period == 0.25
    assert experiment._data_path == experiment._root_path


def test_an_argument_beats_a_class_attribute(root):
    class MyExperiment(Experiment):
        root_path = root
        data_path = "from_class"
        measurement_period = 0.5
        gui = False

    experiment = MyExperiment(data_path="from_argument")

    assert experiment._data_path.name == "from_argument"
    assert experiment._rack.period == 0.5  # the other attribute still applies


def test_a_subclass_that_still_uses_super_init_keeps_working(root):
    class MyExperiment(Experiment):
        def __init__(self):
            super().__init__(root_path=root, data_path="my_data", gui=False)

    assert MyExperiment()._data_path.name == "my_data"


def test_a_class_attribute_can_be_computed_with_a_property(root):
    class MyExperiment(Experiment):
        root_path = root
        gui = False

        @property
        def data_path(self):
            return "computed"

    assert MyExperiment()._data_path.name == "computed"


def test_attributes_are_inherited_by_further_subclasses(root):
    class Base(Experiment):
        root_path = root
        data_path = "base"
        gui = False

    class Child(Base):
        measurement_period = 2.0

    experiment = Child()

    assert experiment._data_path.name == "base"
    assert experiment._rack.period == 2.0


def test_subclasses_do_not_leak_into_one_another(root):
    class First(Experiment):
        root_path = root
        data_path = "first"
        gui = False

    class Second(Experiment):
        root_path = root
        gui = False

    assert Second()._data_path == Second()._root_path
    assert Experiment.data_path == "."
    assert First.data_path == "first"


# -------------------------------------------------------------- validation
@pytest.mark.parametrize(
    "option, value, message",
    [
        ("measurement_period", "fast", "positive number"),
        ("measurement_period", 0, "positive number"),
        ("measurement_period", -1.0, "positive number"),
        ("measurement_period", True, "positive number"),
        ("api_server_port", 0, "port number"),
        ("api_server_port", 70000, "port number"),
        ("api_server_port", "8000", "port number"),
        ("gui", "yes", "True, False or 'new'"),
        ("history_points", 99, "whole number from 100 to 100000000"),
        ("history_points", 1.5e6, "whole number"),
        ("console_log_level", "LOUD", "must be one of"),
        ("data_path", 5, "must be a path"),
        ("data_delimiter", 1, "must be text"),
    ],
)
def test_an_invalid_value_is_refused_by_name(root, option, value, message):
    class MyExperiment(Experiment):
        root_path = root
        gui = False

    setattr(MyExperiment, option, value)

    with pytest.raises(ValueError, match=f"`{option}`.*{message}"):
        MyExperiment()


def test_an_invalid_argument_is_refused(root):
    with pytest.raises(ValueError, match="`measurement_period`"):
        Experiment(root_path=root, measurement_period="fast", gui=False)


def test_a_log_level_is_case_insensitive(root):
    Experiment(root_path=root, console_log_level="info", gui=False)  # accepted
    assert settings.SETTINGS["console_log_level"].check("x", "info") == "INFO"


def test_a_path_object_is_accepted(root, tmp_path):
    experiment = Experiment(root_path=tmp_path, data_path=tmp_path / "d", gui=False)
    assert experiment._data_path.name == "d"


def test_an_unknown_argument_is_refused(root):
    with pytest.raises(TypeError):
        Experiment(root_path=root, data_pth="oops")


# -------------------------------------------------------------- misspellings
@pytest.mark.parametrize(
    "misspelling, option",
    [
        ("data_pth", "data_path"),
        ("datapath", "data_path"),
        ("measurement_perod", "measurement_period"),
        ("Data_Path", "data_path"),
        ("api_server_prot", "api_server_port"),
        ("gui_log_levl", "gui_log_level"),
    ],
)
def test_a_misspelt_option_is_refused_when_the_class_is_defined(misspelling, option):
    with pytest.raises(TypeError, match=f"`{misspelling}`.*`{option}`"):
        type("MyExperiment", (Experiment,), {misspelling: "my_data"})


@pytest.mark.parametrize("name", ["data_pth", "measurement_perod"])
def test_the_misspelling_check_names_the_class_and_the_option(name):
    with pytest.raises(TypeError) as error:
        type("MyExperiment", (Experiment,), {name: 1})
    assert "MyExperiment" in str(error.value)


def test_unrelated_attributes_and_methods_are_fine():
    class MyExperiment(Experiment):
        sample_name = "S1"
        lockin_address = "GPIB0::7::INSTR"
        data_folder_note = "x"

        def setup(self):
            pass

        def teardown(self):
            pass

        def helper(self):
            pass

    assert MyExperiment.sample_name == "S1"


def test_a_misspelling_in_a_parent_is_caught_where_it_is_written():
    with pytest.raises(TypeError, match="data_pth"):
        type("Parent", (Experiment,), {"data_pth": 1})


# -------------------------------------------------------------- from a TOML file
def test_a_toml_value_beats_a_class_attribute(tmp_path, root):
    path = write_toml(tmp_path, '[data]\npath = "from_toml"\n')

    class MyExperiment(Experiment):
        root_path = root
        data_path = "from_class"
        gui = False

    assert MyExperiment.from_config(path)._data_path.name == "from_toml"


def test_options_the_toml_leaves_out_keep_the_class_attributes(tmp_path, root):
    path = write_toml(tmp_path, '[data]\npath = "from_toml"\n')

    class MyExperiment(Experiment):
        root_path = root
        measurement_period = 0.5
        gui = False

    experiment = MyExperiment.from_config(path)

    assert experiment._rack.period == 0.5


def test_an_override_beats_the_toml(tmp_path, root):
    path = write_toml(tmp_path, '[data]\npath = "from_toml"\n[rack]\nperiod = 1.5\n')

    class MyExperiment(Experiment):
        root_path = root
        gui = False

    experiment = MyExperiment.from_config(path, data_path="from_override")

    assert experiment._data_path.name == "from_override"
    assert experiment._rack.period == 1.5


def test_a_plain_experiment_reads_every_section(tmp_path, root):
    body = f"""
[experiment]
root_path = "{root.replace(chr(92), "/")}"

[data]
path = "d"
delimiter = ";"
file_extension = "csv"

[logging]
path = "l"
file_name = "run.log"
console_level = "INFO"
file_level = "INFO"
gui_level = "WARNING"

[rack]
period = 0.75

[gui]
run = false

[api_server]
host = "localhost"
port = 8123
"""
    experiment = Experiment.from_config(write_toml(tmp_path, body))

    assert experiment._data_path.name == "d"
    assert experiment._log_path.name == "l"
    assert experiment._log_file_name.name == "run.log"
    assert experiment._rack.period == 0.75
    assert experiment._run_gui is False


def test_an_empty_toml_gives_the_defaults(tmp_path, root):
    class MyExperiment(Experiment):
        root_path = root
        gui = False

    experiment = MyExperiment.from_config(write_toml(tmp_path, ""))

    assert experiment._rack.period == 0.25


def test_a_misspelt_toml_key_is_refused_with_a_suggestion(tmp_path):
    path = write_toml(tmp_path, '[data]\npth = "x"\n')

    with pytest.raises(ValueError, match=r"Unknown key 'pth' in \[data\].*'path'"):
        Experiment.from_config(path)


def test_an_invalid_toml_value_is_refused(tmp_path):
    path = write_toml(tmp_path, '[rack]\nperiod = "fast"\n')

    with pytest.raises(ValueError, match="measurement_period"):
        Experiment.from_config(path)


def test_an_unknown_override_is_refused(tmp_path):
    path = write_toml(tmp_path, "")

    with pytest.raises(ValueError, match="data_pth"):
        Experiment.from_config(path, data_pth="x")


def test_the_toml_keys_are_documented_once_each():
    sections = {}
    for setting in settings.SETTINGS.values():
        sections.setdefault(setting.section, []).append(setting.key)
    for keys in sections.values():
        assert len(keys) == len(set(keys))


# -------------------------------------------------------------- removed keys
def test_a_removed_toml_key_is_ignored_with_a_warning(tmp_path, root, monkeypatch):
    """`sparkline_points` went with the classic GUI. A file that still has it
    works, as it did, rather than being refused as a mistake."""
    warnings = []
    monkeypatch.setattr(settings.logger, "warning", warnings.append)
    path = write_toml(tmp_path, "[gui]\nsparkline_points = 60\n")

    experiment = Experiment.from_config(path, root_path=root, gui=False)

    assert experiment._run_gui is False
    assert any("'sparkline_points' in [gui] does nothing now" in w for w in warnings)


# -------------------------------------------------------------- described
TOML_DOCS = Path(__file__).resolve().parents[2] / "docs" / "usage" / "toml_config.md"


def documented_rows() -> dict:
    """Each key's description in toml_config.md, by (section, key)."""
    rows, section = {}, None
    for line in TOML_DOCS.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"## `\[(\w+)\]` Section", line)
        if heading:
            section = heading[1]
        elif line.startswith("## "):
            section = None
        row = re.match(r"\|\s*`(\w+)`\s*\|(.*?)\|", line)
        if section and row:
            rows[section, row[1]] = row[2].strip()
    return rows


@pytest.mark.parametrize("setting", settings.SETTINGS.values(), ids=lambda s: s.name)
def test_every_option_has_a_kind_and_a_help_of_one_sentence(setting):
    assert setting.kind in settings.KINDS
    assert setting.help.endswith(".") and setting.help.count(". ") == 0


@pytest.mark.parametrize("setting", settings.SETTINGS.values(), ids=lambda s: s.name)
def test_each_help_is_what_the_toml_docs_say(setting):
    assert documented_rows()[setting.section, setting.key] == setting.help


def test_the_options_are_described_for_the_page():
    import json

    described = settings.describe()

    json.dumps(described)  # all of it can be sent
    assert [d["name"] for d in described] == list(settings.SETTINGS)
    period = next(d for d in described if d["name"] == "measurement_period")
    assert period == {
        "name": "measurement_period",
        "section": "rack",
        "key": "period",
        "default": 0.25,
        "help": "The time between measurements, in seconds.",
        "kind": "seconds",
    }
    level = next(d for d in described if d["name"] == "console_log_level")
    assert level["choices"] == list(settings.LOG_LEVELS)
    points = next(d for d in described if d["name"] == "history_points")
    assert (points["minimum"], points["maximum"]) == (100, 100_000_000)
    ports = next(d for d in described if d["name"] == "api_server_fallback_ports")
    assert ports["default"] == []
