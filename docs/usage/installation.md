# Installation

`pyacquisition` needs **Python 3.11 or newer**.

## Create a project

We strongly recommend that you install `pyacquisition` into its own environment, so that it never conflicts with other Python projects on your computer. The easiest way is with [`uv`](https://docs.astral.sh/uv/), a fast tool that manages Python versions, environments and packages together.

```
uv init my-experiment
cd my-experiment
uv add pyacquisition
```

`uv add` creates the environment and installs `pyacquisition` and everything it depends on. Run your scripts inside it with `uv run`:

```
uv run my_experiment.py
```

??? note "Using `pip` instead"
    `pyacquisition` is on PyPI, so it also installs with `pip`. Create and activate a virtual environment first:

    ```
    python -m venv .venv
    .venv\Scripts\activate
    pip install pyacquisition
    ```

    On macOS and Linux, activate with `source .venv/bin/activate`.

## Check that it worked

```
uv run python -c "import pyacquisition; print('pyacquisition is installed')"
```

## Instrument communication (VISA)

Most laboratory instruments (GPIB, USB, serial, Ethernet) are controlled through [`pyvisa`](https://pyvisa.readthedocs.io/), which is installed with `pyacquisition`. `pyvisa` talks to your hardware through a *VISA library*.

- For **GPIB** instruments you will normally want to install a VISA implementation. [PyVISA recommends the National Instruments implementation](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html), and it is what `pyacquisition` has been tested against.
- `pyvisa-py`, a pure Python backend, is also installed. It can talk to many serial, USB and Ethernet instruments without a separate VISA installation.

You do **not** need any of this to follow this guide, because it uses a simulated instrument. It matters when you connect [real hardware](instruments.md#adding-hardware-instruments).
