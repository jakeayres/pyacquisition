from .ui_plot_widget import Ui_plot_widget

from PySide6 import QtWidgets, QtGui, QtCore
import inspect, enum, time, json
from functools import partial


import numpy as np
import pandas as pd
import pyqtgraph


pyqtgraph.setConfigOption('background', 'w')
pyqtgraph.setConfigOption('foreground', 'k')


class PlotWidget(QtWidgets.QWidget, Ui_plot_widget):


	def __init__(self):
		super().__init__()
		self.setupUi(self)

		pyqtgraph.setConfigOption('background', 'w')
		pyqtgraph.setConfigOption('foreground', 'k')

		self._data = {}
		self._has_data = False
		self._new_length = 0

		
		self._x_key = None
		self._y_keys = []


		self._colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']


		self._timer = QtCore.QTimer(self)
		self._timer.timeout.connect(self.draw_new_data)
		self._rate = 2000
		self._timer.start(self._rate)



	def _change_x_axis(self, key):
		self._x_key = key
		self.graph.setLabel('bottom', f'{key}')


	def _toggle_y_axis(self, key):
		if key in self._y_keys:
			self._y_keys.remove(key)
		else:
			self._y_keys.append(key)


		self.graph.setLabel('left', ', '.join(self._y_keys))



	def _populate_x_menu(self):
		menu = QtWidgets.QMenu(self)
		for k, v in self._data.items():
			action = QtGui.QAction(f'{k}', self)
			# action.setCheckable(True)
			# if k == self._x_key:
			# 	action.setChecked(True)
			action.triggered.connect(partial(self._change_x_axis, k))
			action.triggered.connect(self.clear_graph)
			action.triggered.connect(self.draw_old_data)
			menu.addAction(action)

		self.toolButton_4.setMenu(menu)


	def _populate_y_menu(self):
		menu = QtWidgets.QMenu(self)
		for k, v in self._data.items():
			action = QtGui.QAction(f'{k}', self)
			action.setCheckable(True)
			if k in self._y_keys:
				action.setChecked(True)
			action.triggered.connect(partial(self._toggle_y_axis, k))
			action.triggered.connect(self.clear_graph)
			action.triggered.connect(self.draw_old_data)
			menu.addAction(action)

		self.toolButton_2.setMenu(menu)



	def _initialize_new_data(self, data: dict):
		self._has_data = True

		for k, v in data.items():
			self._data[k] = [v]

		self._populate_x_menu()
		self._populate_y_menu()



	def receive_data(self, data: dict):
		if not self._has_data:
			self._initialize_new_data(data)
		else:
			for k, v in data.items():
				self._data[k].append(v)

		self._new_length += 1


	def clear_graph(self):
		self.graph.clear()


	def draw_old_data(self):
		for i, y_key in enumerate(self._y_keys):
			self.graph.plot(
				self._data[self._x_key], 
				self._data[y_key], 
				pen=None, 
				symbol='o',
				symbolBrush=self._colors[i],
				symbolPen=self._colors[i], 
				symbolSize=2,
				name=f'{y_key}'
				)



	def draw_new_data(self):
		N = self._new_length
		for i, y_key in enumerate(self._y_keys):
			self.graph.plot(
				self._data[self._x_key][-N:], 
				self._data[y_key][-N:], 
				pen=None, 
				symbol='o',
				symbolBrush=self._colors[i],
				symbolPen=self._colors[i],
				symbolSize=2,
				name=f'{y_key}'
				)
		self._new_length = 0
