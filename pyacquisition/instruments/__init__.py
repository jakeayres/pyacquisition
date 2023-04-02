from .software import Clock, WaveformGenerator
from .stanford_research import SR_830
from .lakeshore import Lakeshore_350


instruments = {
	'Clock': Clock,
	'Waveform_Generator': WaveformGenerator,
	'SR_830': SR_830,
	'Lakeshore_350': Lakeshore_350,
}