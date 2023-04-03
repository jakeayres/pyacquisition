from .ui_app import Ui_app
from .. import QueryWidget, CommandWidget


from PySide6 import QtWidgets, QtGui, QtCore
from functools import partial


class App(QtWidgets.QMainWindow, Ui_app):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.setupUi(self)


	def open_query_widget(self, query):

		self.w = QueryWidget(query)
		self.w.show()


	def open_command_widget(self, command):

		self.w = CommandWidget(command)
		self.w.show()


	def populate_instruments_from_rack(self, rack):

		for name, inst in rack.instruments.items():

			inst_menu = QtWidgets.QMenu(name)
			query_menu = QtWidgets.QMenu('Queries')
			command_menu = QtWidgets.QMenu('Commands')

			inst_menu.addMenu(query_menu)
			inst_menu.addMenu(command_menu)

			for query_name, query in inst.queries.items():
				query_action = QtGui.QAction(query_name, self)
				query_action.triggered.connect(partial(self.open_query_widget, query))
				query_menu.addAction(query_action)

			for command_name, command in inst.commands.items():
				command_action = QtGui.QAction(command_name, self)
				command_action.triggered.connect(partial(self.open_command_widget, command))
				command_menu.addAction(command_action)

			self.instruments_menu.addMenu(inst_menu)
