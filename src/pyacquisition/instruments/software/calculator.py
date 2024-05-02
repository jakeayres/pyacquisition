from ...instruments._instrument import SoftInstrument, query, command


"""
INTENDED SOFTWARE INSTRUMENT FOR PERFORMING GENERIC CALCULATIONS
USING ACQUIRED DATA

eg. simple multiplication etc
eg. take a derivative of one quantity w.r.t. another

functionality in Averager class should probably be subsumed into
this class and Averager should be depricated.
"""



class Calculator(SoftInstrument):


	name = 'Calculator'


	def __init__(self):
		super().__init__()
		pass