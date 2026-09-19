import pytest
from fake_instrument import (
    BASE_SPEC,
    FakeInstrument,
    MisbehavingInstrument,
    make_resource,
    make_session,
    make_spec,
    run_all,
)

from pyacquisition.core.adapters.mock import MockResource
from pyacquisition.verify import (
    GuardedResource,
    Hazard,
    Policy,
    SafetyViolation,
    Status,
    coverage,
    plan,
)

REVERSIBLE = Hazard.REVERSIBLE
HAZARDOUS = Hazard.HAZARDOUS


def statuses(results):
    return {check: result.status for check, result in results.items()}


def writes(resource):
    """What was sent to the device that was not a question."""
    return [message for message in resource.written if "?" not in message]


def run_ids(session, spec, ids, cls=FakeInstrument):
    """Runs only the named checks (and identity first), returning results by id."""
    wanted = {"identity", *ids}
    return {c.id: session.run(c) for c in plan(cls, spec) if c.id in wanted}


# ------------------------------------------------------------ the guard
def test_the_guard_lets_questions_through_and_refuses_the_rest():
    inner = MockResource("r")
    guard = GuardedResource(inner)
    assert guard.query("*IDN?")
    with pytest.raises(SafetyViolation, match="SOUR:CURR 1"):
        guard.write("SOUR:CURR 1")
    with pytest.raises(SafetyViolation):
        guard.query("A1")  # a "query" that is not a question
    assert guard.log == ["*IDN?"] and guard.blocked == ["SOUR:CURR 1", "A1"]
    assert inner.written == ["*IDN?"]  # nothing refused reached the device


def test_the_guard_learns_the_reads_of_other_protocols():
    inner = MockResource("r")
    guard = GuardedResource(inner, [r"^R\d+$", r"^X$"])
    for message in ("R7", "R15", "X", "*IDN?"):
        guard.write(message)
    for message in ("A1", "J5.000", "H1", "S0.1", "C3", "R7 now", "XY"):
        with pytest.raises(SafetyViolation):
            guard.write(message)
    assert inner.written == ["R7", "R15", "X", "*IDN?"]


def test_the_write_window_opens_and_closes_and_nests():
    guard = GuardedResource(MockResource("r"))
    with guard.writes_allowed():
        guard.write("A")
        with guard.writes_allowed():
            guard.write("B")
        guard.write("C")  # the inner window did not close the outer one
    assert not guard.allow_writes
    with pytest.raises(SafetyViolation):
        guard.write("D")
    assert guard.log == ["A", "B", "C"]


def test_the_window_closes_even_if_the_block_raises():
    guard = GuardedResource(MockResource("r"))
    with pytest.raises(RuntimeError), guard.writes_allowed():
        raise RuntimeError
    assert not guard.allow_writes


def test_the_guard_passes_everything_else_through():
    inner = MockResource("r", timeout=1234)
    guard = GuardedResource(inner)
    assert guard.timeout == 1234 and guard.resource_name == "r"
    guard.close()
    assert not inner.opened


# ------------------------------------------------------------ the plan
def test_the_plan_runs_identity_first_then_the_safe_state_then_reads_then_writes():
    ids = [c.id for c in plan(FakeInstrument, make_spec())]
    assert ids[:2] == ["identity", "safe_state"]
    assert all(i.startswith("read.") for i in ids[2:-4])
    assert ids[-4:] == [
        "roundtrip.level",
        "roundtrip.mode",
        "roundtrip.gain",
        "roundtrip.output_state",
    ]


def test_every_check_carries_a_hazard_and_only_writes_when_it_says_so():
    for check in plan(FakeInstrument, make_spec()):
        assert isinstance(check.hazard, Hazard)
        assert check.writes == (check.level == 2)
        if check.level < 2:
            assert check.hazard is Hazard.READ_ONLY


def test_only_getters_are_read_whatever_they_are_registered_as():
    ids = {c.id for c in plan(FakeInstrument, make_spec())}
    # set_target and hold are registered as queries, like Mercury_IPS's actions
    assert not {i for i in ids if "set_target" in i or "hold" in i or "reset" in i}
    assert {"read.get_level", "read.get_mode", "read.get_output_state"} <= ids


