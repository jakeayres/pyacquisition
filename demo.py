from pyacquisition.rack import Rack


import os, sys, inspect, time
import click
from PySide6 import QtCore, QtGui, QtWidgets, QtUiTools
from functools import partial


@click.group()
def cli():
	pass



@cli.command()
def qt():

	from pyacquisition.ui.app.app import App
	from pyacquisition.procedures import Procedure, ProcedureList, ProcedureGroup

	import numpy as np

	_ = QtWidgets.QApplication(sys.argv)
	app = App('soft_config.json')

	app._record_widget.set_directory('.')
	app._record_widget.set_stem('test_file')
	app._record_widget.set_number(1)


	start_timer = partial(app.instruments['clock'].commands['start_named_timer'], 'my_timer')
	read_timer = partial(app.instruments['clock'].queries['read_named_timer'], 'my_timer')

	pl = ProcedureList()

	start_timer()
	pl.add_procedures(
		Procedure.poll(app.start_measuring).until(read_timer).greater_than(-1),
		Procedure.poll(app.start_recording).until(read_timer).greater_than(-1),
		Procedure.poll(lambda: print('waiting')).until(read_timer).greater_than(5),
		Procedure.poll(app.increment_file).until(read_timer).greater_than(-1),
		Procedure.poll(lambda: print('waiting')).until(read_timer).greater_than(10),
		Procedure.poll(app.stop_recording).until(read_timer).greater_than(-1),
		Procedure.poll(app.stop_measuring).until(read_timer).greater_than(-1),
		)
	pl.start()

	app.show()
	_.exec()
	sys.exit()


@cli.command()
def test():

	def f(func, condition):
		ff = func() > condition
		return ff

	x = f(lambda: 10, 5)
	print(x)



if __name__ == "__main__":

	cli()







