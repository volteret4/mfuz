# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'radicale_config_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_RadicaleConfigDialog(object):
    def setupUi(self, RadicaleConfigDialog):
        if not RadicaleConfigDialog.objectName():
            RadicaleConfigDialog.setObjectName(u"RadicaleConfigDialog")
        RadicaleConfigDialog.resize(400, 200)
        self.verticalLayout = QVBoxLayout(RadicaleConfigDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.label = QLabel(RadicaleConfigDialog)
        self.label.setObjectName(u"label")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label)

        self.url_input = QLineEdit(RadicaleConfigDialog)
        self.url_input.setObjectName(u"url_input")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.url_input)

        self.label_2 = QLabel(RadicaleConfigDialog)
        self.label_2.setObjectName(u"label_2")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_2)

        self.username_input = QLineEdit(RadicaleConfigDialog)
        self.username_input.setObjectName(u"username_input")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.username_input)

        self.label_3 = QLabel(RadicaleConfigDialog)
        self.label_3.setObjectName(u"label_3")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.label_3)

        self.password_input = QLineEdit(RadicaleConfigDialog)
        self.password_input.setObjectName(u"password_input")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.password_input)

        self.label_4 = QLabel(RadicaleConfigDialog)
        self.label_4.setObjectName(u"label_4")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.label_4)

        self.calendar_input = QLineEdit(RadicaleConfigDialog)
        self.calendar_input.setObjectName(u"calendar_input")

        self.formLayout.setWidget(3, QFormLayout.FieldRole, self.calendar_input)


        self.verticalLayout.addLayout(self.formLayout)

        self.button_box = QHBoxLayout()
        self.button_box.setObjectName(u"button_box")
        self.save_button = QPushButton(RadicaleConfigDialog)
        self.save_button.setObjectName(u"save_button")

        self.button_box.addWidget(self.save_button)

        self.cancel_button = QPushButton(RadicaleConfigDialog)
        self.cancel_button.setObjectName(u"cancel_button")

        self.button_box.addWidget(self.cancel_button)


        self.verticalLayout.addLayout(self.button_box)


        self.retranslateUi(RadicaleConfigDialog)

        QMetaObject.connectSlotsByName(RadicaleConfigDialog)
    # setupUi

    def retranslateUi(self, RadicaleConfigDialog):
        RadicaleConfigDialog.setWindowTitle(QCoreApplication.translate("RadicaleConfigDialog", u"Configuraci\u00f3n de Calendario", None))
        self.label.setText(QCoreApplication.translate("RadicaleConfigDialog", u"URL del servidor:", None))
        self.url_input.setText(QCoreApplication.translate("RadicaleConfigDialog", u"http://localhost:5232/", None))
        self.label_2.setText(QCoreApplication.translate("RadicaleConfigDialog", u"Usuario:", None))
        self.label_3.setText(QCoreApplication.translate("RadicaleConfigDialog", u"Contrase\u00f1a:", None))
        self.label_4.setText(QCoreApplication.translate("RadicaleConfigDialog", u"Calendario:", None))
        self.calendar_input.setText(QCoreApplication.translate("RadicaleConfigDialog", u"default", None))
        self.save_button.setText(QCoreApplication.translate("RadicaleConfigDialog", u"Guardar", None))
        self.cancel_button.setText(QCoreApplication.translate("RadicaleConfigDialog", u"Cancelar", None))
    # retranslateUi

