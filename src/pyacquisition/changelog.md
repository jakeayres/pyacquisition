# Changelog

What changed in each version of PyAcquisition, newest first. The interface
shows a version's **Highlights** once, after you upgrade to it.

## 0.5.0 (2026-10-21)

### Highlights

- PyAcquisition is now under the Mozilla Public License 2.0 (MPL-2.0), instead
  of the GPL. Your own experiments, scripts and drivers can be under any
  license you choose, and changes to PyAcquisition's own files stay open. The
  examples in the documentation are public domain (CC0).
- **About PyAcquisition**, in the command palette or on the name in the top
  bar, shows the version you are running, its license and where its source is.
- An app made with `pyacquisition build` has a `NOTICE.txt` beside it, which
  says what the app contains and under which licenses.
- `TextFile` reads numbers from a file that other software writes, such as a
  magnet's field: the first or last number, the number after a label, a JSON
  value, a CSV column, or a regular expression's match. A software instrument
  can now take options in a config file, and the setup page has fields for
  them.
- The documentation's front page runs the interface itself, live, beside the
  script that makes it, and Getting Started shows what each step makes as you
  read it.

## 0.4.0 (2026-10-10)

### Highlights

- The interface tells you what's new after an upgrade, when a newer version is
  out, and about any serious fix your version needs. Turn it off with the
  environment variable `PYACQUISITION_NEWS=off`.
- The Lakeshore 340 and 350 drivers have every command in their manuals.
- A `PIDController` instrument changes a running PID's setpoint and gains from
  the interface, and the PID task can ramp its setpoint.
- A config file is checked for problems before it runs, and each one is named.
- When an instrument's query or command fails, the interface says why.
- New documentation: Getting Started, a Usage tutorial for each task, and a
  Reference.

### Breaking changes

- PyAcquisition's license is now the GNU General Public License, version 3
  (GPL-3.0-only). Anything you give others that includes it, such as an app
  made with `pyacquisition build`, must be under the GPL too. Versions up to
  0.3.4 stay under the MIT License.
- `pyacquisition.tasks.PIDController` is now `PIDCalculation`. The name
  `PIDController` is the new instrument. `PID` has a new input, `ramp_rate`,
  after `period`, so inputs given by position after it move along.
- A config file that 0.3.2 ran may now be refused: unknown keys in an
  instrument or measurement, a `timeout` with a decimal point, `adapter`,
  `resource` or `args` on a software instrument, entries that used to be
  skipped with a warning, and a measurement's `args` that its query doesn't
  take. Options given to `from_config` no longer stand in for a bad value in
  the file.
- An instrument's `name` defaults to its class's name, which `identify` and
  `/rack/list_instruments` show.
- Lakeshore 340 and 350: `get_display_setup` and `set_display_setup` are
  replaced by `get_display` and `set_display`. `get_curve_header` and
  `get_curve_point` return dictionaries. `set_curve_header` takes enums. The
  350's `get_alarm` needs an `input_channel`, and `get_analog_output` an
  `output`. The enums `DisplayContrastLevel`, `DisplayCustomNumerber` and
  `DisplayAllInputsSize` are gone.

## 0.3.4 (2026-10-09)

### Highlights

- Two new tasks wait on a measurement: `WaitForValue`, until it goes below or
  above a value, and `WaitForStable`, until it has settled in a band, without
  drifting, for as long as you ask.

## 0.3.3 (2026-10-08)

### Highlights

- The window no longer closes, stopping the experiment, while an instrument is
  slow to answer.
