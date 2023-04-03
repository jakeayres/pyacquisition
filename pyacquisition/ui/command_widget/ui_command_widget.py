# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'command_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QFrame, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_command_widget(object):
    def setupUi(self, command_widget):
        if not command_widget.objectName():
            command_widget.setObjectName(u"command_widget")
        command_widget.resize(200, 250)
        command_widget.setStyleSheet(u"background-color: white;")
        self.layoutWidget = QWidget(command_widget)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.layoutWidget.setGeometry(QRect(5, 60, 191, 181))
        self.verticalLayout = QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self._args_label = QLabel(self.layoutWidget)
        self._args_label.setObjectName(u"_args_label")

        self.verticalLayout.addWidget(self._args_label)

        self.args_form = QFormLayout()
        self.args_form.setObjectName(u"args_form")

        self.verticalLayout.addLayout(self.args_form)

        self.vertical_spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout.addItem(self.vertical_spacer)

        self.send_button = QPushButton(self.layoutWidget)
        self.send_button.setObjectName(u"send_button")

        self.verticalLayout.addWidget(self.send_button)

        self._command_label = QLabel(command_widget)
        self._command_label.setObjectName(u"_command_label")
        self._command_label.setGeometry(QRect(5, 0, 191, 16))
        self._command_label.setAlignment(Qt.AlignCenter)
        self.name_label = QLabel(command_widget)
        self.name_label.setObjectName(u"name_label")
        self.name_label.setGeometry(QRect(5, 20, 191, 16))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.name_label.setFont(font)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.line = QFrame(command_widget)
        self.line.setObjectName(u"line")
        self.line.setGeometry(QRect(5, 40, 191, 16))
        self.line.setStyleSheet(u"")
        self.line.setFrameShadow(QFrame.Plain)
        self.line.setLineWidth(1)
        self.line.setFrameShape(QFrame.HLine)

        self.retranslateUi(command_widget)

        QMetaObject.connectSlotsByName(command_widget)
    # setupUi

    def retranslateUi(self, command_widget):
        command_widget.setWindowTitle(QCoreApplication.translate("command_widget", u"Form", None))
        self._args_label.setText(QCoreApplication.translate("command_widget", u"Args:", None))
        self.send_button.setText(QCoreApplication.translate("command_widget", u"Send", None))
        self._command_label.setText(QCoreApplication.translate("command_widget", u"Command", None))
        self.name_label.setText(QCoreApplication.translate("command_widget", u"command_name", None))
    # retranslateUi

