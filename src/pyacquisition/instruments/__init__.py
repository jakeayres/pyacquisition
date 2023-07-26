from .software import Clock, WaveformGenerator, Gizmotron
from .stanford_research import SR_830
from .stanford_research import SR_860
from .lakeshore import Lakeshore_350


instruments = {
	'Gizmotron': Gizmotron,
	'Clock': Clock,
	'Waveform_Generator': WaveformGenerator,
	'SR_830': SR_830,
	'Lakeshore_350': Lakeshore_350,
}