# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'graphical_value_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QLabel, QSizePolicy,
    QWidget)

from pyqtgraph import PlotWidget

class Ui_graphical_value_widget(object):
    def setupUi(self, graphical_value_widget):
        if not graphical_value_widget.objectName():
            graphical_value_widget.setObjectName(u"graphical_value_widget")
        graphical_value_widget.resize(250, 60)
        graphical_value_widget.setMaximumSize(QSize(250, 60))
        graphical_value_widget.setBaseSize(QSize(250, 60))
        self.plot_widget = PlotWidget(graphical_value_widget)
        self.plot_widget.setObjectName(u"plot_widget")
        self.plot_widget.setGeometry(QRect(0, 0, 250, 40))
        self.plot_widget.setStyleSheet(u"")
        self.plot_widget.setFrameShape(QFrame.NoFrame)
        self.plot_widget.setFrameShadow(QFrame.Plain)
        self.plot_widget.setLineWidth(0)
        brush = QBrush(QColor(255, 255, 255, 255))
        brush.setStyle(Qt.NoBrush)
        self.plot_widget.setBackgroundBrush(brush)
        self.plot_widget.setInteractive(False)
        self.plot_widget.setRenderHints(QPainter.Antialiasing|QPainter.TextAntialiasing|QPainter.VerticalSubpixelPositioning)
        self.type_label = QLabel(graphical_value_widget)
        self.type_label.setObjectName(u"type_label")
        self.type_label.setGeometry(QRect(0, 35, 101, 25))
        font = QFont()
        font.setPointSize(7)
        font.setBold(False)
        self.type_label.setFont(font)
        self.type_label.setStyleSheet(u"background-color: white;\n"
"color: #AAA;\n"
"padding-left: 5px;")
        self.type_label.setFrameShape(QFrame.NoFrame)
        self.type_label.setLineWidth(2)
        self.type_label.setTextFormat(Qt.AutoText)
        self.type_label.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
        self.type_label.setMargin(0)
        self.type_label.setIndent(-1)
        self.unit_label = QLabel(graphical_value_widget)
        self.unit_label.setObjectName(u"unit_label")
        self.unit_label.setGeometry(QRect(220, 35, 30, 25))
        font1 = QFont()
        font1.setPointSize(8)
        font1.setBold(False)
        self.unit_label.setFont(font1)
        self.unit_label.setStyleSheet(u"background-color: white;\n"
"padding-right: 3px;")
        self.unit_label.setFrameShape(QFrame.NoFrame)
        self.unit_label.setLineWidth(2)
        self.unit_label.setTextFormat(Qt.AutoText)
        self.unit_label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.unit_label.setMargin(0)
        self.unit_label.setIndent(-1)
        self.name_label = QLabel(graphical_value_widget)
        self.name_label.setObjectName(u"name_label")
        self.name_label.setGeometry(QRect(4, 4, 75, 18))
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.name_label.sizePolicy().hasHeightForWidth())
        self.name_label.setSizePolicy(sizePolicy)
        font2 = QFont()
        font2.setPointSize(8)
        font2.setBold(True)
        self.name_label.setFont(font2)
        self.name_label.setStyleSheet(u"color: white;\n"
"background-color: rgba(0, 0, 0, 100);")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.value_label = QLabel(graphical_value_widget)
        self.value_label.setObjectName(u"value_label")
        self.value_label.setGeometry(QRect(100, 40, 120, 20))
        font3 = QFont()
        font3.setPointSize(10)
        font3.setBold(True)
        self.value_label.setFont(font3)
        self.value_label.setStyleSheet(u"background-color: white;\n"
"padding-right: 5px;")
        self.value_label.setFrameShape(QFrame.NoFrame)
        self.value_label.setLineWidth(0)
        self.value_label.setTextFormat(Qt.AutoText)
        self.value_label.setAlignment(Qt.AlignBottom|Qt.AlignRight|Qt.AlignTrailing)
        self.value_label.setMargin(0)
        self.value_label.setIndent(-1)

        self.retranslateUi(graphical_value_widget)

        QMetaObject.connectSlotsByName(graphical_value_widget)
    # setupUi

    def retranslateUi(self, graphical_value_widget):
        graphical_value_widget.setWindowTitle(QCoreApplication.translate("graphical_value_widget", u"Form", None))
        self.type_label.setText(QCoreApplication.translate("graphical_value_widget", u"(type)", None))
        self.unit_label.setText(QCoreApplication.translate("graphical_value_widget", u"unit", None))
        self.name_label.setText(QCoreApplication.translate("graphical_value_widget", u"Name", None))
        self.value_label.setText(QCoreApplication.translate("graphical_value_widget", u"Value", None))
    # retranslateUi

