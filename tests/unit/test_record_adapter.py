import json

import pytest
from pyvisa.errors import VisaIOError

from pyacquisition import Experiment
from pyacquisition.core.adapters import get_adapter
from pyacquisition.core.adapters.mock import MockResource
from pyacquisition.core.adapters.record import (
    RecordingResource,
    RecordingResourceManager,
    load_transcript,
)
from pyacquisition.instruments import Keithley_6221
from pyacquisition.instruments.keithley.keithley_6221 import State


def events(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.fixture
def transcript(tmp_path):
    return tmp_path / "recordings" / "t.jsonl"


def test_it_logs_writes_queries_and_reads(transcript):
    inner = MockResource("r", responses={"*IDN?": "ACME"})
    resource = RecordingResource(inner, transcript)
    resource.write("SOUR:CURR 1e-3")
    assert resource.query("*IDN?") == "ACME"
    resource.write("*OPC?")
    assert resource.read() == "1"
    resource.close()

    log = events(transcript)
    assert [(e["op"], e.get("message")) for e in log] == [
        ("write", "SOUR:CURR 1e-3"),
        ("query", "*IDN?"),
        ("write", "*OPC?"),
        ("read", None),
    ]
    assert log[1]["reply"] == "ACME"
    assert all(e["resource"] == "r" and "time" in e for e in log)


def test_errors_are_logged_and_re_raised(transcript):
    resource = RecordingResource(MockResource("r"), transcript)
    with pytest.raises(VisaIOError):
        resource.read()  # nothing was asked
    resource.close()
    assert "VisaIOError" in events(transcript)[0]["error"]


def test_the_recording_is_transparent(transcript):
    inner = MockResource("r", timeout=1234)
    resource = RecordingResource(inner, transcript)
    assert resource.timeout == 1234 and resource.resource_name == "r"
    resource.timeout = 99  # goes to the real resource
    assert inner.timeout == 99
    resource.close()
    assert not inner.opened


def test_it_appends(transcript):
    for _ in range(2):
        r = RecordingResource(MockResource("r"), transcript)
        r.write("X")
        r.close()
    assert len(events(transcript)) == 2


def test_the_adapter_is_registered_and_opens_through_another(transcript):
    manager = get_adapter("record")
    assert isinstance(manager, RecordingResourceManager)
    resource = manager.open_resource(
        "res", inner="mock", transcript=str(transcript), timeout=4000
    )
    assert resource.timeout == 4000
    resource.query("*IDN?")
    manager.close()
    assert events(transcript)[0]["message"] == "*IDN?"


def test_experiment_opens_a_recorded_resource_that_was_never_listed(transcript):
    resource = Experiment._open_resource(
        get_adapter("record"),
        "GPIB0::12::INSTR",
        timeout=5000,
        inner="mock",
        transcript=str(transcript),
    )
    assert resource is not None


def test_it_needs_a_transcript_and_cannot_record_itself(transcript):
    manager = RecordingResourceManager()
    with pytest.raises(ValueError, match="transcript"):
        manager.open_resource("r", inner="mock")
    with pytest.raises(ValueError, match="itself"):
        manager.open_resource("r", inner="record", transcript=str(transcript))


# ------------------------------------------------------------ replay
def test_a_transcript_is_replayed_in_order(transcript):
    inner = MockResource("r", responses={"KRDG? A": ["4.2", "4.3"]})
    resource = RecordingResource(inner, transcript)
    assert [resource.query("KRDG? A") for _ in range(3)] == ["4.2", "4.3", "4.3"]
    resource.close()

    replay = MockResource("again", transcript=transcript)
    assert [replay.query("KRDG? A") for _ in range(3)] == ["4.2", "4.3", "4.3"]


def test_explicit_responses_beat_a_transcript(transcript):
    recorded = RecordingResource(
        MockResource("r", responses={"*IDN?": "REAL"}), transcript
    )
    recorded.query("*IDN?")
    recorded.close()

    assert MockResource("m", transcript=transcript).query("*IDN?") == "REAL"
    override = MockResource("m", transcript=transcript, responses={"*IDN?": "OVERRIDE"})
    assert override.query("*IDN?") == "OVERRIDE"


def test_load_transcript_only_keeps_replies_to_queries(transcript):
    resource = RecordingResource(MockResource("r"), transcript)
    resource.write("SOUR:CURR 1e-3")
    resource.query("SOUR:CURR?")
    resource.close()
    assert load_transcript(transcript) == {"SOUR:CURR?": ["1e-3"]}


def test_an_instrument_session_recorded_and_replayed(transcript):
    """What CI does with a recording taken in the lab."""
    live = RecordingResource(MockResource("k"), transcript)
    k = Keithley_6221("k", live)
    k.set_current(1.5e-6)
    k.set_output_state(State.ON)
    seen = (k.get_current(), k.get_output_state(), k.identify())
    live.close()

    # the replay is an empty mock: what it says comes only from the recording
    replayed = Keithley_6221("k", MockResource("k", transcript=transcript))
    assert (
        replayed.get_current(),
        replayed.get_output_state(),
        replayed.identify(),
    ) == seen
