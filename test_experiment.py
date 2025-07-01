from pyacquisition import Experiment


#
#  This should be put pytested
#

class MyExperiment(Experiment):
    
    def setup(self):
        
        print("Setting up the experiment...")
        print('@@@@@@@@@@@@@@@@@@@@@@@@@@@')
        