# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'music_fuzzy_metadata_panel.ui'
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
from PySide6.QtWidgets import (QApplication, QLabel, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_MetadataPanel(object):
    def setupUi(self, MetadataPanel):
        if not MetadataPanel.objectName():
            MetadataPanel.setObjectName(u"MetadataPanel")
        MetadataPanel.resize(300, 200)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MetadataPanel.sizePolicy().hasHeightForWidth())
        MetadataPanel.setSizePolicy(sizePolicy)
        MetadataPanel.setStyleSheet(u"QLabel { \n"
"  padding: 2px; \n"
"  min-width: 280px;\n"
"}")
        self.verticalLayout = QVBoxLayout(MetadataPanel)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(2, 2, 2, 2)
        self.metadata_label = QLabel(MetadataPanel)
        self.metadata_label.setObjectName(u"metadata_label")
        sizePolicy.setHeightForWidth(self.metadata_label.sizePolicy().hasHeightForWidth())
        self.metadata_label.setSizePolicy(sizePolicy)
        self.metadata_label.setMinimumSize(QSize(0, 0))
        self.metadata_label.setStyleSheet(u"font-family: Inter; font-size: 12px;")
        self.metadata_label.setTextFormat(Qt.TextFormat.RichText)
        self.metadata_label.setWordWrap(True)
        self.metadata_label.setOpenExternalLinks(True)

        self.verticalLayout.addWidget(self.metadata_label)


        self.retranslateUi(MetadataPanel)

        QMetaObject.connectSlotsByName(MetadataPanel)
    # setupUi

    def retranslateUi(self, MetadataPanel):
        pass
    # retranslateUi

