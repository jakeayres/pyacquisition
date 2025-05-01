# Installation

## Installation with `pip`

`pyacquisition` is avaiilable on `PyPi` and is installable via `pip`:

```
pip install pyacquisition
```

or using your dependency manager of choice (eg. `uv`):

```
uv add pyacquisition
```

## Installing VISA

`pyacquisition` leverages `pyvisa` for GPIB communication. As documented [at the PyVISA](https://pyvisa.readthedocs.io/en/latest/), a VISA library needs to be installed. Depending on what hardware, you might have a prefered library. PyVISA recommends the [National Instruments implementation](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html). `pyacquisition` has been tested against this implementation.

## Dependency Management

`pyacquisition` relies on a number of well-maintained packages from both the Python standard library and the broader Python ecosystem. To ensure a smooth installation experience and consistent environments across systems, **we strongly recommend using a dependency manager**.

Our recommended choice of dependency manager is `uv`. `uv` is a lightning-fast, modern tool that replaces `pip`, `virtualenv`, `poetry` and other environment tools with a single all-in-one solution. It offers full support for pyproject.toml-based workflows, provides quick and reliable dependency resolution, and makes managing Python environments faster and more predictable. If you're starting fresh, `uv` offers an excellent experience out of the box. [More information on `uv` can be found here](https://docs.astral.sh/uv/)
