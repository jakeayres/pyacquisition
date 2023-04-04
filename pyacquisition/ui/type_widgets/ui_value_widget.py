# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'value_widget.ui'
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

class Ui_value_widget(object):
    def setupUi(self, value_widget):
        if not value_widget.objectName():
            value_widget.setObjectName(u"value_widget")
        value_widget.resize(250, 28)
        value_widget.setStyleSheet(u"background-color: rgba(255, 255, 255, 255);")
        self.value_label = QLabel(value_widget)
        self.value_label.setObjectName(u"value_label")
        self.value_label.setGeometry(QRect(129, 0, 91, 28))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.value_label.setFont(font)
        self.value_label.setStyleSheet(u"background-color: rgba(255, 255, 255, 255);\n"
"padding-right: 5px;")
        self.value_label.setFrameShape(QFrame.Box)
        self.value_label.setLineWidth(0)
        self.value_label.setTextFormat(Qt.AutoText)
        self.value_label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.value_label.setMargin(0)
        self.value_label.setIndent(-1)
        self.type_label = QLabel(value_widget)
        self.type_label.setObjectName(u"type_label")
        self.type_label.setGeometry(QRect(-1, 0, 131, 28))
        font1 = QFont()
        font1.setPointSize(7)
        font1.setBold(False)
        self.type_label.setFont(font1)
        self.type_label.setStyleSheet(u"color: #AAA;\n"
"padding-left: 5px;\n"
"background-color: rgba(255, 255, 255, 255);")
        self.type_label.setFrameShape(QFrame.Box)
        self.type_label.setLineWidth(0)
        self.type_label.setTextFormat(Qt.AutoText)
        self.type_label.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
        self.type_label.setMargin(0)
        self.type_label.setIndent(-1)
        self.unit_label = QLabel(value_widget)
        self.unit_label.setObjectName(u"unit_label")
        self.unit_label.setGeometry(QRect(220, 0, 30, 28))
        font2 = QFont()
        font2.setPointSize(8)
        font2.setBold(False)
        self.unit_label.setFont(font2)
        self.unit_label.setStyleSheet(u"background-color: white;\n"
"padding-right: 3px;")
        self.unit_label.setFrameShape(QFrame.Box)
        self.unit_label.setLineWidth(0)
        self.unit_label.setTextFormat(Qt.AutoText)
        self.unit_label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.unit_label.setMargin(0)
        self.unit_label.setIndent(-1)
        self.name_label = QLabel(value_widget)
        self.name_label.setObjectName(u"name_label")
        self.name_label.setGeometry(QRect(5, 5, 75, 18))
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.name_label.sizePolicy().hasHeightForWidth())
        self.name_label.setSizePolicy(sizePolicy)
        font3 = QFont()
        font3.setPointSize(8)
        font3.setBold(True)
        self.name_label.setFont(font3)
        self.name_label.setStyleSheet(u"color: white;\n"
"background-color: rgba(0, 0, 0, 100);")
        self.name_label.setAlignment(Qt.AlignCenter)

        self.retranslateUi(value_widget)

        QMetaObject.connectSlotsByName(value_widget)
    # setupUi

    def retranslateUi(self, value_widget):
        value_widget.setWindowTitle(QCoreApplication.translate("value_widget", u"Form", None))
        self.value_label.setText(QCoreApplication.translate("value_widget", u"Value", None))
        self.type_label.setText(QCoreApplication.translate("value_widget", u"(type)", None))
        self.unit_label.setText(QCoreApplication.translate("value_widget", u"unit", None))
        self.name_label.setText(QCoreApplication.translate("value_widget", u"Name", None))
    # retranslateUi

