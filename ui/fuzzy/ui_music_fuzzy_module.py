# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'music_fuzzy_module.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLayout, QLineEdit, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QSplitter, QStackedWidget,
    QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget)
import rc_images

class Ui_MusicBrowser(object):
    def setupUi(self, MusicBrowser):
        if not MusicBrowser.objectName():
            MusicBrowser.setObjectName(u"MusicBrowser")
        MusicBrowser.resize(1510, 804)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MusicBrowser.sizePolicy().hasHeightForWidth())
        MusicBrowser.setSizePolicy(sizePolicy)
        MusicBrowser.setStyleSheet(u"            QPushButton {{\n"
"                background-color: {theme['bg']};\n"
"                border: 2px;\n"
"                border-radius: 19px;\n"
"            }}\n"
"            \n"
"            \n"
"            QPushButton:hover {{\n"
"                background-color: {theme['button_hover']};\n"
"                margin: 1px;\n"
"                margin-top: 0px;\n"
"                margin-bottom: 3px;\n"
"            }}\n"
"            \n"
"            QPushButton:pressed {{\n"
"                background-color: {theme['selection']};\n"
"                border: none;\n"
"            }}")
        self.verticalLayout = QVBoxLayout(MusicBrowser)
        self.verticalLayout.setSpacing(5)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.top_container = QFrame(MusicBrowser)
        self.top_container.setObjectName(u"top_container")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.top_container.sizePolicy().hasHeightForWidth())
        self.top_container.setSizePolicy(sizePolicy1)
        self.top_container.setMaximumSize(QSize(16777215, 60))
        self.top_container.setFrameShape(QFrame.Shape.NoFrame)
        self.top_container.setFrameShadow(QFrame.Shadow.Plain)
        self.top_container.setLineWidth(0)
        self.top_layout = QVBoxLayout(self.top_container)
        self.top_layout.setSpacing(5)
        self.top_layout.setObjectName(u"top_layout")
        self.top_layout.setContentsMargins(5, 5, 5, 5)
        self.search_frame = QFrame(self.top_container)
        self.search_frame.setObjectName(u"search_frame")
        sizePolicy1.setHeightForWidth(self.search_frame.sizePolicy().hasHeightForWidth())
        self.search_frame.setSizePolicy(sizePolicy1)
        self.search_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.search_frame.setLineWidth(0)
        self.search_layout = QHBoxLayout(self.search_frame)
        self.search_layout.setObjectName(u"search_layout")
        self.search_layout.setContentsMargins(0, 0, 0, 0)
        self.search_box = QLineEdit(self.search_frame)
        self.search_box.setObjectName(u"search_box")
        self.search_box.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.search_box.setFrame(True)

        self.search_layout.addWidget(self.search_box)

        self.advanced_settings_check = QCheckBox(self.search_frame)
        self.advanced_settings_check.setObjectName(u"advanced_settings_check")
        self.advanced_settings_check.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.search_layout.addWidget(self.advanced_settings_check)

        self.custom_button1 = QPushButton(self.search_frame)
        self.custom_button1.setObjectName(u"custom_button1")
        self.custom_button1.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.custom_button1.setVisible(False)

        self.search_layout.addWidget(self.custom_button1)

        self.custom_button2 = QPushButton(self.search_frame)
        self.custom_button2.setObjectName(u"custom_button2")
        self.custom_button2.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.custom_button2.setVisible(False)

        self.search_layout.addWidget(self.custom_button2)

        self.custom_button3 = QPushButton(self.search_frame)
        self.custom_button3.setObjectName(u"custom_button3")
        self.custom_button3.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.custom_button3.setVisible(False)

        self.search_layout.addWidget(self.custom_button3)


        self.top_layout.addWidget(self.search_frame)


        self.verticalLayout.addWidget(self.top_container)

        self.advanced_settings_container = QFrame(MusicBrowser)
        self.advanced_settings_container.setObjectName(u"advanced_settings_container")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.advanced_settings_container.sizePolicy().hasHeightForWidth())
        self.advanced_settings_container.setSizePolicy(sizePolicy2)
        self.advanced_settings_container.setVisible(False)
        self.advanced_settings_container.setFrameShape(QFrame.Shape.NoFrame)
        self.advanced_settings_container.setFrameShadow(QFrame.Shadow.Plain)

        self.verticalLayout.addWidget(self.advanced_settings_container)

        self.main_splitter = QSplitter(MusicBrowser)
        self.main_splitter.setObjectName(u"main_splitter")
        self.main_splitter.setOrientation(Qt.Orientation.Horizontal)
        self.results_tree_container = QFrame(self.main_splitter)
        self.results_tree_container.setObjectName(u"results_tree_container")
        self.results_tree_container.setMinimumSize(QSize(400, 0))
        self.results_tree_container.setFrameShape(QFrame.Shape.NoFrame)
        self.results_tree_container.setFrameShadow(QFrame.Shadow.Plain)
        self.verticalLayout_4 = QVBoxLayout(self.results_tree_container)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(-1, -1, -1, 0)
        self.results_tree_widget = QTreeWidget(self.results_tree_container)
        self.results_tree_widget.setObjectName(u"results_tree_widget")

        self.verticalLayout_4.addWidget(self.results_tree_widget)

        self.main_splitter.addWidget(self.results_tree_container)
        self.details_widget = QFrame(self.main_splitter)
        self.details_widget.setObjectName(u"details_widget")
        self.details_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.details_widget.setFrameShadow(QFrame.Shadow.Plain)
        self.details_layout = QVBoxLayout(self.details_widget)
        self.details_layout.setSpacing(0)
        self.details_layout.setObjectName(u"details_layout")
        self.details_layout.setContentsMargins(0, 0, 0, 0)
        self.images_container = QFrame(self.details_widget)
        self.images_container.setObjectName(u"images_container")
        sizePolicy2.setHeightForWidth(self.images_container.sizePolicy().hasHeightForWidth())
        self.images_container.setSizePolicy(sizePolicy2)
        self.images_container.setMinimumSize(QSize(0, 100))
        self.images_container.setFrameShape(QFrame.Shape.NoFrame)
        self.images_container.setFrameShadow(QFrame.Shadow.Plain)
        self.images_layout = QHBoxLayout(self.images_container)
        self.images_layout.setSpacing(10)
        self.images_layout.setObjectName(u"images_layout")
        self.images_layout.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_3 = QSpacerItem(40, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.images_layout.addItem(self.horizontalSpacer_3)

        self.cover_label = QLabel(self.images_container)
        self.cover_label.setObjectName(u"cover_label")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.cover_label.sizePolicy().hasHeightForWidth())
        self.cover_label.setSizePolicy(sizePolicy3)
        self.cover_label.setMinimumSize(QSize(200, 200))
        self.cover_label.setMaximumSize(QSize(300, 300))
        self.cover_label.setStyleSheet(u"border: 1px solid rgba(65, 72, 104, 0.5); border-radius: 4px;")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.images_layout.addWidget(self.cover_label)

        self.horizontalSpacer_2 = QSpacerItem(40, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.images_layout.addItem(self.horizontalSpacer_2)

        self.artist_image_label = QLabel(self.images_container)
        self.artist_image_label.setObjectName(u"artist_image_label")
        sizePolicy3.setHeightForWidth(self.artist_image_label.sizePolicy().hasHeightForWidth())
        self.artist_image_label.setSizePolicy(sizePolicy3)
        self.artist_image_label.setMinimumSize(QSize(200, 200))
        self.artist_image_label.setMaximumSize(QSize(300, 300))
        self.artist_image_label.setStyleSheet(u"border: 1px solid rgba(65, 72, 104, 0.5); border-radius: 4px;")
        self.artist_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.images_layout.addWidget(self.artist_image_label)

        self.horizontalSpacer = QSpacerItem(40, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.images_layout.addItem(self.horizontalSpacer)

        self.buttons_container = QFrame(self.images_container)
        self.buttons_container.setObjectName(u"buttons_container")
        self.buttons_container.setMinimumSize(QSize(120, 0))
        self.buttons_container.setMaximumSize(QSize(200, 250))
        self.buttons_container.setStyleSheet(u"            QPushButton {{\n"
"                background-color: {theme['bg']};\n"
"                border: 2px;\n"
"                border-radius: 19px;\n"
"            }}\n"
"            \n"
"            \n"
"            QPushButton:hover {{\n"
"                background-color: {theme['button_hover']};\n"
"                margin: 1px;\n"
"                margin-top: 0px;\n"
"                margin-bottom: 3px;\n"
"            }}\n"
"            \n"
"            QPushButton:pressed {{\n"
"                background-color: {theme['selection']};\n"
"                border: none;\n"
"            }}")
        self.buttons_container.setFrameShape(QFrame.Shape.NoFrame)
        self.gridLayout = QGridLayout(self.buttons_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.prev_button = QPushButton(self.buttons_container)
        self.prev_button.setObjectName(u"prev_button")
        self.prev_button.setMinimumSize(QSize(32, 32))
        self.prev_button.setMaximumSize(QSize(32, 32))
        self.prev_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.prev_button.setStyleSheet(u"            QPushButton {{\n"
"                background-color: {theme['bg']};\n"
"                border: 2px;\n"
"                border-radius: 19px;\n"
"            }}\n"
"            \n"
"            \n"
"            QPushButton:hover {{\n"
"                background-color: {theme['button_hover']};\n"
"                margin: 1px;\n"
"                margin-top: 0px;\n"
"                margin-bottom: 3px;\n"
"            }}\n"
"            \n"
"            QPushButton:pressed {{\n"
"                background-color: {theme['selection']};\n"
"                border: none;\n"
"            }}")
        icon = QIcon()
        icon.addFile(u":/services/rew", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.prev_button.setIcon(icon)
        self.prev_button.setIconSize(QSize(30, 30))
        self.prev_button.setFlat(True)

        self.gridLayout.addWidget(self.prev_button, 0, 0, 1, 1)

        self.folder_button = QPushButton(self.buttons_container)
        self.folder_button.setObjectName(u"folder_button")
        self.folder_button.setMinimumSize(QSize(32, 32))
        self.folder_button.setMaximumSize(QSize(32, 32))
        self.folder_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.folder_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"}")
        icon1 = QIcon()
        icon1.addFile(u":/services/folder", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.folder_button.setIcon(icon1)
        self.folder_button.setIconSize(QSize(30, 30))
        self.folder_button.setFlat(True)

        self.gridLayout.addWidget(self.folder_button, 3, 0, 1, 1)

        self.next_button = QPushButton(self.buttons_container)
        self.next_button.setObjectName(u"next_button")
        self.next_button.setMinimumSize(QSize(32, 32))
        self.next_button.setMaximumSize(QSize(32, 32))
        self.next_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.next_button.setStyleSheet(u"            QPushButton {{\n"
"                background-color: {theme['bg']};\n"
"                border: 2px;\n"
"                border-radius: 19px;\n"
"            }}\n"
"            \n"
"            \n"
"            QPushButton:hover {{\n"
"                background-color: {theme['button_hover']};\n"
"                margin: 1px;\n"
"                margin-top: 0px;\n"
"                margin-bottom: 3px;\n"
"            }}\n"
"            \n"
"            QPushButton:pressed {{\n"
"                background-color: {theme['selection']};\n"
"                border: none;\n"
"            }}")
        icon2 = QIcon()
        icon2.addFile(u":/services/ff", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.next_button.setIcon(icon2)
        self.next_button.setIconSize(QSize(30, 30))
        self.next_button.setFlat(True)

        self.gridLayout.addWidget(self.next_button, 0, 6, 1, 1)

        self.playing_button = QPushButton(self.buttons_container)
        self.playing_button.setObjectName(u"playing_button")
        self.playing_button.setMinimumSize(QSize(32, 32))
        self.playing_button.setMaximumSize(QSize(32, 32))
        self.playing_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"}")
        icon3 = QIcon()
        icon3.addFile(u":/services/search_circulo", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.playing_button.setIcon(icon3)
        self.playing_button.setIconSize(QSize(30, 30))
        self.playing_button.setFlat(True)

        self.gridLayout.addWidget(self.playing_button, 7, 0, 1, 1)

        self.conciertos_button = QPushButton(self.buttons_container)
        self.conciertos_button.setObjectName(u"conciertos_button")
        self.conciertos_button.setMinimumSize(QSize(32, 32))
        self.conciertos_button.setMaximumSize(QSize(32, 32))
        self.conciertos_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.conciertos_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"}")
        icon4 = QIcon()
        icon4.addFile(u":/services/musico2", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.conciertos_button.setIcon(icon4)
        self.conciertos_button.setIconSize(QSize(30, 30))
        self.conciertos_button.setFlat(True)

        self.gridLayout.addWidget(self.conciertos_button, 6, 6, 1, 1)

        self.scrobble_button = QPushButton(self.buttons_container)
        self.scrobble_button.setObjectName(u"scrobble_button")
        self.scrobble_button.setMinimumSize(QSize(32, 32))
        self.scrobble_button.setMaximumSize(QSize(32, 32))
        self.scrobble_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"}")
        icon5 = QIcon()
        icon5.addFile(u":/services/lastfm", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.scrobble_button.setIcon(icon5)
        self.scrobble_button.setIconSize(QSize(30, 30))
        self.scrobble_button.setFlat(True)

        self.gridLayout.addWidget(self.scrobble_button, 6, 3, 1, 1)

        self.muspy_button = QPushButton(self.buttons_container)
        self.muspy_button.setObjectName(u"muspy_button")
        self.muspy_button.setMinimumSize(QSize(32, 32))
        self.muspy_button.setMaximumSize(QSize(32, 32))
        self.muspy_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.muspy_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"}")
        icon6 = QIcon()
        icon6.addFile(u":/services/chicken2", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.muspy_button.setIcon(icon6)
        self.muspy_button.setIconSize(QSize(30, 30))
        self.muspy_button.setFlat(True)

        self.gridLayout.addWidget(self.muspy_button, 7, 3, 1, 1)

        self.url_playlists_button = QPushButton(self.buttons_container)
        self.url_playlists_button.setObjectName(u"url_playlists_button")
        self.url_playlists_button.setMinimumSize(QSize(32, 32))
        self.url_playlists_button.setMaximumSize(QSize(32, 32))
        self.url_playlists_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.url_playlists_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"}")
        icon7 = QIcon()
        icon7.addFile(u":/services/cloud", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.url_playlists_button.setIcon(icon7)
        self.url_playlists_button.setIconSize(QSize(30, 30))
        self.url_playlists_button.setFlat(True)

        self.gridLayout.addWidget(self.url_playlists_button, 3, 5, 1, 1)

        self.jaangle_button = QPushButton(self.buttons_container)
        self.jaangle_button.setObjectName(u"jaangle_button")
        self.jaangle_button.setMinimumSize(QSize(32, 32))
        self.jaangle_button.setMaximumSize(QSize(32, 32))
        self.jaangle_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"}")
        icon8 = QIcon()
        icon8.addFile(u":/services/game", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.jaangle_button.setIcon(icon8)
        self.jaangle_button.setIconSize(QSize(30, 30))
        self.jaangle_button.setFlat(True)

        self.gridLayout.addWidget(self.jaangle_button, 6, 5, 1, 1)

        self.db_editor_button = QPushButton(self.buttons_container)
        self.db_editor_button.setObjectName(u"db_editor_button")
        self.db_editor_button.setMinimumSize(QSize(32, 32))
        self.db_editor_button.setMaximumSize(QSize(32, 32))
        self.db_editor_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.db_editor_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"}")
        icon9 = QIcon()
        icon9.addFile(u":/services/dbsearch", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.db_editor_button.setIcon(icon9)
        self.db_editor_button.setIconSize(QSize(30, 30))
        self.db_editor_button.setFlat(True)

        self.gridLayout.addWidget(self.db_editor_button, 3, 6, 1, 1)

        self.spotify_button = QPushButton(self.buttons_container)
        self.spotify_button.setObjectName(u"spotify_button")
        self.spotify_button.setMinimumSize(QSize(32, 32))
        self.spotify_button.setMaximumSize(QSize(32, 32))
        self.spotify_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"	border: none;\n"
"}\n"
"QPushButton:pressed {{\n"
"	background-color: {theme['selection']};\n"
"	border: none;\n"
"}}")
        icon10 = QIcon()
        icon10.addFile(u":/services/spotify", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.spotify_button.setIcon(icon10)
        self.spotify_button.setIconSize(QSize(30, 30))
        self.spotify_button.setFlat(True)

        self.gridLayout.addWidget(self.spotify_button, 6, 0, 1, 1)

        self.stop_button = QPushButton(self.buttons_container)
        self.stop_button.setObjectName(u"stop_button")
        self.stop_button.setMinimumSize(QSize(32, 32))
        self.stop_button.setMaximumSize(QSize(32, 32))
        self.stop_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"}")
        icon11 = QIcon()
        icon11.addFile(u":/services/stop", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.stop_button.setIcon(icon11)
        self.stop_button.setIconSize(QSize(30, 30))
        self.stop_button.setFlat(True)

        self.gridLayout.addWidget(self.stop_button, 0, 5, 1, 1)

        self.add_to_queue_button = QPushButton(self.buttons_container)
        self.add_to_queue_button.setObjectName(u"add_to_queue_button")
        self.add_to_queue_button.setMinimumSize(QSize(32, 32))
        self.add_to_queue_button.setMaximumSize(QSize(32, 32))
        self.add_to_queue_button.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.add_to_queue_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"	border: none;\n"
"}\n"
"QPushButton:pressed {{\n"
"	background-color: {theme['selection']};\n"
"	border: none;\n"
"}}")
        icon12 = QIcon()
        icon12.addFile(u":/services/clock", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.add_to_queue_button.setIcon(icon12)
        self.add_to_queue_button.setIconSize(QSize(30, 30))
        self.add_to_queue_button.setFlat(True)

        self.gridLayout.addWidget(self.add_to_queue_button, 3, 3, 1, 1)

        self.play_button = QPushButton(self.buttons_container)
        self.play_button.setObjectName(u"play_button")
        self.play_button.setMinimumSize(QSize(32, 32))
        self.play_button.setMaximumSize(QSize(32, 32))
        self.play_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.play_button.setStyleSheet(u"            QPushButton {{\n"
"                background-color: {theme['bg']};\n"
"                border: 2px;\n"
"                border-radius: 19px;\n"
"            }}\n"
"            \n"
"            \n"
"            QPushButton:hover {{\n"
"                background-color: {theme['button_hover']};\n"
"                margin: 1px;\n"
"                margin-top: 0px;\n"
"                margin-bottom: 3px;\n"
"            }}\n"
"            \n"
"            QPushButton:pressed {{\n"
"                background-color: {theme['selection']};\n"
"                border: none;\n"
"            }}")
        icon13 = QIcon()
        icon13.addFile(u":/services/play", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.play_button.setIcon(icon13)
        self.play_button.setIconSize(QSize(30, 30))
        self.play_button.setFlat(True)

        self.gridLayout.addWidget(self.play_button, 0, 3, 1, 1)

        self.feeds_button = QPushButton(self.buttons_container)
        self.feeds_button.setObjectName(u"feeds_button")
        self.feeds_button.setMinimumSize(QSize(32, 32))
        self.feeds_button.setMaximumSize(QSize(32, 32))
        self.feeds_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"}")
        icon14 = QIcon()
        icon14.addFile(u":/services/rss", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.feeds_button.setIcon(icon14)
        self.feeds_button.setIconSize(QSize(30, 30))
        self.feeds_button.setFlat(True)

        self.gridLayout.addWidget(self.feeds_button, 7, 6, 1, 1)

        self.stats_button = QPushButton(self.buttons_container)
        self.stats_button.setObjectName(u"stats_button")
        self.stats_button.setMinimumSize(QSize(32, 32))
        self.stats_button.setMaximumSize(QSize(32, 32))
        self.stats_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stats_button.setStyleSheet(u"QPushButton {{\n"
"  border-radius: 25px;\n"
"  border: none;\n"
"  padding: 8px 16px;\n"
"  margin: 2px\n"
"}}\n"
"QPushButton:hover {\n"
"    background-color: {theme['button_hover']};\n"
"    margin: 1px;\n"
"    margin-top: 0px;\n"
"    margin-bottom: 3px;\n"
"}")
        icon15 = QIcon()
        icon15.addFile(u":/services/msg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.stats_button.setIcon(icon15)
        self.stats_button.setIconSize(QSize(30, 30))
        self.stats_button.setFlat(True)

        self.gridLayout.addWidget(self.stats_button, 7, 5, 1, 1)


        self.images_layout.addWidget(self.buttons_container)


        self.details_layout.addWidget(self.images_container)

        self.info_container = QFrame(self.details_widget)
        self.info_container.setObjectName(u"info_container")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.info_container.sizePolicy().hasHeightForWidth())
        self.info_container.setSizePolicy(sizePolicy4)
        self.info_container.setFrameShape(QFrame.Shape.NoFrame)
        self.info_container.setFrameShadow(QFrame.Shadow.Plain)
        self.verticalLayout_3 = QVBoxLayout(self.info_container)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.info_panel_stacked = QStackedWidget(self.info_container)
        self.info_panel_stacked.setObjectName(u"info_panel_stacked")
        self.info_page = QWidget()
        self.info_page.setObjectName(u"info_page")
        self.verticalLayout_5 = QVBoxLayout(self.info_page)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.info_scroll = QScrollArea(self.info_page)
        self.info_scroll.setObjectName(u"info_scroll")
        self.info_scroll.setWidgetResizable(True)
        self.texto_widget = QWidget()
        self.texto_widget.setObjectName(u"texto_widget")
        self.texto_widget.setGeometry(QRect(0, 0, 1037, 471))
        self.verticalLayout_11 = QVBoxLayout(self.texto_widget)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.artist_links_group = QGroupBox(self.texto_widget)
        self.artist_links_group.setObjectName(u"artist_links_group")
        self.horizontalLayout_3 = QHBoxLayout(self.artist_links_group)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.bc_link_button = QPushButton(self.artist_links_group)
        self.bc_link_button.setObjectName(u"bc_link_button")
        self.bc_link_button.setMinimumSize(QSize(34, 34))
        self.bc_link_button.setMaximumSize(QSize(34, 34))
        icon16 = QIcon()
        icon16.addFile(u":/services/bandcamp", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.bc_link_button.setIcon(icon16)
        self.bc_link_button.setIconSize(QSize(32, 32))
        self.bc_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.bc_link_button)

        self.soudcloud_link_button = QPushButton(self.artist_links_group)
        self.soudcloud_link_button.setObjectName(u"soudcloud_link_button")
        self.soudcloud_link_button.setMinimumSize(QSize(34, 34))
        self.soudcloud_link_button.setMaximumSize(QSize(34, 34))
        icon17 = QIcon()
        icon17.addFile(u":/services/soundcloud", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.soudcloud_link_button.setIcon(icon17)
        self.soudcloud_link_button.setIconSize(QSize(32, 32))
        self.soudcloud_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.soudcloud_link_button)

        self.yt_link_button = QPushButton(self.artist_links_group)
        self.yt_link_button.setObjectName(u"yt_link_button")
        self.yt_link_button.setMinimumSize(QSize(34, 34))
        self.yt_link_button.setMaximumSize(QSize(34, 34))
        icon18 = QIcon()
        icon18.addFile(u":/services/youtube", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.yt_link_button.setIcon(icon18)
        self.yt_link_button.setIconSize(QSize(32, 32))
        self.yt_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.yt_link_button)

        self.spot_link_button = QPushButton(self.artist_links_group)
        self.spot_link_button.setObjectName(u"spot_link_button")
        self.spot_link_button.setMinimumSize(QSize(34, 34))
        self.spot_link_button.setMaximumSize(QSize(34, 34))
        self.spot_link_button.setIcon(icon10)
        self.spot_link_button.setIconSize(QSize(32, 32))
        self.spot_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.spot_link_button)

        self.vimeo_link_button = QPushButton(self.artist_links_group)
        self.vimeo_link_button.setObjectName(u"vimeo_link_button")
        self.vimeo_link_button.setMinimumSize(QSize(34, 34))
        self.vimeo_link_button.setMaximumSize(QSize(34, 34))
        icon19 = QIcon()
        icon19.addFile(u":/services/vimeo", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.vimeo_link_button.setIcon(icon19)
        self.vimeo_link_button.setIconSize(QSize(32, 32))
        self.vimeo_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.vimeo_link_button)

        self.boomkat_link_button = QPushButton(self.artist_links_group)
        self.boomkat_link_button.setObjectName(u"boomkat_link_button")
        self.boomkat_link_button.setMinimumSize(QSize(34, 34))
        self.boomkat_link_button.setMaximumSize(QSize(34, 34))
        icon20 = QIcon()
        icon20.addFile(u":/services/boomkat", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.boomkat_link_button.setIcon(icon20)
        self.boomkat_link_button.setIconSize(QSize(32, 32))
        self.boomkat_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.boomkat_link_button)

        self.juno_link_button = QPushButton(self.artist_links_group)
        self.juno_link_button.setObjectName(u"juno_link_button")
        self.juno_link_button.setMinimumSize(QSize(34, 34))
        self.juno_link_button.setMaximumSize(QSize(34, 34))
        icon21 = QIcon()
        icon21.addFile(u":/services/juno", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.juno_link_button.setIcon(icon21)
        self.juno_link_button.setIconSize(QSize(32, 32))
        self.juno_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.juno_link_button)

        self.allmusic_link_button = QPushButton(self.artist_links_group)
        self.allmusic_link_button.setObjectName(u"allmusic_link_button")
        self.allmusic_link_button.setMinimumSize(QSize(34, 34))
        self.allmusic_link_button.setMaximumSize(QSize(34, 34))
        icon22 = QIcon()
        icon22.addFile(u":/services/allmusic", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.allmusic_link_button.setIcon(icon22)
        self.allmusic_link_button.setIconSize(QSize(32, 32))
        self.allmusic_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.allmusic_link_button)

        self.discogs_link_button = QPushButton(self.artist_links_group)
        self.discogs_link_button.setObjectName(u"discogs_link_button")
        self.discogs_link_button.setMinimumSize(QSize(34, 34))
        self.discogs_link_button.setMaximumSize(QSize(34, 34))
        icon23 = QIcon()
        icon23.addFile(u":/services/discogs", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.discogs_link_button.setIcon(icon23)
        self.discogs_link_button.setIconSize(QSize(32, 32))
        self.discogs_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.discogs_link_button)

        self.imdb_link_button = QPushButton(self.artist_links_group)
        self.imdb_link_button.setObjectName(u"imdb_link_button")
        self.imdb_link_button.setMinimumSize(QSize(34, 34))
        self.imdb_link_button.setMaximumSize(QSize(34, 34))
        icon24 = QIcon()
        icon24.addFile(u":/services/imdb", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.imdb_link_button.setIcon(icon24)
        self.imdb_link_button.setIconSize(QSize(32, 32))
        self.imdb_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.imdb_link_button)

        self.lastfm_link_button = QPushButton(self.artist_links_group)
        self.lastfm_link_button.setObjectName(u"lastfm_link_button")
        self.lastfm_link_button.setMinimumSize(QSize(34, 34))
        self.lastfm_link_button.setMaximumSize(QSize(34, 34))
        self.lastfm_link_button.setIcon(icon5)
        self.lastfm_link_button.setIconSize(QSize(32, 32))
        self.lastfm_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.lastfm_link_button)

        self.mb_link_button = QPushButton(self.artist_links_group)
        self.mb_link_button.setObjectName(u"mb_link_button")
        self.mb_link_button.setMinimumSize(QSize(34, 34))
        self.mb_link_button.setMaximumSize(QSize(34, 34))
        icon25 = QIcon()
        icon25.addFile(u":/services/musicbrainz", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.mb_link_button.setIcon(icon25)
        self.mb_link_button.setIconSize(QSize(32, 32))
        self.mb_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.mb_link_button)

        self.prog_link_button = QPushButton(self.artist_links_group)
        self.prog_link_button.setObjectName(u"prog_link_button")
        self.prog_link_button.setMinimumSize(QSize(34, 34))
        self.prog_link_button.setMaximumSize(QSize(34, 34))
        icon26 = QIcon()
        icon26.addFile(u":/services/guitar", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.prog_link_button.setIcon(icon26)
        self.prog_link_button.setIconSize(QSize(32, 32))
        self.prog_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.prog_link_button)

        self.rym_link_button = QPushButton(self.artist_links_group)
        self.rym_link_button.setObjectName(u"rym_link_button")
        self.rym_link_button.setMinimumSize(QSize(34, 34))
        self.rym_link_button.setMaximumSize(QSize(34, 34))
        icon27 = QIcon()
        icon27.addFile(u":/services/rym_svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.rym_link_button.setIcon(icon27)
        self.rym_link_button.setIconSize(QSize(32, 32))
        self.rym_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.rym_link_button)

        self.ra_link_button = QPushButton(self.artist_links_group)
        self.ra_link_button.setObjectName(u"ra_link_button")
        self.ra_link_button.setMinimumSize(QSize(34, 34))
        self.ra_link_button.setMaximumSize(QSize(34, 34))
        icon28 = QIcon()
        icon28.addFile(u":/services/ra", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.ra_link_button.setIcon(icon28)
        self.ra_link_button.setIconSize(QSize(32, 32))
        self.ra_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.ra_link_button)

        self.setlist_link_button = QPushButton(self.artist_links_group)
        self.setlist_link_button.setObjectName(u"setlist_link_button")
        self.setlist_link_button.setMinimumSize(QSize(34, 34))
        self.setlist_link_button.setMaximumSize(QSize(34, 34))
        self.setlist_link_button.setIcon(icon15)
        self.setlist_link_button.setIconSize(QSize(32, 32))
        self.setlist_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.setlist_link_button)

        self.wiki_link_button = QPushButton(self.artist_links_group)
        self.wiki_link_button.setObjectName(u"wiki_link_button")
        self.wiki_link_button.setMinimumSize(QSize(34, 34))
        self.wiki_link_button.setMaximumSize(QSize(34, 34))
        icon29 = QIcon()
        icon29.addFile(u":/services/wiki", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.wiki_link_button.setIcon(icon29)
        self.wiki_link_button.setIconSize(QSize(32, 32))
        self.wiki_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.wiki_link_button)

        self.whosampled_link_button = QPushButton(self.artist_links_group)
        self.whosampled_link_button.setObjectName(u"whosampled_link_button")
        self.whosampled_link_button.setMinimumSize(QSize(34, 34))
        self.whosampled_link_button.setMaximumSize(QSize(34, 34))
        icon30 = QIcon()
        icon30.addFile(u":/services/whosampled", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.whosampled_link_button.setIcon(icon30)
        self.whosampled_link_button.setIconSize(QSize(32, 32))
        self.whosampled_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.whosampled_link_button)

        self.bluesky_link_button = QPushButton(self.artist_links_group)
        self.bluesky_link_button.setObjectName(u"bluesky_link_button")
        self.bluesky_link_button.setMinimumSize(QSize(34, 34))
        self.bluesky_link_button.setMaximumSize(QSize(34, 34))
        icon31 = QIcon()
        icon31.addFile(u":/services/bluesky", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.bluesky_link_button.setIcon(icon31)
        self.bluesky_link_button.setIconSize(QSize(32, 32))
        self.bluesky_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.bluesky_link_button)

        self.fb_link_button = QPushButton(self.artist_links_group)
        self.fb_link_button.setObjectName(u"fb_link_button")
        self.fb_link_button.setMinimumSize(QSize(34, 34))
        self.fb_link_button.setMaximumSize(QSize(34, 34))
        icon32 = QIcon()
        icon32.addFile(u":/services/facebook", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.fb_link_button.setIcon(icon32)
        self.fb_link_button.setIconSize(QSize(32, 32))
        self.fb_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.fb_link_button)

        self.ig_link_button = QPushButton(self.artist_links_group)
        self.ig_link_button.setObjectName(u"ig_link_button")
        self.ig_link_button.setMinimumSize(QSize(34, 34))
        self.ig_link_button.setMaximumSize(QSize(34, 34))
        icon33 = QIcon()
        icon33.addFile(u":/services/instagram", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.ig_link_button.setIcon(icon33)
        self.ig_link_button.setIconSize(QSize(32, 32))
        self.ig_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.ig_link_button)

        self.mastodon_link_button = QPushButton(self.artist_links_group)
        self.mastodon_link_button.setObjectName(u"mastodon_link_button")
        self.mastodon_link_button.setMinimumSize(QSize(34, 34))
        self.mastodon_link_button.setMaximumSize(QSize(34, 34))
        icon34 = QIcon()
        icon34.addFile(u":/services/mastodon", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.mastodon_link_button.setIcon(icon34)
        self.mastodon_link_button.setIconSize(QSize(32, 32))
        self.mastodon_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.mastodon_link_button)

        self.myspace_link_button = QPushButton(self.artist_links_group)
        self.myspace_link_button.setObjectName(u"myspace_link_button")
        self.myspace_link_button.setMinimumSize(QSize(34, 34))
        self.myspace_link_button.setMaximumSize(QSize(34, 34))
        icon35 = QIcon()
        icon35.addFile(u":/services/myspace", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.myspace_link_button.setIcon(icon35)
        self.myspace_link_button.setIconSize(QSize(32, 32))
        self.myspace_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.myspace_link_button)

        self.twitter_link_button = QPushButton(self.artist_links_group)
        self.twitter_link_button.setObjectName(u"twitter_link_button")
        self.twitter_link_button.setMinimumSize(QSize(34, 34))
        self.twitter_link_button.setMaximumSize(QSize(34, 34))
        icon36 = QIcon()
        icon36.addFile(u":/services/twitter", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.twitter_link_button.setIcon(icon36)
        self.twitter_link_button.setIconSize(QSize(32, 32))
        self.twitter_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.twitter_link_button)

        self.tumblr_link_button = QPushButton(self.artist_links_group)
        self.tumblr_link_button.setObjectName(u"tumblr_link_button")
        self.tumblr_link_button.setMinimumSize(QSize(34, 34))
        self.tumblr_link_button.setMaximumSize(QSize(34, 34))
        icon37 = QIcon()
        icon37.addFile(u":/services/tumblr", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.tumblr_link_button.setIcon(icon37)
        self.tumblr_link_button.setIconSize(QSize(32, 32))
        self.tumblr_link_button.setFlat(True)

        self.horizontalLayout_3.addWidget(self.tumblr_link_button)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_4)


        self.verticalLayout_11.addWidget(self.artist_links_group)

        self.album_links_group = QGroupBox(self.texto_widget)
        self.album_links_group.setObjectName(u"album_links_group")
        self.horizontalLayout_2 = QHBoxLayout(self.album_links_group)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.bc_album_link_button = QPushButton(self.album_links_group)
        self.bc_album_link_button.setObjectName(u"bc_album_link_button")
        self.bc_album_link_button.setMinimumSize(QSize(34, 34))
        self.bc_album_link_button.setMaximumSize(QSize(34, 34))
        self.bc_album_link_button.setIcon(icon16)
        self.bc_album_link_button.setIconSize(QSize(32, 32))
        self.bc_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.bc_album_link_button)

        self.soudcloud_album_link_button = QPushButton(self.album_links_group)
        self.soudcloud_album_link_button.setObjectName(u"soudcloud_album_link_button")
        self.soudcloud_album_link_button.setMinimumSize(QSize(34, 34))
        self.soudcloud_album_link_button.setMaximumSize(QSize(34, 34))
        self.soudcloud_album_link_button.setIcon(icon17)
        self.soudcloud_album_link_button.setIconSize(QSize(32, 32))
        self.soudcloud_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.soudcloud_album_link_button)

        self.yt_album_link_button = QPushButton(self.album_links_group)
        self.yt_album_link_button.setObjectName(u"yt_album_link_button")
        self.yt_album_link_button.setMinimumSize(QSize(34, 34))
        self.yt_album_link_button.setMaximumSize(QSize(34, 34))
        self.yt_album_link_button.setIcon(icon18)
        self.yt_album_link_button.setIconSize(QSize(32, 32))
        self.yt_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.yt_album_link_button)

        self.spot_album_link_button = QPushButton(self.album_links_group)
        self.spot_album_link_button.setObjectName(u"spot_album_link_button")
        self.spot_album_link_button.setMinimumSize(QSize(34, 34))
        self.spot_album_link_button.setMaximumSize(QSize(34, 34))
        self.spot_album_link_button.setIcon(icon10)
        self.spot_album_link_button.setIconSize(QSize(32, 32))
        self.spot_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.spot_album_link_button)

        self.vimeo_album_link_button = QPushButton(self.album_links_group)
        self.vimeo_album_link_button.setObjectName(u"vimeo_album_link_button")
        self.vimeo_album_link_button.setMinimumSize(QSize(34, 34))
        self.vimeo_album_link_button.setMaximumSize(QSize(34, 34))
        self.vimeo_album_link_button.setIcon(icon19)
        self.vimeo_album_link_button.setIconSize(QSize(32, 32))
        self.vimeo_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.vimeo_album_link_button)

        self.boomkat_album_link_button = QPushButton(self.album_links_group)
        self.boomkat_album_link_button.setObjectName(u"boomkat_album_link_button")
        self.boomkat_album_link_button.setMinimumSize(QSize(34, 34))
        self.boomkat_album_link_button.setMaximumSize(QSize(34, 34))
        self.boomkat_album_link_button.setIcon(icon20)
        self.boomkat_album_link_button.setIconSize(QSize(32, 32))
        self.boomkat_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.boomkat_album_link_button)

        self.juno_album_link_button = QPushButton(self.album_links_group)
        self.juno_album_link_button.setObjectName(u"juno_album_link_button")
        self.juno_album_link_button.setMinimumSize(QSize(34, 34))
        self.juno_album_link_button.setMaximumSize(QSize(34, 34))
        self.juno_album_link_button.setIcon(icon21)
        self.juno_album_link_button.setIconSize(QSize(32, 32))
        self.juno_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.juno_album_link_button)

        self.allmusic_album_link_button = QPushButton(self.album_links_group)
        self.allmusic_album_link_button.setObjectName(u"allmusic_album_link_button")
        self.allmusic_album_link_button.setMinimumSize(QSize(34, 34))
        self.allmusic_album_link_button.setMaximumSize(QSize(34, 34))
        self.allmusic_album_link_button.setIcon(icon22)
        self.allmusic_album_link_button.setIconSize(QSize(32, 32))
        self.allmusic_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.allmusic_album_link_button)

        self.discogs_album_link_button = QPushButton(self.album_links_group)
        self.discogs_album_link_button.setObjectName(u"discogs_album_link_button")
        self.discogs_album_link_button.setMinimumSize(QSize(34, 34))
        self.discogs_album_link_button.setMaximumSize(QSize(34, 34))
        self.discogs_album_link_button.setIcon(icon23)
        self.discogs_album_link_button.setIconSize(QSize(32, 32))
        self.discogs_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.discogs_album_link_button)

        self.imdb_album_link_button = QPushButton(self.album_links_group)
        self.imdb_album_link_button.setObjectName(u"imdb_album_link_button")
        self.imdb_album_link_button.setMinimumSize(QSize(34, 34))
        self.imdb_album_link_button.setMaximumSize(QSize(34, 34))
        self.imdb_album_link_button.setIcon(icon24)
        self.imdb_album_link_button.setIconSize(QSize(32, 32))
        self.imdb_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.imdb_album_link_button)

        self.lastfm_album_link_button = QPushButton(self.album_links_group)
        self.lastfm_album_link_button.setObjectName(u"lastfm_album_link_button")
        self.lastfm_album_link_button.setMinimumSize(QSize(34, 34))
        self.lastfm_album_link_button.setMaximumSize(QSize(34, 34))
        self.lastfm_album_link_button.setIcon(icon5)
        self.lastfm_album_link_button.setIconSize(QSize(32, 32))
        self.lastfm_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.lastfm_album_link_button)

        self.mb_album_link_button = QPushButton(self.album_links_group)
        self.mb_album_link_button.setObjectName(u"mb_album_link_button")
        self.mb_album_link_button.setMinimumSize(QSize(34, 34))
        self.mb_album_link_button.setMaximumSize(QSize(34, 34))
        self.mb_album_link_button.setIcon(icon25)
        self.mb_album_link_button.setIconSize(QSize(32, 32))
        self.mb_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.mb_album_link_button)

        self.prog_album_link_button = QPushButton(self.album_links_group)
        self.prog_album_link_button.setObjectName(u"prog_album_link_button")
        self.prog_album_link_button.setMinimumSize(QSize(34, 34))
        self.prog_album_link_button.setMaximumSize(QSize(34, 34))
        self.prog_album_link_button.setIcon(icon26)
        self.prog_album_link_button.setIconSize(QSize(32, 32))
        self.prog_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.prog_album_link_button)

        self.rym_album_link_button = QPushButton(self.album_links_group)
        self.rym_album_link_button.setObjectName(u"rym_album_link_button")
        self.rym_album_link_button.setMinimumSize(QSize(34, 34))
        self.rym_album_link_button.setMaximumSize(QSize(34, 34))
        self.rym_album_link_button.setIcon(icon27)
        self.rym_album_link_button.setIconSize(QSize(32, 32))
        self.rym_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.rym_album_link_button)

        self.ra_album_link_button = QPushButton(self.album_links_group)
        self.ra_album_link_button.setObjectName(u"ra_album_link_button")
        self.ra_album_link_button.setMinimumSize(QSize(34, 34))
        self.ra_album_link_button.setMaximumSize(QSize(34, 34))
        self.ra_album_link_button.setIcon(icon28)
        self.ra_album_link_button.setIconSize(QSize(32, 32))
        self.ra_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.ra_album_link_button)

        self.setlist_album_link_button = QPushButton(self.album_links_group)
        self.setlist_album_link_button.setObjectName(u"setlist_album_link_button")
        self.setlist_album_link_button.setMinimumSize(QSize(34, 34))
        self.setlist_album_link_button.setMaximumSize(QSize(34, 34))
        self.setlist_album_link_button.setIcon(icon15)
        self.setlist_album_link_button.setIconSize(QSize(32, 32))
        self.setlist_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.setlist_album_link_button)

        self.wiki_album_link_button = QPushButton(self.album_links_group)
        self.wiki_album_link_button.setObjectName(u"wiki_album_link_button")
        self.wiki_album_link_button.setMinimumSize(QSize(34, 34))
        self.wiki_album_link_button.setMaximumSize(QSize(34, 34))
        self.wiki_album_link_button.setIcon(icon29)
        self.wiki_album_link_button.setIconSize(QSize(32, 32))
        self.wiki_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.wiki_album_link_button)

        self.whosampled_album_link_button = QPushButton(self.album_links_group)
        self.whosampled_album_link_button.setObjectName(u"whosampled_album_link_button")
        self.whosampled_album_link_button.setMinimumSize(QSize(34, 34))
        self.whosampled_album_link_button.setMaximumSize(QSize(34, 34))
        self.whosampled_album_link_button.setIcon(icon30)
        self.whosampled_album_link_button.setIconSize(QSize(32, 32))
        self.whosampled_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.whosampled_album_link_button)

        self.bluesky_album_link_button = QPushButton(self.album_links_group)
        self.bluesky_album_link_button.setObjectName(u"bluesky_album_link_button")
        self.bluesky_album_link_button.setMinimumSize(QSize(34, 34))
        self.bluesky_album_link_button.setMaximumSize(QSize(34, 34))
        self.bluesky_album_link_button.setIcon(icon31)
        self.bluesky_album_link_button.setIconSize(QSize(32, 32))
        self.bluesky_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.bluesky_album_link_button)

        self.fb_album_link_button = QPushButton(self.album_links_group)
        self.fb_album_link_button.setObjectName(u"fb_album_link_button")
        self.fb_album_link_button.setMinimumSize(QSize(34, 34))
        self.fb_album_link_button.setMaximumSize(QSize(34, 34))
        self.fb_album_link_button.setIcon(icon32)
        self.fb_album_link_button.setIconSize(QSize(32, 32))
        self.fb_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.fb_album_link_button)

        self.ig_album_link_button = QPushButton(self.album_links_group)
        self.ig_album_link_button.setObjectName(u"ig_album_link_button")
        self.ig_album_link_button.setMinimumSize(QSize(34, 34))
        self.ig_album_link_button.setMaximumSize(QSize(34, 34))
        self.ig_album_link_button.setIcon(icon33)
        self.ig_album_link_button.setIconSize(QSize(32, 32))
        self.ig_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.ig_album_link_button)

        self.mastodon_album_link_button = QPushButton(self.album_links_group)
        self.mastodon_album_link_button.setObjectName(u"mastodon_album_link_button")
        self.mastodon_album_link_button.setMinimumSize(QSize(34, 34))
        self.mastodon_album_link_button.setMaximumSize(QSize(34, 34))
        self.mastodon_album_link_button.setIcon(icon34)
        self.mastodon_album_link_button.setIconSize(QSize(32, 32))
        self.mastodon_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.mastodon_album_link_button)

        self.myspace_album_link_button = QPushButton(self.album_links_group)
        self.myspace_album_link_button.setObjectName(u"myspace_album_link_button")
        self.myspace_album_link_button.setMinimumSize(QSize(34, 34))
        self.myspace_album_link_button.setMaximumSize(QSize(34, 34))
        self.myspace_album_link_button.setIcon(icon35)
        self.myspace_album_link_button.setIconSize(QSize(32, 32))
        self.myspace_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.myspace_album_link_button)

        self.twitter_album_link_button = QPushButton(self.album_links_group)
        self.twitter_album_link_button.setObjectName(u"twitter_album_link_button")
        self.twitter_album_link_button.setMinimumSize(QSize(34, 34))
        self.twitter_album_link_button.setMaximumSize(QSize(34, 34))
        self.twitter_album_link_button.setIcon(icon36)
        self.twitter_album_link_button.setIconSize(QSize(32, 32))
        self.twitter_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.twitter_album_link_button)

        self.tumblr_album_link_button = QPushButton(self.album_links_group)
        self.tumblr_album_link_button.setObjectName(u"tumblr_album_link_button")
        self.tumblr_album_link_button.setMinimumSize(QSize(34, 34))
        self.tumblr_album_link_button.setMaximumSize(QSize(34, 34))
        self.tumblr_album_link_button.setIcon(icon37)
        self.tumblr_album_link_button.setIconSize(QSize(32, 32))
        self.tumblr_album_link_button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.tumblr_album_link_button)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_5)


        self.verticalLayout_11.addWidget(self.album_links_group)

        self.artist_group = QGroupBox(self.texto_widget)
        self.artist_group.setObjectName(u"artist_group")
        self.verticalLayout_8 = QVBoxLayout(self.artist_group)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_11.addWidget(self.artist_group)

        self.lastfm_bio_group = QGroupBox(self.texto_widget)
        self.lastfm_bio_group.setObjectName(u"lastfm_bio_group")
        self.verticalLayout_7 = QVBoxLayout(self.lastfm_bio_group)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_11.addWidget(self.lastfm_bio_group)

        self.album_group = QGroupBox(self.texto_widget)
        self.album_group.setObjectName(u"album_group")
        self.verticalLayout_6 = QVBoxLayout(self.album_group)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")

        self.verticalLayout_11.addWidget(self.album_group)

        self.info_scroll.setWidget(self.texto_widget)

        self.verticalLayout_5.addWidget(self.info_scroll)

        self.info_panel_stacked.addWidget(self.info_page)
        self.feeds_page = QWidget()
        self.feeds_page.setObjectName(u"feeds_page")
        self.verticalLayout_10 = QVBoxLayout(self.feeds_page)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.widget_2 = QWidget(self.feeds_page)
        self.widget_2.setObjectName(u"widget_2")
        self.verticalLayout_23 = QVBoxLayout(self.widget_2)
        self.verticalLayout_23.setObjectName(u"verticalLayout_23")
        self.verticalLayout_23.setContentsMargins(0, 0, 0, 0)
        self.stackedWidget_feeds = QStackedWidget(self.widget_2)
        self.stackedWidget_feeds.setObjectName(u"stackedWidget_feeds")
        self.feeds_artists = QWidget()
        self.feeds_artists.setObjectName(u"feeds_artists")
        self.verticalLayout_12 = QVBoxLayout(self.feeds_artists)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.verticalLayout_12.setContentsMargins(0, 0, 0, 0)
        self.scrollArea_artists = QScrollArea(self.feeds_artists)
        self.scrollArea_artists.setObjectName(u"scrollArea_artists")
        self.scrollArea_artists.setWidgetResizable(True)
        self.scrollAreaWidgetContent_artists = QWidget()
        self.scrollAreaWidgetContent_artists.setObjectName(u"scrollAreaWidgetContent_artists")
        self.scrollAreaWidgetContent_artists.setGeometry(QRect(0, 0, 1055, 459))
        self.verticalLayout_15 = QVBoxLayout(self.scrollAreaWidgetContent_artists)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.verticalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.groupBox_artists = QGroupBox(self.scrollAreaWidgetContent_artists)
        self.groupBox_artists.setObjectName(u"groupBox_artists")
        self.verticalLayout_20 = QVBoxLayout(self.groupBox_artists)
        self.verticalLayout_20.setObjectName(u"verticalLayout_20")
        self.verticalLayout_20.setContentsMargins(0, 0, 0, 0)
        self.artistas_label = QLabel(self.groupBox_artists)
        self.artistas_label.setObjectName(u"artistas_label")

        self.verticalLayout_20.addWidget(self.artistas_label)

        self.artistas_textEdit = QTextEdit(self.groupBox_artists)
        self.artistas_textEdit.setObjectName(u"artistas_textEdit")
        self.artistas_textEdit.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse|Qt.TextInteractionFlag.TextEditable|Qt.TextInteractionFlag.TextEditorInteraction|Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)

        self.verticalLayout_20.addWidget(self.artistas_textEdit)


        self.verticalLayout_15.addWidget(self.groupBox_artists)

        self.scrollArea_artists.setWidget(self.scrollAreaWidgetContent_artists)

        self.verticalLayout_12.addWidget(self.scrollArea_artists)

        self.stackedWidget_feeds.addWidget(self.feeds_artists)
        self.feeds_albums = QWidget()
        self.feeds_albums.setObjectName(u"feeds_albums")
        self.verticalLayout_16 = QVBoxLayout(self.feeds_albums)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.verticalLayout_16.setContentsMargins(0, 0, 0, 0)
        self.scrollArea_albums = QScrollArea(self.feeds_albums)
        self.scrollArea_albums.setObjectName(u"scrollArea_albums")
        self.scrollArea_albums.setWidgetResizable(True)
        self.scrollAreaWidgetContents_albums = QWidget()
        self.scrollAreaWidgetContents_albums.setObjectName(u"scrollAreaWidgetContents_albums")
        self.scrollAreaWidgetContents_albums.setGeometry(QRect(0, 0, 1055, 459))
        self.verticalLayout_17 = QVBoxLayout(self.scrollAreaWidgetContents_albums)
        self.verticalLayout_17.setSpacing(6)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.verticalLayout_17.setContentsMargins(0, 0, 0, 0)
        self.groupBox_albums = QGroupBox(self.scrollAreaWidgetContents_albums)
        self.groupBox_albums.setObjectName(u"groupBox_albums")
        self.verticalLayout_21 = QVBoxLayout(self.groupBox_albums)
        self.verticalLayout_21.setObjectName(u"verticalLayout_21")
        self.verticalLayout_21.setContentsMargins(0, 0, 0, 0)
        self.albums_label = QLabel(self.groupBox_albums)
        self.albums_label.setObjectName(u"albums_label")

        self.verticalLayout_21.addWidget(self.albums_label)

        self.albums_textEdit = QTextEdit(self.groupBox_albums)
        self.albums_textEdit.setObjectName(u"albums_textEdit")
        self.albums_textEdit.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse|Qt.TextInteractionFlag.TextEditable|Qt.TextInteractionFlag.TextEditorInteraction|Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)

        self.verticalLayout_21.addWidget(self.albums_textEdit)


        self.verticalLayout_17.addWidget(self.groupBox_albums)

        self.scrollArea_albums.setWidget(self.scrollAreaWidgetContents_albums)

        self.verticalLayout_16.addWidget(self.scrollArea_albums)

        self.stackedWidget_feeds.addWidget(self.feeds_albums)
        self.feeds_menciones = QWidget()
        self.feeds_menciones.setObjectName(u"feeds_menciones")
        self.verticalLayout_19 = QVBoxLayout(self.feeds_menciones)
        self.verticalLayout_19.setObjectName(u"verticalLayout_19")
        self.verticalLayout_19.setContentsMargins(0, 0, 0, 0)
        self.scrollArea_menciones = QScrollArea(self.feeds_menciones)
        self.scrollArea_menciones.setObjectName(u"scrollArea_menciones")
        self.scrollArea_menciones.setWidgetResizable(True)
        self.scrollAreaWidgetContents_menciones = QWidget()
        self.scrollAreaWidgetContents_menciones.setObjectName(u"scrollAreaWidgetContents_menciones")
        self.scrollAreaWidgetContents_menciones.setGeometry(QRect(0, 0, 1055, 459))
        self.verticalLayout_18 = QVBoxLayout(self.scrollAreaWidgetContents_menciones)
        self.verticalLayout_18.setObjectName(u"verticalLayout_18")
        self.verticalLayout_18.setContentsMargins(0, 0, 0, 0)
        self.groupBox_menciones = QGroupBox(self.scrollAreaWidgetContents_menciones)
        self.groupBox_menciones.setObjectName(u"groupBox_menciones")
        self.verticalLayout_22 = QVBoxLayout(self.groupBox_menciones)
        self.verticalLayout_22.setObjectName(u"verticalLayout_22")
        self.verticalLayout_22.setContentsMargins(0, 0, 0, 0)
        self.menciones_label = QLabel(self.groupBox_menciones)
        self.menciones_label.setObjectName(u"menciones_label")

        self.verticalLayout_22.addWidget(self.menciones_label)

        self.menciones_textEdit = QTextEdit(self.groupBox_menciones)
        self.menciones_textEdit.setObjectName(u"menciones_textEdit")
        self.menciones_textEdit.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse|Qt.TextInteractionFlag.TextEditable|Qt.TextInteractionFlag.TextEditorInteraction|Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)

        self.verticalLayout_22.addWidget(self.menciones_textEdit)


        self.verticalLayout_18.addWidget(self.groupBox_menciones)

        self.scrollArea_menciones.setWidget(self.scrollAreaWidgetContents_menciones)

        self.verticalLayout_19.addWidget(self.scrollArea_menciones)

        self.stackedWidget_feeds.addWidget(self.feeds_menciones)

        self.verticalLayout_23.addWidget(self.stackedWidget_feeds)

        self.widget_3 = QWidget(self.widget_2)
        self.widget_3.setObjectName(u"widget_3")
        self.horizontalLayout_4 = QHBoxLayout(self.widget_3)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.artists_pushButton = QPushButton(self.widget_3)
        self.artists_pushButton.setObjectName(u"artists_pushButton")

        self.horizontalLayout_4.addWidget(self.artists_pushButton)

        self.albums_pushButton = QPushButton(self.widget_3)
        self.albums_pushButton.setObjectName(u"albums_pushButton")

        self.horizontalLayout_4.addWidget(self.albums_pushButton)

        self.menciones_pushButton = QPushButton(self.widget_3)
        self.menciones_pushButton.setObjectName(u"menciones_pushButton")

        self.horizontalLayout_4.addWidget(self.menciones_pushButton)


        self.verticalLayout_23.addWidget(self.widget_3)


        self.verticalLayout_10.addWidget(self.widget_2)

        self.info_panel_stacked.addWidget(self.feeds_page)
        self.mas_info_page = QWidget()
        self.mas_info_page.setObjectName(u"mas_info_page")
        self.verticalLayout_13 = QVBoxLayout(self.mas_info_page)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.verticalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.groupBox = QGroupBox(self.mas_info_page)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_14 = QVBoxLayout(self.groupBox)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.groupBox_metadata = QGroupBox(self.groupBox)
        self.groupBox_metadata.setObjectName(u"groupBox_metadata")

        self.verticalLayout_14.addWidget(self.groupBox_metadata)

        self.groupBox_inforelease = QGroupBox(self.groupBox)
        self.groupBox_inforelease.setObjectName(u"groupBox_inforelease")

        self.verticalLayout_14.addWidget(self.groupBox_inforelease)

        self.groupBox_infosello = QGroupBox(self.groupBox)
        self.groupBox_infosello.setObjectName(u"groupBox_infosello")

        self.verticalLayout_14.addWidget(self.groupBox_infosello)


        self.verticalLayout_13.addWidget(self.groupBox)

        self.info_panel_stacked.addWidget(self.mas_info_page)

        self.verticalLayout_3.addWidget(self.info_panel_stacked)


        self.details_layout.addWidget(self.info_container)

        self.main_splitter.addWidget(self.details_widget)

        self.verticalLayout.addWidget(self.main_splitter)


        self.retranslateUi(MusicBrowser)

        self.info_panel_stacked.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(MusicBrowser)
    # setupUi

    def retranslateUi(self, MusicBrowser):
        self.search_box.setPlaceholderText(QCoreApplication.translate("MusicBrowser", u"a:artista - b:\u00e1lbum - g:g\u00e9nero - l:sello - t:t\u00edtulo - aa:album-artist - br:bitrate - d:fecha - w:semanas - m:meses - y:a\u00f1os - am:mes/a\u00f1o - ay:a\u00f1o", None))
        self.advanced_settings_check.setText(QCoreApplication.translate("MusicBrowser", u"M\u00e1s", None))
        self.custom_button1.setText(QCoreApplication.translate("MusicBrowser", u"Reproduciendo", None))
        self.custom_button2.setText(QCoreApplication.translate("MusicBrowser", u"Script 2", None))
        self.custom_button3.setText(QCoreApplication.translate("MusicBrowser", u"Script 3", None))
        ___qtreewidgetitem = self.results_tree_widget.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("MusicBrowser", u"G\u00e9nero", None));
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("MusicBrowser", u"A\u00f1o", None));
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("MusicBrowser", u"Artista / \u00c1lbum / Canci\u00f3n", None));
        self.cover_label.setText(QCoreApplication.translate("MusicBrowser", u"No imagen", None))
        self.artist_image_label.setText(QCoreApplication.translate("MusicBrowser", u"No imagen de artista", None))
