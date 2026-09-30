# Verify a driver on real hardware

<p class="pa-meta" markdown="span">About 20 minutes · Needs [Getting Started](../getting_started/python_api.md), and for the last three steps [Write a hardware instrument](hardware_instrument.md). An instrument connected, or read along</p>

A driver can be wrong about its instrument: a command spelt otherwise in the manual, a reply taken apart wrongly, a firmware that answers differently. A mock can't tell you, since it answers what the driver expects. PyAcquisition's **verification tool** checks a driver against the instrument itself, before you trust it with a measurement. It asks the instrument what it is, calls every query, and, only if you allow it, sets each setting and puts it back. In this tutorial you check Getting Started's lock-in, an SR830, and then the Keithley 2400 driver you wrote.

You write `hardware.toml` and `check.py` in your `my-lab` project, and run them in the terminal. The outputs here were made with a `mock` that answers as the instruments do, since none was connected: with yours connected, they are your instruments' own. Most drivers' checks were written from their manuals, and some haven't yet been run on the instrument: yours may be the first run.

<div class="gs" data-files="hardware.toml:versions check.py:versions keithley_2400.toml:versions" data-lines="14" data-term-lines="10" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-new-file markdown>

## List what is connected

```toml title="hardware.toml"
--8<-- "examples/usage/verify_driver/hardware_1.toml"
```

`hardware.toml` lists the instruments to check, in the same form as a config file's `[instruments]`, so each is opened as it would be in a run: here the SR830 at GPIB address 8. Every hardware driver that comes with PyAcquisition has a **spec** beside it, which says what may be checked on its instrument, and how. So a line like this is all a driver needs to be checked.

