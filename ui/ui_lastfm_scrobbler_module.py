# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'lastfm_scrobbler_module.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHeaderView, QLabel,
    QPushButton, QSizePolicy, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_LastFMScrobblerModule(object):
    def setupUi(self, LastFMScrobblerModule):
        if not LastFMScrobblerModule.objectName():
            LastFMScrobblerModule.setObjectName(u"LastFMScrobblerModule")
        LastFMScrobblerModule.resize(800, 600)
        self.main_layout = QVBoxLayout(LastFMScrobblerModule)
        self.main_layout.setObjectName(u"main_layout")
        self.splitter = QSplitter(LastFMScrobblerModule)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.left_panel = QWidget(self.splitter)
        self.left_panel.setObjectName(u"left_panel")
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setObjectName(u"left_layout")
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_label = QLabel(self.left_panel)
        self.queue_label.setObjectName(u"queue_label")
        self.queue_label.setAlignment(Qt.AlignCenter)

        self.left_layout.addWidget(self.queue_label)

        self.queue_table = QTableWidget(self.left_panel)
        if (self.queue_table.columnCount() < 3):
            self.queue_table.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.queue_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.queue_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.queue_table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.queue_table.setObjectName(u"queue_table")
        self.queue_table.setDragEnabled(True)
        self.queue_table.setDragDropMode(QAbstractItemView.InternalMove)
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.queue_table.setSortingEnabled(False)

        self.left_layout.addWidget(self.queue_table)

        self.scrobble_button = QPushButton(self.left_panel)
        self.scrobble_button.setObjectName(u"scrobble_button")

        self.left_layout.addWidget(self.scrobble_button)

        self.splitter.addWidget(self.left_panel)
        self.right_panel = QWidget(self.splitter)
        self.right_panel.setObjectName(u"right_panel")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setObjectName(u"right_layout")
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.scrobbles_label = QLabel(self.right_panel)
        self.scrobbles_label.setObjectName(u"scrobbles_label")
        self.scrobbles_label.setAlignment(Qt.AlignCenter)

        self.right_layout.addWidget(self.scrobbles_label)

        self.scrobbles_table = QTableWidget(self.right_panel)
        if (self.scrobbles_table.columnCount() < 7):
            self.scrobbles_table.setColumnCount(7)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.scrobbles_table.setHorizontalHeaderItem(0, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.scrobbles_table.setHorizontalHeaderItem(1, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.scrobbles_table.setHorizontalHeaderItem(2, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.scrobbles_table.setHorizontalHeaderItem(3, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.scrobbles_table.setHorizontalHeaderItem(4, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.scrobbles_table.setHorizontalHeaderItem(5, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.scrobbles_table.setHorizontalHeaderItem(6, __qtablewidgetitem9)
        self.scrobbles_table.setObjectName(u"scrobbles_table")
        self.scrobbles_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.scrobbles_table.setAlternatingRowColors(True)
        self.scrobbles_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.scrobbles_table.setSortingEnabled(True)

        self.right_layout.addWidget(self.scrobbles_table)

        self.refresh_button = QPushButton(self.right_panel)
        self.refresh_button.setObjectName(u"refresh_button")

        self.right_layout.addWidget(self.refresh_button)

        self.splitter.addWidget(self.right_panel)

        self.main_layout.addWidget(self.splitter)


        self.retranslateUi(LastFMScrobblerModule)

        QMetaObject.connectSlotsByName(LastFMScrobblerModule)
    # setupUi

    def retranslateUi(self, LastFMScrobblerModule):
        self.queue_label.setText(QCoreApplication.translate("LastFMScrobblerModule", u"Cola de canciones para scrobblear", None))
        ___qtablewidgetitem = self.queue_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("LastFMScrobblerModule", u"T\u00edtulo", None));
        ___qtablewidgetitem1 = self.queue_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("LastFMScrobblerModule", u"\u00c1lbum", None));
        ___qtablewidgetitem2 = self.queue_table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("LastFMScrobblerModule", u"Artista", None));
        self.scrobble_button.setText(QCoreApplication.translate("LastFMScrobblerModule", u"Scrobblear Canciones", None))
        self.scrobbles_label.setText(QCoreApplication.translate("LastFMScrobblerModule", u"\u00daltimos scrobbles", None))
        ___qtablewidgetitem3 = self.scrobbles_table.horizontalHeaderItem(0)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("LastFMScrobblerModule", u"Timestamp", None));
        ___qtablewidgetitem4 = self.scrobbles_table.horizontalHeaderItem(1)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("LastFMScrobblerModule", u"Artista", None));
        ___qtablewidgetitem5 = self.scrobbles_table.horizontalHeaderItem(2)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("LastFMScrobblerModule", u"\u00c1lbum", None));
        ___qtablewidgetitem6 = self.scrobbles_table.horizontalHeaderItem(3)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("LastFMScrobblerModule", u"Canci\u00f3n", None));
        ___qtablewidgetitem7 = self.scrobbles_table.horizontalHeaderItem(4)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("LastFMScrobblerModule", u"Sello", None));
        ___qtablewidgetitem8 = self.scrobbles_table.horizontalHeaderItem(5)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("LastFMScrobblerModule", u"Enlaces", None));
        ___qtablewidgetitem9 = self.scrobbles_table.horizontalHeaderItem(6)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("LastFMScrobblerModule", u"En DB", None));
        self.refresh_button.setText(QCoreApplication.translate("LastFMScrobblerModule", u"Actualizar Scrobbles", None))
        pass
    # retranslateUi

