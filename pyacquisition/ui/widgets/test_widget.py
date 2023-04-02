# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'test.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QTextEdit,
    QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(863, 314)
        self.layoutWidget = QWidget(Form)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.layoutWidget.setGeometry(QRect(10, 10, 258, 295))
        self.message_layout = QVBoxLayout(self.layoutWidget)
        self.message_layout.setObjectName(u"message_layout")
        self.message_layout.setContentsMargins(0, 0, 0, 0)
        self.message_label = QLabel(self.layoutWidget)
        self.message_label.setObjectName(u"message_label")

        self.message_layout.addWidget(self.message_label)

        self.message_edit = QLineEdit(self.layoutWidget)
        self.message_edit.setObjectName(u"message_edit")

        self.message_layout.addWidget(self.message_edit)

        self.send_button = QPushButton(self.layoutWidget)
        self.send_button.setObjectName(u"send_button")

        self.message_layout.addWidget(self.send_button)

        self.response_label = QLabel(self.layoutWidget)
        self.response_label.setObjectName(u"response_label")

        self.message_layout.addWidget(self.response_label)

        self.response_edit = QTextEdit(self.layoutWidget)
        self.response_edit.setObjectName(u"response_edit")
        self.response_edit.setReadOnly(True)

        self.message_layout.addWidget(self.response_edit)

        self.layoutWidget1 = QWidget(Form)
        self.layoutWidget1.setObjectName(u"layoutWidget1")
        self.layoutWidget1.setGeometry(QRect(280, 11, 258, 295))
        self.query_layout = QVBoxLayout(self.layoutWidget1)
        self.query_layout.setObjectName(u"query_layout")
        self.query_layout.setContentsMargins(0, 0, 0, 0)
        self.query_label = QLabel(self.layoutWidget1)
        self.query_label.setObjectName(u"query_label")

        self.query_layout.addWidget(self.query_label)

        self.query_combo = QComboBox(self.layoutWidget1)
        self.query_combo.setObjectName(u"query_combo")

        self.query_layout.addWidget(self.query_combo)

        self.query_button = QPushButton(self.layoutWidget1)
        self.query_button.setObjectName(u"query_button")

        self.query_layout.addWidget(self.query_button)

        self.response_label_2 = QLabel(self.layoutWidget1)
        self.response_label_2.setObjectName(u"response_label_2")

        self.query_layout.addWidget(self.response_label_2)

        self.query_response_edit = QTextEdit(self.layoutWidget1)
        self.query_response_edit.setObjectName(u"query_response_edit")
        self.query_response_edit.setReadOnly(True)

        self.query_layout.addWidget(self.query_response_edit)

        self.layoutWidget2 = QWidget(Form)
        self.layoutWidget2.setObjectName(u"layoutWidget2")
        self.layoutWidget2.setGeometry(QRect(550, 10, 301, 291))
        self.command_layout = QVBoxLayout(self.layoutWidget2)
        self.command_layout.setObjectName(u"command_layout")
        self.command_layout.setContentsMargins(0, 0, 0, 0)
        self.command_label = QLabel(self.layoutWidget2)
        self.command_label.setObjectName(u"command_label")

        self.command_layout.addWidget(self.command_label)

        self.command_combo = QComboBox(self.layoutWidget2)
        self.command_combo.setObjectName(u"command_combo")

        self.command_layout.addWidget(self.command_combo)

        self.command_args_layout = QVBoxLayout()
        self.command_args_layout.setObjectName(u"command_args_layout")

        self.command_layout.addLayout(self.command_args_layout)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.command_layout.addItem(self.verticalSpacer)

        self.command_button = QPushButton(self.layoutWidget2)
        self.command_button.setObjectName(u"command_button")

        self.command_layout.addWidget(self.command_button)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.message_label.setText(QCoreApplication.translate("Form", u"Message:", None))
        self.send_button.setText(QCoreApplication.translate("Form", u"Send", None))
        self.response_label.setText(QCoreApplication.translate("Form", u"Response:", None))
        self.query_label.setText(QCoreApplication.translate("Form", u"Queries:", None))
        self.query_button.setText(QCoreApplication.translate("Form", u"Run", None))
        self.response_label_2.setText(QCoreApplication.translate("Form", u"Response:", None))
        self.command_label.setText(QCoreApplication.translate("Form", u"Commands:", None))
        self.command_button.setText(QCoreApplication.translate("Form", u"Run", None))
    # retranslateUi

