from .ui_command_widget import Ui_command_widget
from ..type_widgets import FloatWidget, IntWidget, EnumWidget, ValueWidget

from PySide6 import QtWidgets, QtGui, QtCore
import inspect, enum
from typing import Union, Tuple

#from __feature__ import snake_case, true_property



class CommandWidget(QtWidgets.QWidget, Ui_command_widget):


	def __init__(self, command):
		super().__init__()
		self.setupUi(self)

		self._command = command
		self._func = command.func
		self._args = {}

		self.name_label.setText(command.func.__name__)

		self.populate_args()

		self.send_button.clicked.connect(self.run_command)


	def get_arg_keys(self):
		return inspect.getfullargspec(self._func).args[1:]


	def widget_from_argument(self, key, type_):
		""" take an argument (it's key and type)
		and return an appropriate widget and a callback
		that returns it's user-provided value.
		"""

		if type_ == int:
			widget = QtWidgets.QLineEdit()
			widget.setPlaceholderText(str(type_))
			validator = QtGui.QIntValidator()
			widget.setValidator(validator)
			return widget, lambda: int(widget.text())
		
		elif type_ == float:
			widget = QtWidgets.QLineEdit()
			widget.setPlaceholderText(str(type_))
			validator = QtGui.QDoubleValidator()
			widget.setValidator(validator)
			return widget, lambda: float(widget.text())
		
		elif issubclass(type_, enum.Enum):
			widget = QtWidgets.QComboBox()
			for option in type_:
				widget.addItem(option.name, option)
			return widget, lambda: widget.currentData()


	def populate_args(self):

		keys = self.get_arg_keys()
		annotations = inspect.getfullargspec(self._func).annotations

		for key in keys:
			widget, callback = self.widget_from_argument(key, annotations[key])
			self.args_form.addRow(key, widget)
			self._args[key] = callback


	def run_command(self):
		d = {key: f() for key, f in self._args.items()}
		response = self._func(*self._command.args, **d)
		print(f'command response: {response}')