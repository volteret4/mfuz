# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'muspy_credentials.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialogButtonBox, QHBoxLayout,
    QLabel, QLineEdit, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(400, 300)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.widget = QWidget(Form)
        self.widget.setObjectName(u"widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.horizontalLayout_4 = QHBoxLayout(self.widget)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.twitter_client_id = QLabel(self.widget)
        self.twitter_client_id.setObjectName(u"twitter_client_id")
        self.twitter_client_id.setMinimumSize(QSize(70, 0))

        self.horizontalLayout_4.addWidget(self.twitter_client_id)

        self.client_id_line = QLineEdit(self.widget)
        self.client_id_line.setObjectName(u"client_id_line")

        self.horizontalLayout_4.addWidget(self.client_id_line)


        self.verticalLayout.addWidget(self.widget)

        self.widget_2 = QWidget(Form)
        self.widget_2.setObjectName(u"widget_2")
        sizePolicy.setHeightForWidth(self.widget_2.sizePolicy().hasHeightForWidth())
        self.widget_2.setSizePolicy(sizePolicy)
        self.horizontalLayout_3 = QHBoxLayout(self.widget_2)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.twitter_client_secret = QLabel(self.widget_2)
        self.twitter_client_secret.setObjectName(u"twitter_client_secret")
        self.twitter_client_secret.setMinimumSize(QSize(70, 0))

        self.horizontalLayout_3.addWidget(self.twitter_client_secret)

        self.client_secret_line = QLineEdit(self.widget_2)
        self.client_secret_line.setObjectName(u"client_secret_line")

        self.horizontalLayout_3.addWidget(self.client_secret_line)


        self.verticalLayout.addWidget(self.widget_2)

        self.widget_3 = QWidget(Form)
        self.widget_3.setObjectName(u"widget_3")
        sizePolicy.setHeightForWidth(self.widget_3.sizePolicy().hasHeightForWidth())
        self.widget_3.setSizePolicy(sizePolicy)
        self.horizontalLayout_2 = QHBoxLayout(self.widget_3)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.twitter_callback_uri = QLabel(self.widget_3)
        self.twitter_callback_uri.setObjectName(u"twitter_callback_uri")
        self.twitter_callback_uri.setMinimumSize(QSize(70, 0))

        self.horizontalLayout_2.addWidget(self.twitter_callback_uri)

        self.callback_url_line = QLineEdit(self.widget_3)
        self.callback_url_line.setObjectName(u"callback_url_line")

        self.horizontalLayout_2.addWidget(self.callback_url_line)


        self.verticalLayout.addWidget(self.widget_3)

        self.widget_4 = QWidget(Form)
        self.widget_4.setObjectName(u"widget_4")
        sizePolicy.setHeightForWidth(self.widget_4.sizePolicy().hasHeightForWidth())
        self.widget_4.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(self.widget_4)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonBox = QDialogButtonBox(self.widget_4)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.horizontalLayout.addWidget(self.buttonBox)


        self.verticalLayout.addWidget(self.widget_4)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.twitter_client_id.setText(QCoreApplication.translate("Form", u"client id", None))
        self.twitter_client_secret.setText(QCoreApplication.translate("Form", u"client secret", None))
        self.twitter_callback_uri.setText(QCoreApplication.translate("Form", u"callback url", None))
    # retranslateUi

