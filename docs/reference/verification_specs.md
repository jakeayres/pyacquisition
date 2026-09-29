# Verification specs

The two files the verification tool reads: the **inventory** of the instruments connected, and each driver's **spec**, which says what may be checked. [Verifying instruments on real hardware](../dev/verifying_hardware.md) runs them, with [`python -m pyacquisition.verify`](command_line.md#python-m-pyacquisitionverify).

Both are checked when they are loaded, and a misspelt key is an error, never a silent default.

## Hazards

Every check has a hazard, and a run does only what it allows.

| Hazard | Meaning | Run with |
|---|---|---|
| `read-only` | Only asks questions. | Always |
| `reversible` | Changes a setting, and puts it back. | `--reversible` |
| `hazardous` | Can act on the outside world: outputs, heaters, excitation. | `--hazardous` |

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

A TOML file beside the driver, with the same name: `keithley_6221.py` has `keithley_6221.toml`. Nothing a spec doesn't list is ever written.

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
