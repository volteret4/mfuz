# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'script_details_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QPushButton, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_ScriptDetailsDialog(object):
    def setupUi(self, ScriptDetailsDialog):
        if not ScriptDetailsDialog.objectName():
            ScriptDetailsDialog.setObjectName(u"ScriptDetailsDialog")
        ScriptDetailsDialog.resize(500, 300)
        self.verticalLayout = QVBoxLayout(ScriptDetailsDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.info_text = QTextEdit(ScriptDetailsDialog)
        self.info_text.setObjectName(u"info_text")
        self.info_text.setReadOnly(True)

        self.verticalLayout.addWidget(self.info_text)

        self.close_button = QPushButton(ScriptDetailsDialog)
        self.close_button.setObjectName(u"close_button")

        self.verticalLayout.addWidget(self.close_button)


        self.retranslateUi(ScriptDetailsDialog)

        QMetaObject.connectSlotsByName(ScriptDetailsDialog)
    # setupUi

    def retranslateUi(self, ScriptDetailsDialog):
        ScriptDetailsDialog.setWindowTitle(QCoreApplication.translate("ScriptDetailsDialog", u"Script Details", None))
        self.close_button.setText(QCoreApplication.translate("ScriptDetailsDialog", u"Close", None))
    # retranslateUi

