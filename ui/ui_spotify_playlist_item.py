# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'spotify_playlist_item.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QPushButton, QSizePolicy,
    QWidget)

class Ui_PlaylistItem(object):
    def setupUi(self, PlaylistItem):
        if not PlaylistItem.objectName():
            PlaylistItem.setObjectName(u"PlaylistItem")
        PlaylistItem.resize(400, 40)
        PlaylistItem.setMinimumSize(QSize(0, 40))
        self.horizontalLayout = QHBoxLayout(PlaylistItem)
        self.horizontalLayout.setSpacing(5)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(3, 5, 3, 5)
        self.playlist_button = QPushButton(PlaylistItem)
        self.playlist_button.setObjectName(u"playlist_button")
        self.playlist_button.setMinimumSize(QSize(0, 30))
        self.playlist_button.setMaximumSize(QSize(16777215, 30))
        self.playlist_button.setStyleSheet(u"QPushButton {\n"
"  text-align: left;\n"
"  border: none;\n"
"  padding: 5px;\n"
"}\n"
"QPushButton:hover {\n"
"  background-color: rgba(255, 255, 255, 0.1);\n"
"}")

        self.horizontalLayout.addWidget(self.playlist_button)

        self.play_button = QPushButton(PlaylistItem)
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

        self.delete_button = QPushButton(PlaylistItem)
        self.delete_button.setObjectName(u"delete_button")
        self.delete_button.setMinimumSize(QSize(30, 0))
        self.delete_button.setMaximumSize(QSize(30, 16777215))
        self.delete_button.setStyleSheet(u"QPushButton {\n"
"  border: none;\n"
"  padding: 5px;\n"
"}\n"
"QPushButton:hover {\n"
"  background-color: rgba(255, 0, 0, 0.2);\n"
"}")

        self.horizontalLayout.addWidget(self.delete_button)


        self.retranslateUi(PlaylistItem)

        QMetaObject.connectSlotsByName(PlaylistItem)
    # setupUi

    def retranslateUi(self, PlaylistItem):
        self.playlist_button.setText(QCoreApplication.translate("PlaylistItem", u"Playlist Name", None))
        self.play_button.setText(QCoreApplication.translate("PlaylistItem", u"\u25b6", None))
        self.delete_button.setText(QCoreApplication.translate("PlaylistItem", u"\u2716", None))
        pass
    # retranslateUi

