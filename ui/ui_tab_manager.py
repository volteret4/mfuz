# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_manager.ui'
##
## Created by: Qt User Interface Compiler version 6.8.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QMainWindow, QSizePolicy, QTabWidget,
    QVBoxLayout, QWidget)

class Ui_TabManager(object):
    def setupUi(self, TabManager):
        if not TabManager.objectName():
            TabManager.setObjectName(u"TabManager")
        TabManager.resize(1200, 800)
        TabManager.setMinimumSize(QSize(1200, 800))
        TabManager.setStyleSheet(u"")
        self.actionReload = QAction(TabManager)
        self.actionReload.setObjectName(u"actionReload")
        self.actionExit = QAction(TabManager)
        self.actionExit.setObjectName(u"actionExit")
        self.actionAbout = QAction(TabManager)
        self.actionAbout.setObjectName(u"actionAbout")
        self.centralwidget = QWidget(TabManager)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tab_widget = QTabWidget(self.centralwidget)
        self.tab_widget.setObjectName(u"tab_widget")

        self.verticalLayout.addWidget(self.tab_widget)

        TabManager.setCentralWidget(self.centralwidget)

        self.retranslateUi(TabManager)

        QMetaObject.connectSlotsByName(TabManager)
    # setupUi

    def retranslateUi(self, TabManager):
        TabManager.setWindowTitle(QCoreApplication.translate("TabManager", u"Multi-Module Manager", None))
        self.actionReload.setText(QCoreApplication.translate("TabManager", u"Recargar m\u00f3dulos", None))
#if QT_CONFIG(shortcut)
        self.actionReload.setShortcut(QCoreApplication.translate("TabManager", u"Ctrl+R", None))
#endif // QT_CONFIG(shortcut)
        self.actionExit.setText(QCoreApplication.translate("TabManager", u"Salir", None))
#if QT_CONFIG(shortcut)
        self.actionExit.setShortcut(QCoreApplication.translate("TabManager", u"Ctrl+Q", None))
#endif // QT_CONFIG(shortcut)
        self.actionAbout.setText(QCoreApplication.translate("TabManager", u"Acerca de", None))
    # retranslateUi

