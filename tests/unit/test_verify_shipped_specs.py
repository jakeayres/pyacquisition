"""The specs that ship beside the instrument classes, and the safety they promise.

These run in CI with no hardware. They are what stands between a typo in a spec
and a command sent to a magnet supply.
"""

import pytest

from pyacquisition.core.adapters.mock import MockResource
from pyacquisition.core.instrument import Instrument
from pyacquisition.instruments import (
    SR_830,
    SR_860,
    Keithley_2000,
    Keithley_6221,
    Lakeshore_340,
    Lakeshore_350,
    Mercury_IPS,
    instrument_map,
)
from pyacquisition.verify import (
    Hazard,
    Policy,
    Status,
    build_session,
    coverage,
    load_spec,
    plan,
)
from pyacquisition.verify.inventory import Entry
from pyacquisition.verify.spec import spec_path

HARDWARE = {
    name: cls
    for name, cls in instrument_map.items()
    if isinstance(cls, type) and issubclass(cls, Instrument)
}
LAB = [
    Keithley_2000,
    Keithley_6221,
    SR_830,
    SR_860,
    Lakeshore_340,
    Lakeshore_350,
    Mercury_IPS,
]


def entry(cls):
    return Entry(name=cls.__name__, cls=cls, adapter="mock", resource="x")


def session_for(cls, limit=Hazard.READ_ONLY, dry_run=False):
    resource = MockResource("x")
    session = build_session(
        entry(cls), resource, Policy(limit), dry_run=dry_run, spec=load_spec(cls)
    )
    return session, resource


# ------------------------------------------------------------ every instrument has one
def test_every_hardware_instrument_has_a_spec_beside_its_class():
    assert set(HARDWARE.values()) == set(LAB)
    for cls in HARDWARE.values():
        path = spec_path(cls)
        assert path.exists(), f"{cls.__name__} has no {path.name}"
        assert path.parent == spec_path(cls).with_name(path.name).parent


@pytest.mark.parametrize("cls", LAB, ids=lambda c: c.__name__)
def test_the_spec_is_valid_and_plans(cls):
    spec = load_spec(cls)  # raises SpecError for any problem
    checks = plan(cls, spec)
    assert checks[0].id == "identity"
    assert len(checks) > 15


@pytest.mark.parametrize("cls", LAB, ids=lambda c: c.__name__)
def test_a_spec_that_writes_declares_who_it_talks_to_and_a_safe_state(cls):
    spec = load_spec(cls)
    if spec.roundtrips:
        assert spec.identity, f"{cls.__name__} writes but declares no identity"
        assert spec.steps is not None, f"{cls.__name__} writes but has no [safe_state]"


@pytest.mark.parametrize("cls", LAB, ids=lambda c: c.__name__)
def test_every_write_is_tagged_and_no_write_is_read_only(cls):
    for rt in load_spec(cls).roundtrips.values():
        assert rt.hazard in (Hazard.REVERSIBLE, Hazard.HAZARDOUS)


# ------------------------------------------------------------ what is dangerous
def hazards(cls):
    return {i: rt.hazard for i, rt in load_spec(cls).roundtrips.items()}


def test_the_keithley_outputs_are_tagged_hazardous():
    tagged = hazards(Keithley_6221)
    for pair in (
        "output_state",
        "low_to_earth",
        "inner_shield",
        "io_pattern_force",
        "io_pattern",
        "power_on_setup",
        "buffer_size",
        "current_range",
    ):
        assert tagged[pair] is Hazard.HAZARDOUS, pair


def test_the_keithley_source_settings_only_run_with_the_output_off():
    for pair in (
        "current",
        "compliance",
        "wave_amplitude",
        "delta_high",
        "pulse_delta_high",
    ):
        calls = load_spec(Keithley_6221).roundtrips[pair].preconditions
        assert any(c.call == "get_output_state" and c.equals == "OFF" for c in calls), (
            pair
        )


def test_the_keithley_safe_state_is_output_off_and_is_verified():
    spec = load_spec(Keithley_6221)
    assert [(s.call, s.args) for s in spec.steps] == [
        ("set_output_state", {"state": "OFF"})
    ]
    assert [(v.call, v.equals) for v in spec.verify] == [("get_output_state", "OFF")]


def test_the_keithley_2000_changes_of_function_and_stored_data_are_hazardous():
    tagged = hazards(Keithley_2000)
    for pair in ("function", "buffer_size", "buffer_control", "power_on_setup"):
        assert tagged[pair] is Hazard.HAZARDOUS, pair
    # the per-function settings do not select the function, so they are only reversible
    for pair in ("nplc", "digits", "range_dcv", "range_res", "reference"):
        assert tagged[pair] is Hazard.REVERSIBLE, pair


def test_the_keithley_2000_range_round_trips_only_run_with_auto_range_off():
    roundtrips = load_spec(Keithley_2000).roundtrips
    ranges = [pair for pair in roundtrips if pair.startswith("range_")]
    assert len(ranges) == 6
    for pair in ranges:
        calls = roundtrips[pair].preconditions
        assert any(c.call == "get_auto_range" and c.equals == "OFF" for c in calls), (
            pair
        )


def test_the_keithley_2000_coupled_settings_have_their_preconditions():
    roundtrips = load_spec(Keithley_2000).roundtrips
    for pair, call in (
        ("buffer_size", "get_buffer_control"),
        ("sample_count", "get_continuous_initiation"),
        ("autozero", "get_continuous_initiation"),
    ):
        assert any(c.call == call for c in roundtrips[pair].preconditions), pair


def test_the_keithley_2000_has_nothing_to_switch_off():
    spec = load_spec(Keithley_2000)
    assert spec.steps == []


