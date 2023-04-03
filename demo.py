from pyacquisition.rack import Rack


from pyacquisition.ui import QueryWidget, CommandWidget
from pyacquisition.ui.type_widgets import GraphicalFloatWidget

import sys, inspect, time
from PySide6 import QtCore, QtGui, QtWidgets, QtUiTools



if __name__ == "__main__":

	from pyacquisition.ui.app.app import App


	app = QtWidgets.QApplication(sys.argv)
	w = App()

	rack = Rack.from_filepath('instrument_config.json', visa_backend='pyvisa')

	w.populate_instruments_from_rack(rack)

	w.show()
	sys.exit(app.exec())


# if __name__ == "__main__":

# 	import numpy as np

# 	rack = Rack.from_filepath('soft_config.json', visa_backend='dummy')
# 	inst = rack.instruments['wave']	
# 	query = inst.queries['get_amplitude']
# 	command = inst.commands['set_amplitude']

# 	app = QtWidgets.QApplication(sys.argv)
# 	w = CommandWidget(command)

# 	w.show()
# 	sys.exit(app.exec())
	


# if __name__ == "__main__":

# 	rack = Rack.from_filepath('soft_config.json', visa_backend='dummy')
# 	inst = rack._instruments['gizmo']
# 	query = inst.queries()['get_color_addition']

# 	app = QtWidgets.QApplication(sys.argv)
# 	w = QueryWidget(query)
# 	w.show()
# 	sys.exit(app.exec())