#if QT_CONFIG(tooltip)
        self.prev_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Previous", None))
#endif // QT_CONFIG(tooltip)
        self.prev_button.setText("")
#if QT_CONFIG(shortcut)
        self.prev_button.setShortcut(QCoreApplication.translate("MusicBrowser", u"Alt+Shift+R", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.folder_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Abrir Carpeta", None))
#endif // QT_CONFIG(tooltip)
        self.folder_button.setText("")
#if QT_CONFIG(tooltip)
        self.next_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Next", None))
#endif // QT_CONFIG(tooltip)
        self.next_button.setText("")
#if QT_CONFIG(shortcut)
        self.next_button.setShortcut(QCoreApplication.translate("MusicBrowser", u"Alt+Shift+R", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.playing_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Mostrar m\u00fasica en reproducci\u00f3n", None))
#endif // QT_CONFIG(tooltip)
        self.playing_button.setText("")
#if QT_CONFIG(tooltip)
        self.conciertos_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Buscar conciertos", None))
#endif // QT_CONFIG(tooltip)
        self.conciertos_button.setText("")
        self.scrobble_button.setText("")
#if QT_CONFIG(tooltip)
        self.muspy_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Buscar discos nuevos", None))
#endif // QT_CONFIG(tooltip)
        self.muspy_button.setText("")
#if QT_CONFIG(tooltip)
        self.url_playlists_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Enviar a Url_Playlists", None))
#endif // QT_CONFIG(tooltip)
        self.url_playlists_button.setText("")
#if QT_CONFIG(tooltip)
        self.jaangle_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Envar a jaangle", None))
#endif // QT_CONFIG(tooltip)
        self.jaangle_button.setText("")
#if QT_CONFIG(tooltip)
        self.db_editor_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Editar elemento en base de datos", None))
#endif // QT_CONFIG(tooltip)
        self.db_editor_button.setText("")
#if QT_CONFIG(tooltip)
        self.spotify_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Enviar enlaces de spotify a Url_Playlists", None))
#endif // QT_CONFIG(tooltip)
        self.spotify_button.setText("")
#if QT_CONFIG(tooltip)
        self.stop_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Stop", None))
#endif // QT_CONFIG(tooltip)
        self.stop_button.setText("")
#if QT_CONFIG(tooltip)
        self.add_to_queue_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"A\u00f1adir a la cola", None))
#endif // QT_CONFIG(tooltip)
        self.add_to_queue_button.setText("")
#if QT_CONFIG(tooltip)
        self.play_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Play", None))
#endif // QT_CONFIG(tooltip)
        self.play_button.setText("")
#if QT_CONFIG(shortcut)
        self.play_button.setShortcut(QCoreApplication.translate("MusicBrowser", u"Alt+Shift+R", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.feeds_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Mostrar feeds", None))
#endif // QT_CONFIG(tooltip)
        self.feeds_button.setText("")
#if QT_CONFIG(tooltip)
        self.stats_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"Mostrar estad\u00edsticas para el elemento", None))
#endif // QT_CONFIG(tooltip)
        self.stats_button.setText("")
        self.artist_links_group.setTitle(QCoreApplication.translate("MusicBrowser", u"Enlaces Artista", None))
        self.bc_link_button.setText("")
        self.soudcloud_link_button.setText("")
        self.yt_link_button.setText("")
        self.spot_link_button.setText("")
        self.vimeo_link_button.setText("")
        self.boomkat_link_button.setText("")
        self.juno_link_button.setText("")
        self.allmusic_link_button.setText("")
        self.discogs_link_button.setText("")
        self.imdb_link_button.setText("")
        self.lastfm_link_button.setText("")
        self.mb_link_button.setText("")
        self.prog_link_button.setText("")
        self.rym_link_button.setText("")
        self.ra_link_button.setText("")
        self.setlist_link_button.setText("")
        self.wiki_link_button.setText("")
        self.whosampled_link_button.setText("")
        self.bluesky_link_button.setText("")
        self.fb_link_button.setText("")
        self.ig_link_button.setText("")
        self.mastodon_link_button.setText("")
        self.myspace_link_button.setText("")
        self.twitter_link_button.setText("")
        self.tumblr_link_button.setText("")
        self.album_links_group.setTitle(QCoreApplication.translate("MusicBrowser", u"Enlaces \u00c1lbum", None))
        self.bc_album_link_button.setText("")
        self.soudcloud_album_link_button.setText("")
        self.yt_album_link_button.setText("")
        self.spot_album_link_button.setText("")
        self.vimeo_album_link_button.setText("")
        self.boomkat_album_link_button.setText("")
        self.juno_album_link_button.setText("")
        self.allmusic_album_link_button.setText("")
        self.discogs_album_link_button.setText("")
        self.imdb_album_link_button.setText("")
        self.lastfm_album_link_button.setText("")
        self.mb_album_link_button.setText("")
        self.prog_album_link_button.setText("")
        self.rym_album_link_button.setText("")
        self.ra_album_link_button.setText("")
        self.setlist_album_link_button.setText("")
        self.wiki_album_link_button.setText("")
        self.whosampled_album_link_button.setText("")
        self.bluesky_album_link_button.setText("")
        self.fb_album_link_button.setText("")
        self.ig_album_link_button.setText("")
        self.mastodon_album_link_button.setText("")
        self.myspace_album_link_button.setText("")
        self.twitter_album_link_button.setText("")
        self.tumblr_album_link_button.setText("")
        self.artist_group.setTitle(QCoreApplication.translate("MusicBrowser", u"Wikipedia del artista", None))
        self.lastfm_bio_group.setTitle(QCoreApplication.translate("MusicBrowser", u"Lastfm Bio", None))
        self.album_group.setTitle(QCoreApplication.translate("MusicBrowser", u"Wikipedia del \u00e1lbum", None))
        self.groupBox_artists.setTitle("")
        self.artistas_label.setText(QCoreApplication.translate("MusicBrowser", u"Artistas", None))
        self.groupBox_albums.setTitle(QCoreApplication.translate("MusicBrowser", u"GroupBox", None))
        self.albums_label.setText(QCoreApplication.translate("MusicBrowser", u"\u00c1lbumes", None))
        self.groupBox_menciones.setTitle(QCoreApplication.translate("MusicBrowser", u"GroupBox", None))
        self.menciones_label.setText(QCoreApplication.translate("MusicBrowser", u"Menciones en otros posts", None))
        self.artists_pushButton.setText(QCoreApplication.translate("MusicBrowser", u"artistas", None))
        self.albums_pushButton.setText(QCoreApplication.translate("MusicBrowser", u"\u00e1lbums", None))
        self.menciones_pushButton.setText(QCoreApplication.translate("MusicBrowser", u"menciones", None))
        self.groupBox.setTitle("")
        self.groupBox_metadata.setTitle(QCoreApplication.translate("MusicBrowser", u"Metadata", None))
        self.groupBox_inforelease.setTitle(QCoreApplication.translate("MusicBrowser", u"Info release", None))
        self.groupBox_infosello.setTitle(QCoreApplication.translate("MusicBrowser", u"Info sello", None))
        pass
    # retranslateUi

