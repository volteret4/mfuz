# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'script_runner.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget)

class Ui_ScriptRunnerForm(object):
    def setupUi(self, ScriptRunnerForm):
        if not ScriptRunnerForm.objectName():
            ScriptRunnerForm.setObjectName(u"ScriptRunnerForm")
        ScriptRunnerForm.resize(800, 600)
        self.main_layout = QVBoxLayout(ScriptRunnerForm)
        self.main_layout.setSpacing(5)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.header_layout = QHBoxLayout()
        self.header_layout.setObjectName(u"header_layout")
        self.header_layout.setContentsMargins(0, 0, 0, 5)
        self.title_label = QLabel(ScriptRunnerForm)
        self.title_label.setObjectName(u"title_label")

        self.header_layout.addWidget(self.title_label)

        self.toggle_args_btn = QPushButton(ScriptRunnerForm)
        self.toggle_args_btn.setObjectName(u"toggle_args_btn")
        self.toggle_args_btn.setProperty(u"fixedWidth", 140)

        self.header_layout.addWidget(self.toggle_args_btn)


        self.main_layout.addLayout(self.header_layout)

        self.scripts_scroll = QScrollArea(ScriptRunnerForm)
        self.scripts_scroll.setObjectName(u"scripts_scroll")
        self.scripts_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scripts_scroll.setLineWidth(0)
        self.scripts_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scripts_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scripts_scroll.setWidgetResizable(True)
        self.scripts_container = QWidget()
        self.scripts_container.setObjectName(u"scripts_container")
        self.scripts_container.setGeometry(QRect(0, 0, 780, 386))
        self.scripts_layout = QVBoxLayout(self.scripts_container)
        self.scripts_layout.setSpacing(5)
        self.scripts_layout.setObjectName(u"scripts_layout")
        self.scripts_layout.setContentsMargins(0, 0, 0, 0)
        self.scripts_scroll.setWidget(self.scripts_container)

        self.main_layout.addWidget(self.scripts_scroll)

        self.log_text = QTextEdit(ScriptRunnerForm)
        self.log_text.setObjectName(u"log_text")
        self.log_text.setFrameShape(QFrame.Shape.NoFrame)
        self.log_text.setLineWidth(0)
        self.log_text.setReadOnly(True)

        self.main_layout.addWidget(self.log_text)


        self.retranslateUi(ScriptRunnerForm)

        QMetaObject.connectSlotsByName(ScriptRunnerForm)
    # setupUi

    def retranslateUi(self, ScriptRunnerForm):
        ScriptRunnerForm.setWindowTitle(QCoreApplication.translate("ScriptRunnerForm", u"Script Runner", None))
        self.title_label.setStyleSheet(QCoreApplication.translate("ScriptRunnerForm", u"font-weight: bold; font-size: 14px;", None))
        self.title_label.setText(QCoreApplication.translate("ScriptRunnerForm", u"Script Runner", None))
        self.toggle_args_btn.setStyleSheet(QCoreApplication.translate("ScriptRunnerForm", u"QPushButton {\n"
"  border: 1px solid;\n"
"  border-radius: 3px;\n"
"  padding: 5px;\n"
"}", None))
        self.toggle_args_btn.setText(QCoreApplication.translate("ScriptRunnerForm", u"Advanced Settings", None))
        self.scripts_scroll.setStyleSheet(QCoreApplication.translate("ScriptRunnerForm", u"QScrollArea {\n"
"  border: none;\n"
"  background-color: transparent;\n"
"}\n"
"QScrollBar:vertical {\n"
"  width: 10px;\n"
"  background: transparent;\n"
"}\n"
"QScrollBar::handle:vertical {\n"
"  background: rgba(128, 128, 128, 0.5);\n"
"  border-radius: 5px;\n"
"}\n"
"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {\n"
"  height: 0px;\n"
"}", None))
        self.log_text.setStyleSheet(QCoreApplication.translate("ScriptRunnerForm", u"QTextEdit {\n"
"  border: 1px solid;\n"
"  border-radius: 3px;\n"
"  padding: 5px;\n"
"}", None))
    # retranslateUi

