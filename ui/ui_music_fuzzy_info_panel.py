# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'music_fuzzy_info_panel.ui'
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
from PySide6.QtWidgets import (QApplication, QLabel, QLayout, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_InfoPanel(object):
    def setupUi(self, InfoPanel):
        if not InfoPanel.objectName():
            InfoPanel.setObjectName(u"InfoPanel")
        InfoPanel.resize(900, 565)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(InfoPanel.sizePolicy().hasHeightForWidth())
        InfoPanel.setSizePolicy(sizePolicy)
        InfoPanel.setMinimumSize(QSize(0, 0))
        InfoPanel.setStyleSheet(u"QLabel { \n"
"  padding: 5px; \n"
"  min-width: 750px;\n"
"}")
        self.verticalLayout = QVBoxLayout(InfoPanel)
        self.verticalLayout.setSpacing(15)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.verticalLayout.setContentsMargins(5, 5, 5, 5)
        self.links_label = QLabel(InfoPanel)
        self.links_label.setObjectName(u"links_label")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.links_label.sizePolicy().hasHeightForWidth())
        self.links_label.setSizePolicy(sizePolicy1)
        self.links_label.setStyleSheet(u"font-family: Inter; font-size: 13px;")
        self.links_label.setTextFormat(Qt.TextFormat.RichText)
        self.links_label.setWordWrap(True)
        self.links_label.setOpenExternalLinks(True)

        self.verticalLayout.addWidget(self.links_label)

        self.wikipedia_artist_label = QLabel(InfoPanel)
        self.wikipedia_artist_label.setObjectName(u"wikipedia_artist_label")
        sizePolicy.setHeightForWidth(self.wikipedia_artist_label.sizePolicy().hasHeightForWidth())
        self.wikipedia_artist_label.setSizePolicy(sizePolicy)
        self.wikipedia_artist_label.setStyleSheet(u"font-family: Inter; font-size: 13px;")
        self.wikipedia_artist_label.setTextFormat(Qt.TextFormat.RichText)
        self.wikipedia_artist_label.setWordWrap(True)
        self.wikipedia_artist_label.setOpenExternalLinks(True)

        self.verticalLayout.addWidget(self.wikipedia_artist_label)

        self.lastfm_label = QLabel(InfoPanel)
        self.lastfm_label.setObjectName(u"lastfm_label")
        sizePolicy.setHeightForWidth(self.lastfm_label.sizePolicy().hasHeightForWidth())
        self.lastfm_label.setSizePolicy(sizePolicy)
        self.lastfm_label.setStyleSheet(u"font-family: Inter; font-size: 13px;")
        self.lastfm_label.setTextFormat(Qt.TextFormat.RichText)
        self.lastfm_label.setWordWrap(True)
        self.lastfm_label.setOpenExternalLinks(True)

        self.verticalLayout.addWidget(self.lastfm_label)

        self.wikipedia_album_label = QLabel(InfoPanel)
        self.wikipedia_album_label.setObjectName(u"wikipedia_album_label")
        sizePolicy.setHeightForWidth(self.wikipedia_album_label.sizePolicy().hasHeightForWidth())
        self.wikipedia_album_label.setSizePolicy(sizePolicy)
        self.wikipedia_album_label.setStyleSheet(u"font-family: Inter; font-size: 13px;")
        self.wikipedia_album_label.setTextFormat(Qt.TextFormat.RichText)
        self.wikipedia_album_label.setWordWrap(True)
        self.wikipedia_album_label.setOpenExternalLinks(True)

        self.verticalLayout.addWidget(self.wikipedia_album_label)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(InfoPanel)

        QMetaObject.connectSlotsByName(InfoPanel)
    # setupUi

    def retranslateUi(self, InfoPanel):
        pass
    # retranslateUi

