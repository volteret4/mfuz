# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'muspy_releases_module.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLineEdit,
    QPushButton, QSizePolicy, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_MuspyArtistModule(object):
    def setupUi(self, MuspyArtistModule):
        if not MuspyArtistModule.objectName():
            MuspyArtistModule.setObjectName(u"MuspyArtistModule")
        MuspyArtistModule.resize(800, 600)
        self.verticalLayout = QVBoxLayout(MuspyArtistModule)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.search_layout_2 = QFrame(MuspyArtistModule)
        self.search_layout_2.setObjectName(u"search_layout_2")
        self.search_layout = QHBoxLayout(self.search_layout_2)
        self.search_layout.setObjectName(u"search_layout")
        self.artist_input = QLineEdit(self.search_layout_2)
        self.artist_input.setObjectName(u"artist_input")

        self.search_layout.addWidget(self.artist_input)

        self.search_button = QPushButton(self.search_layout_2)
        self.search_button.setObjectName(u"search_button")

        self.search_layout.addWidget(self.search_button)


        self.verticalLayout.addWidget(self.search_layout_2)

        self.results_text = QTextEdit(MuspyArtistModule)
        self.results_text.setObjectName(u"results_text")
        self.results_text.setReadOnly(True)

        self.verticalLayout.addWidget(self.results_text)

        self.frame = QFrame(MuspyArtistModule)
        self.frame.setObjectName(u"frame")
        self.bottom_layout = QHBoxLayout(self.frame)
        self.bottom_layout.setObjectName(u"bottom_layout")
        self.load_artists_button = QPushButton(self.frame)
        self.load_artists_button.setObjectName(u"load_artists_button")

        self.bottom_layout.addWidget(self.load_artists_button)

        self.sync_artists_button = QPushButton(self.frame)
        self.sync_artists_button.setObjectName(u"sync_artists_button")

        self.bottom_layout.addWidget(self.sync_artists_button)

        self.sync_lastfm_button = QPushButton(self.frame)
        self.sync_lastfm_button.setObjectName(u"sync_lastfm_button")

        self.bottom_layout.addWidget(self.sync_lastfm_button)

        self.get_releases_button = QPushButton(self.frame)
        self.get_releases_button.setObjectName(u"get_releases_button")

        self.bottom_layout.addWidget(self.get_releases_button)

        self.get_new_releases_button = QPushButton(self.frame)
        self.get_new_releases_button.setObjectName(u"get_new_releases_button")

        self.bottom_layout.addWidget(self.get_new_releases_button)

        self.get_my_releases_button = QPushButton(self.frame)
        self.get_my_releases_button.setObjectName(u"get_my_releases_button")

        self.bottom_layout.addWidget(self.get_my_releases_button)


        self.verticalLayout.addWidget(self.frame)


        self.retranslateUi(MuspyArtistModule)

        QMetaObject.connectSlotsByName(MuspyArtistModule)
    # setupUi

    def retranslateUi(self, MuspyArtistModule):
        MuspyArtistModule.setWindowTitle(QCoreApplication.translate("MuspyArtistModule", u"Muspy Artist Module", None))
        self.artist_input.setPlaceholderText(QCoreApplication.translate("MuspyArtistModule", u"Introduce el nombre de un artista para buscar discos anunciados", None))
        self.search_button.setText(QCoreApplication.translate("MuspyArtistModule", u"Voy a tener suerte", None))
        self.results_text.setHtml(QCoreApplication.translate("MuspyArtistModule", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Sans Serif'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Leer db: Mostrar\u00e1 una selecci\u00f3n con los artistas a escoger para sincronizar con muspy</p>\n"
"<p style=\" margin-top:0px"
                        "; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Sincronizar artistas: A\u00f1adir\u00e1 los artistas faltantes a Muspy</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Sincronizar Lastfm: Sincronizar\u00e1 artistas seguidos en lastfm en Muspy</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Mis Pr\u00f3ximos discos: Buscar\u00e1 lanzamientos anunciados de tus artistas seguidos</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Discos ausentes: Comprobar\u00e1 qu\u00e9 discos de los artistas seleccionados no existe en tu base de datos</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Obtener todo: Obtiene TODO lo anunciado, ser\u00e1n decenas de miles..."
                        "</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>", None))
        self.load_artists_button.setText(QCoreApplication.translate("MuspyArtistModule", u"Leer db", None))
        self.sync_artists_button.setText(QCoreApplication.translate("MuspyArtistModule", u"Sincronizar Artistas", None))
        self.sync_lastfm_button.setText(QCoreApplication.translate("MuspyArtistModule", u"Sync Lastfm", None))
        self.get_releases_button.setText(QCoreApplication.translate("MuspyArtistModule", u"Mis pr\u00f3ximos discos", None))
        self.get_new_releases_button.setText(QCoreApplication.translate("MuspyArtistModule", u"Discos ausentes", None))
        self.get_my_releases_button.setText(QCoreApplication.translate("MuspyArtistModule", u"Obtener todo...", None))
    # retranslateUi

