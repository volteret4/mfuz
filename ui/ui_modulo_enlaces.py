# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'modulo_enlaces.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QHeaderView,
    QLineEdit, QPushButton, QSizePolicy, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_MusicBrainzReleasesModule(object):
    def setupUi(self, MusicBrainzReleasesModule):
        if not MusicBrainzReleasesModule.objectName():
            MusicBrainzReleasesModule.setObjectName(u"MusicBrainzReleasesModule")
        MusicBrainzReleasesModule.resize(900, 600)
        self.verticalLayout = QVBoxLayout(MusicBrainzReleasesModule)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.search_layout = QHBoxLayout()
        self.search_layout.setObjectName(u"search_layout")
        self.artist_input = QLineEdit(MusicBrainzReleasesModule)
        self.artist_input.setObjectName(u"artist_input")

        self.search_layout.addWidget(self.artist_input)

        self.search_button = QPushButton(MusicBrainzReleasesModule)
        self.search_button.setObjectName(u"search_button")

        self.search_layout.addWidget(self.search_button)


        self.verticalLayout.addLayout(self.search_layout)

        self.results_table = QTableWidget(MusicBrainzReleasesModule)
        if (self.results_table.columnCount() < 6):
            self.results_table.setColumnCount(6)
        __qtablewidgetitem = QTableWidgetItem()
        self.results_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.results_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.results_table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.results_table.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.results_table.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.results_table.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        self.results_table.setObjectName(u"results_table")
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSortingEnabled(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)

        self.verticalLayout.addWidget(self.results_table)


        self.retranslateUi(MusicBrainzReleasesModule)

        QMetaObject.connectSlotsByName(MusicBrainzReleasesModule)
    # setupUi

    def retranslateUi(self, MusicBrainzReleasesModule):
        self.artist_input.setPlaceholderText(QCoreApplication.translate("MusicBrainzReleasesModule", u"Enter artist name", None))
        self.search_button.setText(QCoreApplication.translate("MusicBrainzReleasesModule", u"Search Releases", None))
        ___qtablewidgetitem = self.results_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("MusicBrainzReleasesModule", u"In DB", None));
        ___qtablewidgetitem1 = self.results_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("MusicBrainzReleasesModule", u"Checked", None));
        ___qtablewidgetitem2 = self.results_table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("MusicBrainzReleasesModule", u"Title", None));
        ___qtablewidgetitem3 = self.results_table.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("MusicBrainzReleasesModule", u"Date", None));
        ___qtablewidgetitem4 = self.results_table.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("MusicBrainzReleasesModule", u"Type", None));
        ___qtablewidgetitem5 = self.results_table.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("MusicBrainzReleasesModule", u"Label", None));
        pass
    # retranslateUi

