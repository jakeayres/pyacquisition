from .graphical_value_widget import GraphicalValueWidget
from PySide6 import QtWidgets, QtGui



class GraphicalFloatWidget(GraphicalValueWidget):


    def __init__(
    	self, 
    	value=0.0, 
    	type_=float, 
    	formatter=lambda x: f'{x:.3f}', 
    	*args, 
    	**kwargs
    	):
        super().__init__(value=value, type_=type_, formatter=formatter, *args, **kwargs)
