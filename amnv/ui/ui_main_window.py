# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
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
from PySide6.QtWidgets import (QApplication, QGroupBox, QMainWindow, QPlainTextEdit,
    QPushButton, QSizePolicy, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(800, 700)
        MainWindow.setMinimumSize(QSize(800, 700))
        MainWindow.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.groupValidation = QGroupBox(self.centralwidget)
        self.groupValidation.setObjectName(u"groupValidation")
        self.groupValidation.setGeometry(QRect(10, 10, 581, 231))
        self.btnT01 = QPushButton(self.groupValidation)
        self.btnT01.setObjectName(u"btnT01")
        self.btnT01.setGeometry(QRect(11, 41, 175, 40))
        self.btnT01.setMinimumSize(QSize(175, 40))
        self.btnT01.setMaximumSize(QSize(16777215, 16777215))
        self.btnT01.setStyleSheet(u"text-align: left;\n"
"padding-left: 10px;")
        self.btnT02 = QPushButton(self.groupValidation)
        self.btnT02.setObjectName(u"btnT02")
        self.btnT02.setGeometry(QRect(11, 87, 175, 40))
        self.btnT02.setMinimumSize(QSize(175, 40))
        self.btnT02.setMaximumSize(QSize(16777215, 16777215))
        self.btnT02.setStyleSheet(u"text-align: left;\n"
"padding-left: 10px;")
        self.btnT03 = QPushButton(self.groupValidation)
        self.btnT03.setObjectName(u"btnT03")
        self.btnT03.setGeometry(QRect(11, 133, 175, 40))
        self.btnT03.setMinimumSize(QSize(175, 40))
        self.btnT03.setMaximumSize(QSize(16777215, 16777215))
        self.btnT03.setStyleSheet(u"text-align: left;\n"
"padding-left: 10px;")
        self.btnT04 = QPushButton(self.groupValidation)
        self.btnT04.setObjectName(u"btnT04")
        self.btnT04.setGeometry(QRect(200, 41, 175, 40))
        self.btnT04.setMinimumSize(QSize(175, 40))
        self.btnT04.setMaximumSize(QSize(16777215, 16777215))
        self.btnT04.setStyleSheet(u"text-align: left;\n"
"padding-left: 10px;")
        self.btnT05 = QPushButton(self.groupValidation)
        self.btnT05.setObjectName(u"btnT05")
        self.btnT05.setGeometry(QRect(200, 87, 175, 40))
        self.btnT05.setMinimumSize(QSize(175, 40))
        self.btnT05.setMaximumSize(QSize(16777215, 16777215))
        self.btnT05.setStyleSheet(u"text-align: left;\n"
"padding-left: 10px;")
        self.btnT06 = QPushButton(self.groupValidation)
        self.btnT06.setObjectName(u"btnT06")
        self.btnT06.setGeometry(QRect(200, 133, 175, 40))
        self.btnT06.setMinimumSize(QSize(175, 40))
        self.btnT06.setMaximumSize(QSize(16777215, 16777215))
        self.btnT06.setStyleSheet(u"text-align: left;\n"
"padding-left: 10px;")
        self.btnT07 = QPushButton(self.groupValidation)
        self.btnT07.setObjectName(u"btnT07")
        self.btnT07.setGeometry(QRect(390, 41, 175, 40))
        self.btnT07.setMinimumSize(QSize(175, 40))
        self.btnT07.setMaximumSize(QSize(16777215, 16777215))
        self.btnT07.setStyleSheet(u"text-align: left;\n"
"padding-left: 10px;")
        self.btnT08 = QPushButton(self.groupValidation)
        self.btnT08.setObjectName(u"btnT08")
        self.btnT08.setGeometry(QRect(390, 87, 175, 40))
        self.btnT08.setMinimumSize(QSize(175, 40))
        self.btnT08.setMaximumSize(QSize(16777215, 16777215))
        self.btnT08.setStyleSheet(u"text-align: left;\n"
"padding-left: 10px;")
        self.btnT09 = QPushButton(self.groupValidation)
        self.btnT09.setObjectName(u"btnT09")
        self.btnT09.setGeometry(QRect(390, 133, 175, 40))
        self.btnT09.setMinimumSize(QSize(175, 40))
        self.btnT09.setMaximumSize(QSize(16777215, 16777215))
        self.btnT09.setStyleSheet(u"text-align: left;\n"
"padding-left: 10px;")
        self.btnA01 = QPushButton(self.groupValidation)
        self.btnA01.setObjectName(u"btnA01")
        self.btnA01.setGeometry(QRect(70, 180, 200, 40))
        self.btnA01.setMinimumSize(QSize(200, 40))
        self.btnA02 = QPushButton(self.groupValidation)
        self.btnA02.setObjectName(u"btnA02")
        self.btnA02.setGeometry(QRect(310, 180, 200, 40))
        self.btnA02.setMinimumSize(QSize(200, 40))
        self.groupControl = QGroupBox(self.centralwidget)
        self.groupControl.setObjectName(u"groupControl")
        self.groupControl.setGeometry(QRect(600, 10, 191, 231))
        self.btnTestStop = QPushButton(self.groupControl)
        self.btnTestStop.setObjectName(u"btnTestStop")
        self.btnTestStop.setGeometry(QRect(20, 150, 151, 26))
        self.btnReadCurrentData = QPushButton(self.groupControl)
        self.btnReadCurrentData.setObjectName(u"btnReadCurrentData")
        self.btnReadCurrentData.setGeometry(QRect(20, 40, 151, 26))
        self.btnResetData = QPushButton(self.groupControl)
        self.btnResetData.setObjectName(u"btnResetData")
        self.btnResetData.setGeometry(QRect(20, 80, 151, 26))
        self.btnOpenLastReport = QPushButton(self.groupControl)
        self.btnOpenLastReport.setObjectName(u"btnOpenLastReport")
        self.btnOpenLastReport.setGeometry(QRect(20, 190, 151, 26))
        self.groupConsole = QGroupBox(self.centralwidget)
        self.groupConsole.setObjectName(u"groupConsole")
        self.groupConsole.setGeometry(QRect(10, 250, 781, 441))
        self.txtConsole = QPlainTextEdit(self.groupConsole)
        self.txtConsole.setObjectName(u"txtConsole")
        self.txtConsole.setGeometry(QRect(10, 30, 761, 371))
        self.txtConsole.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.txtConsole.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.txtConsole.setReadOnly(True)
        self.btnClearConsole = QPushButton(self.groupConsole)
        self.btnClearConsole.setObjectName(u"btnClearConsole")
        self.btnClearConsole.setGeometry(QRect(720, 410, 51, 26))
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Automation Mock NVMe Validation", None))
        self.groupValidation.setTitle(QCoreApplication.translate("MainWindow", u"Validation Tests", None))
        self.btnT01.setText(QCoreApplication.translate("MainWindow", u"T01 Device Baseline", None))
        self.btnT02.setText(QCoreApplication.translate("MainWindow", u"T02 Write / Readback", None))
        self.btnT03.setText(QCoreApplication.translate("MainWindow", u"T03 Invalid Range", None))
        self.btnT04.setText(QCoreApplication.translate("MainWindow", u"T04 Unsupported Cmd", None))
        self.btnT05.setText(QCoreApplication.translate("MainWindow", u"T05 Timeout / Recovery", None))
        self.btnT06.setText(QCoreApplication.translate("MainWindow", u"T06 Data Integrity", None))
        self.btnT07.setText(QCoreApplication.translate("MainWindow", u"T07 Log Parsing", None))
        self.btnT08.setText(QCoreApplication.translate("MainWindow", u"T08 Read FW Error", None))
        self.btnT09.setText(QCoreApplication.translate("MainWindow", u"T09 Write Failure", None))
        self.btnA01.setText(QCoreApplication.translate("MainWindow", u"A01 Full Validation", None))
        self.btnA02.setText(QCoreApplication.translate("MainWindow", u"A02 Fault Campaign", None))
        self.groupControl.setTitle(QCoreApplication.translate("MainWindow", u"Control", None))
        self.btnTestStop.setText(QCoreApplication.translate("MainWindow", u"Test Stop", None))
        self.btnReadCurrentData.setText(QCoreApplication.translate("MainWindow", u"Read Current Data", None))
        self.btnResetData.setText(QCoreApplication.translate("MainWindow", u"Reset Data", None))
        self.btnOpenLastReport.setText(QCoreApplication.translate("MainWindow", u"Open Last Report", None))
        self.groupConsole.setTitle(QCoreApplication.translate("MainWindow", u"Console / Log Viewer", None))
        self.btnClearConsole.setText(QCoreApplication.translate("MainWindow", u"Clear", None))
    # retranslateUi

