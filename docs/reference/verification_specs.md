# Verification specs

The two files the verification tool reads: the **inventory** of the instruments connected, and each driver's **spec**, which says what may be checked. [Verify a driver on real hardware](../usage/verify_driver.md) runs them, with [`python -m pyacquisition.verify`](command_line.md#python-m-pyacquisitionverify).

Both are checked when they are loaded, and a misspelt key is an error, never a silent default.

## Hazards

Every check has a hazard, and a run does only what it allows.

| Hazard | Meaning | Run with |
|---|---|---|
| `read-only` | Only asks questions. | Always |
| `reversible` | Changes a setting, and puts it back. | `--reversible` |
| `hazardous` | Can act on the outside world: outputs, heaters, excitation. | `--hazardous` |

## What keeps a run safe

Each of these rules stands between a check and the instrument, and each has a test that fails if it is removed.

1. **The run.** Nothing beyond read-only, unless the run asks for it. `--hazardous` includes `--reversible`.
2. **The instrument.** `max_hazard` in the inventory caps one instrument, whatever the run allows.
3. **The spec.** Only the round trips a spec lists can ever write, and each must give its `hazard`: there is no default.
4. **The identity.** A device whose identity check fails isn't talked to again, and nothing is written to one whose identity wasn't confirmed. So a spec that writes needs an `[identity]`.
5. **The safe state.** Nothing is written without a `[safe_state]`. It is entered before each check that writes, after it whatever happened, and once more when the run ends, even on an error or Ctrl-C. If it can't be confirmed, every later check that writes is refused.
6. **Preconditions.** A round trip can require a condition, such as an output being off, and is skipped if it doesn't hold.
7. **The guard.** Between the driver and the instrument, only reads get through: messages with a `?`, or that match the spec's `[guard]`. A write gets through only during a check that may write. A getter that writes is stopped, and reported.

A driver's decorators aren't trusted to say what a method does: `Mercury_IPS` once registered actions such as `set_target_field` as queries, and its protocol has no `?` to tell a read from a write. Only methods **named** `get_...` are read, and a setter registered as a query is listed at the end of the report.

## The inventory

A TOML file, such as `hardware.toml`, in the form of a config file's [`[instruments]`](config_file.md#instruments), with a `verify` table for each instrument. `tests/hardware/hardware.example.toml` is one to copy.

```toml
[instruments.k6221]
instrument = "Keithley_6221"
adapter = "pyvisa"
resource = "GPIB0::12::INSTR"
args = { read_termination = "\n" }

[instruments.k6221.verify]
capabilities = []
max_hazard = "reversible"
record = "recordings/k6221.jsonl"
```

