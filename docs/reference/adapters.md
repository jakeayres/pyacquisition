# Adapters

How a hardware instrument reaches its device, the address each expects, and the options each takes. [Connect a real instrument](../usage/connect_instrument.md) shows them in use.

An adapter is named in a [config file](config_file.md#instruments) with `adapter`, and its options go in `args`:

```toml
[instruments.lockin]
instrument = "SR_830"
adapter = "pyvisa"
resource = "GPIB0::8::INSTR"
args = { timeout = 10000 }
```

In Python, the address comes after the instrument's name, and the adapter and options are keyword arguments:

```python
lockin = SR_830("lockin", "GPIB0::8::INSTR", adapter="pyvisa", timeout=10000)
```

| Adapter | For | Address |
|---|---|---|
| [`pyvisa`](#pyvisa) | GPIB, USB, serial and Ethernet instruments, through a VISA library. The default in Python. | `GPIB0::8::INSTR` |
| [`prologix`](#prologix) | GPIB instruments behind a Prologix GPIB-USB controller | `COM3::8` |
| [`mock`](#mock) | Running a driver with no device | anything |
| [`record`](#record) | Recording the traffic with a real device, to replay with `mock` | as its inner adapter's |

## `pyvisa`

Talks to the instrument through [PyVISA](https://pyvisa.readthedocs.io/). GPIB needs a VISA library, such as NI-VISA (see [installing a VISA library](../getting_started/installation.md#before-you-connect-real-instruments)).

| Option | Meaning | Default |
|---|---|---|
| `timeout` | The longest wait for a reply, in milliseconds. | `5000` |
| `read_termination` | What the instrument sends at the end of a reply, such as `"\n"`. | PyVISA's |
| `write_termination` | What is sent at the end of each message. | PyVISA's |

Any other option is passed on to PyVISA's `open_resource`. To find an address, list what PyVISA can see: `pyvisa.ResourceManager().list_resources()`.

## `prologix`

For GPIB instruments behind a [Prologix GPIB-USB controller](https://prologix.biz), which shows up as a virtual serial port. It gives an instrument the same interface as `pyvisa` does over GPIB, so a driver works the same over either.

The address is `<serial port>::<GPIB address>`, with a secondary address after it if there is one: `COM3::12`, `/dev/ttyUSB0::12` or `COM3::9::0`. A trailing `::INSTR` is accepted. It takes the same options as `pyvisa`.

- **Several instruments share one controller.** Give each its own GPIB address on the same port. The port is opened once, and instruments used from different threads can't mix up their replies.
- **A reply ends on EOI**, as over GPIB. An instrument that doesn't assert EOI needs `read_termination`, such as `"\n"`.
- **The controller waits at most 3 s for a reply.** A longer `timeout` still works, by asking again until it runs out.
- **The controller's settings are managed for you.** Saving them to its EEPROM is turned off, so switching between instruments doesn't wear it out.

## `mock`

Runs a driver with no device connected, to try a config, develop a task, or test away from the lab. Any address is accepted. It has no model of the instrument, and answers each query with the first of:

1. a reply given in `responses`;
2. the value last written, so that after `set_current(1e-3)`, `get_current()` answers `1e-3`;
3. the default reply, `"0"`, so that a query never set still answers a number.

| Option | Meaning | Default |
|---|---|---|
| `responses` | Replies to give, by query. A key is a whole query (`"KRDG? A"`) or its header (`"KRDG?"`), and the whole query wins. A list of replies is given in turn, holding on the last. | none |
| `default_reply` | The reply to a query with no other answer. | `"0"` |
| `transcript` | A file written by the [`record`](#record) adapter, whose replies are given in the order they were recorded. `responses` still win. | none |

```toml
[instruments.temperature]
instrument = "Lakeshore_350"
adapter = "mock"
resource = "mock"
args = { responses = { "KRDG? A" = ["4.20", "4.21", "4.19"] } }
```

## `record`

Records every message to and from a real instrument, one JSON object a line, for the `mock` adapter to replay later, in tests, say.

| Option | Meaning | Default |
|---|---|---|
| `transcript` | The file the traffic is added to. Required. | none |
| `inner` | The adapter that talks to the instrument. | `"pyvisa"` |

Any other option goes to the inner adapter.

```toml
[instruments.k]
instrument = "Keithley_6221"
adapter = "record"
resource = "GPIB0::12::INSTR"
args = { inner = "pyvisa", transcript = "recordings/k6221.jsonl" }
```
