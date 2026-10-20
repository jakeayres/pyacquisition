"""What PyAcquisition says about itself (core/about.py): `about()`, and `GET
/about`, which the interface's About shows."""

from fastapi.testclient import TestClient

from pyacquisition import Experiment
from pyacquisition.core import about
from pyacquisition.core.news import installed_version

FACTS = {
    "name": "PyAcquisition",
    "license": "MPL-2.0",
    "license_name": "Mozilla Public License 2.0",
    "copyright": "Copyright (C) 2023-2026 Jake Ayres",
    "source_url": "https://github.com/jakeayres/pyacquisition",
    "license_url": "https://pyacquisition.readthedocs.io/en/latest/overview/license/",
    "libraries": [
        {"name": "Preact", "license": "MIT"},
        {"name": "uPlot", "license": "MIT"},
        {"name": "htm", "license": "Apache-2.0"},
    ],
}


def test_about_gives_the_facts_and_the_version_running():
    assert about.about() == {**FACTS, "version": installed_version()}


def test_a_version_that_isnt_known_is_none(monkeypatch):
    monkeypatch.setattr(about, "installed_version", lambda: None)

    assert about.about()["version"] is None


def test_each_library_is_in_the_vendor_folder_with_its_license():
    from pyacquisition.gui import STATIC_DIR

    for library in about.LIBRARIES:
        assert (STATIC_DIR / "vendor" / library["folder"] / "LICENSE").is_file()


def test_the_notice_names_the_version_the_license_and_the_source():
    text = about.notice("0.5.0")

    assert text.startswith("PyAcquisition 0.5.0\nCopyright (C) 2023-2026 Jake Ayres\n")
    assert "Mozilla Public License 2.0 (MPL-2.0): https://mozilla.org/MPL/2.0/" in text
    assert "Its source code is at https://github.com/jakeayres/pyacquisition" in text
    assert "are its\nauthor's, under whatever license they chose." in text
    assert "- Python, and the packages PyAcquisition and the experiment use, each under\n  its own license." in text


def test_the_notice_has_each_librarys_license_in_full():
    from pyacquisition.gui import STATIC_DIR

    text = about.notice("0.5.0")

    for library in about.LIBRARIES:
        license_text = (STATIC_DIR / "vendor" / library["folder"] / "LICENSE").read_text(encoding="utf-8")
        assert f"{library['name']}\n{'=' * 72}\n\n{license_text.strip()}" in text


def test_a_notice_without_a_version_says_so():
    assert about.notice(None).startswith("PyAcquisition (version unknown)\n")


def test_the_endpoint_answers_with_the_same(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    experiment._register_endpoints(experiment._api_server)

    response = TestClient(experiment._api_server.app).get("/about")

    assert response.json() == {"status": 200, "data": {**FACTS, "version": installed_version()}}
