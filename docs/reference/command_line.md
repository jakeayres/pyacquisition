# Command line

The `pyacquisition` command, and the verification tool. In a uv project, start each with `uv run`: `uv run pyacquisition run --toml rig.toml`. `--help` after any command lists its options.

| Command | Does |
|---|---|
| [`pyacquisition run`](#pyacquisition-run) | Runs an experiment from a config file or a Python script. |
| [`pyacquisition new`](#pyacquisition-new) | Builds or changes a config file in a window, and runs it from there. |
| [`pyacquisition build`](#pyacquisition-build) | Freezes an experiment into a standalone application. |
| [`python -m pyacquisition.verify`](#python-m-pyacquisitionverify) | Checks instrument drivers against the instruments connected. |

## `pyacquisition run`

```text
pyacquisition run (--toml TOML | --py PY)
```

| Option | Meaning |
|---|---|
| `--toml TOML` | The config file to run. |
| `--py PY` | The Python script to run. The `Experiment` subclass in it is made and run (the first by name, if there are several), so the script needs no `if __name__ == "__main__":` block. The script must be self-contained: modules beside it can't be imported. |

Give one of `--toml` and `--py`. `pyacquisition --toml rig.toml`, without `run`, does the same. A config file with mistakes stops the command with the list of them (see [Mistakes in the file](config_file.md#mistakes-in-the-file)).

## `pyacquisition new`

```text
pyacquisition new [--port PORT] config
```

| Option | Meaning |
|---|---|
| `config` | The config file to build or change. A file that doesn't exist yet is made when it is first saved. It must end `.toml`, and its folder must exist. |
| `--port PORT` | The port for the setup page, and for the experiment it runs. By default, the file's own, or 8000. |

See [Build a config in the interface](../usage/setup_page.md).

## `pyacquisition build`

```text
pyacquisition build (--toml TOML | --py PY) [--name NAME] [--onedir] [--console] [--icon ICON]
```

| Option | Meaning |
|---|---|
| `--toml TOML` | Build from a config file. The app reads `config.toml` beside itself, which can be changed without building again. |
| `--py PY` | Build from a Python script. |
| `--name NAME` | The application's name. By default, the file's own name. |
| `--onedir` | Build a folder instead of a single executable. It starts faster, but is a folder rather than one file to hand over. |
| `--console` | Keep the console window, to see the errors of an app that misbehaves. |
| `--icon ICON` | An `.ico` file for the application's icon. |

It needs PyInstaller, which comes with the build extra: `uv add "pyacquisition[build]"`. The app is written to `dist/`. On the PC it runs on, the window needs the Microsoft Edge WebView2 Runtime, which Windows 11 has.

See [Build a standalone app](../usage/standalone_app.md).

## `python -m pyacquisition.verify`

```text
python -m pyacquisition.verify [--reversible] [--hazardous] [--dry-run] [--list] [--only NAME [NAME ...]] [--json PATH] [-v] inventory
```

| Option | Meaning |
|---|---|
| `inventory` | The hardware inventory: a TOML file listing the instruments connected. |
| `--reversible` | Also run checks that change a setting and put it back. |
| `--hazardous` | Also run hazardous checks (outputs, heaters, excitation). Includes `--reversible`. |
| `--dry-run` | Contact nothing, and print the commands that would be sent. |
| `--list` | Print the plan, and stop. |
| `--only NAME [NAME ...]` | Only these instruments. |
| `--json PATH` | Also write the report as JSON. |
| `-v`, `--verbose` | Show the commands sent. |

Without `--reversible` or `--hazardous`, only read-only checks run. Each driver's checks come from its [verification spec](verification_specs.md). It ends with `0` if no check failed, `1` if one did, and `2` if the inventory can't be read.

See [Verify a driver on real hardware](../usage/verify_driver.md).
