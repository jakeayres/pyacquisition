Every task that comes with PyAcquisition, imported from `pyacquisition.tasks`: those every experiment has, those an instrument brings with it, and those to register yourself. [Write a task](../../usage/write_task.md) shows how to write one of your own.

## Default

The following tasks are registered to your experiment by default.


#### Files

`STANDARD` [`Task` **NewFile**](new_file.md) - Start a new file.

#### Wait

`STANDARD` [`Task` **WaitFor**](wait_for.md) - Wait for a specified amount of time.

`STANDARD` [`Task` **WaitUntil**](wait_until.md) - Wait until a specified time (24 hr clock).

#### Measurements

`STANDARD` [`Task` **PauseMeasurements**](measurements.md) - Pause the measurements.

`STANDARD` [`Task` **ResumeMeasurements**](measurements.md) - Resume the measurements.

`STANDARD` [`Task` **SetMeasurementPeriod**](measurements.md) - Set the time between measurements.

#### Traces

`STANDARD` [`Task` **AcquireTrace**](acquire_trace.md) - Take a trace now, and wait for it. Registered when the experiment has traces.


## With an instrument

The following tasks are registered to your experiment **when the instrument they are for is in it**. They are listed in **Add task**, and their instrument's id is filled in for you if there is only one. Set `auto_tasks = False` to turn this off, and register the ones you want yourself. See [`auto_tasks`](../experiment_options.md).

#### Lakeshore 340 and 350

`AUTOMATIC` [`Task` **RampTemperature**](ramp_temperature.md) - Ramp the setpoint of an output to a temperature, and wait until it gets there.

#### Mercury IPS

`AUTOMATIC` [`Task` **SweepMagneticField**](field_sweep.md) - Sweep the field to a setpoint and back to zero, checking the magnet at every step.


## Importable

The following tasks are **not registered** to your experiment by default. They can be imported from `pyacquisition.tasks` and registered to your experiment within `your_experiment.setup()` using `self.register_task(...)`.

#### Control

`IMPORTABLE` [`Task` **PID**](pid.md) - Hold a value at a setpoint with a PID controller.

#### Mercury IPS

The building blocks of `SweepMagneticField`, for a task of your own.

`IMPORTABLE` [`Task` **RampMagnet**](field_sweep.md) - Sweep the field to a setpoint. Pausing holds the magnet.

`IMPORTABLE` [`Task` **RampMagnetToZero**](field_sweep.md) - Sweep the field to zero. Pausing holds the magnet.