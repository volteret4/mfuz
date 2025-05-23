# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'muspy_artist_selection_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout,
    QWidget)

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
        self.scroll_area.setGeometry(QRect(0, 0, 580, 463))
        self.scroll_layout = QVBoxLayout(self.scroll_area)
        self.scroll_layout.setObjectName(u"scroll_layout")
        self.example_artist = QCheckBox(self.scroll_area)
        self.example_artist.setObjectName(u"example_artist")
        self.example_artist.setCheckable(True)
        self.example_artist.setChecked(False)

        self.scroll_layout.addWidget(self.example_artist)

        self.example_artist_2 = QCheckBox(self.scroll_area)
        self.example_artist_2.setObjectName(u"example_artist_2")
        font = QFont()
        font.setItalic(True)
        font.setStrikeOut(True)
        self.example_artist_2.setFont(font)
        self.example_artist_2.setCheckable(True)
        self.example_artist_2.setChecked(False)

        self.scroll_layout.addWidget(self.example_artist_2)

        self.scroll_widget.setWidget(self.scroll_area)

        self.verticalLayout.addWidget(self.scroll_widget)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName(u"button_layout")
        self.select_all_button = QPushButton(ArtistSelectionDialog)
        self.select_all_button.setObjectName(u"select_all_button")

        self.button_layout.addWidget(self.select_all_button)

        self.deselect_all_button = QPushButton(ArtistSelectionDialog)
        self.deselect_all_button.setObjectName(u"deselect_all_button")

        self.button_layout.addWidget(self.deselect_all_button)


        self.verticalLayout.addLayout(self.button_layout)

        self.buttonBox = QDialogButtonBox(ArtistSelectionDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(ArtistSelectionDialog)

        QMetaObject.connectSlotsByName(ArtistSelectionDialog)
    # setupUi

    def retranslateUi(self, ArtistSelectionDialog):
        ArtistSelectionDialog.setWindowTitle(QCoreApplication.translate("ArtistSelectionDialog", u"Seleccionar Artistas", None))
        self.info_label.setText(QCoreApplication.translate("ArtistSelectionDialog", u"Selecciona los artistas que deseas a\u00f1adir a muspy (0 encontrados)", None))
        self.search_label.setText(QCoreApplication.translate("ArtistSelectionDialog", u"Buscar:", None))
        self.example_artist.setText(QCoreApplication.translate("ArtistSelectionDialog", u"Ejemplo de Artista (a1b2c3d4-e5f6-7890-1234-567890abcdef)", None))
        self.example_artist_2.setText(QCoreApplication.translate("ArtistSelectionDialog", u"Otro Artista (12345678-9abc-def0-1234-56789abcdef0)", None))
        self.select_all_button.setText(QCoreApplication.translate("ArtistSelectionDialog", u"Seleccionar Todos", None))
        self.deselect_all_button.setText(QCoreApplication.translate("ArtistSelectionDialog", u"Deseleccionar Todos", None))
    # retranslateUi

