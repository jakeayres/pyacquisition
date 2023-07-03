from .software import Clock, WaveformGenerator, Gizmotron, FileRecorder
from .stanford_research import SR_830
from .lakeshore import Lakeshore_350


instruments = {
	'Gizmotron': Gizmotron,
	'File_Recorder': FileRecorder,
	'Clock': Clock,
	'Waveform_Generator': WaveformGenerator,
	'SR_830': SR_830,
	'Lakeshore_350': Lakeshore_350,
}