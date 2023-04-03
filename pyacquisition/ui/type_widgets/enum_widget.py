from .value_widget import ValueWidget
from PySide6 import QtWidgets, QtGui



class EnumWidget(ValueWidget):


    def __init__(self, formatter=lambda x: f'{x.name}', *args, **kwargs):
        super().__init__(formatter=formatter, *args, **kwargs)
