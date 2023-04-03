from .ui_query_widget import Ui_query_widget
from ..type_widgets import FloatWidget, IntWidget, EnumWidget, ValueWidget

from PySide6 import QtWidgets, QtGui, QtCore
import inspect, enum
from typing import Union, Tuple

#from __feature__ import snake_case, true_property



class QueryWidget(QtWidgets.QWidget, Ui_query_widget):


	def __init__(self, query):
		super().__init__()
		self.setupUi(self)

		self._query = query
		self._func = query.func
		self._args = {}

		self.name_label.setText(query.func.__name__)

		self.populate_args()

		self.send_button.clicked.connect(self.run_query)


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


	def clear_response_layout(self):
		for i in reversed(range(self.response_layout.count())): 
			self.response_layout.itemAt(i).widget().setParent(None)


	def put_response_in_widgets_layout(self, response):
		self.clear_response_layout()
		widgets = self.widgets_from_response(response)
		for widget in widgets:
			self.response_layout.addWidget(widget)


	def widget_from_flat_type(self, type_):
		if type_ == int:
			return IntWidget
		elif type_ == float:
			return FloatWidget
		elif issubclass(type_, enum.Enum):
			return EnumWidget
		else:
			return ValueWidget


	def widgets_from_response(self, response):

		if isinstance(response, (int, float, enum.Enum)):
			widget = self.widget_from_flat_type(type(response))(value=response, type_=type(response))
			return [widget]

		elif isinstance(response, (tuple, list)):
			widgets = [self.widget_from_flat_type(type(x))(value=x, type_=type(x)) for x in response]
			return widgets

		else:
			print('widgets not assigned')

	
	def populate_args(self):

		keys = self.get_arg_keys()
		annotations = inspect.getfullargspec(self._func).annotations

		for key in keys:
			widget, callback = self.widget_from_argument(key, annotations[key])
			self.args_form.addRow(key, widget)
			self._args[key] = callback


	def put_response_in_editbox(self, response):
		return_type = inspect.getfullargspec(self._func).annotations['return']

		if return_type == float:
			self.response_edit.setText(f'{response:.6e}')
		elif return_type == int:
			self.response_edit.setText(f'{response}')
		else:
			self.response_edit.setText(f'{response}')


	def run_query(self):
		d = {key: f() for key, f in self._args.items()}
		response = self._func(*self._query.args, **d)

		self.put_response_in_editbox(response)
		self.put_response_in_widgets_layout(response)