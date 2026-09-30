"""Usage › Verify a driver on real hardware (docs/usage/verify_driver.md): each
version of hardware.toml loads, each command on the page parses, and each run
prints what the page says, with the instruments answered by a mock (as the page's
own outputs were), and check.py run on Write a hardware instrument's driver."""

import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from pyacquisition.instruments import SR_830
from pyacquisition.verify import Hazard, load_inventory
from pyacquisition.verify.__main__ import build_parser, main

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "verify_driver"
DRIVER = ROOT / "examples" / "usage" / "hardware_instrument" / "keithley_2400_5.py"
PAGE = ROOT / "docs" / "usage" / "verify_driver.md"

SR830_IDN = "Stanford_Research_Systems,SR830,s/n12345,ver1.07"
K2400_IDN = "KEITHLEY INSTRUMENTS INC.,MODEL 2400,1234567,C32"
READING = "+1.000000E+00,+1.021450E-06,+9.910000E+37,+2.515590E+03,+2.150800E+04"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def step(heading: str) -> str:
    page = text(PAGE)
    start = page.index(heading)
    end = page.find("\n## ", start + 1)
    return page[start:end]


def page_says(heading: str) -> list[str]:
    return re.search(r"```text\n(.*?)```", step(heading), re.S).group(1).splitlines()


def shows(page: list[str], printed: list[str]) -> bool:
    """Whether what the page shows was printed, in order, with `...` for lines left out."""
    printed = [line for line in printed if line.strip()] if "" not in page else printed
    at = 0
    for line in page:
        if line.strip() == "...":
            continue
        try:
            at = printed.index(line, at) + 1
        except ValueError:
            return False
    return True


def commands() -> list[list[str]]:
    """The page's `python -m pyacquisition.verify` commands, as argument lists."""
    found = []
    for block in re.findall(r"```bash\n(.*?)```", text(PAGE), re.S):
        for line in block.splitlines():
            if line.startswith("uv run python -m pyacquisition.verify "):
                found.append(shlex.split(line)[5:])
    return found


def mocked(version: int, folder: Path) -> Path:
    """hardware_<version>.toml with the lock-in answered by a mock, as the page's runs were."""
    source = text(HERE / f"hardware_{version}.toml").replace(
        'adapter = "pyvisa"',
        f'adapter = "mock"\nargs = {{ responses = {{ "*IDN?" = "{SR830_IDN}" }} }}',
    )
    (folder / "hardware.toml").write_text(source, encoding="utf-8")
    return folder / "hardware.toml"


def run(arguments: list[str], capsys) -> tuple[int, list[str]]:
    code = main(arguments)
    return code, capsys.readouterr().out.splitlines()


@pytest.mark.parametrize("version", [1, 2, 3])
def test_each_version_of_the_inventory_loads(version):
    [lockin] = load_inventory(HERE / f"hardware_{version}.toml")
    assert (lockin.name, lockin.cls, lockin.adapter, lockin.resource) == ("lockin", SR_830, "pyvisa", "GPIB0::8::INSTR")
    assert lockin.max_hazard is (None if version == 1 else Hazard.REVERSIBLE)
    assert lockin.record == (None if version < 3 else "recordings/lockin.jsonl")


def test_each_command_on_the_page_parses():
    assert [c[1:] for c in commands()] == [["--dry-run"], [], ["--reversible"], ["--reversible", "--json", "report.json"]]
    for arguments in commands():
        assert build_parser().parse_args(arguments).inventory == "hardware.toml"


