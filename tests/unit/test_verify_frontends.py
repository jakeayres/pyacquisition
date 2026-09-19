import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fake_instrument import (
    FakeInstrument,
    make_resource,
    make_session,
    make_spec,
)

from pyacquisition import Experiment
from pyacquisition.core.instrument import Instrument
from pyacquisition.verify import (
    Bench,
    Entry,
    Hazard,
    Policy,
    SpecError,
    Status,
    Unreachable,
    inventory,
    load_inventory,
    open_session,
    runner,
    verify,
)
from pyacquisition.verify import __main__ as cli

ROOT = Path(__file__).resolve().parents[2]
HAZARDOUS = Hazard.HAZARDOUS


def fake_entry(**kwargs):
    return Entry(name="fake", cls=FakeInstrument, adapter=None, resource=None, **kwargs)


@pytest.fixture
def fake_bench(monkeypatch):
    """Runs FakeInstrument, which has no spec file, with BASE_SPEC."""
    resource = make_resource()
    monkeypatch.setattr(runner, "load_spec", lambda cls: make_spec())
    monkeypatch.setattr(inventory, "load_spec", lambda cls: make_spec())

    def open_fake(entry, policy, dry_run=False):
        session, _, _ = make_session(
            limit=policy.max_hazard, resource=resource, dry_run=dry_run
        )
        return session

    monkeypatch.setattr(runner, "open_session", open_fake)
    return resource


# ------------------------------------------------------------ the bench
def test_an_unreachable_instrument_skips_every_check(monkeypatch):
    attempts = []

    def refuse(entry, policy, dry_run=False):
        attempts.append(entry.name)
        raise Unreachable("no answer from GPIB0::12")

    monkeypatch.setattr(runner, "open_session", refuse)
    monkeypatch.setattr(runner, "load_spec", lambda cls: make_spec())

    report = verify([fake_entry()], Policy(HAZARDOUS))
    assert report.results and all(r.status is Status.SKIPPED for r in report.results)
    assert all("not reachable: no answer" in r.detail for r in report.results)
    assert attempts == ["fake"]  # asked once, not once per check
    assert report.ok


def test_a_run_reports_by_instrument(fake_bench):
    report = verify([fake_entry()], Policy(HAZARDOUS))
    assert report.ok
    assert report.counts()["passed"] > 10
    info = report.instruments["fake"]
    assert info["class"] == "FakeInstrument" and info["identity"] == "ACME,FAKE-100,1"
    assert "hold" in info["untested"] and info["set_registered_as_query"] == [
        "set_target"
    ]

    text = report.text()
    assert "fake (FakeInstrument)  ACME,FAKE-100,1" in text
    assert "WARNING set_target is registered as a query" in text
    assert "not covered" in text and "summary:" in text
    assert "> " not in text  # commands are only shown when asked for
    assert "> LEVEL 1.0" in report.text(verbose=True)


def test_the_report_is_json_serialisable(fake_bench):
    data = verify([fake_entry()], Policy(HAZARDOUS)).to_dict()
    assert json.loads(json.dumps(data))["counts"]["failed"] == 0
    first = data["results"][0]
    assert set(first) == {
        "instrument",
        "check",
        "level",
        "hazard",
        "status",
        "detail",
        "sent",
    }


def test_closing_the_bench_restores_the_safe_state_and_closes(fake_bench):
    bench = Bench(Policy(HAZARDOUS))
    entry = fake_entry()
    for check in bench.plan(entry):
        if check.id in ("identity", "safe_state", "roundtrip.level"):
            bench.run(entry, check)
    fake_bench.state["OUT"] = "1"  # left on, however the run ended

    bench.close()
    assert fake_bench.state["OUT"] == "0" and not fake_bench.opened
    assert "close_problems" not in bench.report.instruments["fake"]


def test_a_safe_state_that_cannot_be_reached_at_the_end_is_reported(fake_bench):
    fake_bench.respond("OUT?", "1")  # will not go off
    with Bench(Policy(HAZARDOUS)) as bench:
        bench.run_entry(fake_entry())
    problems = bench.report.instruments["fake"]["close_problems"]
    assert any("SAFE STATE NOT REACHED AT THE END" in p for p in problems)
    assert "SAFE STATE NOT REACHED" in bench.report.text()


def test_the_bench_closes_even_if_the_run_raises(fake_bench):
    with pytest.raises(KeyboardInterrupt), Bench(Policy(HAZARDOUS)) as bench:
        entry = fake_entry()
        for check in bench.plan(entry)[:4]:
            bench.run(entry, check)
        fake_bench.state["OUT"] = "1"
        raise KeyboardInterrupt
    assert fake_bench.state["OUT"] == "0" and not fake_bench.opened


