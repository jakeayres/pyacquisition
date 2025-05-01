from .software import Clock
from .stanford_research import SR_830, SR_860
from .lakeshore import Lakeshore_340, Lakeshore_350
from .oxford_instruments import Mercury_IPS
from .mock import MockInstrument


instrument_map = {
    'Mock': MockInstrument,
    'Clock': Clock,
    'SR_830': SR_830,
    'SR_860': SR_860,
    'Lakeshore_340': Lakeshore_340,
    'Lakeshore_350': Lakeshore_350,
    'Mercury_IPS': Mercury_IPS,
}