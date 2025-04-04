# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'spotify_track_item.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QWidget)

class Ui_TrackItem(object):
    def setupUi(self, TrackItem):
        if not TrackItem.objectName():
            TrackItem.setObjectName(u"TrackItem")
        TrackItem.resize(400, 50)
        TrackItem.setMinimumSize(QSize(0, 50))
        self.horizontalLayout = QHBoxLayout(TrackItem)
        self.horizontalLayout.setSpacing(5)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(5, 5, 5, 5)
        self.track_label = QLabel(TrackItem)
        self.track_label.setObjectName(u"track_label")
        self.track_label.setWordWrap(True)

        self.horizontalLayout.addWidget(self.track_label)

        self.play_button = QPushButton(TrackItem)
        self.play_button.setObjectName(u"play_button")
        self.play_button.setMinimumSize(QSize(30, 0))
        self.play_button.setMaximumSize(QSize(30, 16777215))
        self.play_button.setStyleSheet(u"QPushButton {\n"
"  border: none;\n"
"  padding: 5px;\n"
"}\n"
"QPushButton:hover {\n"
"  background-color: rgba(0, 255, 0, 0.2);\n"
"}")

        self.horizontalLayout.addWidget(self.play_button)

        self.action_button = QPushButton(TrackItem)
        self.action_button.setObjectName(u"action_button")
        self.action_button.setMinimumSize(QSize(30, 0))
        self.action_button.setMaximumSize(QSize(30, 16777215))
        self.action_button.setStyleSheet(u"QPushButton {\n"
"  border: none;\n"
"  padding: 5px;\n"
"}\n"
"QPushButton:hover {\n"
"  background-color: rgba(0, 0, 255, 0.2);\n"
"}")

        self.horizontalLayout.addWidget(self.action_button)


        self.retranslateUi(TrackItem)

        QMetaObject.connectSlotsByName(TrackItem)
    # setupUi

    def retranslateUi(self, TrackItem):
        self.track_label.setText(QCoreApplication.translate("TrackItem", u"Track Name - Artists", None))
        self.play_button.setText(QCoreApplication.translate("TrackItem", u"\u25b6", None))
        self.action_button.setText(QCoreApplication.translate("TrackItem", u"+", None))
        pass
    # retranslateUi

