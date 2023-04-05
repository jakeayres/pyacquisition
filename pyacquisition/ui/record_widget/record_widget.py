from .ui_record_widget import Ui_record_widget

from PySide6 import QtWidgets, QtGui, QtCore
import inspect, enum, time, json
from functools import partial


import numpy as np


class RecordWidget(QtWidgets.QWidget, Ui_record_widget):


	def __init__(self):
		super().__init__()
		self.setupUi(self)