# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'calendar_module.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_CalendarModule(object):
    def setupUi(self, CalendarModule):
        if not CalendarModule.objectName():
            CalendarModule.setObjectName(u"CalendarModule")
        CalendarModule.resize(800, 600)
        self.verticalLayout = QVBoxLayout(CalendarModule)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setObjectName(u"toolbar_layout")
        self.label = QLabel(CalendarModule)
        self.label.setObjectName(u"label")

        self.toolbar_layout.addWidget(self.label)

        self.calendar_selector = QComboBox(CalendarModule)
        self.calendar_selector.setObjectName(u"calendar_selector")

        self.toolbar_layout.addWidget(self.calendar_selector)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.toolbar_layout.addItem(self.horizontalSpacer)

        self.refresh_button = QPushButton(CalendarModule)
        self.refresh_button.setObjectName(u"refresh_button")

        self.toolbar_layout.addWidget(self.refresh_button)

        self.add_event_button = QPushButton(CalendarModule)
        self.add_event_button.setObjectName(u"add_event_button")

        self.toolbar_layout.addWidget(self.add_event_button)


        self.verticalLayout.addLayout(self.toolbar_layout)

        self.daily_view_container = QWidget(CalendarModule)
        self.daily_view_container.setObjectName(u"daily_view_container")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.daily_view_container.sizePolicy().hasHeightForWidth())
        self.daily_view_container.setSizePolicy(sizePolicy)

        self.verticalLayout.addWidget(self.daily_view_container)


        self.retranslateUi(CalendarModule)

        QMetaObject.connectSlotsByName(CalendarModule)
    # setupUi

    def retranslateUi(self, CalendarModule):
        CalendarModule.setWindowTitle(QCoreApplication.translate("CalendarModule", u"Calendario Radicale", None))
        self.label.setText(QCoreApplication.translate("CalendarModule", u"Calendario:", None))
        self.refresh_button.setText(QCoreApplication.translate("CalendarModule", u"Actualizar", None))
        self.add_event_button.setText(QCoreApplication.translate("CalendarModule", u"Nuevo Evento", None))
    # retranslateUi

