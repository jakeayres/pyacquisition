# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'query_widget.ui'
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
    QPushButton, QSizePolicy, QSpacerItem, QTextEdit,
    QVBoxLayout, QWidget)

class Ui_query_widget(object):
    def setupUi(self, query_widget):
        if not query_widget.objectName():
            query_widget.setObjectName(u"query_widget")
        query_widget.resize(600, 239)
        query_widget.setStyleSheet(u"background-color: white;\n"
"")
        self._query_label = QLabel(query_widget)
        self._query_label.setObjectName(u"_query_label")
        self._query_label.setGeometry(QRect(10, 10, 191, 16))
        self._query_label.setAlignment(Qt.AlignCenter)
        self.name_label = QLabel(query_widget)
        self.name_label.setObjectName(u"name_label")
        self.name_label.setGeometry(QRect(10, 30, 191, 16))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.name_label.setFont(font)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.line = QFrame(query_widget)
        self.line.setObjectName(u"line")
        self.line.setGeometry(QRect(10, 50, 191, 16))
        self.line.setStyleSheet(u"")
        self.line.setFrameShadow(QFrame.Plain)
        self.line.setLineWidth(1)
        self.line.setFrameShape(QFrame.HLine)
        self.response_edit = QTextEdit(query_widget)
        self.response_edit.setObjectName(u"response_edit")
        self.response_edit.setGeometry(QRect(220, 30, 181, 201))
        self.response_edit.setStyleSheet(u"")
        self._response_label = QLabel(query_widget)
        self._response_label.setObjectName(u"_response_label")
        self._response_label.setGeometry(QRect(220, 10, 91, 16))
        self.verticalLayoutWidget = QWidget(query_widget)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(410, 30, 181, 201))
        self.response_layout = QVBoxLayout(self.verticalLayoutWidget)
        self.response_layout.setObjectName(u"response_layout")
        self.response_layout.setContentsMargins(0, 0, 0, 0)
        self._response_label_2 = QLabel(query_widget)
        self._response_label_2.setObjectName(u"_response_label_2")
        self._response_label_2.setGeometry(QRect(410, 10, 101, 16))
        self.widget = QWidget(query_widget)
        self.widget.setObjectName(u"widget")
        self.widget.setGeometry(QRect(10, 70, 191, 161))
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self._args_label = QLabel(self.widget)
        self._args_label.setObjectName(u"_args_label")

        self.verticalLayout.addWidget(self._args_label)

        self.args_form = QFormLayout()
        self.args_form.setObjectName(u"args_form")

        self.verticalLayout.addLayout(self.args_form)

        self.vertical_spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout.addItem(self.vertical_spacer)

        self.send_button = QPushButton(self.widget)
        self.send_button.setObjectName(u"send_button")

        self.verticalLayout.addWidget(self.send_button)


        self.retranslateUi(query_widget)

        QMetaObject.connectSlotsByName(query_widget)
    # setupUi

    def retranslateUi(self, query_widget):
        query_widget.setWindowTitle(QCoreApplication.translate("query_widget", u"Form", None))
        self._query_label.setText(QCoreApplication.translate("query_widget", u"Query", None))
        self.name_label.setText(QCoreApplication.translate("query_widget", u"query_name", None))
        self._response_label.setText(QCoreApplication.translate("query_widget", u"Response Text:", None))
        self._response_label_2.setText(QCoreApplication.translate("query_widget", u"Response Widgets:", None))
        self._args_label.setText(QCoreApplication.translate("query_widget", u"Args:", None))
        self.send_button.setText(QCoreApplication.translate("query_widget", u"Send", None))
    # retranslateUi

