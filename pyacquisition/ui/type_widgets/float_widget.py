from PySide6 import QtCore, QtWidgets, QtUiTools


class FloatWidget(QtWidgets.QWidget):


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


        w = QtUiTools.QUiLoader().load("float_widget.ui", self)