# ------------------------------------------------------------ the inventory
def write_inventory(tmp_path, body):
    path = tmp_path / "hardware.toml"
    path.write_text(body, encoding="utf-8")
    return path


KEITHLEY = """
[instruments.k]
instrument = "Keithley_6221"
adapter = "mock"
resource = "GPIB0::12::INSTR"
args = { responses = { "*IDN?" = "KEITHLEY INSTRUMENTS INC.,MODEL 6221,1,D03" } }
"""


def test_an_inventory_is_read(tmp_path):
    path = write_inventory(
        tmp_path,
        """
[instruments.k]
instrument = "Keithley_6221"
adapter = "pyvisa"
resource = "GPIB0::12::INSTR"
args = { timeout = 3000 }

[instruments.k.verify]
capabilities = ["nanovoltmeter"]
max_hazard = "reversible"
skip = ["set_wave_function"]
record = "rec/k.jsonl"

[instruments.magnet]
instrument = "Mercury_IPS"
adapter = "pyvisa"
resource = "GPIB0::25::INSTR"
""",
    )
    k, magnet = load_inventory(path)
    assert (k.name, k.cls.__name__, k.adapter, k.resource) == (
        "k",
        "Keithley_6221",
        "pyvisa",
        "GPIB0::12::INSTR",
    )
    assert k.args == {"timeout": 3000}
    assert k.capabilities == ("nanovoltmeter",) and k.skip == ("set_wave_function",)
    assert k.max_hazard is Hazard.REVERSIBLE and k.record == "rec/k.jsonl"
    assert magnet.max_hazard is None and magnet.capabilities == ()


@pytest.mark.parametrize(
    "body, match",
    [
        ('[instruments.k]\ninstrument = "Keithley_6221"\nadaptor = "x"', "unknown key"),
        (
            '[instruments.k]\ninstrument = "Keithley_6221"\n[instruments.k.verify]\nlevel = 1',
            "unknown key",
        ),
        ('[instruments.k]\ninstrument = "Nothing"', "unknown instrument"),
        ('[instruments.c]\ninstrument = "Clock"', "not a hardware instrument"),
        (
            '[instruments.k]\ninstrument = "Keithley_6221"\n[instruments.k.verify]\nmax_hazard = "some"',
            "unknown hazard",
        ),
    ],
)
def test_a_bad_inventory_is_refused(tmp_path, body, match):
    with pytest.raises(SpecError, match=match):
        load_inventory(write_inventory(tmp_path, body))


def test_a_dry_run_opens_nothing(tmp_path):
    (entry,) = load_inventory(
        write_inventory(tmp_path, KEITHLEY.replace("mock", "pyvisa"))
    )
    session = open_session(entry, Policy(), dry_run=True)  # pyvisa is never asked
    assert session.dry_run and session.instrument.__class__.__name__ == "Keithley_6221"


def test_the_inventorys_limit_reaches_the_session(tmp_path):
    body = KEITHLEY + '[instruments.k.verify]\nmax_hazard = "read-only"\n'
    (entry,) = load_inventory(write_inventory(tmp_path, body))
    assert (
        open_session(entry, Policy(HAZARDOUS), dry_run=True).max_hazard
        is Hazard.READ_ONLY
    )


def test_an_instrument_that_cannot_be_opened_is_unreachable(tmp_path, monkeypatch):
    (entry,) = load_inventory(write_inventory(tmp_path, KEITHLEY))
    monkeypatch.setattr(
        Experiment, "_open_resource", staticmethod(lambda *a, **k: None)
    )
    with pytest.raises(Unreachable, match="could not open"):
        open_session(entry, Policy())


def test_a_misconfigured_adapter_is_an_error_not_a_skip(tmp_path):
    body = KEITHLEY.replace('adapter = "mock"', 'adapter = "nope"')
    (entry,) = load_inventory(write_inventory(tmp_path, body))
    with pytest.raises(ValueError, match="not found"):
        open_session(entry, Policy())


def test_an_instrument_that_fails_to_initialise_is_unreachable_and_closed():
    class Exploding(Instrument):
        def __init__(self, uid, visa_resource):
            raise OSError("no reply to *CLS")

    from pyacquisition.core.adapters.mock import MockResource

    resource = MockResource("x")
    entry = Entry(name="e", cls=Exploding, adapter="mock", resource="x")
    with pytest.raises(Unreachable, match="did not initialise: OSError"):
        inventory.build_session(entry, resource, Policy())
    assert not resource.opened


def test_the_traffic_can_be_recorded_while_verifying(tmp_path):
    record = tmp_path / "rec" / "k.jsonl"
    body = KEITHLEY + f'[instruments.k.verify]\nrecord = "{record.as_posix()}"\n'
    (entry,) = load_inventory(write_inventory(tmp_path, body))
    with Bench(Policy()) as bench:
        bench.run_entry(entry)
    lines = [json.loads(line) for line in record.read_text().splitlines()]
    assert {"*CLS", "*IDN?"} <= {e["message"] for e in lines}


