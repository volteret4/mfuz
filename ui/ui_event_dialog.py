# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'event_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.8.3
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QTextEdit,
    QTimeEdit, QVBoxLayout, QWidget)

class Ui_EventDialog(object):
    def setupUi(self, EventDialog):
        if not EventDialog.objectName():
            EventDialog.setObjectName(u"EventDialog")
        EventDialog.resize(400, 300)
        EventDialog.setMinimumSize(QSize(400, 0))
        self.verticalLayout = QVBoxLayout(EventDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(EventDialog)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)

        self.title_edit = QLineEdit(EventDialog)
        self.title_edit.setObjectName(u"title_edit")

        self.verticalLayout.addWidget(self.title_edit)

        self.time_layout = QHBoxLayout()
        self.time_layout.setObjectName(u"time_layout")
        self.label_2 = QLabel(EventDialog)
        self.label_2.setObjectName(u"label_2")

        self.time_layout.addWidget(self.label_2)

        self.start_time = QTimeEdit(EventDialog)
        self.start_time.setObjectName(u"start_time")

        self.time_layout.addWidget(self.start_time)

        self.label_3 = QLabel(EventDialog)
        self.label_3.setObjectName(u"label_3")

        self.time_layout.addWidget(self.label_3)

        self.end_time = QTimeEdit(EventDialog)
        self.end_time.setObjectName(u"end_time")

        self.time_layout.addWidget(self.end_time)


        self.verticalLayout.addLayout(self.time_layout)

        self.label_4 = QLabel(EventDialog)
        self.label_4.setObjectName(u"label_4")

        self.verticalLayout.addWidget(self.label_4)

        self.description_edit = QTextEdit(EventDialog)
        self.description_edit.setObjectName(u"description_edit")
        self.description_edit.setMaximumHeight(100)

        self.verticalLayout.addWidget(self.description_edit)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName(u"button_layout")
        self.cancel_button = QPushButton(EventDialog)
        self.cancel_button.setObjectName(u"cancel_button")

        self.button_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton(EventDialog)
        self.save_button.setObjectName(u"save_button")

        self.button_layout.addWidget(self.save_button)


        self.verticalLayout.addLayout(self.button_layout)


        self.retranslateUi(EventDialog)

        QMetaObject.connectSlotsByName(EventDialog)
    # setupUi

    def retranslateUi(self, EventDialog):
        EventDialog.setWindowTitle(QCoreApplication.translate("EventDialog", u"Evento de Calendario", None))
        self.label.setText(QCoreApplication.translate("EventDialog", u"T\u00edtulo:", None))
        self.label_2.setText(QCoreApplication.translate("EventDialog", u"Hora inicio:", None))
        self.start_time.setDisplayFormat(QCoreApplication.translate("EventDialog", u"HH:mm", None))
        self.label_3.setText(QCoreApplication.translate("EventDialog", u"Hora fin:", None))
        self.end_time.setDisplayFormat(QCoreApplication.translate("EventDialog", u"HH:mm", None))
        self.label_4.setText(QCoreApplication.translate("EventDialog", u"Descripci\u00f3n:", None))
        self.cancel_button.setText(QCoreApplication.translate("EventDialog", u"Cancelar", None))
        self.save_button.setText(QCoreApplication.translate("EventDialog", u"Guardar", None))
    # retranslateUi

