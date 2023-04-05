# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'record_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QWidget)

class Ui_record_widget(object):
    def setupUi(self, record_widget):
        if not record_widget.objectName():
            record_widget.setObjectName(u"record_widget")
        record_widget.resize(250, 240)
        record_widget.setStyleSheet(u"background-color: white;")
        self.title_widget = QWidget(record_widget)
        self.title_widget.setObjectName(u"title_widget")
        self.title_widget.setGeometry(QRect(0, 0, 248, 50))
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.title_widget.sizePolicy().hasHeightForWidth())
        self.title_widget.setSizePolicy(sizePolicy)
        self.title_widget.setMinimumSize(QSize(0, 50))
        self.title_widget.setStyleSheet(u"background: rgb(50, 55, 175);")
        self.run_button = QPushButton(self.title_widget)
        self.run_button.setObjectName(u"run_button")
        self.run_button.setGeometry(QRect(160, 10, 80, 30))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.run_button.setFont(font)
        self.run_button.setStyleSheet(u"QPushButton {\n"
"	background: rgb(100, 200, 25);\n"
"	border-radius: 5px;\n"
"	color: white;\n"
"}")
        self._measure_label = QLabel(self.title_widget)
        self._measure_label.setObjectName(u"_measure_label")
        self._measure_label.setGeometry(QRect(20, 0, 91, 51))
        font1 = QFont()
        font1.setPointSize(12)
        font1.setBold(True)
        self._measure_label.setFont(font1)
        self._measure_label.setStyleSheet(u"color: white;")
        self.bar_widget = QWidget(record_widget)
        self.bar_widget.setObjectName(u"bar_widget")
        self.bar_widget.setEnabled(True)
        self.bar_widget.setGeometry(QRect(0, 50, 248, 30))
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.bar_widget.sizePolicy().hasHeightForWidth())
        self.bar_widget.setSizePolicy(sizePolicy1)
        self.bar_widget.setMinimumSize(QSize(0, 30))
        self.bar_widget.setStyleSheet(u"background: #CCD;")
        self.time_label = QLabel(self.bar_widget)
        self.time_label.setObjectName(u"time_label")
        self.time_label.setGeometry(QRect(20, 0, 71, 30))
        self.points_label = QLabel(self.bar_widget)
        self.points_label.setObjectName(u"points_label")
        self.points_label.setGeometry(QRect(160, 0, 71, 30))
        self.points_label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.directory_edit = QLineEdit(record_widget)
        self.directory_edit.setObjectName(u"directory_edit")
        self.directory_edit.setGeometry(QRect(80, 90, 150, 25))
        self.directory_edit.setStyleSheet(u"border-radius: 4px;\n"
"border: 1px solid #AAA;")
        self.stem_edit = QLineEdit(record_widget)
        self.stem_edit.setObjectName(u"stem_edit")
        self.stem_edit.setGeometry(QRect(80, 130, 150, 25))
        self.stem_edit.setStyleSheet(u"border-radius: 4px;\n"
"border: 1px solid #AAA;")
        self.number_edit = QLineEdit(record_widget)
        self.number_edit.setObjectName(u"number_edit")
        self.number_edit.setGeometry(QRect(80, 170, 150, 25))
        self.number_edit.setStyleSheet(u"border-radius: 4px;\n"
"border: 1px solid #AAA;")
        self._measure_label_2 = QLabel(record_widget)
        self._measure_label_2.setObjectName(u"_measure_label_2")
        self._measure_label_2.setGeometry(QRect(20, 90, 60, 25))
        font2 = QFont()
        font2.setPointSize(8)
        font2.setBold(True)
        self._measure_label_2.setFont(font2)
        self._measure_label_2.setStyleSheet(u"color: black;")
        self._measure_label_3 = QLabel(record_widget)
        self._measure_label_3.setObjectName(u"_measure_label_3")
        self._measure_label_3.setGeometry(QRect(20, 130, 60, 25))
        self._measure_label_3.setFont(font2)
        self._measure_label_3.setStyleSheet(u"color: black;")
        self._measure_label_4 = QLabel(record_widget)
        self._measure_label_4.setObjectName(u"_measure_label_4")
        self._measure_label_4.setGeometry(QRect(20, 170, 60, 25))
        self._measure_label_4.setFont(font2)
        self._measure_label_4.setStyleSheet(u"color: black;")
        self._measure_label_5 = QLabel(record_widget)
        self._measure_label_5.setObjectName(u"_measure_label_5")
        self._measure_label_5.setGeometry(QRect(20, 210, 211, 25))
        font3 = QFont()
        font3.setPointSize(7)
        font3.setBold(False)
        self._measure_label_5.setFont(font3)
        self._measure_label_5.setStyleSheet(u"color: black;")

        self.retranslateUi(record_widget)

        QMetaObject.connectSlotsByName(record_widget)
    # setupUi

    def retranslateUi(self, record_widget):
        record_widget.setWindowTitle(QCoreApplication.translate("record_widget", u"Form", None))
        self.run_button.setText(QCoreApplication.translate("record_widget", u"Run", None))
        self._measure_label.setText(QCoreApplication.translate("record_widget", u"Record", None))
        self.time_label.setText(QCoreApplication.translate("record_widget", u"00:00:00.000", None))
        self.points_label.setText(QCoreApplication.translate("record_widget", u"0", None))
        self._measure_label_2.setText(QCoreApplication.translate("record_widget", u"Directory", None))
        self._measure_label_3.setText(QCoreApplication.translate("record_widget", u"Stem", None))
        self._measure_label_4.setText(QCoreApplication.translate("record_widget", u"Number", None))
        self._measure_label_5.setText(QCoreApplication.translate("record_widget", u"root/directory/stem_number.data", None))
    # retranslateUi

