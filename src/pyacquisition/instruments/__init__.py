from .software import Clock
from .stanford_research import SR_830
from enum import Enum



instrument_map = {
    'clock': Clock,
    'sr830': SR_830,
}