def test_coverage_names_what_is_untested_and_what_is_misregistered():
    cover = coverage(FakeInstrument, plan(FakeInstrument, make_spec()))
    assert cover["untested"] == ["hold", "reset", "set_target"]
    assert cover["set_registered_as_query"] == ["set_target"]


def test_enum_arguments_are_expanded_and_others_need_the_spec():
    ids = [c.id for c in plan(FakeInstrument, make_spec())]
    assert "read.get_gain[channel=ONE]" in ids and "read.get_gain[channel=TWO]" in ids
    assert "read.get_count[index=1]" in ids  # from [read.get_count] args

    without = plan(FakeInstrument, make_spec("[identity]\ncontains = ['ACME']"))
    count = next(c for c in without if c.id == "read.get_count")
    assert "give 'args'" in count.reason  # visible, and skipped, not silently dropped


def test_a_class_with_no_spec_still_gets_a_read_plan():
    ids = [c.id for c in plan(FakeInstrument, None)]
    assert ids[0] == "identity" and "read.get_level" in ids
    assert not any(i.startswith("roundtrip") or i == "safe_state" for i in ids)


# ------------------------------------------------------------ hazard gates
def test_by_default_only_reads_run():
    session, _, spec = make_session()
    results = run_all(session, spec=spec)

    assert results["identity"].status is Status.PASSED
    assert results["read.get_level"].status is Status.PASSED
    for check in ("safe_state", "roundtrip.level", "roundtrip.output_state"):
        assert results[check].status is Status.SKIPPED
    assert "--reversible" in results["roundtrip.level"].detail
    assert "--hazardous" in results["roundtrip.output_state"].detail


def test_a_default_run_sends_nothing_but_questions_after_construction():
    session, resource, spec = make_session(cls=MisbehavingInstrument)
    resource.respond("BAD?", "1.0")
    run_all(session, MisbehavingInstrument, spec)
    assert writes(resource) == ["INIT"]  # the constructor's, and nothing since


def test_reversible_runs_round_trips_but_not_hazardous_ones():
    session, _, spec = make_session(limit=REVERSIBLE)
    results = statuses(run_all(session, spec=spec))
    assert results["roundtrip.level"] is Status.PASSED
    assert results["roundtrip.mode"] is Status.PASSED
    assert results["roundtrip.gain"] is Status.PASSED
    assert results["roundtrip.output_state"] is Status.SKIPPED


def test_hazardous_implies_reversible_and_runs_everything():
    session, resource, spec = make_session(limit=HAZARDOUS)
    results = statuses(run_all(session, spec=spec))
    assert all(
        results[c] is Status.PASSED for c in results if c.startswith("roundtrip")
    )
    assert results["safe_state"] is Status.PASSED
    assert resource.state["OUT"] == "0"  # ON was written, and put back


def test_an_instrument_can_be_limited_below_the_run():
    session, resource, spec = make_session(limit=HAZARDOUS, max_hazard=Hazard.READ_ONLY)
    results = run_all(session, spec=spec)
    assert results["roundtrip.level"].status is Status.SKIPPED
    assert "limited to read-only" in results["roundtrip.level"].detail
    assert "inventory" in results["roundtrip.level"].detail
    assert writes(resource) == ["INIT"]


def test_an_instrument_cannot_be_raised_above_the_run():
    session, _, spec = make_session(limit=Hazard.READ_ONLY, max_hazard=HAZARDOUS)
    assert run_all(session, spec=spec)["roundtrip.level"].status is Status.SKIPPED


def test_nothing_is_written_without_a_safe_state_in_the_spec():
    text = (
        BASE_SPEC.split("[safe_state]")[0]
        + "[roundtrip.level]\nhazard='reversible'\nvalues=[1.0]"
    )
    session, resource, spec = make_session(text, limit=HAZARDOUS)
    result = run_all(session, spec=spec)["roundtrip.level"]
    assert result.status is Status.SKIPPED and "[safe_state]" in result.detail
    assert writes(resource) == ["INIT"]


