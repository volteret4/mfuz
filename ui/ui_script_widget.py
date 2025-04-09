# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'script_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)
import rc_images

class Ui_ScriptWidget(object):
    def setupUi(self, ScriptWidget):
        if not ScriptWidget.objectName():
            ScriptWidget.setObjectName(u"ScriptWidget")
        ScriptWidget.resize(400, 150)
        self.main_layout = QVBoxLayout(ScriptWidget)
        self.main_layout.setSpacing(5)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.title_container = QWidget(ScriptWidget)
        self.title_container.setObjectName(u"title_container")
        self.title_layout = QHBoxLayout(self.title_container)
        self.title_layout.setSpacing(10)
        self.title_layout.setObjectName(u"title_layout")
        self.title_layout.setContentsMargins(10, 5, 10, 5)
        self.title = QLabel(self.title_container)
        self.title.setObjectName(u"title")

        self.title_layout.addWidget(self.title)

        self.save_button = QPushButton(self.title_container)
        self.save_button.setObjectName(u"save_button")
        self.save_button.setMaximumSize(QSize(40, 40))
        icon = QIcon()
        icon.addFile(u":/services/b_save", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_button.setIcon(icon)
        self.save_button.setIconSize(QSize(36, 36))
        self.save_button.setProperty(u"fixedSize", QSize(60, 25))

        self.title_layout.addWidget(self.save_button)

        self.run_button = QPushButton(self.title_container)
        self.run_button.setObjectName(u"run_button")
        self.run_button.setMaximumSize(QSize(40, 40))
        icon1 = QIcon()
        icon1.addFile(u":/services/b_play", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.run_button.setIcon(icon1)
        self.run_button.setIconSize(QSize(36, 36))
        self.run_button.setProperty(u"fixedSize", QSize(60, 25))

        self.title_layout.addWidget(self.run_button)


        self.main_layout.addWidget(self.title_container)

        self.args_container = QWidget(ScriptWidget)
        self.args_container.setObjectName(u"args_container")
        self.args_layout = QVBoxLayout(self.args_container)
        self.args_layout.setSpacing(5)
        self.args_layout.setObjectName(u"args_layout")
        self.args_layout.setContentsMargins(10, 0, 10, 5)
        self.args_grid = QGridLayout()
        self.args_grid.setSpacing(10)
        self.args_grid.setObjectName(u"args_grid")

        self.args_layout.addLayout(self.args_grid)


        self.main_layout.addWidget(self.args_container)

        self.line = QWidget(ScriptWidget)
        self.line.setObjectName(u"line")
        self.line.setMinimumSize(QSize(0, 1))
        self.line.setMaximumSize(QSize(16777215, 1))

        self.main_layout.addWidget(self.line)


        self.retranslateUi(ScriptWidget)

        QMetaObject.connectSlotsByName(ScriptWidget)
    # setupUi

    def retranslateUi(self, ScriptWidget):
        self.title.setStyleSheet(QCoreApplication.translate("ScriptWidget", u"font-weight: bold; cursor: pointer;", None))
        self.title.setText(QCoreApplication.translate("ScriptWidget", u"Script Name", None))
#if QT_CONFIG(tooltip)
        self.save_button.setToolTip(QCoreApplication.translate("ScriptWidget", u"Guardar", None))
#endif // QT_CONFIG(tooltip)
        self.save_button.setStyleSheet(QCoreApplication.translate("ScriptWidget", u"QPushButton {\n"
"  border: 1px solid;\n"
"  border-radius: 3px;\n"
"}", None))
        self.save_button.setText("")
#if QT_CONFIG(tooltip)
        self.run_button.setToolTip(QCoreApplication.translate("ScriptWidget", u"Correr script", None))
#endif // QT_CONFIG(tooltip)
        self.run_button.setStyleSheet(QCoreApplication.translate("ScriptWidget", u"QPushButton {\n"
"  border: 1px solid;\n"
"  border-radius: 3px;\n"
"}", None))
        self.run_button.setText("")
        self.line.setStyleSheet(QCoreApplication.translate("ScriptWidget", u"background-color: rgba(128, 128, 128, 0.3);", None))
        pass
    # retranslateUi

