# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'plot_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.4.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QSizePolicy, QSpacerItem, QToolButton, QPushButton,
    QWidget)

from pyqtgraph import PlotWidget

class Ui_plot_widget(object):
    def setupUi(self, plot_widget):
        if not plot_widget.objectName():
            plot_widget.setObjectName(u"plot_widget")
        plot_widget.resize(400, 342)
        self.gridLayout = QGridLayout(plot_widget)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.title_widget = QWidget(plot_widget)
        self.title_widget.setObjectName(u"title_widget")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.title_widget.sizePolicy().hasHeightForWidth())
        self.title_widget.setSizePolicy(sizePolicy)
        self.title_widget.setMinimumSize(QSize(0, 50))
        self.title_widget.setStyleSheet(u"background: rgb(15, 15, 45);")
        self.horizontalLayout = QHBoxLayout(self.title_widget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self._measure_label = QLabel(self.title_widget)
        self._measure_label.setObjectName(u"_measure_label")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self._measure_label.setFont(font)
        self._measure_label.setStyleSheet(u"color: white;")

        self.horizontalLayout.addWidget(self._measure_label)

        self.horizontalSpacer = QSpacerItem(195, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.toolButton_4 = QToolButton(self.title_widget)
        self.toolButton_4.setObjectName(u"toolButton_4")
        self.toolButton_4.setMinimumSize(QSize(30, 30))
        self.toolButton_4.setMaximumSize(QSize(30, 30))
        self.toolButton_4.setStyleSheet(u"background: rgb(100, 100, 125);\n"
"color: #EEE;\n"
"border-radius: 5px")
        self.toolButton_4.setPopupMode(QToolButton.MenuButtonPopup)

        self.horizontalLayout.addWidget(self.toolButton_4)

        self.toolButton_2 = QToolButton(self.title_widget)
        self.toolButton_2.setObjectName(u"toolButton_2")
        self.toolButton_2.setMinimumSize(QSize(30, 30))
        self.toolButton_2.setMaximumSize(QSize(30, 30))
        self.toolButton_2.setStyleSheet(u"background: rgb(50, 50, 150);\n"
"color: #EEE;\n"
"border-radius: 5px")
        self.toolButton_2.setPopupMode(QToolButton.MenuButtonPopup)

        self.horizontalLayout.addWidget(self.toolButton_2)

        self.line = QFrame(self.title_widget)
        self.line.setObjectName(u"line")
        self.line.setFrameShadow(QFrame.Plain)
        self.line.setFrameShape(QFrame.VLine)

        self.horizontalLayout.addWidget(self.line)

        self.toolButton = QToolButton(self.title_widget)
        self.toolButton.setObjectName(u"toolButton")
        self.toolButton.setMinimumSize(QSize(30, 30))
        self.toolButton.setMaximumSize(QSize(30, 30))
        self.toolButton.setStyleSheet(u"background: rgb(200, 25, 45);\n"
"color: #EEE;\n"
"border-radius: 5px")
        self.toolButton.setPopupMode(QToolButton.DelayedPopup)

        self.horizontalLayout.addWidget(self.toolButton)


        self.gridLayout.addWidget(self.title_widget, 0, 0, 1, 1)

        self.bar_widget = QWidget(plot_widget)
        self.bar_widget.setObjectName(u"bar_widget")
        self.bar_widget.setEnabled(True)
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.bar_widget.sizePolicy().hasHeightForWidth())
        self.bar_widget.setSizePolicy(sizePolicy1)
        self.bar_widget.setMinimumSize(QSize(0, 15))
        self.bar_widget.setMaximumSize(QSize(16777215, 15))
        self.bar_widget.setStyleSheet(u"background: #CCD;")

        self.gridLayout.addWidget(self.bar_widget, 1, 0, 1, 1)

        self.graph = PlotWidget(plot_widget)
        self.graph.setObjectName(u"graph")

        self.gridLayout.addWidget(self.graph, 2, 0, 1, 1)

        self.gridLayout.setRowStretch(2, 1)

        self.retranslateUi(plot_widget)

        QMetaObject.connectSlotsByName(plot_widget)
    # setupUi

    def retranslateUi(self, plot_widget):
        plot_widget.setWindowTitle(QCoreApplication.translate("plot_widget", u"Form", None))
        self._measure_label.setText(QCoreApplication.translate("plot_widget", u"Plotting", None))
        self.toolButton_4.setText(QCoreApplication.translate("plot_widget", u"X", None))
        self.toolButton_2.setText(QCoreApplication.translate("plot_widget", u"Y", None))
        self.toolButton.setText(QCoreApplication.translate("plot_widget", u"C", None))
    # retranslateUi

