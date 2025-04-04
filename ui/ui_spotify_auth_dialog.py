# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'spotify_auth_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QFrame, QLabel, QLineEdit, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_AuthDialog(object):
    def setupUi(self, AuthDialog):
        if not AuthDialog.objectName():
            AuthDialog.setObjectName(u"AuthDialog")
        AuthDialog.resize(500, 350)
        self.verticalLayout = QVBoxLayout(AuthDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.auth_title = QLabel(AuthDialog)
        self.auth_title.setObjectName(u"auth_title")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.auth_title.setFont(font)
        self.auth_title.setAlignment(Qt.AlignCenter)

        self.verticalLayout.addWidget(self.auth_title)

        self.instructions_frame = QFrame(AuthDialog)
        self.instructions_frame.setObjectName(u"instructions_frame")
        self.instructions_frame.setFrameShape(QFrame.StyledPanel)
        self.instructions_frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.instructions_frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.instructions_label = QLabel(self.instructions_frame)
        self.instructions_label.setObjectName(u"instructions_label")
        self.instructions_label.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.instructions_label.setWordWrap(True)

        self.verticalLayout_2.addWidget(self.instructions_label)


        self.verticalLayout.addWidget(self.instructions_frame)

        self.auth_url_field = QLineEdit(AuthDialog)
        self.auth_url_field.setObjectName(u"auth_url_field")
        self.auth_url_field.setReadOnly(True)

        self.verticalLayout.addWidget(self.auth_url_field)

        self.redirect_label = QLabel(AuthDialog)
        self.redirect_label.setObjectName(u"redirect_label")

        self.verticalLayout.addWidget(self.redirect_label)

        self.redirect_url_field = QLineEdit(AuthDialog)
        self.redirect_url_field.setObjectName(u"redirect_url_field")

        self.verticalLayout.addWidget(self.redirect_url_field)

        self.button_box = QDialogButtonBox(AuthDialog)
        self.button_box.setObjectName(u"button_box")
        self.button_box.setOrientation(Qt.Horizontal)
        self.button_box.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.button_box)


        self.retranslateUi(AuthDialog)
        self.button_box.accepted.connect(AuthDialog.accept)
        self.button_box.rejected.connect(AuthDialog.reject)

        QMetaObject.connectSlotsByName(AuthDialog)
    # setupUi

    def retranslateUi(self, AuthDialog):
        AuthDialog.setWindowTitle(QCoreApplication.translate("AuthDialog", u"Autorizaci\u00f3n de Spotify", None))
        self.auth_title.setText(QCoreApplication.translate("AuthDialog", u"Autorizaci\u00f3n de Spotify Requerida", None))
        self.instructions_label.setText(QCoreApplication.translate("AuthDialog", u"Para usar las funciones de Spotify, necesita autorizar esta aplicaci\u00f3n.\n"
"\n"
"1. Copie el siguiente enlace y \u00e1bralo manualmente en su navegador:\n"
"\n"
"2. Inicie sesi\u00f3n en Spotify si se le solicita.\n"
"\n"
"3. Haga clic en 'Agree' para autorizar la aplicaci\u00f3n.\n"
"\n"
"4. Ser\u00e1 redirigido a una p\u00e1gina. Copie la URL completa de esa p\u00e1gina.", None))
        self.redirect_label.setText(QCoreApplication.translate("AuthDialog", u"Despu\u00e9s de autorizar, ingrese la URL de redirecci\u00f3n:", None))
    # retranslateUi

