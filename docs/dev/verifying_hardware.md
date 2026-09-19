# Verifying instruments on real hardware

The unit tests run every instrument class against a mock. That proves the code is self-consistent, not that a real instrument understands it. The verification engine checks an instrument class against the physical device, and is built so that **it cannot do harm by accident**.

## What it checks

| Level | Check | Changes the instrument? |
|---|---|---|
| 0 | **Identity.** `*IDN?` contains the words the spec expects | No |
| 1 | **Read smoke.** Every `get_...` method runs and returns what it promises (type, enum member, range) | No |
| 2 | **Round trip.** `set_x(v)`, then `get_x()` must return `v`, then the original value is put back | Yes, and restores |

Levels 0 and 1 are found by introspection, so a new getter is checked without writing anything. Level 2 only runs for the pairs a spec declares.

## Running it

Copy [`tests/hardware/hardware.example.toml`](https://github.com/jakeayres/pyacquisition/blob/main/tests/hardware/hardware.example.toml) to `hardware.toml` (it is git-ignored) and list what is connected. It reuses the `[instruments]` format of an experiment config, so an instrument is opened exactly as in a real run, adapter included.

```toml
[instruments.k6221]
instrument = "Keithley_6221"
adapter = "pyvisa"
resource = "GPIB0::12::INSTR"
args = { read_termination = "\n" }

[instruments.k6221.verify]
capabilities = ["nanovoltmeter"]   # what is attached, for checks that need it
max_hazard = "reversible"          # this instrument is never asked for more
skip = ["set_wave_function"]       # methods to leave alone here
record = "recordings/k6221.jsonl"  # log the traffic, for replay in CI
```

Always start with a dry run. It contacts nothing and prints every command a run would send:

```bash
python -m pyacquisition.verify hardware.toml --dry-run --hazardous
```

Then, from least to most:

```bash
pytest tests/hardware --hardware hardware.toml               # read-only checks
pytest tests/hardware --hardware hardware.toml --reversible  # also change settings and restore
pytest tests/hardware --hardware hardware.toml --hazardous   # also run hazardous checks
```

The same runs are available without pytest as `python -m pyacquisition.verify hardware.toml [--reversible|--hazardous] [--json report.json] [--only NAME] [-v]`, and `--list` prints the plan and stops. Set `PYACQ_HARDWARE` to avoid repeating the path.

Without `--hardware` every hardware test is **skipped**, so a plain `pytest` and CI never touch an instrument. An instrument that cannot be opened skips its own tests. `-m "not hardware"` leaves them out altogether.

## Safety

Every check carries a hazard, and a run only performs what it allows:

| Hazard | Meaning | Enabled by |
|---|---|---|
| `read-only` | Only asks questions | Always |
| `reversible` | Changes a setting and puts it back | `--reversible` |
| `hazardous` | Can act on the outside world: outputs, heaters, excitation | `--hazardous` |

There are seven layers between a check and the device. Each one is covered by a test that fails if the rule is removed.

1. **The run.** Nothing beyond read-only unless asked for. `--hazardous` includes `--reversible`.
2. **The instrument.** `max_hazard` in the inventory caps one instrument whatever the run allows. Pin a magnet supply to `"read-only"` and it stays there.
3. **The spec.** Only the round trips a spec lists can ever write, and every one must state its `hazard`. There is no default.
4. **Identity.** A device that fails its identity check is not talked to again. Nothing is written to a device whose identity has not been *verified*, so a spec that writes must declare an `[identity]`.
5. **The safe state.** A spec must declare a `[safe_state]` before anything can be written. It is entered and verified **before** each write check, **after** it whatever happened, and once more when the run ends, even on an error or Ctrl-C. If it cannot be confirmed, every later check that writes is refused.
6. **Preconditions.** A round trip can require a condition, such as the Keithley output being off, and is skipped if it does not hold.
7. **The guard.** Between every instrument and its resource sits a guard that only lets *reads* through. Writes pass only inside a window that a permitted check opens, and only for the check's own calls. So even a getter that secretly writes is stopped, and reported.

Every restore is verified as well: a round trip reports `RESTORE FAILED` if the original value did not come back. A setting can only be round-tripped if what the getter returns can be given back to the setter.

### The decorator is not trusted

`Mercury_IPS` registers its `set_target_field`, `to_setpoint`, `switch_heater_on` and other *actions* as queries, and its protocol has no `?` to tell reads from writes. So the engine never decides what to run from `@mark_query`. It reads only methods **named** `get_...`, and each spec declares the reads of its own protocol for the guard:

```toml
[guard]
read = ['^R\d+$', '^X$']
```

Only messages matching those patterns (or containing `?`) can reach the magnet supply. Anything else is refused and reported. Methods that are registered but never exercised, and setters registered as queries, are listed at the end of each report so you can see the gaps.

## Writing a spec

The spec for `keithley_6221.py` is `keithley_6221.toml`, in the same folder. A spec is validated against its class when it is loaded, and **a typo is an error, not a silent default**. The full format is described in `pyacquisition/verify/spec.py`. The shape is:

```toml
[identity]                       # *IDN? must contain all of these (any case)
contains = ["KEITHLEY", "6221"]

[safe_state]                     # required before anything can be written
steps = [{ call = "set_output_state", args = { state = "OFF" } }]
verify = [{ call = "get_output_state", equals = "OFF" }]

[read.get_buffer_selected]       # only for getters that need help
args = [{ start = 1, count = 1 }]
requires = ["nanovoltmeter"]     # skipped unless the inventory lists it
# skip = "why it is not run"     # or leave one out, with the reason
# range = [0, 500]               # the reading must lie in this range

[roundtrip.current]              # set_current / get_current, unless named
hazard = "reversible"            # required: "reversible" or "hazardous"
values = [1e-9, -1e-9]           # or "*" for every member of an enum
select = { line = ["TOP", "BOTTOM"] }   # other arguments, in every combination
rel = 1e-3                       # how closely the readback must match
abs = 1e-12
preconditions = [{ call = "get_output_state", equals = "OFF" }]
note = "why, for whoever reads this next"
```

Enum arguments and values are written by member name (`"OFF"`, `"SINUSOID"`). A getter whose parameters are not enums is skipped, visibly, until the spec supplies its `args`. A spec with no `[safe_state]` can be read but never written.

The specs that ship were written from the classes and the manuals and have not been run against real instruments. Expect to adjust values and tolerances the first time each is on the bench, and treat every `hazard` as a claim to review.

## Recording for CI

Hardware runs cannot happen in CI, but their traffic can. With `record` set (or `adapter = "record"` in any config), every command and reply is written to a JSON-lines transcript. Replay it through the mock, and CI checks the driver against what the instrument *really* said:

```toml
[instruments.k]
instrument = "Keithley_6221"
adapter = "mock"
resource = "anything"
args = { transcript = "recordings/k6221.jsonl" }
```

Replies come back in the order they were recorded. Explicit `responses` still win.

## Reading a report

```
k6221 (Keithley_6221)  KEITHLEY INSTRUMENTS INC.,MODEL 6221,1,D03
  pass  read-only  identity
  pass  read-only  read.get_current
  skip  read-only  read.get_fresh_reading  -- can only be read once, ...
  FAIL  reversible roundtrip.current  -- wrote 1e-09, read back 0.0
  skip  hazardous  roundtrip.output_state  -- hazardous checks are not enabled: run with --hazardous
  not covered (29): abort_sweep, arm_delta, ...
summary: 148 pass, 1 FAIL, 90 skip
```

`dry` in place of `pass` means a dry run: the commands are listed and no result is evidence. Write the report to JSON with `--json` (or `--hardware-report` under pytest) to keep a record of firmware, date and result per instrument.