def test_the_dry_run_contacts_nothing_and_lists_the_messages(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    shutil.copy(HERE / "hardware_1.toml", "hardware.toml")  # pyvisa, with nothing there
    code, printed = run(["hardware.toml", "--dry-run"], capsys)
    assert code == 0
    assert shows(page_says("## See what would be checked"), printed)


def test_the_read_only_run_prints_what_the_page_says(tmp_path, capsys):
    code, printed = run([str(mocked(1, tmp_path))], capsys)
    assert code == 0
    assert shows(page_says("## Run the read-only checks"), printed)


def test_the_reversible_run_leaves_the_amplitude_alone(tmp_path, capsys):
    code, printed = run([str(mocked(2, tmp_path)), "--reversible"], capsys)
    assert code == 0
    assert shows(page_says("## Allow checks that change settings"), printed)


def test_the_report_keeps_the_identity_and_each_check(tmp_path, capsys):
    code, _ = run([str(mocked(2, tmp_path)), "--reversible", "--json", str(tmp_path / "report.json")], capsys)
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert code == 0
    assert report["instruments"]["lockin"]["identity"] == SR830_IDN
    assert report["instruments"]["lockin"]["untested"] == ["clear", "reset", "reset_data_buffer"]
    assert report["results"][0]["check"] == "identity"
    assert report["results"][0]["sent"] == ["*IDN?"]


def test_a_recording_replays_with_no_instrument(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    mocked(3, tmp_path)
    _, recorded = run(["hardware.toml"], capsys)
    assert (tmp_path / "recordings" / "lockin.jsonl").exists()
    (tmp_path / "replay.toml").write_text(
        '[instruments.lockin]\ninstrument = "SR_830"\nadapter = "mock"\nresource = "anything"\n'
        'args = { transcript = "recordings/lockin.jsonl" }\n',
        encoding="utf-8",
    )
    code, replayed = run(["replay.toml"], capsys)
    assert code == 0
    assert replayed[-1] == recorded[-1] == "summary: 26 passed, 16 skipped"


def check(version: int, folder: Path, reading: str = READING, spec: bool = False, idn: str = K2400_IDN) -> list[str]:
    """check_<version>.py, run in a folder with the 2400's driver, and a mock in its place."""
    shutil.copy(DRIVER, folder / "keithley_2400.py")
    if spec:
        shutil.copy(HERE / "keithley_2400_1.toml", folder / "keithley_2400.toml")
    source = text(HERE / f"check_{version}.py")
    assert 'adapter="pyvisa",' in source
    source = source.replace(
        'adapter="pyvisa",',
        f'adapter="mock",\n    args={{"responses": {{":READ?": "{reading}", "*IDN?": "{idn}"}}}},',
    )
    (folder / "check.py").write_text(source, encoding="utf-8")
    done = subprocess.run([sys.executable, "check.py"], cwd=folder, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    return done.stdout.splitlines()


def test_a_driver_of_your_own_is_checked_from_python(tmp_path):
    printed = check(1, tmp_path)
    assert printed[1:] == page_says("## Check a driver of your own")


def test_a_mistake_in_the_driver_fails_as_the_page_says(tmp_path):
    printed = check(1, tmp_path, reading="+1.021450E-06")
    failure = re.search(r"`(FAIL  read-only  read\.get_current  -- [^`]*)`", step("## Check a driver of your own")).group(1)
    assert "  " + failure in printed


def test_with_its_spec_the_round_trip_runs(tmp_path):
    printed = check(2, tmp_path, spec=True)
    assert printed[1:] == page_says("## Allow the round trip")


def test_the_troubleshooting_messages_are_the_tools(tmp_path, capsys):
    problems = step("??? failure")
    (tmp_path / "hardware.toml").write_text(
        '[instruments.smu]\ninstrument = "Keithley_2400"\nadapter = "pyvisa"\nresource = "GPIB0::24::INSTR"\n',
        encoding="utf-8",
    )
    assert main([str(tmp_path / "hardware.toml")]) == 2
    assert capsys.readouterr().err.strip().replace(str(tmp_path / "hardware.toml"), "hardware.toml") in problems

    printed = check(2, tmp_path, spec=True, idn=K2400_IDN.replace("2400", "2410"))
    assert "which lacks ['2400']: is this the right device?" in printed[2]
    assert all(line.endswith("-- the identity check failed: this device is not talked to") for line in printed[3:-3])
    assert "which lacks ['2400']: is this the right device?`, and every other check says `the identity check failed: this device is not talked to`" in problems

    check(2, tmp_path, spec=True)  # check.py answering as a 2400 again
    (tmp_path / "keithley_2400.toml").write_text(
        text(HERE / "keithley_2400_1.toml").replace('[identity]\ncontains = ["KEITHLEY", "2400"]\n\n', ""),
        encoding="utf-8",
    )
    done = subprocess.run([sys.executable, "check.py"], cwd=tmp_path, capture_output=True, text=True, timeout=120)
    message = "the identity was not verified: nothing is written to a device that has not shown what it is"
    assert f"  skip  reversible roundtrip.voltage  -- {message}" in done.stdout.splitlines()
    assert f"`{message}`" in problems

    (tmp_path / "keithley_2400.toml").write_text(
        text(HERE / "keithley_2400_1.toml").replace('hazard = "reversible"\n', ""), encoding="utf-8"
    )
    done = subprocess.run([sys.executable, "check.py"], cwd=tmp_path, capture_output=True, text=True, timeout=120)
    error = done.stderr.strip().splitlines()[-1].removeprefix("pyacquisition.verify.model.")
    assert f"`{error}`" in problems
