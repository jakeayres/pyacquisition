# Calculations

A **calculation** makes new columns from your measurements, and saves them to the data file next to the raw values. Use one to add two columns together, smooth a noisy signal, or compute a derived quantity such as power or resistance from measured values.

## Adding a calculation

A calculation is a function that takes a **row** (a dict of column name to value) and returns a dict of new columns:

```python
self.add_calculation(lambda row: {"power": row["voltage"] * row["current"]})
```

The raw columns are always kept. The data file above would have the columns `voltage`, `current` and `power`.

Add calculations in `setup()`, after the measurements they use. Once the experiment is running, the set of calculations is fixed.

Calculations run in the order they are added, and each one can use the columns made by the ones before it:

```python
self.add_calculation(lambda row: {"power": row["voltage"] * row["current"]})
self.add_calculation(RollingMean("power", window=10))
```

For anything longer than a line, write a function:

```python
def resistance(row):
    return {"resistance": row["voltage"] / row["current"]}

self.add_calculation(resistance)
```

## Built-in calculations

`Sum` adds up columns, and `RollingMean` averages a column's last few values. Both can also go in a config file's `[calculations]`. Their arguments, the columns they make and their TOML form are in [Calculations](../reference/calculations.md) in the Reference.

```python
from pyacquisition import RollingMean, Sum

self.add_calculation(Sum("v1", "v2", name="v_total", unit="V"))
self.add_calculation(RollingMean("v_total", window=10, unit="V"))
```

## Units

Give the new columns units with `units`, a dict of column name to unit. They are shown beside the values in the interface and on plot axes, and do not change the data file:

```python
self.add_calculation(
    lambda row: {"power": row["voltage"] * row["current"]},
    units={"power": "W"},
)
self.add_calculation(RollingMean("power", window=10, unit="W"))
```

The built-in calculations take a single `unit=` for the column they make. A `Calculation` subclass can set `units` itself, as it sets `columns`.

## Keeping state between rows

A function can only see the current row. For anything that remembers earlier rows, such as a filter, write a class that inherits from `Calculation` and set `columns` to the names of the columns it makes:

```python
from collections import deque
from pyacquisition import Calculation

class RollingMax(Calculation):
    def __init__(self, column, window):
        self.column = column
        self.columns = (f"{column}_max",)
        self._values = deque(maxlen=window)

    def __call__(self, row):
        self._values.append(row[self.column])
        return {self.columns[0]: max(self._values)}

self.add_calculation(RollingMax("voltage", window=20))
```

## The columns of a file stay the same

The header of a data file is written from the first row, and every later row must line up with it. So the columns of the first row decide the columns of the whole run:

- If a calculation raises an error, the error is logged and its columns are `NaN` for that row. Everything else carries on. Calculations that inherit from `Calculation` list their `columns`, so they always have somewhere to put the `NaN`.
- If a function returns a column that was not in the first row, that column is left out, and a warning is logged. Return the same columns on every call.

If a measurement has failed and has no value yet, it is `None`. `Sum` and `RollingMean` treat that as `NaN`.

## Where the results appear

Calculated columns are saved to the data file, and shown in the interface like the measurements: each has a tile in the **Values** tab, and can be plotted.
