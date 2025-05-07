from .software import Clock, Calculator
from .stanford_research import SR_830, SR_860
from .lakeshore import Lakeshore_340, Lakeshore_350
from .oxford_instruments import Mercury_IPS


instrument_map = {
    "Calculator": Calculator,
    "Clock": Clock,
    "SR_830": SR_830,
    "SR_860": SR_860,
    "Lakeshore_340": Lakeshore_340,
    "Lakeshore_350": Lakeshore_350,
    "Mercury_IPS": Mercury_IPS,
}
