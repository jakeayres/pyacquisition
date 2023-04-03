from .value_widget import ValueWidget
from PySide6 import QtWidgets, QtGui



class FloatWidget(ValueWidget):


    def __init__(self, type_=float, formatter=lambda x: f'{x:.3f}', *args, **kwargs):
        super().__init__(type_=type_, formatter=formatter, *args, **kwargs)