# ------------------------------------------------------------ the CLI
def test_the_cli_dry_run_lists_commands_and_exits_cleanly(tmp_path, capsys):
    path = write_inventory(tmp_path, KEITHLEY)
    assert cli.main([str(path), "--dry-run", "--reversible"]) == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out and "summary:" in out
    assert "> SOUR:CURR 1.000000e-09" in out  # a round trip's write is listed
    assert "> OUTP 0" in out  # and so is the safe state


def test_the_cli_lists_the_plan_without_running_it(tmp_path, capsys):
    path = write_inventory(tmp_path, KEITHLEY)
    assert cli.main([str(path), "--list"]) == 0
    out = capsys.readouterr().out
    assert "k (Keithley_6221)" in out
    assert "hazardous  roundtrip.output_state" in out
    assert "summary" not in out


def test_the_cli_fails_when_a_check_fails(tmp_path, capsys):
    # a mock knows no instrument, so the reads of a real driver do not parse
    path = write_inventory(tmp_path, KEITHLEY)
    assert cli.main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out and "KEITHLEY INSTRUMENTS INC." in out


def test_the_cli_stops_at_the_wrong_device(tmp_path, capsys):
    path = write_inventory(
        tmp_path,
        KEITHLEY.replace("KEITHLEY INSTRUMENTS INC.,MODEL 6221", "OTHER,MODEL 9"),
    )
    assert cli.main([str(path), "--hazardous"]) == 1
    out = capsys.readouterr().out
    assert "is this the right device" in out
    assert "identity check failed" in out
    assert "PASS" not in out.split("summary")[0].replace(
        "pass", ""
    )  # nothing passed after it


def test_the_cli_writes_a_json_report(tmp_path, capsys):
    report = tmp_path / "out" / "report.json"
    report.parent.mkdir()
    path = write_inventory(tmp_path, KEITHLEY)
    cli.main([str(path), "--dry-run", "--json", str(report)])
    data = json.loads(report.read_text())
    assert data["dry_run"] is True and data["counts"]["failed"] == 0


@pytest.mark.parametrize(
    "argv, message",
    [
        (["missing.toml"], "error"),
        (["INV", "--only", "nobody"], "not in the inventory"),
    ],
)
def test_the_cli_reports_usage_errors(tmp_path, capsys, argv, message):
    path = write_inventory(tmp_path, KEITHLEY)
    argv = [str(path) if a == "INV" else a for a in argv]
    assert cli.main(argv) == 2
    assert message in capsys.readouterr().err


# ------------------------------------------------------------ the pytest layer
def pytest_run(*args):
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def test_hardware_tests_are_skipped_unless_asked_for():
    result = pytest_run("tests/hardware", "-q", "-rs")
    assert result.returncode == 0, result.stdout
    assert "1 skipped" in result.stdout and "--hardware" in result.stdout


def test_hardware_tests_can_be_left_out_entirely():
    result = pytest_run("tests/hardware", "-q", "-m", "not hardware")
    assert "deselected" in result.stdout


def test_hardware_tests_run_in_dry_run_mode_and_report(tmp_path):
    inventory_path = write_inventory(tmp_path, KEITHLEY)
    report = tmp_path / "report.json"
    result = pytest_run(
        "tests/hardware",
        "--hardware",
        str(inventory_path),
        "--dry-run",
        "--reversible",
        "--hardware-report",
        str(report),
        "-q",
    )
    assert result.returncode == 0, result.stdout[-2000:]
    assert " passed" in result.stdout
    assert not re.search(r"\d+ failed", result.stdout)
    assert (
        "hardware verification report" in result.stdout and "DRY RUN" in result.stdout
    )
    data = json.loads(report.read_text())
    assert data["dry_run"] and data["counts"]["dry_run"] > 100


def test_hardware_tests_read_only_by_default(tmp_path):
    inventory_path = write_inventory(tmp_path, KEITHLEY)
    report = tmp_path / "report.json"
    result = pytest_run(
        "tests/hardware",
        "--hardware",
        str(inventory_path),
        "--dry-run",
        "--hardware-report",
        str(report),
        "-q",
    )
    assert result.returncode == 0, result.stdout[-2000:]
    results = json.loads(report.read_text())["results"]
    assert all(r["status"] in ("dry_run", "skipped") for r in results)
    assert all(r["hazard"] == "read-only" for r in results if r["status"] == "dry_run")
    assert not any(
        m.startswith(("SOUR:CURR 1", "OUTP 1")) for r in results for m in r["sent"]
    )
