from pyacquisition.rack import Rack


from pyacquisition.ui import QueryWidget
from pyacquisition.ui.type_widgets import GraphicalFloatWidget

import sys, inspect, time
from PySide6 import QtCore, QtGui, QtWidgets, QtUiTools





if __name__ == "__main__":

	import numpy as np

	rack = Rack.from_filepath('soft_config.json', visa_backend='dummy')
	inst = rack._instruments['wave']
	query = inst.queries()['get_signal']

	app = QtWidgets.QApplication(sys.argv)
	w = GraphicalFloatWidget()
	w._plot()

	for i in range(100):
		time.sleep(0.015)
		w.set_value(query())

	w.show()
	sys.exit(app.exec())
	


# if __name__ == "__main__":

# 	rack = Rack.from_filepath('soft_config.json', visa_backend='dummy')
# 	inst = rack._instruments['gizmo']
# 	query = inst.queries()['get_color_addition']

# 	app = QtWidgets.QApplication(sys.argv)
# 	w = QueryWidget(query)
# 	w.show()
# 	sys.exit(app.exec())