def test_a_class_without_a_spec_is_never_written_to():
    session, resource, _ = make_session(None, limit=HAZARDOUS)
    results = run_all(session, spec=None)
    assert results["read.get_level"].status is Status.PASSED
    assert writes(resource) == ["INIT"]


# ------------------------------------------------------------ identity
def test_the_wrong_device_is_not_talked_to_again():
    session, resource, spec = make_session(
        limit=HAZARDOUS, resource=make_resource(identity="SOMEONE,ELSE,1")
    )
    results = run_all(session, spec=spec)
    assert results["identity"].status is Status.FAILED
    assert "right device" in results["identity"].detail
    assert all(
        r.status is Status.SKIPPED for c, r in results.items() if c != "identity"
    )
    assert "identity check failed" in results["read.get_level"].detail
    assert writes(resource) == ["INIT"]
    assert resource.written.count("LEVEL?") == 0  # not even asked


def test_identity_must_contain_every_word_case_insensitively():
    session, _, spec = make_session(resource=make_resource(identity="acme,fake-100,9"))
    assert run_all(session, spec=spec)["identity"].status is Status.PASSED
    session, _, spec = make_session(resource=make_resource(identity="ACME,OTHER,9"))
    assert run_all(session, spec=spec)["identity"].status is Status.FAILED


def test_a_device_that_has_not_proven_its_identity_is_read_but_not_written():
    text = BASE_SPEC.replace('contains = ["ACME", "FAKE"]', "")
    text = text.replace("[identity]", "")
    session, resource, spec = make_session(text, limit=HAZARDOUS)
    results = run_all(session, spec=spec)
    assert results["identity"].status is Status.SKIPPED
    assert "*IDN?" not in resource.written  # nothing to compare with, so not asked
    assert results["read.get_level"].status is Status.PASSED
    assert results["roundtrip.level"].status is Status.SKIPPED
    assert "identity" in results["roundtrip.level"].detail
    assert writes(resource) == ["INIT"]


# ------------------------------------------------------------ round trips
def test_a_round_trip_writes_reads_back_and_restores():
    session, resource, spec = make_session(limit=REVERSIBLE)
    results = run_ids(
        session, spec, ["roundtrip.level", "roundtrip.mode", "roundtrip.gain"]
    )
    assert all(r.status is Status.PASSED for r in results.values()), results
    assert resource.state["LEVEL"] == "3.0"  # the original, put back
    assert resource.state["MODE"] == "a"
    assert resource.state["GAIN 1"] == "1.5" and resource.state["GAIN 2"] == "2.5"
    assert "LEVEL 1.0" in resource.written and "LEVEL 2.0" in resource.written
    assert "3 value(s)" in results["roundtrip.mode"].detail


def test_a_wrong_readback_fails_and_is_still_restored():
    session, resource, spec = make_session(limit=REVERSIBLE)
    # a device that rounds what it stores to a whole number
    resource.respond("LEVEL?", lambda q: str(round(float(resource.state["LEVEL"]))))
    text = BASE_SPEC.replace("values = [1.0, 2.0]", "values = [0.5, 2.0]")
    session, resource, spec = make_session(text, limit=REVERSIBLE, resource=resource)

    result = run_ids(session, spec, ["roundtrip.level"])["roundtrip.level"]
    assert result.status is Status.FAILED
    assert "wrote 0.5, read back 0.0" in result.detail
    assert "wrote 2.0" not in result.detail  # the good value did not fail
    assert resource.state["LEVEL"] == "3.0"


def test_a_failed_restore_is_reported_loudly():
    session, resource, spec = make_session(limit=REVERSIBLE)
    # original, after 1.0, after 2.0, and then the device does not come back
    resource.respond("LEVEL?", ["3.0", "1.0", "2.0", "9.0"])
    result = run_ids(session, spec, ["roundtrip.level"])["roundtrip.level"]
    assert result.status is Status.FAILED
    assert "RESTORE FAILED: was 3.0, now 9.0" in result.detail


def test_a_setter_that_raises_still_leads_to_a_restore_and_a_safe_state():
    text = BASE_SPEC.replace("values = [1.0, 2.0]", "values = [1.0, 99.0]")
    session, resource, spec = make_session(text, limit=REVERSIBLE)
    result = run_ids(session, spec, ["roundtrip.level"])["roundtrip.level"]
    assert result.status is Status.FAILED and "the setter blew up" in result.detail
    assert resource.state["LEVEL"] == "3.0"
    assert writes(resource)[-1] == "OUT 0"


