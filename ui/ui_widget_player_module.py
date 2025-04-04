# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'widget_player_module.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QSplitter, QVBoxLayout,
    QWidget)

class Ui_MusicSearchForm(object):
    def setupUi(self, MusicSearchForm):
        if not MusicSearchForm.objectName():
            MusicSearchForm.setObjectName(u"MusicSearchForm")
        MusicSearchForm.resize(800, 600)
        self.main_layout = QVBoxLayout(MusicSearchForm)
        self.main_layout.setObjectName(u"main_layout")
        self.search_layout_2 = QFrame(MusicSearchForm)
        self.search_layout_2.setObjectName(u"search_layout_2")
        self.search_layout = QHBoxLayout(self.search_layout_2)
        self.search_layout.setObjectName(u"search_layout")
        self.source_combo = QComboBox(self.search_layout_2)
        self.source_combo.setObjectName(u"source_combo")

        self.search_layout.addWidget(self.source_combo)

        self.search_input = QLineEdit(self.search_layout_2)
        self.search_input.setObjectName(u"search_input")

        self.search_layout.addWidget(self.search_input)

        self.search_button = QPushButton(self.search_layout_2)
        self.search_button.setObjectName(u"search_button")

        self.search_layout.addWidget(self.search_button)


        self.main_layout.addWidget(self.search_layout_2)

        self.progress_bar = QProgressBar(MusicSearchForm)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)

        self.main_layout.addWidget(self.progress_bar)

        self.splitter = QSplitter(MusicSearchForm)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.results_scroll = QScrollArea(self.splitter)
        self.results_scroll.setObjectName(u"results_scroll")
        self.results_scroll.setWidgetResizable(True)
        self.results_widget = QWidget()
        self.results_widget.setObjectName(u"results_widget")
        self.results_widget.setGeometry(QRect(0, 0, 780, 182))
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.results_widget.sizePolicy().hasHeightForWidth())
        self.results_widget.setSizePolicy(sizePolicy)
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setObjectName(u"results_layout")
        self.results_scroll.setWidget(self.results_widget)
        self.splitter.addWidget(self.results_scroll)
        self.info_frame = QFrame(self.splitter)
        self.info_frame.setObjectName(u"info_frame")
        self.info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.info_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.info_layout = QVBoxLayout(self.info_frame)
        self.info_layout.setObjectName(u"info_layout")
        self.info_title = QLabel(self.info_frame)
        self.info_title.setObjectName(u"info_title")
        self.info_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.info_layout.addWidget(self.info_title)

        self.splitter.addWidget(self.info_frame)

        self.main_layout.addWidget(self.splitter)


        self.retranslateUi(MusicSearchForm)

        QMetaObject.connectSlotsByName(MusicSearchForm)
    # setupUi

    def retranslateUi(self, MusicSearchForm):
        MusicSearchForm.setWindowTitle(QCoreApplication.translate("MusicSearchForm", u"Music Search", None))
        self.search_input.setPlaceholderText(QCoreApplication.translate("MusicSearchForm", u"Buscar artista, \u00e1lbum o canci\u00f3n...", None))
        self.search_button.setText(QCoreApplication.translate("MusicSearchForm", u"Buscar", None))
        self.info_title.setText(QCoreApplication.translate("MusicSearchForm", u"Selecciona un \u00e1lbum para ver m\u00e1s detalles", None))
    # retranslateUi

