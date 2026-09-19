from .software import Clock, Calculator, RandomNumberGenerator, SignalGenerator
from .stanford_research import SR_830, SR_860
from .keithley import Keithley_2000, Keithley_6221
from .lakeshore import Lakeshore_340, Lakeshore_350
from .oxford_instruments import Mercury_IPS


instrument_map = {
    "Calculator": Calculator,
    "Clock": Clock,
    "RandomNumberGenerator": RandomNumberGenerator,
    "SignalGenerator": SignalGenerator,
    "Keithley_2000": Keithley_2000,
    "Keithley_6221": Keithley_6221,
    "SR_830": SR_830,
    "SR_860": SR_860,
    "Lakeshore_340": Lakeshore_340,
    "Lakeshore_350": Lakeshore_350,
    "Mercury_IPS": Mercury_IPS,
}
