from .software import Clock
from enum import Enum



class Instruments(str, Enum):
    CLOCK = Clock