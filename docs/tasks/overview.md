A number of generic tasks have been added to `pyacquisition` and are registered to experiments by default. Others are not added by default but can be imported from `pyacquisition.tasks` and registered in `your_experiment.setup()`. 

All of the tasks are listed below.


## Default

The following tasks are registered to your experiment by default.


#### Files

`STANDARD` [`Task` **NewFile**](new_file.md) - Start a new file.

#### Wait

`STANDARD` [`Task` **WaitFor**](wait_for.md) - Wait for a specified amount of time.

`STANDARD` [`Task` **WaitUntil**](wait_until.md) - Wait until a specified time (24 hr clock).


## With an instrument

The following tasks are registered to your experiment **when the instrument they are for is in it**. They are listed in **Add task**, and their instrument's id is filled in for you if there is only one. Set `auto_tasks = False` to turn this off, and register the ones you want yourself. See [tasks that are already included](../usage/tasks.md#tasks-that-are-already-included).

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