def test_the_safe_state_comes_before_and_after_every_write_and_at_the_end():
    session, resource, spec = make_session(limit=REVERSIBLE)
    run_ids(session, spec, ["roundtrip.level"])
    sent = writes(resource)
    assert sent == ["INIT", "OUT 0", "LEVEL 1.0", "LEVEL 2.0", "LEVEL 3.0", "OUT 0"]

    resource.state["OUT"] = "1"  # something switched it on meanwhile
    problems = session.close()
    assert not problems and resource.state["OUT"] == "0"  # and closing puts it back
    assert not resource.opened


def test_the_safe_state_is_not_entered_by_a_session_that_wrote_nothing():
    session, resource, spec = make_session()
    run_all(session, spec=spec)
    session.close()
    assert "OUT 0" not in resource.written


def test_a_safe_state_that_cannot_be_confirmed_stops_every_later_write():
    resource = make_resource()
    resource.respond("OUT?", "1")  # it will not go off
    session, _, spec = make_session(limit=HAZARDOUS, resource=resource)
    results = run_all(session, spec=spec)

    assert results["safe_state"].status is Status.FAILED
    assert "SAFE STATE NOT REACHED" in results["safe_state"].detail
    for check in ("roundtrip.level", "roundtrip.mode", "roundtrip.gain"):
        assert results[check].status is Status.SKIPPED
        assert "safe state could not be reached" in results[check].detail
    assert results["read.get_level"].status is Status.PASSED  # reading is still fine
    assert "LEVEL 1.0" not in resource.written  # nothing was changed


def test_a_precondition_that_does_not_hold_skips_without_writing():
    text = BASE_SPEC.replace(
        '[roundtrip.level]\nhazard = "reversible"',
        '[roundtrip.level]\nhazard = "reversible"\n'
        "preconditions = [{ call = 'get_mode', equals = 'C' }]",
    )
    session, resource, spec = make_session(text, limit=REVERSIBLE)
    result = run_ids(session, spec, ["roundtrip.level"])["roundtrip.level"]
    assert result.status is Status.SKIPPED
    assert "precondition not met" in result.detail and "get_mode" in result.detail
    assert not any(m.startswith("LEVEL ") for m in resource.written)


def test_the_write_window_is_closed_after_every_check():
    session, _, spec = make_session(limit=HAZARDOUS)
    run_all(session, spec=spec)
    assert not session.guard.allow_writes


# ------------------------------------------------------------ misbehaviour
def test_the_guard_stops_a_getter_that_writes():
    session, resource, spec = make_session(cls=MisbehavingInstrument, limit=HAZARDOUS)
    resource.respond("BAD?", "1.0")
    result = run_all(session, MisbehavingInstrument, spec)["read.get_sneaky"]
    assert result.status is Status.FAILED
    assert "BLOCKED BY THE GUARD" in result.detail and "BOOM" in result.detail
    assert "BOOM" not in resource.written
    assert session.guard.blocked == ["BOOM"]


def test_a_getter_that_raises_is_a_failure_not_a_crash():
    session, resource, spec = make_session(cls=MisbehavingInstrument)
    resource.respond("BAD?", "not a number")
    results = run_all(session, MisbehavingInstrument, spec)
    assert results["read.get_bad"].status is Status.FAILED
    assert "ValueError" in results["read.get_bad"].detail
    assert results["read.get_level"].status is Status.PASSED  # the run carried on


def test_a_reply_of_the_wrong_type_fails():
    class Liar(FakeInstrument):
        from pyacquisition.core.instrument import mark_query as _q

        @_q
        def get_typed(self) -> float:
            return "text"

    session, _, spec = make_session(cls=Liar)
    result = run_all(session, Liar, spec)["read.get_typed"]
    assert result.status is Status.FAILED and "expected float" in result.detail


