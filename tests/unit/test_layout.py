"""The GUI's layout, kept by the experiment for the next run (milestone 15)."""

import json

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment
from pyacquisition.core.layout import Layout


class Rig(Experiment):
    pass


class OtherRig(Experiment):
    pass


def serve(experiment):
    experiment._register_endpoints(experiment._api_server)
    return TestClient(experiment._api_server.app)


LAYOUT = {
    "plots": {"panels": [{"id": 1, "x": "time", "series": [{"name": "T"}]}], "link": False},
    "dock": {"active": "queue", "collapsed": False, "height": 280},
    "theme": "dark",
}


def test_there_is_no_layout_at_first(tmp_path):
    client = serve(Rig(root_path=str(tmp_path), gui=False))

    assert client.get("/experiment/layout").json()["data"] == {}


def test_a_layout_comes_back_in_the_next_run(tmp_path):
    client = serve(Rig(root_path=str(tmp_path), gui=False))
    assert client.put("/experiment/layout", json=LAYOUT).status_code == 200

    # A new run, on the same folder.
    client = serve(Rig(root_path=str(tmp_path), gui=False))

    assert client.get("/experiment/layout").json()["data"] == LAYOUT


def test_it_is_kept_in_a_file_under_the_root(tmp_path):
    serve(Rig(root_path=str(tmp_path), gui=False)).put("/experiment/layout", json=LAYOUT)

    saved = json.loads((tmp_path / ".pyacquisition" / "layout.json").read_text())
    assert saved == {"Rig": LAYOUT}


def test_experiments_sharing_a_folder_keep_their_own(tmp_path):
    serve(Rig(root_path=str(tmp_path), gui=False)).put("/experiment/layout", json=LAYOUT)
    other = serve(OtherRig(root_path=str(tmp_path), gui=False))
    other.put("/experiment/layout", json={"theme": "light"})

    assert other.get("/experiment/layout").json()["data"] == {"theme": "light"}
    rig = serve(Rig(root_path=str(tmp_path), gui=False))
    assert rig.get("/experiment/layout").json()["data"] == LAYOUT


def test_an_experiment_from_toml_is_kept_by_its_files_name(tmp_path):
    config = tmp_path / "cryostat.toml"
    config.write_text(f'[experiment]\nroot_path = "{tmp_path.as_posix()}"\n[gui]\nrun = false\n')
    serve(Experiment.from_config(str(config))).put("/experiment/layout", json=LAYOUT)

    saved = json.loads((tmp_path / ".pyacquisition" / "layout.json").read_text())
    assert list(saved) == ["cryostat"]


def test_only_an_object_is_taken(tmp_path):
    client = serve(Rig(root_path=str(tmp_path), gui=False))

    assert client.put("/experiment/layout", json=[1, 2]).status_code == 422
    assert client.get("/experiment/layout").json()["data"] == {}


def test_a_layout_far_too_big_is_refused(tmp_path):
    client = serve(Rig(root_path=str(tmp_path), gui=False))

    response = client.put("/experiment/layout", json={"junk": "x" * 1_100_000})

    assert response.status_code == 413


def test_a_file_that_cannot_be_read_starts_afresh(tmp_path):
    folder = tmp_path / ".pyacquisition"
    folder.mkdir()
    (folder / "layout.json").write_text("{not json")
    layout = Layout(tmp_path, "Rig")

    assert layout.get() == {}
    layout.put({"theme": "dark"})  # and a new one can be saved over it
    assert layout.get() == {"theme": "dark"}
