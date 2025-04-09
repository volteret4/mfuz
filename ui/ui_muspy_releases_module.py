# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'muspy_releases_module.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLineEdit,
    QPushButton, QSizePolicy, QTextEdit, QVBoxLayout,
    QWidget)
import rc_images

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
        self.results_text.setMaximumSize(QSize(16777215, 16777215))
        self.results_text.setReadOnly(True)

        self.verticalLayout.addWidget(self.results_text)

        self.frame = QFrame(MuspyArtistModule)
        self.frame.setObjectName(u"frame")
        self.bottom_layout = QHBoxLayout(self.frame)
        self.bottom_layout.setObjectName(u"bottom_layout")
        self.load_artists_button = QPushButton(self.frame)
        self.load_artists_button.setObjectName(u"load_artists_button")
        self.load_artists_button.setMaximumSize(QSize(40, 40))
        icon = QIcon()
        icon.addFile(u":/services/dbsearch", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.load_artists_button.setIcon(icon)
        self.load_artists_button.setIconSize(QSize(36, 36))

        self.bottom_layout.addWidget(self.load_artists_button)

        self.sync_artists_button = QPushButton(self.frame)
        self.sync_artists_button.setObjectName(u"sync_artists_button")
        self.sync_artists_button.setMaximumSize(QSize(40, 40))
        icon1 = QIcon()
        icon1.addFile(u":/services/b_link", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.sync_artists_button.setIcon(icon1)
        self.sync_artists_button.setIconSize(QSize(36, 36))

        self.bottom_layout.addWidget(self.sync_artists_button)

        self.sync_lastfm_button = QPushButton(self.frame)
        self.sync_lastfm_button.setObjectName(u"sync_lastfm_button")
        self.sync_lastfm_button.setMaximumSize(QSize(40, 40))
        icon2 = QIcon()
        icon2.addFile(u":/services/lastfm", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.sync_lastfm_button.setIcon(icon2)
        self.sync_lastfm_button.setIconSize(QSize(36, 36))

        self.bottom_layout.addWidget(self.sync_lastfm_button)

        self.get_releases_button = QPushButton(self.frame)
        self.get_releases_button.setObjectName(u"get_releases_button")
        self.get_releases_button.setMaximumSize(QSize(40, 40))
        icon3 = QIcon()
        icon3.addFile(u":/services/vinyl", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.get_releases_button.setIcon(icon3)
        self.get_releases_button.setIconSize(QSize(36, 36))

        self.bottom_layout.addWidget(self.get_releases_button)

        self.get_new_releases_button = QPushButton(self.frame)
        self.get_new_releases_button.setObjectName(u"get_new_releases_button")
        self.get_new_releases_button.setMaximumSize(QSize(40, 40))
        icon4 = QIcon()
        icon4.addFile(u":/services/pls", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.get_new_releases_button.setIcon(icon4)
        self.get_new_releases_button.setIconSize(QSize(36, 36))

        self.bottom_layout.addWidget(self.get_new_releases_button)

        self.get_my_releases_button = QPushButton(self.frame)
        self.get_my_releases_button.setObjectName(u"get_my_releases_button")
        self.get_my_releases_button.setMaximumSize(QSize(40, 40))
        self.get_my_releases_button.setStyleSheet(u"QPushButton {{ border-radius: 20}}")
        icon5 = QIcon()
        icon5.addFile(u":/services/b_download", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.get_my_releases_button.setIcon(icon5)
        self.get_my_releases_button.setIconSize(QSize(36, 36))

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
#if QT_CONFIG(tooltip)
        self.load_artists_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Cargar artistas desde db", None))
#endif // QT_CONFIG(tooltip)
        self.load_artists_button.setText("")
#if QT_CONFIG(tooltip)
        self.sync_artists_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Sincronizar Artistas con Muspy", None))
#endif // QT_CONFIG(tooltip)
        self.sync_artists_button.setText("")
#if QT_CONFIG(tooltip)
        self.sync_lastfm_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Sync Lastfm con Muspy", None))
#endif // QT_CONFIG(tooltip)
        self.sync_lastfm_button.setText("")
#if QT_CONFIG(tooltip)
        self.get_releases_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Mis pr\u00f3ximos discos", None))
#endif // QT_CONFIG(tooltip)
        self.get_releases_button.setText("")
#if QT_CONFIG(tooltip)
        self.get_new_releases_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Discos ausentes", None))
#endif // QT_CONFIG(tooltip)
        self.get_new_releases_button.setText("")
#if QT_CONFIG(tooltip)
        self.get_my_releases_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Obtener todo...", None))
#endif // QT_CONFIG(tooltip)
        self.get_my_releases_button.setText("")
    # retranslateUi

