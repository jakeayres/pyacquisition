from .ui_graphical_value_widget import Ui_graphical_value_widget

from PySide6 import QtWidgets, QtGui, QtCore
import pyqtgraph, time


pyqtgraph.setConfigOptions(antialias=True)


class GraphicalValueWidget(QtWidgets.QWidget, Ui_graphical_value_widget):

    def __init__(
        self,
        name = '',
        value='', 
        type_='unknown',
        unit='', 
        formatter=lambda x: f'{x}',
        ):
        super().__init__()
        self.setupUi(self)


        self._name = name
        self._value = value
        self._type = type_
        self._unit = unit
        self._formatter = formatter

        self._pen = pyqtgraph.mkPen('#f39c12', width=2, style=QtCore.Qt.SolidLine)
        self._t0 = time.time()
        self._pts = 200
        self._x_data = [0]*self._pts
        self._y_data = [0]*self._pts


        self.set_value(value)
        self.set_name(name)
        self.set_unit(unit)
        self.set_type(type_)

        self.plot_widget.getPlotItem().hideAxis('bottom')
        self.plot_widget.getPlotItem().hideAxis('left')
        self.plot_widget.setBackground('w')


    def set_value(self, value):
        self._value = value
        self.value_label.setText(self._formatter(self._value))

        self._plot()


    def set_formatter(self, formatter):
        self._formatter = formatter
        self.value_label.setText(self._formatter(self._value))


    def set_name(self, name):
        self._name = name
        self.name_label.setText(self._name)


    def set_unit(self, unit):
        self._unit = unit
        self.unit_label.setText(self._unit)


    def set_type(self, type_):
        self._type = type_
        self.type_label.setText(f'{self._type}')


    def _plot(self):
        self._x_data.append(time.time()-self._t0)
        self._y_data.append(self._value)

        self._x_data = self._x_data[-self._pts:]
        self._y_data = self._y_data[-self._pts:]

        self.plot_widget.plot(
            self._x_data[-self._pts:], 
            self._y_data[-self._pts:],
            pen=self._pen, 
            fillLevel=0,
            brush=(230,126,34,75),
            clear=True
            )