from .wait import WaitFor, WaitUntil
from .files import NewFile
from .ramp_temperature import RampTemperature as RampTemperature
from .field_sweep import SweepMagneticField as SweepMagneticField
from .pid import PID as PID
from .pid import PIDController as PIDController


standard_tasks = [NewFile, WaitFor, WaitUntil]
