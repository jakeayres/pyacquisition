from .value_widget import ValueWidget
from PySide6 import QtWidgets, QtGui



class IntWidget(ValueWidget):


    def __init__(
    	self, 
    	value=0, 
    	type_=int, 
    	formatter=lambda x: f'{x}', 
    	*args, 
    	**kwargs
    	):
        super().__init__(value=value, type_=type_, formatter=formatter, *args, **kwargs)
