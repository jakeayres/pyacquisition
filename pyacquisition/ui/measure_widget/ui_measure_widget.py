# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'measure_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

class Ui_measure_widget(object):
    def setupUi(self, measure_widget):
        if not measure_widget.objectName():
            measure_widget.setObjectName(u"measure_widget")
        measure_widget.resize(250, 388)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(measure_widget.sizePolicy().hasHeightForWidth())
        measure_widget.setSizePolicy(sizePolicy)
        measure_widget.setMinimumSize(QSize(250, 100))
        measure_widget.setMaximumSize(QSize(250, 16777215))
        self.gridLayout = QGridLayout(measure_widget)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout = QVBoxLayout()
        self.widget_layout.setSpacing(0)
        self.widget_layout.setObjectName(u"widget_layout")
        self.title_widget = QWidget(measure_widget)
        self.title_widget.setObjectName(u"title_widget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.title_widget.sizePolicy().hasHeightForWidth())
        self.title_widget.setSizePolicy(sizePolicy1)
        self.title_widget.setMinimumSize(QSize(0, 50))
        self.title_widget.setStyleSheet(u"background: rgb(40, 35, 75);")
        self.run_button = QPushButton(self.title_widget)
        self.run_button.setObjectName(u"run_button")
        self.run_button.setGeometry(QRect(160, 10, 80, 30))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.run_button.setFont(font)
        self.run_button.setStyleSheet(u"background: rgb(100, 200, 25);\n"
"border-radius: 5px;\n"
"color: white;")
        self._measure_label = QLabel(self.title_widget)
        self._measure_label.setObjectName(u"_measure_label")
        self._measure_label.setGeometry(QRect(20, 0, 91, 51))
        font1 = QFont()
        font1.setPointSize(12)
        font1.setBold(True)
        self._measure_label.setFont(font1)
        self._measure_label.setStyleSheet(u"color: white;")

        self.widget_layout.addWidget(self.title_widget)

        self.bar_widget = QWidget(measure_widget)
        self.bar_widget.setObjectName(u"bar_widget")
        self.bar_widget.setEnabled(True)
        sizePolicy2 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.bar_widget.sizePolicy().hasHeightForWidth())
        self.bar_widget.setSizePolicy(sizePolicy2)
        self.bar_widget.setMinimumSize(QSize(0, 30))
        self.bar_widget.setStyleSheet(u"background: #CCD;")
        self.time_label = QLabel(self.bar_widget)
        self.time_label.setObjectName(u"time_label")
        self.time_label.setGeometry(QRect(20, 0, 71, 30))
        self.loop_label = QLabel(self.bar_widget)
        self.loop_label.setObjectName(u"loop_label")
        self.loop_label.setGeometry(QRect(160, 0, 71, 30))
        self.loop_label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.widget_layout.addWidget(self.bar_widget, 0, Qt.AlignTop)

        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(1)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(-1, 1, -1, 1)

        self.widget_layout.addLayout(self.main_layout)

        self.verticalSpacer = QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)

        self.widget_layout.addItem(self.verticalSpacer)


        self.gridLayout.addLayout(self.widget_layout, 0, 0, 1, 1)


        self.retranslateUi(measure_widget)

        QMetaObject.connectSlotsByName(measure_widget)
    # setupUi

    def retranslateUi(self, measure_widget):
        measure_widget.setWindowTitle(QCoreApplication.translate("measure_widget", u"Form", None))
        self.run_button.setText(QCoreApplication.translate("measure_widget", u"Run", None))
        self._measure_label.setText(QCoreApplication.translate("measure_widget", u"Measure", None))
        self.time_label.setText(QCoreApplication.translate("measure_widget", u"00:00:00.000", None))
        self.loop_label.setText(QCoreApplication.translate("measure_widget", u"00.000", None))
    # retranslateUi

