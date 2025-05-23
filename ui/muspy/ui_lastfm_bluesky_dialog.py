# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'lastfm_bluesky_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialogButtonBox,
    QHBoxLayout, QLabel, QSizePolicy, QSpinBox,
    QStackedWidget, QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(534, 322)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.stackedWidget = QStackedWidget(Form)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.page = QWidget()
        self.page.setObjectName(u"page")
        self.verticalLayout_2 = QVBoxLayout(self.page)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.widget = QWidget(self.page)
        self.widget.setObjectName(u"widget")
        self.verticalLayout_3 = QVBoxLayout(self.widget)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.widget_2 = QWidget(self.widget)
        self.widget_2.setObjectName(u"widget_2")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_2.sizePolicy().hasHeightForWidth())
        self.widget_2.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(self.widget_2)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.period_label = QLabel(self.widget_2)
        self.period_label.setObjectName(u"period_label")

        self.horizontalLayout.addWidget(self.period_label)

        self.period_combo = QComboBox(self.widget_2)
        self.period_combo.addItem("")
        self.period_combo.addItem("")
        self.period_combo.addItem("")
        self.period_combo.addItem("")
        self.period_combo.addItem("")
        self.period_combo.addItem("")
        self.period_combo.setObjectName(u"period_combo")

        self.horizontalLayout.addWidget(self.period_combo)


        self.verticalLayout_3.addWidget(self.widget_2)

        self.widget_3 = QWidget(self.widget)
        self.widget_3.setObjectName(u"widget_3")
        sizePolicy.setHeightForWidth(self.widget_3.sizePolicy().hasHeightForWidth())
        self.widget_3.setSizePolicy(sizePolicy)
        self.horizontalLayout_2 = QHBoxLayout(self.widget_3)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.count_label = QLabel(self.widget_3)
        self.count_label.setObjectName(u"count_label")

        self.horizontalLayout_2.addWidget(self.count_label)

        self.count_spin = QSpinBox(self.widget_3)
        self.count_spin.setObjectName(u"count_spin")

        self.horizontalLayout_2.addWidget(self.count_spin)


        self.verticalLayout_3.addWidget(self.widget_3)


        self.verticalLayout_2.addWidget(self.widget)

        self.buttonBox = QDialogButtonBox(self.page)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout_2.addWidget(self.buttonBox)

        self.stackedWidget.addWidget(self.page)
        self.page_2 = QWidget()
        self.page_2.setObjectName(u"page_2")
        self.stackedWidget.addWidget(self.page_2)

        self.verticalLayout.addWidget(self.stackedWidget)


        self.retranslateUi(Form)

        self.period_combo.setCurrentIndex(5)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.period_label.setText(QCoreApplication.translate("Form", u"Per\u00edodo de tiempo:", None))
        self.period_combo.setItemText(0, QCoreApplication.translate("Form", u"7 d\u00edas", None))
        self.period_combo.setItemText(1, QCoreApplication.translate("Form", u"1 mes", None))
        self.period_combo.setItemText(2, QCoreApplication.translate("Form", u"3 meses", None))
        self.period_combo.setItemText(3, QCoreApplication.translate("Form", u"6 meses", None))
        self.period_combo.setItemText(4, QCoreApplication.translate("Form", u"1 a\u00f1o", None))
        self.period_combo.setItemText(5, QCoreApplication.translate("Form", u"Siempre", None))

        self.count_label.setText(QCoreApplication.translate("Form", u"N\u00famero de artistas:", None))
    # retranslateUi

