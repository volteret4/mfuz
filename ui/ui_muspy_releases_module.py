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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QStackedWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget)
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
        self.search_layout.setContentsMargins(0, 0, 0, 0)
        self.artist_input = QLineEdit(self.search_layout_2)
        self.artist_input.setObjectName(u"artist_input")
        self.artist_input.setMinimumSize(QSize(0, 30))

        self.search_layout.addWidget(self.artist_input)

        self.search_button = QPushButton(self.search_layout_2)
        self.search_button.setObjectName(u"search_button")
        icon = QIcon()
        icon.addFile(u":/services/search_music", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.search_button.setIcon(icon)
        self.search_button.setIconSize(QSize(30, 30))

        self.search_layout.addWidget(self.search_button)


        self.verticalLayout.addWidget(self.search_layout_2)

        self.stackedWidget = QStackedWidget(MuspyArtistModule)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.artists_page = QWidget()
        self.artists_page.setObjectName(u"artists_page")
        self.verticalLayout_9 = QVBoxLayout(self.artists_page)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.top_artists_label = QLabel(self.artists_page)
        self.top_artists_label.setObjectName(u"top_artists_label")

        self.verticalLayout_9.addWidget(self.top_artists_label)

        self.artists_table = QTableWidget(self.artists_page)
        if (self.artists_table.columnCount() < 5):
            self.artists_table.setColumnCount(5)
        icon1 = QIcon()
        icon1.addFile(u":/services/lastfm_h", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        __qtablewidgetitem = QTableWidgetItem()
        __qtablewidgetitem.setIcon(icon1);
        self.artists_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.artists_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.artists_table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.artists_table.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.artists_table.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        self.artists_table.setObjectName(u"artists_table")

        self.verticalLayout_9.addWidget(self.artists_table)

        self.stackedWidget.addWidget(self.artists_page)
        self.spotify_saved_tracks_page = QWidget()
        self.spotify_saved_tracks_page.setObjectName(u"spotify_saved_tracks_page")
        self.verticalLayout_12 = QVBoxLayout(self.spotify_saved_tracks_page)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.spotify_saved_tracks_count_label = QLabel(self.spotify_saved_tracks_page)
        self.spotify_saved_tracks_count_label.setObjectName(u"spotify_saved_tracks_count_label")

        self.verticalLayout_12.addWidget(self.spotify_saved_tracks_count_label)

        self.spotify_saved_tracks_table = QTableWidget(self.spotify_saved_tracks_page)
        if (self.spotify_saved_tracks_table.columnCount() < 5):
            self.spotify_saved_tracks_table.setColumnCount(5)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.spotify_saved_tracks_table.setHorizontalHeaderItem(0, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.spotify_saved_tracks_table.setHorizontalHeaderItem(1, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.spotify_saved_tracks_table.setHorizontalHeaderItem(2, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.spotify_saved_tracks_table.setHorizontalHeaderItem(3, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.spotify_saved_tracks_table.setHorizontalHeaderItem(4, __qtablewidgetitem9)
        self.spotify_saved_tracks_table.setObjectName(u"spotify_saved_tracks_table")

        self.verticalLayout_12.addWidget(self.spotify_saved_tracks_table)

        self.stackedWidget.addWidget(self.spotify_saved_tracks_page)
        self.spotify_top_items_page = QWidget()
        self.spotify_top_items_page.setObjectName(u"spotify_top_items_page")
        self.verticalLayout_13 = QVBoxLayout(self.spotify_top_items_page)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.verticalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.spotify_top_items_count_label = QLabel(self.spotify_top_items_page)
        self.spotify_top_items_count_label.setObjectName(u"spotify_top_items_count_label")

        self.verticalLayout_13.addWidget(self.spotify_top_items_count_label)

        self.spotify_top_items_table = QTableWidget(self.spotify_top_items_page)
        self.spotify_top_items_table.setObjectName(u"spotify_top_items_table")

        self.verticalLayout_13.addWidget(self.spotify_top_items_table)

        self.stackedWidget.addWidget(self.spotify_top_items_page)
        self.bluesky_page = QWidget()
        self.bluesky_page.setObjectName(u"bluesky_page")
        self.verticalLayout_14 = QVBoxLayout(self.bluesky_page)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.verticalLayout_14.setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget(self.bluesky_page)
        self.widget.setObjectName(u"widget")
        self.verticalLayout_15 = QVBoxLayout(self.widget)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.verticalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.bluesky_count_label = QLabel(self.widget)
        self.bluesky_count_label.setObjectName(u"bluesky_count_label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bluesky_count_label.sizePolicy().hasHeightForWidth())
        self.bluesky_count_label.setSizePolicy(sizePolicy)

        self.verticalLayout_15.addWidget(self.bluesky_count_label)

        self.widget_3 = QWidget(self.widget)
        self.widget_3.setObjectName(u"widget_3")
        self.horizontalLayout = QHBoxLayout(self.widget_3)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.widget_6 = QWidget(self.widget_3)
        self.widget_6.setObjectName(u"widget_6")
        self.verticalLayout_19 = QVBoxLayout(self.widget_6)
        self.verticalLayout_19.setObjectName(u"verticalLayout_19")
        self.verticalLayout_19.setContentsMargins(0, 0, 0, 0)
        self.bluesky_artists_table = QTableWidget(self.widget_6)
        if (self.bluesky_artists_table.columnCount() < 4):
            self.bluesky_artists_table.setColumnCount(4)
        __qtablewidgetitem10 = QTableWidgetItem()
        self.bluesky_artists_table.setHorizontalHeaderItem(0, __qtablewidgetitem10)
        __qtablewidgetitem11 = QTableWidgetItem()
        self.bluesky_artists_table.setHorizontalHeaderItem(1, __qtablewidgetitem11)
        __qtablewidgetitem12 = QTableWidgetItem()
        self.bluesky_artists_table.setHorizontalHeaderItem(2, __qtablewidgetitem12)
        __qtablewidgetitem13 = QTableWidgetItem()
        self.bluesky_artists_table.setHorizontalHeaderItem(3, __qtablewidgetitem13)
        self.bluesky_artists_table.setObjectName(u"bluesky_artists_table")

        self.verticalLayout_19.addWidget(self.bluesky_artists_table)

        self.bluesky_table_buttons = QWidget(self.widget_6)
        self.bluesky_table_buttons.setObjectName(u"bluesky_table_buttons")
        self.horizontalLayout_2 = QHBoxLayout(self.bluesky_table_buttons)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.bluesky_follow = QPushButton(self.bluesky_table_buttons)
        self.bluesky_follow.setObjectName(u"bluesky_follow")
        icon2 = QIcon()
        icon2.addFile(u":/services/bluesky", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.bluesky_follow.setIcon(icon2)

        self.horizontalLayout_2.addWidget(self.bluesky_follow)


        self.verticalLayout_19.addWidget(self.bluesky_table_buttons)


        self.horizontalLayout.addWidget(self.widget_6)

        self.bluesky_selected_artist_panel = QWidget(self.widget_3)
        self.bluesky_selected_artist_panel.setObjectName(u"bluesky_selected_artist_panel")
        self.verticalLayout_16 = QVBoxLayout(self.bluesky_selected_artist_panel)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.verticalLayout_16.setContentsMargins(0, 0, 0, 0)
        self.widget_5 = QWidget(self.bluesky_selected_artist_panel)
        self.widget_5.setObjectName(u"widget_5")
        self.verticalLayout_17 = QVBoxLayout(self.widget_5)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.verticalLayout_17.setContentsMargins(0, 0, 0, 0)
        self.widget_4 = QWidget(self.widget_5)
        self.widget_4.setObjectName(u"widget_4")
        self.widget_4.setMinimumSize(QSize(250, 250))
        self.horizontalLayout_3 = QHBoxLayout(self.widget_4)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.bluesky_selected_artist_foto = QLabel(self.widget_4)
        self.bluesky_selected_artist_foto.setObjectName(u"bluesky_selected_artist_foto")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.bluesky_selected_artist_foto.sizePolicy().hasHeightForWidth())
        self.bluesky_selected_artist_foto.setSizePolicy(sizePolicy1)

        self.horizontalLayout_3.addWidget(self.bluesky_selected_artist_foto)

        self.widget_7 = QWidget(self.widget_4)
        self.widget_7.setObjectName(u"widget_7")
        self.verticalLayout_18 = QVBoxLayout(self.widget_7)
        self.verticalLayout_18.setObjectName(u"verticalLayout_18")
        self.verticalLayout_18.setContentsMargins(0, 0, 0, 0)
        self.bluesky_profile_panel = QTextEdit(self.widget_7)
        self.bluesky_profile_panel.setObjectName(u"bluesky_profile_panel")

        self.verticalLayout_18.addWidget(self.bluesky_profile_panel)


        self.horizontalLayout_3.addWidget(self.widget_7)


        self.verticalLayout_17.addWidget(self.widget_4)


        self.verticalLayout_16.addWidget(self.widget_5)

        self.bluesky_selected_artist_mensajes = QTextEdit(self.bluesky_selected_artist_panel)
        self.bluesky_selected_artist_mensajes.setObjectName(u"bluesky_selected_artist_mensajes")

        self.verticalLayout_16.addWidget(self.bluesky_selected_artist_mensajes)


        self.horizontalLayout.addWidget(self.bluesky_selected_artist_panel)


        self.verticalLayout_15.addWidget(self.widget_3)


        self.verticalLayout_14.addWidget(self.widget)

        self.stackedWidget.addWidget(self.bluesky_page)
        self.twitter_users_page = QWidget()
        self.twitter_users_page.setObjectName(u"twitter_users_page")
        self.horizontalLayout_4 = QHBoxLayout(self.twitter_users_page)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.twitter_users_widget = QWidget(self.twitter_users_page)
        self.twitter_users_widget.setObjectName(u"twitter_users_widget")
        self.horizontalLayout_6 = QHBoxLayout(self.twitter_users_widget)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.twitter_count_widget = QWidget(self.twitter_users_widget)
        self.twitter_count_widget.setObjectName(u"twitter_count_widget")
        self.verticalLayout_21 = QVBoxLayout(self.twitter_count_widget)
        self.verticalLayout_21.setObjectName(u"verticalLayout_21")
        self.verticalLayout_21.setContentsMargins(0, 0, 0, 0)
        self.twitter_users_count_label = QLabel(self.twitter_count_widget)
        self.twitter_users_count_label.setObjectName(u"twitter_users_count_label")

        self.verticalLayout_21.addWidget(self.twitter_users_count_label)

        self.twitter_users_table = QTableWidget(self.twitter_count_widget)
        if (self.twitter_users_table.columnCount() < 6):
            self.twitter_users_table.setColumnCount(6)
        __qtablewidgetitem14 = QTableWidgetItem()
        self.twitter_users_table.setHorizontalHeaderItem(0, __qtablewidgetitem14)
        __qtablewidgetitem15 = QTableWidgetItem()
        self.twitter_users_table.setHorizontalHeaderItem(1, __qtablewidgetitem15)
        __qtablewidgetitem16 = QTableWidgetItem()
        self.twitter_users_table.setHorizontalHeaderItem(2, __qtablewidgetitem16)
        __qtablewidgetitem17 = QTableWidgetItem()
        self.twitter_users_table.setHorizontalHeaderItem(3, __qtablewidgetitem17)
        __qtablewidgetitem18 = QTableWidgetItem()
        self.twitter_users_table.setHorizontalHeaderItem(4, __qtablewidgetitem18)
        __qtablewidgetitem19 = QTableWidgetItem()
        self.twitter_users_table.setHorizontalHeaderItem(5, __qtablewidgetitem19)
        self.twitter_users_table.setObjectName(u"twitter_users_table")

        self.verticalLayout_21.addWidget(self.twitter_users_table)

        self.seguir_twitter = QPushButton(self.twitter_count_widget)
        self.seguir_twitter.setObjectName(u"seguir_twitter")

        self.verticalLayout_21.addWidget(self.seguir_twitter)


        self.horizontalLayout_6.addWidget(self.twitter_count_widget)

        self.twitter_user_panel = QWidget(self.twitter_users_widget)
        self.twitter_user_panel.setObjectName(u"twitter_user_panel")
        self.verticalLayout_20 = QVBoxLayout(self.twitter_user_panel)
        self.verticalLayout_20.setObjectName(u"verticalLayout_20")
        self.verticalLayout_20.setContentsMargins(0, 0, 0, 0)
        self.twitter_user_profile = QWidget(self.twitter_user_panel)
        self.twitter_user_profile.setObjectName(u"twitter_user_profile")
        self.horizontalLayout_5 = QHBoxLayout(self.twitter_user_profile)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.twitter_foto_widget = QWidget(self.twitter_user_profile)
        self.twitter_foto_widget.setObjectName(u"twitter_foto_widget")
        self.verticalLayout_22 = QVBoxLayout(self.twitter_foto_widget)
        self.verticalLayout_22.setObjectName(u"verticalLayout_22")
        self.verticalLayout_22.setContentsMargins(0, 0, 0, 0)
        self.twitter_foto_label = QLabel(self.twitter_foto_widget)
        self.twitter_foto_label.setObjectName(u"twitter_foto_label")

        self.verticalLayout_22.addWidget(self.twitter_foto_label)


        self.horizontalLayout_5.addWidget(self.twitter_foto_widget)

        self.widget_12 = QWidget(self.twitter_user_profile)
        self.widget_12.setObjectName(u"widget_12")
        self.verticalLayout_23 = QVBoxLayout(self.widget_12)
        self.verticalLayout_23.setObjectName(u"verticalLayout_23")
        self.verticalLayout_23.setContentsMargins(0, 0, 0, 0)
        self.twitter_textEdit = QTextEdit(self.widget_12)
        self.twitter_textEdit.setObjectName(u"twitter_textEdit")

        self.verticalLayout_23.addWidget(self.twitter_textEdit)


        self.horizontalLayout_5.addWidget(self.widget_12)


        self.verticalLayout_20.addWidget(self.twitter_user_profile)

        self.widget_11 = QWidget(self.twitter_user_panel)
        self.widget_11.setObjectName(u"widget_11")
        self.verticalLayout_24 = QVBoxLayout(self.widget_11)
        self.verticalLayout_24.setObjectName(u"verticalLayout_24")
        self.verticalLayout_24.setContentsMargins(0, 0, 0, 0)
        self.twitter_user_msg = QTextEdit(self.widget_11)
        self.twitter_user_msg.setObjectName(u"twitter_user_msg")

        self.verticalLayout_24.addWidget(self.twitter_user_msg)


        self.verticalLayout_20.addWidget(self.widget_11)


        self.horizontalLayout_6.addWidget(self.twitter_user_panel)


        self.horizontalLayout_4.addWidget(self.twitter_users_widget)

        self.stackedWidget.addWidget(self.twitter_users_page)
        self.musicbrainz_collection_page = QWidget()
        self.musicbrainz_collection_page.setObjectName(u"musicbrainz_collection_page")
        self.verticalLayout_7 = QVBoxLayout(self.musicbrainz_collection_page)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.mb_label = QLabel(self.musicbrainz_collection_page)
        self.mb_label.setObjectName(u"mb_label")

        self.verticalLayout_7.addWidget(self.mb_label)

        self.tabla_musicbrainz_collection = QTableWidget(self.musicbrainz_collection_page)
        if (self.tabla_musicbrainz_collection.columnCount() < 7):
            self.tabla_musicbrainz_collection.setColumnCount(7)
        icon3 = QIcon()
        icon3.addFile(u":/services/mb", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        __qtablewidgetitem20 = QTableWidgetItem()
        __qtablewidgetitem20.setIcon(icon3);
        self.tabla_musicbrainz_collection.setHorizontalHeaderItem(0, __qtablewidgetitem20)
        __qtablewidgetitem21 = QTableWidgetItem()
        self.tabla_musicbrainz_collection.setHorizontalHeaderItem(1, __qtablewidgetitem21)
        __qtablewidgetitem22 = QTableWidgetItem()
        self.tabla_musicbrainz_collection.setHorizontalHeaderItem(2, __qtablewidgetitem22)
        __qtablewidgetitem23 = QTableWidgetItem()
        self.tabla_musicbrainz_collection.setHorizontalHeaderItem(3, __qtablewidgetitem23)
        __qtablewidgetitem24 = QTableWidgetItem()
        self.tabla_musicbrainz_collection.setHorizontalHeaderItem(4, __qtablewidgetitem24)
        __qtablewidgetitem25 = QTableWidgetItem()
        self.tabla_musicbrainz_collection.setHorizontalHeaderItem(5, __qtablewidgetitem25)
        __qtablewidgetitem26 = QTableWidgetItem()
        self.tabla_musicbrainz_collection.setHorizontalHeaderItem(6, __qtablewidgetitem26)
        self.tabla_musicbrainz_collection.setObjectName(u"tabla_musicbrainz_collection")

        self.verticalLayout_7.addWidget(self.tabla_musicbrainz_collection)

        self.stackedWidget.addWidget(self.musicbrainz_collection_page)
        self._create_releases_page = QWidget()
        self._create_releases_page.setObjectName(u"_create_releases_page")
        self.verticalLayout_3 = QVBoxLayout(self._create_releases_page)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.create_label = QLabel(self._create_releases_page)
        self.create_label.setObjectName(u"create_label")

        self.verticalLayout_3.addWidget(self.create_label)

        self.tabla_crear_collection = QTableWidget(self._create_releases_page)
        self.tabla_crear_collection.setObjectName(u"tabla_crear_collection")

        self.verticalLayout_3.addWidget(self.tabla_crear_collection)

        self.stackedWidget.addWidget(self._create_releases_page)
        self.muspy_results_widget = QWidget()
        self.muspy_results_widget.setObjectName(u"muspy_results_widget")
        self.verticalLayout_8 = QVBoxLayout(self.muspy_results_widget)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.muspy_results_widget_2 = QWidget(self.muspy_results_widget)
        self.muspy_results_widget_2.setObjectName(u"muspy_results_widget_2")
        self.verticalLayout_2 = QVBoxLayout(self.muspy_results_widget_2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label_result_count = QLabel(self.muspy_results_widget_2)
        self.label_result_count.setObjectName(u"label_result_count")

        self.verticalLayout_2.addWidget(self.label_result_count)

        self.tableWidget_muspy_results = QTableWidget(self.muspy_results_widget_2)
        if (self.tableWidget_muspy_results.columnCount() < 5):
            self.tableWidget_muspy_results.setColumnCount(5)
        __qtablewidgetitem27 = QTableWidgetItem()
        self.tableWidget_muspy_results.setHorizontalHeaderItem(0, __qtablewidgetitem27)
        __qtablewidgetitem28 = QTableWidgetItem()
        self.tableWidget_muspy_results.setHorizontalHeaderItem(1, __qtablewidgetitem28)
        __qtablewidgetitem29 = QTableWidgetItem()
        self.tableWidget_muspy_results.setHorizontalHeaderItem(2, __qtablewidgetitem29)
        __qtablewidgetitem30 = QTableWidgetItem()
        self.tableWidget_muspy_results.setHorizontalHeaderItem(3, __qtablewidgetitem30)
        __qtablewidgetitem31 = QTableWidgetItem()
        self.tableWidget_muspy_results.setHorizontalHeaderItem(4, __qtablewidgetitem31)
        self.tableWidget_muspy_results.setObjectName(u"tableWidget_muspy_results")

        self.verticalLayout_2.addWidget(self.tableWidget_muspy_results)

        self.widget_2 = QWidget(self.muspy_results_widget_2)
        self.widget_2.setObjectName(u"widget_2")
        self.horizontalLayout_7 = QHBoxLayout(self.widget_2)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.follow_artist_button = QPushButton(self.widget_2)
        self.follow_artist_button.setObjectName(u"follow_artist_button")

        self.horizontalLayout_7.addWidget(self.follow_artist_button)


        self.verticalLayout_2.addWidget(self.widget_2)


        self.verticalLayout_8.addWidget(self.muspy_results_widget_2)

        self.stackedWidget.addWidget(self.muspy_results_widget)
        self.releases_page = QWidget()
        self.releases_page.setObjectName(u"releases_page")
        self.verticalLayout_10 = QVBoxLayout(self.releases_page)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.releases_label = QLabel(self.releases_page)
        self.releases_label.setObjectName(u"releases_label")

        self.verticalLayout_10.addWidget(self.releases_label)

        self.releases_table = QTableWidget(self.releases_page)
        if (self.releases_table.columnCount() < 5):
            self.releases_table.setColumnCount(5)
        __qtablewidgetitem32 = QTableWidgetItem()
        self.releases_table.setHorizontalHeaderItem(0, __qtablewidgetitem32)
        __qtablewidgetitem33 = QTableWidgetItem()
        self.releases_table.setHorizontalHeaderItem(1, __qtablewidgetitem33)
        __qtablewidgetitem34 = QTableWidgetItem()
        self.releases_table.setHorizontalHeaderItem(2, __qtablewidgetitem34)
        __qtablewidgetitem35 = QTableWidgetItem()
        self.releases_table.setHorizontalHeaderItem(3, __qtablewidgetitem35)
        __qtablewidgetitem36 = QTableWidgetItem()
        self.releases_table.setHorizontalHeaderItem(4, __qtablewidgetitem36)
        self.releases_table.setObjectName(u"releases_table")

        self.verticalLayout_10.addWidget(self.releases_table)

        self.stackedWidget.addWidget(self.releases_page)
        self.loved_tracks_page = QWidget()
        self.loved_tracks_page.setObjectName(u"loved_tracks_page")
        self.verticalLayout_6 = QVBoxLayout(self.loved_tracks_page)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.loved_songs_label = QLabel(self.loved_tracks_page)
        self.loved_songs_label.setObjectName(u"loved_songs_label")

        self.verticalLayout_6.addWidget(self.loved_songs_label)

        self.loved_tracks_table = QTableWidget(self.loved_tracks_page)
        if (self.loved_tracks_table.columnCount() < 4):
            self.loved_tracks_table.setColumnCount(4)
        __qtablewidgetitem37 = QTableWidgetItem()
        __qtablewidgetitem37.setIcon(icon1);
        self.loved_tracks_table.setHorizontalHeaderItem(0, __qtablewidgetitem37)
        __qtablewidgetitem38 = QTableWidgetItem()
        self.loved_tracks_table.setHorizontalHeaderItem(1, __qtablewidgetitem38)
        __qtablewidgetitem39 = QTableWidgetItem()
        self.loved_tracks_table.setHorizontalHeaderItem(2, __qtablewidgetitem39)
        __qtablewidgetitem40 = QTableWidgetItem()
        self.loved_tracks_table.setHorizontalHeaderItem(3, __qtablewidgetitem40)
        self.loved_tracks_table.setObjectName(u"loved_tracks_table")

        self.verticalLayout_6.addWidget(self.loved_tracks_table)

        self.stackedWidget.addWidget(self.loved_tracks_page)
        self.text_page = QWidget()
        self.text_page.setObjectName(u"text_page")
        self.verticalLayout_11 = QVBoxLayout(self.text_page)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.text_page)
        self.label.setObjectName(u"label")

        self.verticalLayout_11.addWidget(self.label)

        self.results_text = QTextEdit(self.text_page)
        self.results_text.setObjectName(u"results_text")

        self.verticalLayout_11.addWidget(self.results_text)

        self.stackedWidget.addWidget(self.text_page)
        self.spotify_artists_page = QWidget()
        self.spotify_artists_page.setObjectName(u"spotify_artists_page")
        self.verticalLayout_4 = QVBoxLayout(self.spotify_artists_page)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.spotify_artists_count_label = QLabel(self.spotify_artists_page)
        self.spotify_artists_count_label.setObjectName(u"spotify_artists_count_label")

        self.verticalLayout_4.addWidget(self.spotify_artists_count_label)

        self.spotify_artists_table = QTableWidget(self.spotify_artists_page)
        if (self.spotify_artists_table.columnCount() < 4):
            self.spotify_artists_table.setColumnCount(4)
        icon4 = QIcon()
        icon4.addFile(u":/services/spotify_ol", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        __qtablewidgetitem41 = QTableWidgetItem()
        __qtablewidgetitem41.setIcon(icon4);
        self.spotify_artists_table.setHorizontalHeaderItem(0, __qtablewidgetitem41)
        __qtablewidgetitem42 = QTableWidgetItem()
        self.spotify_artists_table.setHorizontalHeaderItem(1, __qtablewidgetitem42)
        __qtablewidgetitem43 = QTableWidgetItem()
        self.spotify_artists_table.setHorizontalHeaderItem(2, __qtablewidgetitem43)
        __qtablewidgetitem44 = QTableWidgetItem()
        self.spotify_artists_table.setHorizontalHeaderItem(3, __qtablewidgetitem44)
        self.spotify_artists_table.setObjectName(u"spotify_artists_table")

        self.verticalLayout_4.addWidget(self.spotify_artists_table)

        self.stackedWidget.addWidget(self.spotify_artists_page)
        self.spotify_releases_page = QWidget()
        self.spotify_releases_page.setObjectName(u"spotify_releases_page")
        self.verticalLayout_5 = QVBoxLayout(self.spotify_releases_page)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.spotify_releases_count_label = QLabel(self.spotify_releases_page)
        self.spotify_releases_count_label.setObjectName(u"spotify_releases_count_label")

        self.verticalLayout_5.addWidget(self.spotify_releases_count_label)

        self.spotify_releases_table = QTableWidget(self.spotify_releases_page)
        if (self.spotify_releases_table.columnCount() < 5):
            self.spotify_releases_table.setColumnCount(5)
        __qtablewidgetitem45 = QTableWidgetItem()
        __qtablewidgetitem45.setIcon(icon4);
        self.spotify_releases_table.setHorizontalHeaderItem(0, __qtablewidgetitem45)
        __qtablewidgetitem46 = QTableWidgetItem()
        self.spotify_releases_table.setHorizontalHeaderItem(1, __qtablewidgetitem46)
        __qtablewidgetitem47 = QTableWidgetItem()
        self.spotify_releases_table.setHorizontalHeaderItem(2, __qtablewidgetitem47)
        __qtablewidgetitem48 = QTableWidgetItem()
        self.spotify_releases_table.setHorizontalHeaderItem(3, __qtablewidgetitem48)
        __qtablewidgetitem49 = QTableWidgetItem()
        self.spotify_releases_table.setHorizontalHeaderItem(4, __qtablewidgetitem49)
        self.spotify_releases_table.setObjectName(u"spotify_releases_table")

        self.verticalLayout_5.addWidget(self.spotify_releases_table)

        self.stackedWidget.addWidget(self.spotify_releases_page)

        self.verticalLayout.addWidget(self.stackedWidget)

        self.frame = QFrame(MuspyArtistModule)
        self.frame.setObjectName(u"frame")
        self.frame.setMaximumSize(QSize(16777215, 40))
        self.bottom_layout = QHBoxLayout(self.frame)
        self.bottom_layout.setObjectName(u"bottom_layout")
        self.bottom_layout.setContentsMargins(3, 3, 3, 3)
        self.load_artists_button = QPushButton(self.frame)
        self.load_artists_button.setObjectName(u"load_artists_button")
        self.load_artists_button.setMinimumSize(QSize(32, 32))
        self.load_artists_button.setMaximumSize(QSize(32, 32))
        icon5 = QIcon()
        icon5.addFile(u":/services/db_ol", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.load_artists_button.setIcon(icon5)
        self.load_artists_button.setIconSize(QSize(30, 30))
        self.load_artists_button.setFlat(True)

        self.bottom_layout.addWidget(self.load_artists_button)

        self.sync_artists_button = QPushButton(self.frame)
        self.sync_artists_button.setObjectName(u"sync_artists_button")
        self.sync_artists_button.setMinimumSize(QSize(32, 32))
        self.sync_artists_button.setMaximumSize(QSize(32, 32))
        icon6 = QIcon()
        icon6.addFile(u":/services/links_ol", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.sync_artists_button.setIcon(icon6)
        self.sync_artists_button.setIconSize(QSize(30, 30))
        self.sync_artists_button.setFlat(True)

        self.bottom_layout.addWidget(self.sync_artists_button)

        self.get_releases_button = QPushButton(self.frame)
        self.get_releases_button.setObjectName(u"get_releases_button")
        self.get_releases_button.setMinimumSize(QSize(32, 32))
        self.get_releases_button.setMaximumSize(QSize(32, 32))
        icon7 = QIcon()
        icon7.addFile(u":/services/musico", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.get_releases_button.setIcon(icon7)
        self.get_releases_button.setIconSize(QSize(30, 30))
        self.get_releases_button.setFlat(True)

        self.bottom_layout.addWidget(self.get_releases_button)

        self.get_releases_spotify_button = QPushButton(self.frame)
        self.get_releases_spotify_button.setObjectName(u"get_releases_spotify_button")
        self.get_releases_spotify_button.setMinimumSize(QSize(32, 32))
        self.get_releases_spotify_button.setMaximumSize(QSize(32, 32))
        self.get_releases_spotify_button.setIcon(icon4)
        self.get_releases_spotify_button.setIconSize(QSize(30, 30))
        self.get_releases_spotify_button.setFlat(True)

        self.bottom_layout.addWidget(self.get_releases_spotify_button)

        self.sync_lastfm_button = QPushButton(self.frame)
        self.sync_lastfm_button.setObjectName(u"sync_lastfm_button")
        self.sync_lastfm_button.setMinimumSize(QSize(32, 32))
        self.sync_lastfm_button.setMaximumSize(QSize(32, 32))
        icon8 = QIcon()
        icon8.addFile(u":/services/lastfm_ol", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.sync_lastfm_button.setIcon(icon8)
        self.sync_lastfm_button.setIconSize(QSize(30, 30))
        self.sync_lastfm_button.setFlat(True)

        self.bottom_layout.addWidget(self.sync_lastfm_button)

        self.get_releases_musicbrainz_button = QPushButton(self.frame)
        self.get_releases_musicbrainz_button.setObjectName(u"get_releases_musicbrainz_button")
        self.get_releases_musicbrainz_button.setMinimumSize(QSize(32, 32))
        self.get_releases_musicbrainz_button.setMaximumSize(QSize(32, 32))
        icon9 = QIcon()
        icon9.addFile(u":/services/musicbrainz", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.get_releases_musicbrainz_button.setIcon(icon9)
        self.get_releases_musicbrainz_button.setIconSize(QSize(30, 30))
        self.get_releases_musicbrainz_button.setFlat(True)

        self.bottom_layout.addWidget(self.get_releases_musicbrainz_button)

        self.networks_artists_button = QPushButton(self.frame)
        self.networks_artists_button.setObjectName(u"networks_artists_button")
        self.networks_artists_button.setMinimumSize(QSize(32, 32))
        self.networks_artists_button.setMaximumSize(QSize(32, 32))
        self.networks_artists_button.setStyleSheet(u"QPushButton {{ border-radius: 20}}")
        icon10 = QIcon()
        icon10.addFile(u":/services/networks_ol", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.networks_artists_button.setIcon(icon10)
        self.networks_artists_button.setIconSize(QSize(30, 30))
        self.networks_artists_button.setFlat(True)

        self.bottom_layout.addWidget(self.networks_artists_button)

        self.get_new_releases_button = QPushButton(self.frame)
        self.get_new_releases_button.setObjectName(u"get_new_releases_button")
        self.get_new_releases_button.setMinimumSize(QSize(32, 32))
        self.get_new_releases_button.setMaximumSize(QSize(32, 32))
        icon11 = QIcon()
        icon11.addFile(u":/services/save_ol", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.get_new_releases_button.setIcon(icon11)
        self.get_new_releases_button.setIconSize(QSize(30, 30))
        self.get_new_releases_button.setFlat(True)

        self.bottom_layout.addWidget(self.get_new_releases_button)


        self.verticalLayout.addWidget(self.frame)


        self.retranslateUi(MuspyArtistModule)

        self.stackedWidget.setCurrentIndex(9)


        QMetaObject.connectSlotsByName(MuspyArtistModule)
    # setupUi

    def retranslateUi(self, MuspyArtistModule):
        MuspyArtistModule.setWindowTitle(QCoreApplication.translate("MuspyArtistModule", u"Muspy Artist Module", None))
        self.artist_input.setPlaceholderText(QCoreApplication.translate("MuspyArtistModule", u"Introduce el nombre de un artista para buscar discos anunciados", None))
#if QT_CONFIG(tooltip)
        self.search_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Pos claro que es buscar...", None))
#endif // QT_CONFIG(tooltip)
        self.search_button.setText("")
        self.top_artists_label.setText(QCoreApplication.translate("MuspyArtistModule", u"Top Artistas Lastfm", None))
        ___qtablewidgetitem = self.artists_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("MuspyArtistModule", u"Artista", None));
        ___qtablewidgetitem1 = self.artists_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("MuspyArtistModule", u"Play Count", None));
        ___qtablewidgetitem2 = self.artists_table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("MuspyArtistModule", u"Usuarios", None));
        ___qtablewidgetitem3 = self.artists_table.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("MuspyArtistModule", u"Lastfm url", None));
        ___qtablewidgetitem4 = self.artists_table.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("MuspyArtistModule", u"Acciones", None));
        self.spotify_saved_tracks_count_label.setText(QCoreApplication.translate("MuspyArtistModule", u"Spotify Canciones Guardadas", None))
        ___qtablewidgetitem5 = self.spotify_saved_tracks_table.horizontalHeaderItem(0)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("MuspyArtistModule", u"Canci\u00f3n", None));
        ___qtablewidgetitem6 = self.spotify_saved_tracks_table.horizontalHeaderItem(1)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("MuspyArtistModule", u"Artista", None));
        ___qtablewidgetitem7 = self.spotify_saved_tracks_table.horizontalHeaderItem(2)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("MuspyArtistModule", u"\u00c1lbum", None));
        ___qtablewidgetitem8 = self.spotify_saved_tracks_table.horizontalHeaderItem(3)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("MuspyArtistModule", u"Duraci\u00f3n", None));
        ___qtablewidgetitem9 = self.spotify_saved_tracks_table.horizontalHeaderItem(4)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("MuspyArtistModule", u"Fecha", None));
        self.spotify_top_items_count_label.setText(QCoreApplication.translate("MuspyArtistModule", u"Spotify Top Items", None))
        self.bluesky_count_label.setText(QCoreApplication.translate("MuspyArtistModule", u"Bluesky", None))
        ___qtablewidgetitem10 = self.bluesky_artists_table.horizontalHeaderItem(0)
        ___qtablewidgetitem10.setText(QCoreApplication.translate("MuspyArtistModule", u"seguir", None));
        ___qtablewidgetitem11 = self.bluesky_artists_table.horizontalHeaderItem(1)
        ___qtablewidgetitem11.setText(QCoreApplication.translate("MuspyArtistModule", u"artista", None));
        ___qtablewidgetitem12 = self.bluesky_artists_table.horizontalHeaderItem(2)
        ___qtablewidgetitem12.setText(QCoreApplication.translate("MuspyArtistModule", u"bluesky id", None));
        ___qtablewidgetitem13 = self.bluesky_artists_table.horizontalHeaderItem(3)
        ___qtablewidgetitem13.setText(QCoreApplication.translate("MuspyArtistModule", u"bluesky url", None));
        self.bluesky_follow.setText(QCoreApplication.translate("MuspyArtistModule", u"Seguir artistas en Bluesky", None))
        self.bluesky_selected_artist_foto.setText(QCoreApplication.translate("MuspyArtistModule", u"TextLabel", None))
        self.bluesky_profile_panel.setHtml(QCoreApplication.translate("MuspyArtistModule", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Sans Serif'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Selecciona alg\u00fan artista</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>", None))
        self.bluesky_selected_artist_mensajes.setHtml(QCoreApplication.translate("MuspyArtistModule", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Sans Serif'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Selecciona alg\u00fan artista</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>", None))
        self.twitter_users_count_label.setText(QCoreApplication.translate("MuspyArtistModule", u"Artistas en Twitter", None))
        ___qtablewidgetitem14 = self.twitter_users_table.horizontalHeaderItem(0)
        ___qtablewidgetitem14.setText(QCoreApplication.translate("MuspyArtistModule", u"Select", None));
        ___qtablewidgetitem15 = self.twitter_users_table.horizontalHeaderItem(1)
        ___qtablewidgetitem15.setText(QCoreApplication.translate("MuspyArtistModule", u"Name", None));
        ___qtablewidgetitem16 = self.twitter_users_table.horizontalHeaderItem(2)
        ___qtablewidgetitem16.setText(QCoreApplication.translate("MuspyArtistModule", u"Username", None));
        ___qtablewidgetitem17 = self.twitter_users_table.horizontalHeaderItem(3)
        ___qtablewidgetitem17.setText(QCoreApplication.translate("MuspyArtistModule", u"Followers", None));
        ___qtablewidgetitem18 = self.twitter_users_table.horizontalHeaderItem(4)
        ___qtablewidgetitem18.setText(QCoreApplication.translate("MuspyArtistModule", u"Following", None));
        ___qtablewidgetitem19 = self.twitter_users_table.horizontalHeaderItem(5)
        ___qtablewidgetitem19.setText(QCoreApplication.translate("MuspyArtistModule", u"Tweets", None));
        self.seguir_twitter.setText(QCoreApplication.translate("MuspyArtistModule", u"Seguir en Twitter / X", None))
        self.twitter_foto_label.setText(QCoreApplication.translate("MuspyArtistModule", u"TextLabel", None))
        self.mb_label.setText(QCoreApplication.translate("MuspyArtistModule", u"Colecciones de musicbrainz", None))
        ___qtablewidgetitem20 = self.tabla_musicbrainz_collection.horizontalHeaderItem(0)
        ___qtablewidgetitem20.setText(QCoreApplication.translate("MuspyArtistModule", u"Artista", None));
        ___qtablewidgetitem21 = self.tabla_musicbrainz_collection.horizontalHeaderItem(1)
        ___qtablewidgetitem21.setText(QCoreApplication.translate("MuspyArtistModule", u"Artista MBID", None));
        ___qtablewidgetitem22 = self.tabla_musicbrainz_collection.horizontalHeaderItem(2)
        ___qtablewidgetitem22.setText(QCoreApplication.translate("MuspyArtistModule", u"T\u00edtulo Lanzamiento", None));
        ___qtablewidgetitem23 = self.tabla_musicbrainz_collection.horizontalHeaderItem(3)
        ___qtablewidgetitem23.setText(QCoreApplication.translate("MuspyArtistModule", u"Tipo", None));
        ___qtablewidgetitem24 = self.tabla_musicbrainz_collection.horizontalHeaderItem(4)
        ___qtablewidgetitem24.setText(QCoreApplication.translate("MuspyArtistModule", u"Fecha", None));
        ___qtablewidgetitem25 = self.tabla_musicbrainz_collection.horizontalHeaderItem(5)
        ___qtablewidgetitem25.setText(QCoreApplication.translate("MuspyArtistModule", u"Estado", None));
        ___qtablewidgetitem26 = self.tabla_musicbrainz_collection.horizontalHeaderItem(6)
        ___qtablewidgetitem26.setText(QCoreApplication.translate("MuspyArtistModule", u"Pa\u00eds", None));
        self.create_label.setText(QCoreApplication.translate("MuspyArtistModule", u"Crear publicaci\u00f3n?", None))
        self.label_result_count.setText(QCoreApplication.translate("MuspyArtistModule", u"Resultados de la b\u00fasqueda", None))
        ___qtablewidgetitem27 = self.tableWidget_muspy_results.horizontalHeaderItem(0)
        ___qtablewidgetitem27.setText(QCoreApplication.translate("MuspyArtistModule", u"Artista", None));
        ___qtablewidgetitem28 = self.tableWidget_muspy_results.horizontalHeaderItem(1)
        ___qtablewidgetitem28.setText(QCoreApplication.translate("MuspyArtistModule", u"Publicaci\u00f3n", None));
        ___qtablewidgetitem29 = self.tableWidget_muspy_results.horizontalHeaderItem(2)
        ___qtablewidgetitem29.setText(QCoreApplication.translate("MuspyArtistModule", u"Tipo", None));
        ___qtablewidgetitem30 = self.tableWidget_muspy_results.horizontalHeaderItem(3)
        ___qtablewidgetitem30.setText(QCoreApplication.translate("MuspyArtistModule", u"Fecha", None));
        ___qtablewidgetitem31 = self.tableWidget_muspy_results.horizontalHeaderItem(4)
        ___qtablewidgetitem31.setText(QCoreApplication.translate("MuspyArtistModule", u"Desambiguaci\u00f3n", None));
        self.follow_artist_button.setText(QCoreApplication.translate("MuspyArtistModule", u"Seguir Artista", None))
        self.releases_label.setText(QCoreApplication.translate("MuspyArtistModule", u"Futuros \u00e1lbumes", None))
        ___qtablewidgetitem32 = self.releases_table.horizontalHeaderItem(0)
        ___qtablewidgetitem32.setText(QCoreApplication.translate("MuspyArtistModule", u"Artista", None));
        ___qtablewidgetitem33 = self.releases_table.horizontalHeaderItem(1)
        ___qtablewidgetitem33.setText(QCoreApplication.translate("MuspyArtistModule", u"Lanzamiento", None));
        ___qtablewidgetitem34 = self.releases_table.horizontalHeaderItem(2)
        ___qtablewidgetitem34.setText(QCoreApplication.translate("MuspyArtistModule", u"Tipo", None));
        ___qtablewidgetitem35 = self.releases_table.horizontalHeaderItem(3)
        ___qtablewidgetitem35.setText(QCoreApplication.translate("MuspyArtistModule", u"Fecha", None));
        ___qtablewidgetitem36 = self.releases_table.horizontalHeaderItem(4)
        ___qtablewidgetitem36.setText(QCoreApplication.translate("MuspyArtistModule", u"Desambiguaci\u00f3n", None));
        self.loved_songs_label.setText(QCoreApplication.translate("MuspyArtistModule", u"Canciones destacadas en LastFm", None))
        ___qtablewidgetitem37 = self.loved_tracks_table.horizontalHeaderItem(0)
        ___qtablewidgetitem37.setText(QCoreApplication.translate("MuspyArtistModule", u"Canci\u00f3n", None));
        ___qtablewidgetitem38 = self.loved_tracks_table.horizontalHeaderItem(1)
        ___qtablewidgetitem38.setText(QCoreApplication.translate("MuspyArtistModule", u"\u00c1lbum", None));
        ___qtablewidgetitem39 = self.loved_tracks_table.horizontalHeaderItem(2)
        ___qtablewidgetitem39.setText(QCoreApplication.translate("MuspyArtistModule", u"Artista", None));
        ___qtablewidgetitem40 = self.loved_tracks_table.horizontalHeaderItem(3)
        ___qtablewidgetitem40.setText(QCoreApplication.translate("MuspyArtistModule", u"Fecha", None));
        self.label.setText(QCoreApplication.translate("MuspyArtistModule", u"Log", None))
        self.spotify_artists_count_label.setText(QCoreApplication.translate("MuspyArtistModule", u"Artistas seguidos en Spotify", None))
        ___qtablewidgetitem41 = self.spotify_artists_table.horizontalHeaderItem(0)
        ___qtablewidgetitem41.setText(QCoreApplication.translate("MuspyArtistModule", u"Artista", None));
        ___qtablewidgetitem42 = self.spotify_artists_table.horizontalHeaderItem(1)
        ___qtablewidgetitem42.setText(QCoreApplication.translate("MuspyArtistModule", u"G\u00e9nero", None));
        ___qtablewidgetitem43 = self.spotify_artists_table.horizontalHeaderItem(2)
        ___qtablewidgetitem43.setText(QCoreApplication.translate("MuspyArtistModule", u"Seguidores", None));
        ___qtablewidgetitem44 = self.spotify_artists_table.horizontalHeaderItem(3)
        ___qtablewidgetitem44.setText(QCoreApplication.translate("MuspyArtistModule", u"Popularidad", None));
        self.spotify_releases_count_label.setText(QCoreApplication.translate("MuspyArtistModule", u"Nuevos \u00e1lbumes seg\u00fan Spotify", None))
        ___qtablewidgetitem45 = self.spotify_releases_table.horizontalHeaderItem(0)
        ___qtablewidgetitem45.setText(QCoreApplication.translate("MuspyArtistModule", u"New Column", None));
        ___qtablewidgetitem46 = self.spotify_releases_table.horizontalHeaderItem(1)
        ___qtablewidgetitem46.setText(QCoreApplication.translate("MuspyArtistModule", u"Lanzamiento", None));
        ___qtablewidgetitem47 = self.spotify_releases_table.horizontalHeaderItem(2)
        ___qtablewidgetitem47.setText(QCoreApplication.translate("MuspyArtistModule", u"Tipo", None));
        ___qtablewidgetitem48 = self.spotify_releases_table.horizontalHeaderItem(3)
        ___qtablewidgetitem48.setText(QCoreApplication.translate("MuspyArtistModule", u"Fecha", None));
        ___qtablewidgetitem49 = self.spotify_releases_table.horizontalHeaderItem(4)
        ___qtablewidgetitem49.setText(QCoreApplication.translate("MuspyArtistModule", u"Canciones", None));
#if QT_CONFIG(tooltip)
        self.load_artists_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Cargar desde db", None))
#endif // QT_CONFIG(tooltip)
        self.load_artists_button.setText("")
#if QT_CONFIG(tooltip)
        self.sync_artists_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Sincronizar con Muspy", None))
#endif // QT_CONFIG(tooltip)
        self.sync_artists_button.setText("")
#if QT_CONFIG(tooltip)
        self.get_releases_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Pr\u00f3ximos lanzamientos", None))
#endif // QT_CONFIG(tooltip)
        self.get_releases_button.setText("")
#if QT_CONFIG(tooltip)
        self.get_releases_spotify_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Spotify", None))
#endif // QT_CONFIG(tooltip)
        self.get_releases_spotify_button.setText("")
#if QT_CONFIG(tooltip)
        self.sync_lastfm_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Lastfm", None))
#endif // QT_CONFIG(tooltip)
        self.sync_lastfm_button.setText("")
#if QT_CONFIG(tooltip)
        self.get_releases_musicbrainz_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Colecciones Musicbrainz", None))
#endif // QT_CONFIG(tooltip)
        self.get_releases_musicbrainz_button.setText("")
#if QT_CONFIG(tooltip)
        self.networks_artists_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Redes de los artistas", None))
#endif // QT_CONFIG(tooltip)
        self.networks_artists_button.setText("")
#if QT_CONFIG(tooltip)
        self.get_new_releases_button.setToolTip(QCoreApplication.translate("MuspyArtistModule", u"Discos ausentes", None))
#endif // QT_CONFIG(tooltip)
        self.get_new_releases_button.setText("")
    # retranslateUi

