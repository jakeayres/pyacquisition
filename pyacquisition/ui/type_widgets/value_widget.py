from .ui_value_widget import Ui_value_widget
from PySide6 import QtWidgets, QtGui


class ValueWidget(QtWidgets.QWidget, Ui_value_widget):


    def __init__(self, value='', type_='unknown', unit='', formatter=lambda x: f'{x}'):
        super().__init__()
        self.setupUi(self)

        self._value = value
        self._type = type_
        self._unit = unit
        self._formatter = formatter

        self.set_value(value)
        self.set_unit(unit)
        self.set_type(type_)


    def set_value(self, value):
        self._value = value
        self.value_label.setText(self._formatter(self._value))


    def set_formatter(self, formatter):
        self._formatter = formatter
        self.value_label.setText(self._formatter(self._value))


    def set_unit(self, unit):
        self._unit = unit
        self.unit_label.setText(self._unit)


    def set_type(self, type_):
        self._type = type_
        self.type_label.setText(f'{self._type}')