def test_a_reading_outside_its_range_fails():
    text = "[identity]\ncontains = ['ACME']\n[read.get_level]\nrange = [0, 1]"
    session, _, spec = make_session(text)
    result = run_all(session, spec=spec)["read.get_level"]
    assert (
        result.status is Status.FAILED and "outside the expected range" in result.detail
    )
    session, _, spec = make_session(text.replace("[0, 1]", "[0, 10]"))
    assert run_all(session, spec=spec)["read.get_level"].status is Status.PASSED


def test_a_rule_can_skip_a_getter_and_say_why():
    text = "[read.get_level]\nskip = 'consumes a reading'"
    session, _, spec = make_session(text)
    result = run_all(session, spec=spec)["read.get_level"]
    assert result.status is Status.SKIPPED and result.detail == "consumes a reading"


def test_capabilities_unlock_the_checks_that_need_them():
    text = "[read.get_level]\nrequires = ['nanovoltmeter']"
    session, _, spec = make_session(text)
    result = run_all(session, spec=spec)["read.get_level"]
    assert result.status is Status.SKIPPED and "nanovoltmeter" in result.detail
    session, _, spec = make_session(text, capabilities=["nanovoltmeter"])
    assert run_all(session, spec=spec)["read.get_level"].status is Status.PASSED


def test_the_inventory_can_exclude_methods_on_one_instrument():
    session, resource, spec = make_session(limit=REVERSIBLE, skip=["get_level"])
    results = run_all(session, spec=spec)
    assert results["read.get_level"].status is Status.SKIPPED
    assert results["roundtrip.level"].status is Status.SKIPPED  # it needs get_level
    assert results["roundtrip.mode"].status is Status.PASSED
    assert not any(m.startswith("LEVEL ") for m in resource.written)


# ------------------------------------------------------------ dry run
def test_a_dry_run_lists_what_would_be_sent_and_verifies_nothing():
    session, _, spec = make_session(limit=REVERSIBLE, dry_run=True)
    results = run_all(session, spec=spec)

    assert results["roundtrip.level"].status is Status.DRY_RUN
    assert "LEVEL 1.0" in results["roundtrip.level"].sent
    assert "OUT 0" in results["roundtrip.level"].sent  # the safe state is shown too
    assert results["identity"].status is Status.SKIPPED
    assert not any(r.status is Status.FAILED for r in results.values())


def test_a_dry_run_survives_replies_that_mean_nothing():
    # an empty device: every getter's reply is "0", which is no enum member
    session, _, spec = make_session(
        limit=REVERSIBLE, dry_run=True, resource=make_resource(seed={})
    )
    results = run_all(session, spec=spec)
    assert not any(r.status is Status.FAILED for r in results.values())
    # the whole round trip is still listed although nothing could be read back
    assert {"LEVEL 1.0", "LEVEL 2.0"} <= set(results["roundtrip.level"].sent)


def test_a_dry_run_does_not_list_what_the_policy_would_refuse():
    session, _, spec = make_session(limit=REVERSIBLE, dry_run=True)
    result = run_all(session, spec=spec)["roundtrip.output_state"]
    assert result.status is Status.SKIPPED and result.sent == []
    session, _, spec = make_session(limit=HAZARDOUS, dry_run=True)
    assert "OUT 1" in run_all(session, spec=spec)["roundtrip.output_state"].sent


def test_a_dry_run_still_enforces_the_guard():
    session, _, spec = make_session(cls=MisbehavingInstrument, dry_run=True)
    result = run_all(session, MisbehavingInstrument, spec)["read.get_sneaky"]
    assert result.status is Status.FAILED and "GUARD" in result.detail


def test_policy_ranks_hazards():
    read_only, reversible, hazardous = Policy(), Policy(REVERSIBLE), Policy(HAZARDOUS)
    assert read_only.allows(Hazard.READ_ONLY) and not read_only.allows(REVERSIBLE)
    assert reversible.allows(REVERSIBLE) and not reversible.allows(HAZARDOUS)
    assert hazardous.allows(Hazard.READ_ONLY) and hazardous.allows(HAZARDOUS)
    assert not hazardous.allows(
        HAZARDOUS, Hazard.READ_ONLY
    )  # the instrument's own limit
    assert not hazardous.allows(HAZARDOUS, REVERSIBLE)
