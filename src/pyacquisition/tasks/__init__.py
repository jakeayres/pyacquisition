from .wait import WaitFor, WaitUntil
from .files import NewFile
from .ramp_temperature import RampTemperature as RampTemperature
from .field_sweep import SweepMagneticField as SweepMagneticField


standard_tasks = [NewFile, WaitFor, WaitUntil]
