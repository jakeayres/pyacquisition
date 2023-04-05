from .ui_plot_widget import Ui_plot_widget

from PySide6 import QtWidgets, QtGui, QtCore
import inspect, enum, time, json
from functools import partial


import numpy as np
import pandas as pd
import pyqtgraph


class PlotWidget(QtWidgets.QWidget, Ui_plot_widget):


	new_data = QtCore.Signal()


	def __init__(self):
		super().__init__()
		self.setupUi(self)

		self._data = {}
		self._has_data = False

		self.new_data.connect(self.redraw_plot)

		self.pen = pyqtgraph.mkPen('#FFF', width=1, style=QtCore.Qt.SolidLine)

		self._buffer = {}



	def receive_data(self, data: dict):
		if not self._has_data:
			self._has_data = True
			for k, v in data.items():
				self._data[k] = [v]
		else:
			for k, v in data.items():
				self._data[k].append(v)

		self.new_data.emit()


	def redraw_plot(self):
		self.graph.plot([self._data['float1'][-1]], [self._data['float0'][-1]], symbol='o', symbolPen='w')
