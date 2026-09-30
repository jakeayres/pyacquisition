from .wait import WaitFor, WaitUntil
from .files import NewFile
from .measurements import PauseMeasurements, ResumeMeasurements, SetMeasurementPeriod
from .traces import AcquireTrace as AcquireTrace
from .ramp_temperature import RampTemperature as RampTemperature
from .field_sweep import RampMagnet as RampMagnet
from .field_sweep import RampMagnetToZero as RampMagnetToZero
from .field_sweep import SweepMagneticField as SweepMagneticField
from .pid import PID as PID
from .pid import PIDCalculation as PIDCalculation


standard_tasks = [
    NewFile,
    WaitFor,
    WaitUntil,
    PauseMeasurements,
    ResumeMeasurements,
    SetMeasurementPeriod,
]

# Registered by themselves when an instrument they are for is in the experiment.
# What a task is for is its `applies_to`.
instrument_tasks = [RampTemperature, SweepMagneticField]
