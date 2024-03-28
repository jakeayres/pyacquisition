from .software import Clock, WaveformGenerator, Gizmotron
from .stanford_research import SR_830
from .stanford_research import SR_860
from .lakeshore import Lakeshore_340
from .lakeshore import Lakeshore_350
from .oxford_instruments import Mercury_IPS
from .keithley import Keithley_2000, Keithley_6221
from .fake import FakeMagnetPSU


instruments = {
	'Gizmotron': Gizmotron,
	'Clock': Clock,
	'Waveform_Generator': WaveformGenerator,
	'SR_830': SR_830,
	'Lakeshore_340': Lakeshore_340,
	'Lakeshore_350': Lakeshore_350,
	'Keithley_2000': Keithley_2000,
	'Keithley_6221': Keithley_6221,
	'Mercury_IPS': Mercury_IPS,
	'Fake_Magnet_PSU': FakeMagnetPSU,
}