# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'muspy_artists_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QScrollArea,
    QSizePolicy, QStackedWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)

class Ui_ArtistSelectionDialog(object):
    def setupUi(self, ArtistSelectionDialog):
        if not ArtistSelectionDialog.objectName():
            ArtistSelectionDialog.setObjectName(u"ArtistSelectionDialog")
        ArtistSelectionDialog.resize(600, 600)
        ArtistSelectionDialog.setMinimumSize(QSize(600, 600))
        self.verticalLayout = QVBoxLayout(ArtistSelectionDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.info_label = QLabel(ArtistSelectionDialog)
        self.info_label.setObjectName(u"info_label")

        self.verticalLayout.addWidget(self.info_label)

        self.search_layout = QHBoxLayout()
        self.search_layout.setObjectName(u"search_layout")
        self.search_label = QLabel(ArtistSelectionDialog)
        self.search_label.setObjectName(u"search_label")

        self.search_layout.addWidget(self.search_label)

        self.search_input = QLineEdit(ArtistSelectionDialog)
        self.search_input.setObjectName(u"search_input")

        self.search_layout.addWidget(self.search_input)


        self.verticalLayout.addLayout(self.search_layout)

        self.scroll_widget = QScrollArea(ArtistSelectionDialog)
        self.scroll_widget.setObjectName(u"scroll_widget")
        self.scroll_widget.setWidgetResizable(True)
        self.scroll_area = QWidget()
        self.scroll_area.setObjectName(u"scroll_area")
        self.scroll_area.setGeometry(QRect(0, 0, 580, 464))
        self.scroll_layout = QVBoxLayout(self.scroll_area)
        self.scroll_layout.setObjectName(u"scroll_layout")
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.stackedWidget = QStackedWidget(self.scroll_area)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.page = QWidget()
        self.page.setObjectName(u"page")
        self.verticalLayout_2 = QVBoxLayout(self.page)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.treeWidget = QTreeWidget(self.page)
        self.treeWidget.headerItem().setText(2, "")
        self.treeWidget.setObjectName(u"treeWidget")

        self.verticalLayout_2.addWidget(self.treeWidget)

        self.stackedWidget.addWidget(self.page)
        self.page_2 = QWidget()
        self.page_2.setObjectName(u"page_2")
        self.verticalLayout_3 = QVBoxLayout(self.page_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.listWidget = QListWidget(self.page_2)
        self.listWidget.setObjectName(u"listWidget")

        self.verticalLayout_3.addWidget(self.listWidget)

        self.stackedWidget.addWidget(self.page_2)

        self.scroll_layout.addWidget(self.stackedWidget)

        self.scroll_widget.setWidget(self.scroll_area)

        self.verticalLayout.addWidget(self.scroll_widget)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName(u"button_layout")
        self.action_select_all = QPushButton(ArtistSelectionDialog)
        self.action_select_all.setObjectName(u"action_select_all")

        self.button_layout.addWidget(self.action_select_all)

        self.action_deselect_all = QPushButton(ArtistSelectionDialog)
        self.action_deselect_all.setObjectName(u"action_deselect_all")

        self.button_layout.addWidget(self.action_deselect_all)


        self.verticalLayout.addLayout(self.button_layout)

        self.buttons = QDialogButtonBox(ArtistSelectionDialog)
        self.buttons.setObjectName(u"buttons")
        self.buttons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttons)


        self.retranslateUi(ArtistSelectionDialog)

        self.stackedWidget.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(ArtistSelectionDialog)
    # setupUi

    def retranslateUi(self, ArtistSelectionDialog):
        ArtistSelectionDialog.setWindowTitle(QCoreApplication.translate("ArtistSelectionDialog", u"Seleccionar Artistas", None))
        self.info_label.setText(QCoreApplication.translate("ArtistSelectionDialog", u"Selecciona los artistas que deseas guardar (0 encontrados)", None))
        self.search_label.setText(QCoreApplication.translate("ArtistSelectionDialog", u"Buscar:", None))
        ___qtreewidgetitem = self.treeWidget.headerItem()
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("ArtistSelectionDialog", u"MBID", None));
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("ArtistSelectionDialog", u"Artista / \u00c1lbum", None));
        self.action_select_all.setText(QCoreApplication.translate("ArtistSelectionDialog", u"Seleccionar Todos", None))
        self.action_deselect_all.setText(QCoreApplication.translate("ArtistSelectionDialog", u"Deseleccionar Todos", None))
    # retranslateUi

