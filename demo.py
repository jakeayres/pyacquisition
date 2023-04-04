from pyacquisition.rack import Rack


import sys, inspect, time
from PySide6 import QtCore, QtGui, QtWidgets, QtUiTools



if __name__ == "__main__":

	from pyacquisition.ui.app.app import App


	app = QtWidgets.QApplication(sys.argv)
	w = App('instrument_config.json')
	w.show()
	sys.exit(app.exec())


# if __name__ == "__main__":

# 	from pyacquisition.ui import MeasureWidget

# 	app = QtWidgets.QApplication(sys.argv)

# 	rack = Rack.from_filepath('instrument_config.json', visa_backend='pyvisa')


# 	w = MeasureWidget.from_filepath('instrument_config.json', rack)

# 	w.show()
# 	sys.exit(app.exec())


# if __name__ == "__main__":

# 	import numpy as np
# 	from pyacquisition.ui.type_widgets import GraphicalFloatWidget

# 	rack = Rack.from_filepath('soft_config.json', visa_backend='dummy')
# 	inst = rack.instruments['wave']	

# 	inst.commands['set_frequency'](5)

# 	app = QtWidgets.QApplication(sys.argv)
# 	w = GraphicalFloatWidget()

# 	for i in range(100):
# 		time.sleep(0.001)
# 		w.set_value(inst.queries['get_signal']())

# 	w.show()
# 	sys.exit(app.exec())