**More:** [the `[instruments]` table](../reference/config_file.md#instruments), and [the inventory](../reference/verification_specs.md#the-inventory).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## See what would be checked

```bash
uv run python -m pyacquisition.verify hardware.toml --dry-run
```

```text
DRY RUN: no instrument was contacted, results are not evidence

lockin (SR_830)  MOCK,GPIB0::8::INSTR,0,0
  skip  read-only  identity  -- dry run: the reply is not compared
          > *IDN?
  skip  reversible safe_state  -- reversible checks are not enabled: run with --reversible
  dry   read-only  read.get_display_buffer_length
          > SPTS?
  ...
```

Always start with a dry run. It contacts nothing, since a stand-in answers in the instrument's place: the `MOCK` in its first line. It lists each check, with the messages it would send: `*IDN?` to ask what the instrument is, then each of the driver's queries. Each check has a **hazard**. A `read-only` check only asks, and one that changes a setting is skipped unless you allow it. `--list` lists the checks alone, and `--only lockin` checks one instrument of several.

**More:** [the tool's options](../reference/command_line.md#python-m-pyacquisitionverify).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Run the read-only checks

```bash
uv run python -m pyacquisition.verify hardware.toml
```

```text
lockin (SR_830)  Stanford_Research_Systems,SR830,s/n12345,ver1.07
  pass  read-only  identity
  pass  read-only  read.get_display_buffer_length
  ...
  skip  hazardous  roundtrip.reference_amplitude  -- hazardous checks are not enabled: run with --hazardous
  not covered (3): clear, reset, reset_data_buffer

summary: 26 passed, 16 skipped
```

Now the instrument is asked. Its answer to `*IDN?` must name an SR830, or nothing more is sent to it. Then each query is called, and passes if it answers what it promises: a number, one of its choices, or a value within range. `not covered` lists the driver's methods that no check tried. Nothing on the instrument changes, so this is safe with a sample connected.

**More:** [what a spec can ask of a query](../reference/verification_specs.md#readgetter).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Allow checks that change settings

```toml title="hardware.toml"
--8<-- "examples/usage/verify_driver/hardware_2.toml"
```

```bash
uv run python -m pyacquisition.verify hardware.toml --reversible
```

```text
lockin (SR_830)  Stanford_Research_Systems,SR830,s/n12345,ver1.07
  pass  read-only  identity
  pass  reversible safe_state
  ...
  pass  reversible roundtrip.frequency
  skip  hazardous  roundtrip.reference_amplitude  -- this instrument is limited to reversible checks by the inventory
  not covered (3): clear, reset, reset_data_buffer

summary: 41 passed, 1 skipped
```

`--reversible` also sets each setting the spec lists, reads it back, and puts back what it was. Before and after each, the instrument is put in its **safe state**, such as a current source's output off. A lock-in has none. The SR830's excitation amplitude drives the sample, so it is `hazardous`. `max_hazard` caps what this instrument is ever asked, whatever the command says. Disconnect the sample regardless: the sensitivity steps through every range, and a live signal overloads.

**More:** [hazards](../reference/verification_specs.md#hazards), and [the safe state](../reference/verification_specs.md#safe_state).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Keep the report

```bash
uv run python -m pyacquisition.verify hardware.toml --reversible --json report.json
```

Each line of the report is a check, `pass`, `FAIL` or `skip`, with its hazard, and after `--`, why it failed or was skipped. `--json` also writes it to `report.json`, with the instrument's identification (firmware and all), each check's messages and replies, and the methods no check covered. Keep it with your data, as a record of what was checked, on which instrument, and when. If a check fails, the tool ends with an error, for a script to notice.

**More:** [the tool's options](../reference/command_line.md#python-m-pyacquisitionverify).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Record a run, to replay without the instrument

```toml title="hardware.toml"
--8<-- "examples/usage/verify_driver/hardware_3.toml"
```

`record` writes every message to and from the instrument to `recordings/lockin.jsonl`, one a line. The `mock` adapter answers from it, in the order it was recorded: with `adapter = "mock"` and `args = { transcript = "recordings/lockin.jsonl" }`, the checks run again with no instrument, and the replies the real one gave. So a change to the driver can be checked on any PC, or in a test, against what the instrument really said.

**More:** [the `record` adapter](../reference/adapters.md#record), and [`mock`'s `transcript`](../reference/adapters.md#mock).
{ .gs-more }

</section>

<section class="gs-step" data-new-file="check.py" markdown>

## Check a driver of your own

```python title="check.py"
--8<-- "examples/usage/verify_driver/check_1.py"
```

```bash
uv run check.py
```

```text
smu (Keithley_2400)
  skip  read-only  identity  -- the spec declares no [identity] to compare with
  pass  read-only  read.get_current
  pass  read-only  read.get_voltage
  not covered (3): set_output, set_terminals, set_voltage

summary: 2 passed, 1 skipped
```

`hardware.toml` takes only the drivers that come with PyAcquisition. Your own, such as the 2400's from [Write a hardware instrument](hardware_instrument.md), is checked from Python: an `Entry` is what a table of `hardware.toml` would be. With no spec, each method named `get_...` is checked, and nothing is written. A mistake fails, such as `FAIL  read-only  read.get_current  -- IndexError: list index out of range`: a 2400 set to answer `:READ?` with one number, not five.

**More:** [checking from Python](../reference/verification_specs.md#from-python).
{ .gs-more }

</section>

<section class="gs-step" data-new-file="keithley_2400.toml" markdown>

## Write a spec for your driver

```toml title="keithley_2400.toml"
--8<-- "examples/usage/verify_driver/keithley_2400_1.toml"
```

A spec beside the driver, with its name, says what may be written. `[identity]` is what the answer to `*IDN?` must contain, since nothing is written to an instrument until it has shown what it is. `[safe_state]` turns the output off, before and after each check that writes. `[roundtrip.voltage]` sets the voltage to 0 V and then 0.5 V, reads each back, and puts back what it was. It is `reversible`, since the output is off while it runs.

**More:** [every key of a spec](../reference/verification_specs.md#the-spec).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Allow the round trip

```python title="check.py" hl_lines="2 11"
--8<-- "examples/usage/verify_driver/check_2.py"
```

```bash
uv run check.py
```

```text
smu (Keithley_2400)  KEITHLEY INSTRUMENTS INC.,MODEL 2400,1234567,C32
  pass  read-only  identity
  pass  reversible safe_state
  pass  read-only  read.get_current
  pass  read-only  read.get_voltage
  pass  reversible roundtrip.voltage
  not covered (1): set_terminals

summary: 5 passed
```

`Hazard.REVERSIBLE` allows reversible checks, as `--reversible` does. Now the 2400 is asked what it is, its output turned off, and its voltage set, read back and put back, with the output off throughout. `set_terminals` is still not covered: with no query to read the terminals back, no check can confirm the setting took. That is a reason to give each setting a query, when the instrument has one.

**More:** [what keeps a run safe](../reference/verification_specs.md#what-keeps-a-run-safe).
{ .gs-more }

</section>

</div>

</div>

</div>

!!! success "Checkpoint"
    The dry run lists the checks, and contacts nothing. The read-only run passes `identity` and each query, and the reversible run each round trip, with the excitation amplitude left alone. `report.json` and `recordings/lockin.jsonl` are in `my-lab`. `check.py` passes the 2400's identity and its voltage round trip, and both instruments are as they were.

??? failure "Something not working?"
    - **Every check says `not reachable: Could not open 'GPIB0::8::INSTR' with the pyvisa adapter`.** The instrument isn't at that address, or there is no VISA library: see [Connect a real instrument](connect_instrument.md).
    - **`identity` fails with `the instrument answered '...', which lacks ['2400']: is this the right device?`, and every other check says `the identity check failed: this device is not talked to`.** Another instrument is at that address. Check it, on the instrument's front panel.
    - **`error: hardware.toml [instruments.smu]: unknown instrument 'Keithley_2400'`.** A driver of your own can't go in `hardware.toml`. Check it from Python, as `check.py` does.
    - **A round trip fails with `wrote 0.5, read back 0.0`.** The setting didn't take, or the query reads something else. Try the command on the instrument's front panel, or in its manual, and fix the driver.
    - **Checks that write say `the identity was not verified: nothing is written to a device that has not shown what it is`.** The spec has no `[identity]`. Add one: the words of the instrument's answer to `*IDN?`.
    - **`SpecError: keithley_2400.toml [roundtrip.voltage]: 'hazard' is required ('reversible' or 'hazardous'), so that every write is tagged deliberately`.** Every round trip says how hazardous it is. The spec's mistakes are found before anything is sent.
    - **A check is skipped for its hazard.** `--reversible` allows reversible checks, `--hazardous` hazardous ones too, and `max_hazard` caps an instrument whatever the command says.

## What you learned

- `hardware.toml` lists the instruments to check, in a config file's `[instruments]` form. A dry run contacts nothing, and lists every message a run would send.
- Checks only read unless `--reversible` or `--hazardous` allows more, and `max_hazard` caps an instrument for good. Every setting changed is put back, with the instrument in its safe state before and after.
- `--json` keeps the report, and `record` the traffic, for `mock` to replay.
- A driver of your own is checked from Python with `Entry` and `verify`. A spec beside it, with an `[identity]` and a `[safe_state]`, lets its round trips run.

Next: [Verification specs](../reference/verification_specs.md), for every key of a spec, and what keeps a run safe.