def test_the_keithley_2000_scanner_card_is_optional():
    spec = load_spec(Keithley_2000)
    for pair in ("internal_scan_list", "scan_mode"):
        assert "scanner" in spec.roundtrips[pair].requires


@pytest.mark.parametrize("cls", [SR_830, SR_860], ids=lambda c: c.__name__)
def test_what_drives_the_sample_is_hazardous(cls):
    tagged = hazards(cls)
    assert tagged["reference_amplitude"] is Hazard.HAZARDOUS
    if cls is SR_860:
        assert tagged["reference_offset"] is Hazard.HAZARDOUS


@pytest.mark.parametrize(
    "cls", [Lakeshore_340, Lakeshore_350], ids=lambda c: c.__name__
)
def test_no_heater_setting_is_active_in_a_lakeshore_spec(cls):
    assert set(load_spec(cls).roundtrips) == {"display_contrast"}


# ------------------------------------------------------------ the magnet
def test_the_mercury_spec_can_only_read():
    spec = load_spec(Mercury_IPS)
    assert spec.roundtrips == {} and spec.steps is None
    assert set(spec.read_patterns) == {r"^R\d+$", r"^X$"}
    assert not any(c.writes for c in plan(Mercury_IPS, spec))


def test_the_mercury_setters_and_actions_are_never_in_the_plan_but_are_flagged():
    checks = plan(Mercury_IPS, load_spec(Mercury_IPS))
    ids = {c.id for c in checks}
    for method in (
        "set_target_field",
        "set_target_current",
        "set_field_sweep_rate",
        "set_current_sweep_rate",
        "hold",
        "to_setpoint",
        "to_zero",
        "clamp",
        "switch_heater_on",
        "switch_heater_off",
        "force_heater_on",
        "remote_and_locked",
    ):
        assert not any(method in i for i in ids), method

    cover = coverage(Mercury_IPS, checks)
    assert {"set_target_field", "set_target_current"} <= set(
        cover["set_registered_as_query"]
    )
    assert {"hold", "to_setpoint", "switch_heater_on"} <= set(cover["untested"])


@pytest.mark.parametrize("limit", list(Hazard), ids=lambda h: h.value)
def test_the_magnet_only_ever_receives_reads_whatever_the_run_allows(limit):
    session, resource = session_for(Mercury_IPS, limit)
    for check in plan(Mercury_IPS, load_spec(Mercury_IPS)):
        session.run(check)

    sent = set(resource.written)
    assert sent and all(m == "X" or (m[0] == "R" and m[1:].isdigit()) for m in sent), (
        sent
    )
    assert session.guard.blocked == []
    for action in ("A0", "A1", "A2", "A4", "H0", "H1", "H2", "C1", "C2", "C3"):
        assert action not in sent


def test_the_guard_refuses_a_magnet_command_even_if_asked_directly():
    session, resource = session_for(Mercury_IPS, Hazard.HAZARDOUS)
    from pyacquisition.verify import SafetyViolation

    for call in (
        lambda: session.instrument.set_target_field(5.0),
        lambda: session.instrument.to_setpoint(),
        lambda: session.instrument.switch_heater_on(),
    ):
        with pytest.raises(SafetyViolation):
            call()
    assert not any(m[0] in "AHJIS" and m != "X" for m in resource.written)


# ------------------------------------------------------------ nothing is written by default
@pytest.mark.parametrize("cls", LAB, ids=lambda c: c.__name__)
def test_a_default_run_sends_nothing_but_reads_after_construction(cls):
    session, resource = session_for(cls)
    after_construction = len(resource.written)
    for check in plan(cls, load_spec(cls)):
        session.run(check)
    sent = resource.written[after_construction:]
    assert sent, "the run asked nothing"
    # by the guard's own test, which knows the instrument's protocol
    assert all(session.guard.is_read(m) for m in sent), sent
    assert session.guard.blocked == []


@pytest.mark.parametrize("cls", LAB, ids=lambda c: c.__name__)
def test_hazardous_checks_are_refused_and_send_nothing_without_the_flag(cls):
    session, _ = session_for(cls, Hazard.REVERSIBLE, dry_run=True)
    for check in plan(cls, load_spec(cls)):
        result = session.run(check)
        if result.hazard is Hazard.HAZARDOUS:
            assert result.status is Status.SKIPPED and result.sent == []


@pytest.mark.parametrize("cls", LAB, ids=lambda c: c.__name__)
def test_a_full_dry_run_of_every_check_completes_without_failures(cls):
    session, _ = session_for(cls, Hazard.HAZARDOUS, dry_run=True)
    results = [session.run(c) for c in plan(cls, load_spec(cls))]
    assert not [(r.check, r.detail) for r in results if r.status is Status.FAILED]
    spec = load_spec(cls)
    for r in results:
        if r.check == "safe_state" and not spec.steps:
            continue  # "nothing to do" is a safe state that sends nothing
        if r.status is Status.DRY_RUN and r.hazard is not Hazard.READ_ONLY:
            assert any("?" not in m for m in r.sent), f"{r.check} listed no write"


@pytest.mark.parametrize("cls", LAB, ids=lambda c: c.__name__)
def test_every_round_trip_names_its_setter_in_a_dry_run(cls):
    spec = load_spec(cls)
    session, _ = session_for(cls, Hazard.HAZARDOUS, dry_run=True)
    for check in plan(cls, spec):
        if check.id.startswith("roundtrip."):
            result = session.run(check)
            assert result.status in (Status.DRY_RUN, Status.SKIPPED), result
            if result.status is Status.DRY_RUN:
                assert any("?" not in m for m in result.sent)
