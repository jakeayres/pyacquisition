# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'app.ui'
##
## Created by: Qt User Interface Compiler version 6.4.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QMainWindow, QMenu,
    QMenuBar, QSizePolicy, QStatusBar, QWidget)

class Ui_app(object):
    def setupUi(self, app):
        if not app.objectName():
            app.setObjectName(u"app")
        app.resize(957, 815)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        app.setFont(font)
        self.actionAdd_Instrument = QAction(app)
        self.actionAdd_Instrument.setObjectName(u"actionAdd_Instrument")
        self.actionRemove = QAction(app)
        self.actionRemove.setObjectName(u"actionRemove")
        self.actionLoad_Config = QAction(app)
        self.actionLoad_Config.setObjectName(u"actionLoad_Config")
        self.actionQuery1 = QAction(app)
        self.actionQuery1.setObjectName(u"actionQuery1")
        self.actionQuery2 = QAction(app)
        self.actionQuery2.setObjectName(u"actionQuery2")
        self.actionCommand1 = QAction(app)
        self.actionCommand1.setObjectName(u"actionCommand1")
        self.actionCommand2 = QAction(app)
        self.actionCommand2.setObjectName(u"actionCommand2")
        self.centralwidget = QWidget(app)
        self.centralwidget.setObjectName(u"centralwidget")
        self.widget = QWidget(self.centralwidget)
        self.widget.setObjectName(u"widget")
        self.widget.setGeometry(QRect(0, 0, 261, 761))
        self.widget.setStyleSheet(u"")
        self.gridLayoutWidget = QWidget(self.widget)
        self.gridLayoutWidget.setObjectName(u"gridLayoutWidget")
        self.gridLayoutWidget.setGeometry(QRect(10, 10, 251, 741))
        self.left_layout = QGridLayout(self.gridLayoutWidget)
        self.left_layout.setObjectName(u"left_layout")
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        app.setCentralWidget(self.centralwidget)
        self.menu_bar = QMenuBar(app)
        self.menu_bar.setObjectName(u"menu_bar")
        self.menu_bar.setGeometry(QRect(0, 0, 957, 26))
        self.instruments_menu = QMenu(self.menu_bar)
        self.instruments_menu.setObjectName(u"instruments_menu")
        app.setMenuBar(self.menu_bar)
        self.statusbar = QStatusBar(app)
        self.statusbar.setObjectName(u"statusbar")
        app.setStatusBar(self.statusbar)

        self.menu_bar.addAction(self.instruments_menu.menuAction())

        self.retranslateUi(app)

        QMetaObject.connectSlotsByName(app)
    # setupUi

    def retranslateUi(self, app):
        app.setWindowTitle(QCoreApplication.translate("app", u"MainWindow", None))
        self.actionAdd_Instrument.setText(QCoreApplication.translate("app", u"Add Inst.", None))
        self.actionRemove.setText(QCoreApplication.translate("app", u"Remove Inst.", None))
        self.actionLoad_Config.setText(QCoreApplication.translate("app", u"Load Config", None))
        self.actionQuery1.setText(QCoreApplication.translate("app", u"Query1", None))
        self.actionQuery2.setText(QCoreApplication.translate("app", u"Query2", None))
        self.actionCommand1.setText(QCoreApplication.translate("app", u"Command1", None))
        self.actionCommand2.setText(QCoreApplication.translate("app", u"Command2", None))
        self.instruments_menu.setTitle(QCoreApplication.translate("app", u"Instruments", None))
    # retranslateUi

