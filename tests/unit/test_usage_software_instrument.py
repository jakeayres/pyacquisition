"""Usage › Write a software instrument (docs/usage/software_instrument.md): each
version of disk_space.py and lab.py runs, and does what the page says."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "software_instrument"
GETTING_STARTED = ROOT / "examples" / "getting_started"


def load(name: str, monkeypatch=None):
    """An example file as a module of its own name, so that it can't be mistaken for
    Getting Started's lab_1.py and the rest. lab.py's `import disk_space` is the
    finished driver's."""
    if monkeypatch is not None:
        monkeypatch.setitem(sys.modules, "disk_space", load("disk_space_5"))
    spec = importlib.util.spec_from_file_location(f"software_instrument_{name}", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_it_starts_from_the_end_of_getting_started():
    assert text(HERE / "lab_1.py") == text(GETTING_STARTED / "lab_6.py")


# -------------------------------------------------------------- disk_space.py
@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_each_version_makes_a_disk_space_instrument(version):
    disk = load(f"disk_space_{version}").DiskSpace("disk")
    assert disk.name == "Disk Space"
    assert disk.identify() == "Disk Space"  # under Other, it answers its name


def test_what_each_version_offers_in_the_instruments_tab():
    offered = {v: (sorted(d.queries), sorted(d.commands)) for v in range(1, 6)
               for d in [load(f"disk_space_{v}").DiskSpace("d")]}
    assert offered == {
        1: ([], []),
        2: (["get_space"], []),
        3: (["get_space"], ["set_folder"]),
        4: (["get_space"], ["set_folder"]),
        5: (["get_space"], ["set_folder"]),
    }


def test_the_query_answers_the_free_space_where_the_experiment_runs_in_gb(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    free = shutil.disk_usage(tmp_path).free / 1e9
    assert load("disk_space_2").DiskSpace("d").get_space() == pytest.approx(free, abs=0.1)


def test_the_command_watches_another_folder_and_refuses_one_that_isnt_there(tmp_path):
    disk = load("disk_space_3").DiskSpace("d")
    assert disk._folder == "."
    disk.set_folder(str(tmp_path))
    assert disk._folder == str(tmp_path)
    with pytest.raises(ValueError, match=r"^There is no folder called 'nowhere'\.$"):
        disk.set_folder("nowhere")
    assert disk._folder == str(tmp_path)  # unchanged


def test_the_choices_codes_are_the_names_disk_usage_gives_its_figures():
    space = load("disk_space_4").Space
    assert [(s.name, s.raw_value, s.label) for s in space] == [
        ("FREE", "free", "Free"), ("USED", "used", "Used"), ("TOTAL", "total", "Total")
    ]
    assert {s.raw_value for s in space} == set(shutil.disk_usage(".")._fields)


def test_the_query_reads_the_chosen_space(tmp_path):
    module = load("disk_space_5")
    disk = module.DiskSpace("d")
    disk.set_folder(str(tmp_path))
    usage = shutil.disk_usage(tmp_path)
    assert disk.get_space(module.Space.TOTAL) == usage.total / 1e9
    assert disk.get_space(module.Space.USED) == pytest.approx(usage.used / 1e9, abs=0.1)
    assert disk.get_space() == pytest.approx(usage.free / 1e9, abs=0.1)  # free, by default


# -------------------------------------------------------------- lab.py
@pytest.fixture
def lab(tmp_path, monkeypatch):
    """The finished lab.py, made from Getting Started's rig, as it would run."""
    shutil.copy(GETTING_STARTED / "rig.toml", tmp_path / "rig.toml")
    monkeypatch.chdir(tmp_path)
    experiment = load("lab_2", monkeypatch).Lab.from_config("rig.toml", root_path=str(tmp_path), gui=False)
    experiment.setup()
    return experiment


def test_the_lab_has_the_instrument_and_records_the_free_space(lab, tmp_path):
    assert lab.instruments["disk"].name == "Disk Space"
    free_space = lab.measurements["free_space"]
    assert free_space.unit == "GB"
    assert free_space.run() == pytest.approx(shutil.disk_usage(tmp_path).free / 1e9, abs=0.1)


def client(lab) -> TestClient:
    api = lab._api_server
    lab._rack._register_endpoints(api)  # the instruments' endpoints, as a run registers them
    return TestClient(api.app)


def test_the_interface_describes_each_method_with_its_docstring_and_offers_the_choice(lab):
    schema = client(lab).get("/openapi.json").json()
    query = schema["paths"]["/disk/get_space"]["get"]
    command = schema["paths"]["/disk/set_folder"]["get"]
    assert query["description"] == "The space on the drive, in GB: free, used, or in total."
    assert command["description"] == "Watches the drive that a folder is on."
    (space,) = query["parameters"]
    assert space["schema"]["default"] == "Free"
    assert schema["components"]["schemas"]["Space"]["enum"] == ["Free", "Used", "Total"]
    assert schema["components"]["schemas"]["Space"]["description"] == "Which space on the drive."
    (folder,) = command["parameters"]
    assert folder["required"] and folder["schema"]["type"] == "string"


def test_the_interface_reads_the_total_and_shows_why_a_folder_is_refused(lab, tmp_path):
    api = client(lab)
    total = api.get("/disk/get_space", params={"space": "Total"})
    assert total.json()["data"] == shutil.disk_usage(tmp_path).total / 1e9
    refused = api.get("/disk/set_folder", params={"folder": "nowhere"})
    assert refused.json() == {"detail": "There is no folder called 'nowhere'."}
    assert api.get("/disk/set_folder", params={"folder": str(tmp_path)}).json()["data"] is None
