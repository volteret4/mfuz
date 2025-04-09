# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'script_details_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout,
    QPushButton, QSizePolicy, QTextEdit, QVBoxLayout,
    QWidget)
import rc_images

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

        self.frame = QFrame(ScriptDetailsDialog)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.NoFrame)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.frame.setLineWidth(0)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.close_button = QPushButton(self.frame)
        self.close_button.setObjectName(u"close_button")
        self.close_button.setMaximumSize(QSize(40, 40))
        icon = QIcon()
        icon.addFile(u":/services/msgsent", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.close_button.setIcon(icon)
        self.close_button.setIconSize(QSize(36, 36))

        self.horizontalLayout.addWidget(self.close_button)


        self.verticalLayout.addWidget(self.frame)


        self.retranslateUi(ScriptDetailsDialog)

        QMetaObject.connectSlotsByName(ScriptDetailsDialog)
    # setupUi

    def retranslateUi(self, ScriptDetailsDialog):
        ScriptDetailsDialog.setWindowTitle(QCoreApplication.translate("ScriptDetailsDialog", u"Script Details", None))
#if QT_CONFIG(tooltip)
        self.close_button.setToolTip(QCoreApplication.translate("ScriptDetailsDialog", u"Aceptar", None))
#endif // QT_CONFIG(tooltip)
        self.close_button.setText("")
    # retranslateUi

