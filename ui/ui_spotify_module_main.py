# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'spotify_module_main.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGroupBox,
    QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QSplitter, QVBoxLayout,
    QWidget)
import rc_images

class Ui_SpotifyPlaylistManager(object):
    def setupUi(self, SpotifyPlaylistManager):
        if not SpotifyPlaylistManager.objectName():
            SpotifyPlaylistManager.setObjectName(u"SpotifyPlaylistManager")
        SpotifyPlaylistManager.resize(800, 606)
        self.verticalLayout = QVBoxLayout(SpotifyPlaylistManager)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.frame = QFrame(SpotifyPlaylistManager)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.NoFrame)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.frame.setLineWidth(0)
        self.horizontalLayout_5 = QHBoxLayout(self.frame)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 5, 0, 5)
        self.search_input = QLineEdit(self.frame)
        self.search_input.setObjectName(u"search_input")

        self.horizontalLayout_5.addWidget(self.search_input)

        self.search_button = QPushButton(self.frame)
        self.search_button.setObjectName(u"search_button")

        self.horizontalLayout_5.addWidget(self.search_button)

        self.playlist_selector = QComboBox(self.frame)
        icon = QIcon()
        icon.addFile(u":/services/spotify", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.playlist_selector.addItem(icon, "")
        self.playlist_selector.addItem(icon, "")
        self.playlist_selector.setObjectName(u"playlist_selector")

        self.horizontalLayout_5.addWidget(self.playlist_selector)


        self.verticalLayout.addWidget(self.frame)

        self.results_splitter = QSplitter(SpotifyPlaylistManager)
        self.results_splitter.setObjectName(u"results_splitter")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.results_splitter.sizePolicy().hasHeightForWidth())
        self.results_splitter.setSizePolicy(sizePolicy)
        self.results_splitter.setOrientation(Qt.Orientation.Horizontal)
        self.search_results_group = QGroupBox(self.results_splitter)
        self.search_results_group.setObjectName(u"search_results_group")
        self.search_results_layout = QVBoxLayout(self.search_results_group)
        self.search_results_layout.setObjectName(u"search_results_layout")
        self.search_results = QListWidget(self.search_results_group)
        self.search_results.setObjectName(u"search_results")
        self.search_results.setMinimumSize(QSize(0, 200))

        self.search_results_layout.addWidget(self.search_results)

        self.results_splitter.addWidget(self.search_results_group)
        self.playlist_creator_group = QGroupBox(self.results_splitter)
        self.playlist_creator_group.setObjectName(u"playlist_creator_group")
        self.playlist_creator_layout = QVBoxLayout(self.playlist_creator_group)
        self.playlist_creator_layout.setObjectName(u"playlist_creator_layout")
        self.playlist_creator = QListWidget(self.playlist_creator_group)
        self.playlist_creator.setObjectName(u"playlist_creator")
        self.playlist_creator.setMinimumSize(QSize(0, 200))

        self.playlist_creator_layout.addWidget(self.playlist_creator)

        self.playlist_buttons_container = QFrame(self.playlist_creator_group)
        self.playlist_buttons_container.setObjectName(u"playlist_buttons_container")
        self.playlist_buttons_container.setFrameShape(QFrame.Shape.NoFrame)
        self.playlist_buttons_container.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.playlist_buttons_container)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.save_loacal_playlist_button = QPushButton(self.playlist_buttons_container)
        self.save_loacal_playlist_button.setObjectName(u"save_loacal_playlist_button")
        self.save_loacal_playlist_button.setMaximumSize(QSize(40, 40))
        icon1 = QIcon()
        icon1.addFile(u":/services/data", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_loacal_playlist_button.setIcon(icon1)
        self.save_loacal_playlist_button.setIconSize(QSize(36, 36))

        self.horizontalLayout_3.addWidget(self.save_loacal_playlist_button)

        self.youtube_playlist_button = QPushButton(self.playlist_buttons_container)
        self.youtube_playlist_button.setObjectName(u"youtube_playlist_button")
        self.youtube_playlist_button.setMaximumSize(QSize(40, 40))
        icon2 = QIcon()
        icon2.addFile(u":/services/youtube", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.youtube_playlist_button.setIcon(icon2)
        self.youtube_playlist_button.setIconSize(QSize(36, 36))

        self.horizontalLayout_3.addWidget(self.youtube_playlist_button)

        self.save_playlist_button = QPushButton(self.playlist_buttons_container)
        self.save_playlist_button.setObjectName(u"save_playlist_button")
        self.save_playlist_button.setMaximumSize(QSize(40, 40))
        self.save_playlist_button.setIcon(icon)
        self.save_playlist_button.setIconSize(QSize(36, 36))

        self.horizontalLayout_3.addWidget(self.save_playlist_button)

        self.clear_playlist_button = QPushButton(self.playlist_buttons_container)
        self.clear_playlist_button.setObjectName(u"clear_playlist_button")
        self.clear_playlist_button.setMaximumSize(QSize(40, 40))
        icon3 = QIcon()
        icon3.addFile(u":/services/cancel", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.clear_playlist_button.setIcon(icon3)
        self.clear_playlist_button.setIconSize(QSize(36, 36))

        self.horizontalLayout_3.addWidget(self.clear_playlist_button)


        self.playlist_creator_layout.addWidget(self.playlist_buttons_container)

        self.results_splitter.addWidget(self.playlist_creator_group)

        self.verticalLayout.addWidget(self.results_splitter)

        self.playlist_container = QFrame(SpotifyPlaylistManager)
        self.playlist_container.setObjectName(u"playlist_container")
        self.playlist_container.setFrameShape(QFrame.Shape.NoFrame)
        self.playlist_container.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.playlist_container)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.new_playlist_input = QLineEdit(self.playlist_container)
        self.new_playlist_input.setObjectName(u"new_playlist_input")

        self.horizontalLayout_2.addWidget(self.new_playlist_input)

        self.new_playlist_button = QPushButton(self.playlist_container)
        self.new_playlist_button.setObjectName(u"new_playlist_button")

        self.horizontalLayout_2.addWidget(self.new_playlist_button)


        self.verticalLayout.addWidget(self.playlist_container)

        self.selector_container = QFrame(SpotifyPlaylistManager)
        self.selector_container.setObjectName(u"selector_container")
        self.selector_container.setFrameShape(QFrame.Shape.NoFrame)
        self.selector_container.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.selector_container)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout.addWidget(self.selector_container)


        self.retranslateUi(SpotifyPlaylistManager)

        QMetaObject.connectSlotsByName(SpotifyPlaylistManager)
    # setupUi

    def retranslateUi(self, SpotifyPlaylistManager):
        SpotifyPlaylistManager.setWindowTitle(QCoreApplication.translate("SpotifyPlaylistManager", u"Spotify Playlist Manager", None))
        self.search_input.setPlaceholderText(QCoreApplication.translate("SpotifyPlaylistManager", u"Buscar canci\u00f3n o artista...", None))
        self.search_button.setText(QCoreApplication.translate("SpotifyPlaylistManager", u"Buscar", None))
        self.playlist_selector.setItemText(0, QCoreApplication.translate("SpotifyPlaylistManager", u"Playlist_spotify_1", None))
        self.playlist_selector.setItemText(1, QCoreApplication.translate("SpotifyPlaylistManager", u"Nueva Playlist...", None))

        self.search_results_group.setTitle(QCoreApplication.translate("SpotifyPlaylistManager", u"Resultados de b\u00fasqueda", None))
        self.playlist_creator_group.setTitle(QCoreApplication.translate("SpotifyPlaylistManager", u"Creador de playlists", None))
        self.save_loacal_playlist_button.setText("")
#if QT_CONFIG(tooltip)
        self.youtube_playlist_button.setToolTip(QCoreApplication.translate("SpotifyPlaylistManager", u"Crear en youtube", None))
#endif // QT_CONFIG(tooltip)
        self.youtube_playlist_button.setText("")
#if QT_CONFIG(tooltip)
        self.save_playlist_button.setToolTip(QCoreApplication.translate("SpotifyPlaylistManager", u"Guardar playlist", None))
#endif // QT_CONFIG(tooltip)
        self.save_playlist_button.setText("")
        self.clear_playlist_button.setText("")
        self.new_playlist_input.setPlaceholderText(QCoreApplication.translate("SpotifyPlaylistManager", u"Nueva playlist...", None))
        self.new_playlist_button.setText(QCoreApplication.translate("SpotifyPlaylistManager", u"Crear Playlist", None))
    # retranslateUi

