from pyacquisition.rack import Rack


from pyacquisition.ui.widgets.ui_test import TestWidget
#from pyacquisition.ui.type_widgets import FloatWidget


import sys, inspect
from PySide6 import QtCore, QtGui, QtWidgets, QtUiTools




if __name__ == "__main__":

	rack = Rack.from_filepath('instrument_config.json', visa_backend='pyvisa')

	wave = rack._instruments['lakeshore']


	app = QtWidgets.QApplication(sys.argv)
		
	# # w = QtUiTools.QUiLoader().load("pyacquisition/ui/type_widgets/float_widget.ui", None)
	w = TestWidget(wave)

	w.show()

	sys.exit(app.exec())