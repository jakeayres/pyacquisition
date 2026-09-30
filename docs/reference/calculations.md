# Calculations

The calculations that come with PyAcquisition, and the base class for your own. [Calculate new columns](../usage/calculations.md) shows them in use.

```python
from pyacquisition import Calculation, RollingMean, Sum
```

A calculation is added in `setup()` with `self.add_calculation(...)`, or, for `Sum` and `RollingMean`, in a config file's [`[calculations]`](config_file.md#calculations). Each makes new columns from each row as it is recorded, saved in the data file after the measurements.

| Calculation | Makes | Its column |
|---|---|---|
| [`Sum`](#sum) | The sum of two or more columns. | `a+b`, or `name` |
| [`RollingMean`](#rollingmean) | The mean of a column's last few values. | `a_mean10`, or `name` |
| A function of the row | Whatever it returns. | The keys it returns |
| A [`Calculation`](#calculation) subclass | Whatever it returns, keeping state between rows if it needs to. | Its `columns` |

A `NaN` is written to the data file as an empty cell, which pandas reads as `NaN` again.

## `Sum`

`Sum("a", "b", name=None, unit=None)`

| Argument | Meaning |
|---|---|
| `*inputs` | The columns to add together, one or more. |
| `name` | The new column's name. By default, the inputs joined with `+`: `a+b`. |
| `unit` | The new column's unit, shown in the interface. |

A column that has no value yet counts as `NaN`, and so does the sum.

## `RollingMean`

`RollingMean("a", window=10, name=None, unit=None)`

| Argument | Meaning |
|---|---|
| `column` | The column to average. |
| `window` | How many of its last values to average: a whole number, at least 1. |
| `name` | The new column's name. By default, `<column>_mean<window>`: `a_mean10`. |
| `unit` | The new column's unit, shown in the interface. |

It is `NaN` until `window` values have been seen. A `NaN` among the values stays in the mean until it leaves the window.

## `Calculation`

The base class for a calculation of your own. A subclass sets `columns`, the names of the columns it adds, and defines `__call__(self, row)`, which takes the row (a `dict` of column names to values) and returns a `dict` of the new columns. It can keep state on `self` between rows. `units`, a `dict` of column names to units, is optional. If it raises an error, the error is logged, and its `columns` are `NaN` for that row.

A plain function of the row works too, and takes its units as `add_calculation(function, units={"power": "W"})`.

## In a config file

```toml
--8<-- "examples/calculations.toml"
```

The table's name is the new column's. This is the same as adding `Sum("v1", "v2", name="v_total", unit="V")`, then `RollingMean("v_total", window=10, name="v_smooth", unit="V")`, in `setup()`. The keys are listed under [`[calculations]`](config_file.md#calculations). Functions and `Calculation` subclasses are Python only.
