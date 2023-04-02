# import sys
# from PySide6 import QtCore, QtGui, QtWidgets
# from PySide6.QtUiTools import QUiLoader

# loader = QUiLoader()
# app = QtWidgets.QApplication(sys.argv)
# window = loader.load("main_window.ui", None)
# window.show()
# app.exec_()

import inspect
import json
import enum
from typing import Union, get_origin, get_args

from PySide6 import QtWidgets
from .test_widget import Ui_Form


from __feature__ import snake_case, true_property


class TestWidget(QtWidgets.QWidget, Ui_Form):
	
	def __init__(self, instrument):
		super().__init__()
		self.setupUi(self)

		self._instrument = instrument

		self.populate_queries()
		self.populate_commands()
		self._command_args = {}

		self.send_button.clicked.connect(self.send_message)
		self.query_button.clicked.connect(self.run_query)

		self.command_combo.activated.connect(self.populate_command_args)
		self.command_button.clicked.connect(self.run_command)


	def send_message(self):
		message = self.message_edit.text

		if '?' in message:
			response = self._instrument._query(message)
		else:
			response = self._instrument._command(message)

		self.response_edit.set_text(response)


	def populate_queries(self):
		for name, func in self._instrument.queries().items():
			self.query_combo.add_item(name, func)


	def populate_commands(self):
		for name, func in self._instrument.commands().items():
			self.command_combo.add_item(name, func)


	def run_query(self):
		f = self.query_combo.current_data()
		annotations = inspect.getfullargspec(f).annotations
		return_type = annotations['return']
		response = f()

		if return_type == dict:
			self.query_response_edit.set_text(json.dumps(response, indent=2))
		elif return_type == float:
			self.query_response_edit.set_text(f'{response:.6e}')
		elif return_type == int:
			self.query_response_edit.set_text(f'{response}')
		elif return_type == list[float]:
			self.query_response_edit.set_text(f'{response}')
		elif return_type == list[int]:
			self.query_response_edit.set_text(f'{response}')
		elif issubclass(return_type, enum.Enum):
			self.query_response_edit.set_text(f'{response}')
		else:
			self.query_response_edit.set_text(response)


	def clear_layout(self, layout):
		for i in reversed(range(layout.count())): 
			layout.item_at(i).widget().set_parent(None)


	def make_command_arg_widget(self, type_, key):

		if type_ == int:
			widget = QtWidgets.QLineEdit(f'{key} (int)')
			self._command_args[key] = {'callable': lambda: widget.text, 'type': type_}

		elif type_ == float:
			widget = QtWidgets.QLineEdit(f'{key} (float)')
			self._command_args[key] = {'callable': lambda: widget.text, 'type': type_}

		elif issubclass(type_, enum.Enum):
			widget = QtWidgets.QComboBox()
			for s in type_:
				widget.add_item(s.name, s.value)
			self._command_args[key] = {'callable': widget.current_data, 'type': type_}

		return widget


	def populate_command_args(self):
		f = self.command_combo.current_data()
		annotations = inspect.getfullargspec(f).annotations
		self._command_args = {}

		print(annotations)

		self.clear_layout(self.command_args_layout)

		for key, type_ in annotations.items():

			if get_origin(type_) is Union:
				for uniontype in get_args(type_):
					widget = self.make_command_arg_widget(uniontype, key)
					self.command_args_layout.add_widget(widget)

			else:
				widget = self.make_command_arg_widget(type_, key)
				self.command_args_layout.add_widget(widget)


	def run_command(self):
		f = self.command_combo.current_data()
		d = {k: v['type'](v['callable']()) for k, v in self._command_args.items()}
		f(**d)