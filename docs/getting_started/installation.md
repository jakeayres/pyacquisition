# 0. Installation

<p class="pa-meta" markdown="span">About 5 minutes · Needs a terminal, and an internet connection</p>

PyAcquisition is a Python package, and it installs into a **project**: a folder for your experiment, with an *environment* of its own. The environment is the Python the project runs with, and the packages installed for that project alone. So the packages one project needs can't clash with another's, or with any Python already on your computer.

[uv](https://docs.astral.sh/uv/) makes and manages projects. It is one program that installs Python when a project needs it, makes each project's environment, and adds packages to it, writing down exactly which ones, so that the project can be set up again anywhere. It is the first thing to install, below.

<div class="gs" data-mode="versions" data-file="pyproject.toml" data-lines="10" data-term-lines="10" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" markdown>

## Install uv

```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows
winget install --id=astral-sh.uv -e
```

uv is installed once, for your whole computer. In a terminal (on Windows, PowerShell or the Command Prompt), run the command for your system. When it has finished, close the terminal and open a new one, so that it finds `uv`.

You don't need to install Python yourself: if you don't have one that a project can use, uv downloads it.

**More:** [other ways to install uv](https://docs.astral.sh/uv/getting-started/installation/), such as Homebrew, on uv's site.
{ .gs-more }

</section>

<section class="gs-step" data-new-file markdown>

## Make a project

```bash
uv init my-lab
cd my-lab
```

```toml title="pyproject.toml"
[project]
name = "my-lab"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.13"
dependencies = []
```

`uv init my-lab` makes a folder called `my-lab` for the project, and `cd my-lab` moves the terminal into it. Run every command from now on in that folder.

`pyproject.toml` describes the project: its name, the versions of Python it runs on (`requires-python`), and its `dependencies`, the packages it uses, which is none yet. uv makes a `README.md` and a `main.py` too, which you can leave or delete.

Open the `my-lab` folder in your editor. Your experiment's files go in it.

**More:** [working on projects](https://docs.astral.sh/uv/guides/projects/), and [what each of a project's files is for](https://docs.astral.sh/uv/concepts/projects/layout/), on uv's site.
{ .gs-more }

</section>

<section class="gs-step" data-result="Installed 67 packages in 1.30s" markdown>

## Add PyAcquisition

```bash
uv add pyacquisition
```

```toml title="pyproject.toml" hl_lines="7-9"
[project]
name = "my-lab"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "pyacquisition>=0.3.2",
]
```

`uv add` adds PyAcquisition to the project's `dependencies`, with the lowest version the project accepts. Then it works out everything PyAcquisition needs in turn, at versions that work together, writes them all down in `uv.lock`, and installs them into the project's environment, the `.venv` folder, which it makes the first time.

Nothing outside `my-lab` changes, so another project can use other versions of the same packages.

**More:** [managing dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/), on uv's site.
{ .gs-more }

</section>

<section class="gs-step" data-result="pyacquisition is installed" markdown>

## Check it worked

```bash
uv run python -c "import pyacquisition; print('pyacquisition is installed')"
```

`uv run` runs a command inside the project's environment, so it uses the project's Python and packages, and no others. Here, Python imports PyAcquisition, and prints a line to say it could.

Start every command in this guide with `uv run`, from the `my-lab` folder. There is no environment to activate first.

**More:** [running commands in a project](https://docs.astral.sh/uv/concepts/projects/run/), on uv's site.
{ .gs-more }

</section>

</div>

</div>

</div>

## Real instruments, later

Nothing more is needed until you connect real instruments. PyAcquisition talks to them through [`pyvisa`](https://pyvisa.readthedocs.io/), which it installs, and `pyvisa` talks to the hardware through a *VISA library*:

- For **GPIB** instruments, install one. [PyVISA recommends the National Instruments implementation](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html), and it is what PyAcquisition has been tested against.
- `pyvisa-py`, a pure Python backend installed alongside it, talks to many serial, USB and Ethernet instruments without a separate VISA installation.

!!! success "Checkpoint"
    In the `my-lab` folder, the check prints `pyacquisition is installed`.

??? failure "Something not working?"
    - **`uv` is not found.** Open a new terminal after installing it, so that it is on your path.
    - **`ModuleNotFoundError: No module named 'pyacquisition'`.** Plain `python` doesn't use the project's environment. Run commands with `uv run`, from the `my-lab` folder.
    - **uv says there is no `pyproject.toml`.** The terminal is in another folder. `cd` into `my-lab` first.

??? note "Using `pip` instead"
    `pyacquisition` is on PyPI, so it also installs with `pip`. Create and activate a virtual environment first:

    ```
    python -m venv .venv
    .venv\Scripts\activate
    pip install pyacquisition
    ```

    On macOS and Linux, activate with `source .venv/bin/activate`.

## What you learned

- A **project** is a folder with an environment of its own, so its packages can't clash with anything else's.
- **uv** installs Python, makes a project's environment, and adds packages to it. `pyproject.toml` lists what the project needs, and `uv.lock` the exact versions.
- `uv run` runs a command in the project's environment.

Next: [1. The Config File](config_file.md) describes a whole experiment in one small file.
