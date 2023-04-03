from .value_widget import ValueWidget
from PySide6 import QtWidgets, QtGui



class StringWidget(ValueWidget):


    def __init__(self, type_=str, formatter=lambda x: f'{x}'):
        super().__init__(type_=type_,formatter=formatter, *args, **kwargs)