| Key of `verify` | Meaning |
|---|---|
| `capabilities` | What is attached, for checks that need it, such as `"nanovoltmeter"`. |
| `max_hazard` | The most this instrument is ever asked, whatever the run allows. `"read-only"` pins it for good. |
| `skip` | Methods to leave alone on this instrument. |
| `record` | A file to record every command and reply to, for the `mock` adapter to replay (see [`record`](adapters.md#record)). |

## The spec

A TOML file beside the driver, with the same name: `keithley_6221.py` has `keithley_6221.toml`. Nothing a spec doesn't list is ever written. A driver with no spec has its getters checked, and nothing written.

The specs that come with PyAcquisition were written from the drivers and the manuals, and most haven't yet been run on the instrument. Expect to adjust values and tolerances the first time one is, and read each `hazard` as a claim to review.

```toml
[identity]
contains = ["KEITHLEY", "6221"]

[guard]
read = ['^R\d+$']

[safe_state]
steps = [{ call = "set_output_state", args = { state = "OFF" } }]
verify = [{ call = "get_output_state", equals = "OFF" }]

[read.get_buffer_selected]
args = [{ start = 1, count = 1 }]
requires = ["nanovoltmeter"]

[roundtrip.current]
hazard = "reversible"
values = [1e-9, -1e-9]
rel = 1e-3
abs = 1e-12
preconditions = [{ call = "get_output_state", equals = "OFF" }]
```

### `[identity]`

| Key | Meaning |
|---|---|
| `contains` | Text that `*IDN?`'s answer must contain, all of it, in any case. A spec that writes needs it: nothing is written to a device whose identity isn't confirmed. |

### `[guard]`

| Key | Meaning |
|---|---|
| `read` | Patterns (regular expressions) of the messages that are reads, besides those with a `?`. Only these reach the instrument outside a check that is allowed to write. |

### `[safe_state]`

Required before anything can be written. It is entered and confirmed before each check that writes, after it whatever happened, and once more when the run ends.

| Key | Meaning |
|---|---|
| `steps` | Calls that put the instrument in its safe state: `{ call = "<method>", args = {...} }`. |
| `verify` | Calls that confirm it: `{ call = "<method>", args = {...}, equals = <value> }`. |

### `[read.<getter>]`

For a getter (a method named `get_...`) that needs help to run. A getter with no table is run with every combination of the choices and true-or-false values it takes, or with none if it takes none. One that takes any other argument is skipped, and says so, until its table gives `args`. So is one with too many combinations to try.

| Key | Meaning |
|---|---|
| `args` | A list of argument sets to call it with. |
| `requires` | Capabilities the inventory must list, or the check is skipped. |
| `range` | `[low, high]`: the reading must lie between them. |
| `skip` | Leave it out, and say why. |
| `hazard` | The read's hazard, if it isn't `read-only`. |
| `note` | Why, for whoever reads the spec next. |

### `[roundtrip.<name>]`

A setting written with a setter, read back with a getter, and put back as it was.

| Key | Meaning |
|---|---|
| `hazard` | `"reversible"` or `"hazardous"`. Required. |
| `values` | The values to write in turn, or `"*"` for every member of the setter's choice. |
| `setter`, `getter` | The methods, if they aren't `set_<name>` and `get_<name>`. |
| `param` | The setter's argument that takes the value. By default, its last. |
| `select` | The setter's other arguments, as lists of values, tried in every combination. |
| `rel`, `abs` | How closely the value read back must match: relative, and absolute. |
| `requires` | Capabilities the inventory must list, or the check is skipped. |
| `preconditions` | Calls with `equals` that must hold, or the check is skipped. |
| `note` | Why, for whoever reads the spec next. |

Choices are written by their members' names: `"OFF"`, `"SINUSOID"`.

A round trip fails with `wrote <value>, read back <value>` if the setting didn't take, and with `RESTORE FAILED: was <value>, now <value>` if the value it found didn't come back. A setting can only be round-tripped if what its getter answers can be given back to its setter.

## From Python

The inventory takes only the drivers that come with PyAcquisition. Any driver, your own included, is checked from `pyacquisition.verify`, with its spec, if it has one, found beside it.

```python
from keithley_2400 import Keithley_2400
from pyacquisition.verify import Entry, Hazard, Policy, verify

smu = Entry(name="smu", cls=Keithley_2400, adapter="pyvisa", resource="GPIB0::24::INSTR")
report = verify([smu], Policy(Hazard.REVERSIBLE))
print(report.text())
```

| Name | Meaning |
|---|---|
| `Entry(name, cls, adapter, resource, args={}, capabilities=(), max_hazard=None, skip=(), record=None)` | One instrument, as a table of the inventory would give it, with its class in place of its name. |
| `load_inventory(path)` | An inventory file's entries. |
| `Policy(max_hazard=Hazard.READ_ONLY)` | What the run may do: `Hazard.READ_ONLY`, `Hazard.REVERSIBLE` or `Hazard.HAZARDOUS`. |
| `verify(entries, policy, *, dry_run=False)` | Runs every check on each instrument, puts each one written to back in its safe state, closes them, and answers a `Report`. |
| `Report.text(verbose=False)` | The report as the tool prints it. `verbose` adds the messages sent. |
| `Report.to_dict()` | The report as `--json` writes it. |
| `Report.ok` | True if no check failed. |

## In PyAcquisition's tests

PyAcquisition's own repository runs the same checks under pytest, from `tests/hardware`, with `tests/hardware/hardware.example.toml` as an inventory to copy. Without `--hardware`, every hardware test is skipped, so a plain `pytest` never touches an instrument.

```bash
pytest tests/hardware --hardware hardware.toml               # read-only checks
pytest tests/hardware --hardware hardware.toml --reversible  # also change settings and put them back
pytest tests/hardware --hardware hardware.toml --hazardous   # also run hazardous checks
```

`PYACQ_HARDWARE` gives the inventory in place of `--hardware`, `--dry-run` contacts nothing, `--hardware-report report.json` writes the report, and `-m "not hardware"` leaves the hardware tests out altogether.
