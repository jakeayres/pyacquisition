# Build a standalone app

<p class="pa-meta" markdown="span">About 15 minutes, most of it waiting · Needs [Getting Started](../getting_started/python_api.md), and Windows</p>

The PC beside a cryostat often has no Python, and shouldn't need one. `pyacquisition build` freezes an experiment into an **app**: one file that runs on any Windows PC, with its interface, its drivers and Python inside it. In this tutorial you build one from Getting Started's `rig.toml`, try it, build one from `lab.py` instead, and take it to the lab PC.

It starts where [2. The Python API](../getting_started/python_api.md) ends: your `my-lab` project, with `rig.toml` and `lab.py`. Everything happens in the terminal.

<div class="gs" data-files="" data-lines="18" data-term-lines="4" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" markdown>

## Install the build tools

```bash
uv add "pyacquisition[build]"
```

An app is built by [PyInstaller](https://pyinstaller.org), which doesn't come with PyAcquisition, since only the PC that builds apps needs it. The `build` extra adds it to your project.

**More:** [`pyacquisition build`](../reference/command_line.md#pyacquisition-build).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Build from the config file

```bash
uv run pyacquisition build --toml rig.toml
```

```text
Building a standalone application from TOML file: rig.toml
Built dist
```

The file is checked first, so a mistake stops the build at once. Then PyInstaller gathers everything the experiment needs, and prints about 160 lines of its own while it works, which take a minute or two. The app is `dist/rig.exe`, named after the file, with `config.toml` beside it: a copy of `rig.toml`, which the app reads each time it starts.

**More:** [`pyacquisition build`'s options](../reference/command_line.md#pyacquisition-build).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Try the app on this PC

Double-click `dist/rig.exe`. After a few seconds its window opens, with the clock, the signal and the lock-in, as `uv run pyacquisition run --toml rig.toml` would, and it makes its `data` and `logs` folders beside itself.

`config.toml` can be changed without building again: an instrument's address on the lab PC, say, or the period. The app reads it as it starts.

**More:** [the config file](../reference/config_file.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Build from Python instead

```bash
uv run pyacquisition build --py lab.py
```

An experiment in Python is built from its script. The app, `dist/lab.exe`, runs `lab.py` as `uv run lab.py` would, with its own tasks, calculations and setup. Getting Started's `lab.py` reads `rig.toml`, so the app does too, from the folder it starts in: put `rig.toml` beside `lab.exe`. Everything the script imports is built in, modules of your own beside it included.

**More:** [`--py`](../reference/command_line.md#pyacquisition-build).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Name it, and build a folder

```bash
uv run pyacquisition build --py lab.py --name "My Lab" --onedir
```

`--name` names the app, `My Lab.exe`. `--onedir` builds a folder, `dist/My Lab`, with the app and what it needs beside it, instead of one file. It starts faster, since a single file unpacks itself each time, but it is a folder to copy. `--icon lab.ico` gives the app an icon.

**More:** [every option](../reference/command_line.md#pyacquisition-build).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Take it to the lab PC

Copy the app to the lab PC, with `config.toml` for a config file's app, or `rig.toml` for `lab.exe`, or the whole folder for `--onedir`. It needs no Python there. Its window needs the Microsoft Edge WebView2 Runtime, which Windows 11 has, and Windows 10 with a current Edge. Without it, the window says so, with where to get it, and the experiment runs regardless: its interface is at `http://localhost:8000` in a browser.

**More:** [the interface in a browser](../reference/interface.md).
{ .gs-more }

</section>

</div>

</div>

</div>

!!! success "Checkpoint"
    `dist` has `rig.exe` and `config.toml`. Double-clicked, `rig.exe` opens the interface's window with the clock, the signal and the lock-in, and makes `data` and `logs` beside itself. `dist/My Lab` is a folder with `My Lab.exe` in it.

??? failure "Something not working?"
    - **`pyacquisition build: PyInstaller is not installed. Add it with ``uv add pyacquisition[build]`` (or ``uv pip install pyinstaller``), then try again.`** Install the build tools first.
    - **`pyacquisition build: rig.toml has 1 problem:`, and the problem.** The file is checked before anything is built. Fix it, and build again.
    - **The app starts, and closes at once, with nothing to say why.** An app has no console, so its errors aren't seen. Build it again with `--console`, which keeps a console window open with them.
    - **`lab.exe` shows an error, `FileNotFoundError: [Errno 2] No such file or directory: 'rig.toml'`.** It reads the file from the folder it starts in. Put `rig.toml` beside it.

## What you learned

- `pyacquisition build` freezes an experiment into an app that runs on a PC with no Python. It needs the `build` extra.
- `--toml` builds from a config file, with `config.toml` beside the app to change later. `--py` builds from a script, with everything it imports.
- `--name`, `--icon` and `--onedir` name the app, give it an icon, and make it a folder that starts faster. `--console` shows its errors.
- The window needs the WebView2 Runtime, and the interface is in a browser regardless.

Next: [Verify a driver on real hardware](verify_driver.md), before you trust an instrument with a measurement.
