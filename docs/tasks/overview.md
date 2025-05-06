A number of generic tasks have been added to `pyacquisition` and are registered to experiments by default. Others are not added by default but can be imported from `pyacquisition.tasks` and registered in `your_experiment.setup()`. 

All of the tasks are listed below.


## Default

The following tasks are registered to your experiment by default.


#### Files

`STANDARD` [`Task` **NewFile**](new_file.md) - Start a new file.

#### Wait

`STANDARD` [`Task` **WaitFor**](wait_for.md) - Wait for a specified amount of time.

`STANDARD` [`Task` **WaitUntil**](wait_until.md) - Wait until a specified time (24 hr clock).


## Importable

The following tasks are **not registered** to your experiment by default. They can be imported from `pyacquisition.tasks` and registered to your experiment within `your_experiment.setup()` using `self.register_task(...)`.

#### Mercury IPS

`IMPORTABLE` [`Task` **SweepMagneticField**](wait_for.md) - Sweep magnetic field.