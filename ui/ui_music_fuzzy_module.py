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
    QHBoxLayout, QLabel, QLayout, QLineEdit,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QSplitter, QVBoxLayout, QWidget)
import rc_images

class Ui_MusicBrowser(object):
    def setupUi(self, MusicBrowser):
        if not MusicBrowser.objectName():
            MusicBrowser.setObjectName(u"MusicBrowser")
        MusicBrowser.resize(1200, 800)
        MusicBrowser.setStyleSheet(u"")
        self.verticalLayout = QVBoxLayout(MusicBrowser)
        self.verticalLayout.setSpacing(5)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.top_container = QFrame(MusicBrowser)
        self.top_container.setObjectName(u"top_container")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.top_container.sizePolicy().hasHeightForWidth())
        self.top_container.setSizePolicy(sizePolicy)
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
        sizePolicy.setHeightForWidth(self.search_frame.sizePolicy().hasHeightForWidth())
        self.search_frame.setSizePolicy(sizePolicy)
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
        sizePolicy.setHeightForWidth(self.images_container.sizePolicy().hasHeightForWidth())
        self.images_container.setSizePolicy(sizePolicy)
        self.images_container.setMinimumSize(QSize(0, 100))
        self.images_container.setFrameShape(QFrame.Shape.NoFrame)
        self.images_container.setFrameShadow(QFrame.Shadow.Plain)
        self.images_layout = QHBoxLayout(self.images_container)
        self.images_layout.setSpacing(10)
        self.images_layout.setObjectName(u"images_layout")
        self.images_layout.setContentsMargins(10, 5, 10, 5)
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.images_layout.addItem(self.horizontalSpacer_3)

        self.cover_label = QLabel(self.images_container)
        self.cover_label.setObjectName(u"cover_label")
        self.cover_label.setMinimumSize(QSize(200, 200))
        self.cover_label.setMaximumSize(QSize(200, 200))
        self.cover_label.setStyleSheet(u"border: 1px solid rgba(65, 72, 104, 0.5); border-radius: 4px;")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.images_layout.addWidget(self.cover_label)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.images_layout.addItem(self.horizontalSpacer_2)

        self.artist_image_label = QLabel(self.images_container)
        self.artist_image_label.setObjectName(u"artist_image_label")
        self.artist_image_label.setMinimumSize(QSize(200, 200))
        self.artist_image_label.setMaximumSize(QSize(200, 200))
        self.artist_image_label.setStyleSheet(u"border: 1px solid rgba(65, 72, 104, 0.5); border-radius: 4px;")
        self.artist_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.images_layout.addWidget(self.artist_image_label)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.images_layout.addItem(self.horizontalSpacer)

        self.metadata_scroll = QScrollArea(self.images_container)
        self.metadata_scroll.setObjectName(u"metadata_scroll")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.metadata_scroll.sizePolicy().hasHeightForWidth())
        self.metadata_scroll.setSizePolicy(sizePolicy1)
        self.metadata_scroll.setMinimumSize(QSize(50, 0))
        self.metadata_scroll.setMaximumSize(QSize(16777215, 200))
        self.metadata_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.metadata_scroll.setLineWidth(0)
        self.metadata_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.metadata_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.metadata_scroll.setWidgetResizable(True)
        self.metadata_scroll.setAlignment(Qt.AlignmentFlag.AlignJustify|Qt.AlignmentFlag.AlignVCenter)

        self.images_layout.addWidget(self.metadata_scroll)

        self.buttons_container = QFrame(self.images_container)
        self.buttons_container.setObjectName(u"buttons_container")
        self.buttons_container.setMinimumSize(QSize(120, 0))
        self.buttons_container.setMaximumSize(QSize(200, 16777215))
        self.buttons_container.setStyleSheet(u"QPushButton {{\n"
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
        self.buttons_container.setFrameShape(QFrame.Shape.NoFrame)
        self.gridLayout = QGridLayout(self.buttons_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.play_button = QPushButton(self.buttons_container)
        self.play_button.setObjectName(u"play_button")
        self.play_button.setMinimumSize(QSize(50, 50))
        self.play_button.setMaximumSize(QSize(50, 50))
        self.play_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.play_button.setStyleSheet(u"QPushButton {{\n"
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
        icon = QIcon()
        icon.addFile(u":/services/play", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.play_button.setIcon(icon)
        self.play_button.setIconSize(QSize(40, 40))

        self.gridLayout.addWidget(self.play_button, 0, 0, 1, 1)

        self.spotify_button = QPushButton(self.buttons_container)
        self.spotify_button.setObjectName(u"spotify_button")
        self.spotify_button.setMinimumSize(QSize(0, 0))
        self.spotify_button.setMaximumSize(QSize(50, 50))
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
        icon1 = QIcon()
        icon1.addFile(u":/services/spotify", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.spotify_button.setIcon(icon1)
        self.spotify_button.setIconSize(QSize(40, 40))
        self.spotify_button.setFlat(True)

        self.gridLayout.addWidget(self.spotify_button, 3, 0, 1, 1)

        self.jaangle_button = QPushButton(self.buttons_container)
        self.jaangle_button.setObjectName(u"jaangle_button")
        self.jaangle_button.setMinimumSize(QSize(50, 50))
        self.jaangle_button.setMaximumSize(QSize(50, 50))
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
        icon2 = QIcon()
        icon2.addFile(u":/services/game", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.jaangle_button.setIcon(icon2)
        self.jaangle_button.setIconSize(QSize(40, 40))

        self.gridLayout.addWidget(self.jaangle_button, 5, 0, 1, 1)

        self.folder_button = QPushButton(self.buttons_container)
        self.folder_button.setObjectName(u"folder_button")
        self.folder_button.setMinimumSize(QSize(50, 50))
        self.folder_button.setMaximumSize(QSize(50, 50))
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
        icon3 = QIcon()
        icon3.addFile(u":/services/folder", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.folder_button.setIcon(icon3)
        self.folder_button.setIconSize(QSize(40, 40))

        self.gridLayout.addWidget(self.folder_button, 0, 1, 1, 1)

        self.scrobble_button = QPushButton(self.buttons_container)
        self.scrobble_button.setObjectName(u"scrobble_button")
        self.scrobble_button.setMinimumSize(QSize(50, 50))
        self.scrobble_button.setMaximumSize(QSize(50, 50))
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
        icon4 = QIcon()
        icon4.addFile(u":/services/lastfm", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.scrobble_button.setIcon(icon4)
        self.scrobble_button.setIconSize(QSize(40, 40))

        self.gridLayout.addWidget(self.scrobble_button, 3, 1, 1, 1)

        self.extra_button = QPushButton(self.buttons_container)
        self.extra_button.setObjectName(u"extra_button")
        self.extra_button.setMinimumSize(QSize(50, 50))
        self.extra_button.setMaximumSize(QSize(50, 50))
        self.extra_button.setStyleSheet(u"QPushButton {{\n"
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
        icon5.addFile(u":/services/chicken2", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.extra_button.setIcon(icon5)
        self.extra_button.setIconSize(QSize(40, 40))

        self.gridLayout.addWidget(self.extra_button, 5, 1, 1, 1)


        self.images_layout.addWidget(self.buttons_container)


        self.details_layout.addWidget(self.images_container)

        self.info_container = QFrame(self.details_widget)
        self.info_container.setObjectName(u"info_container")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.info_container.sizePolicy().hasHeightForWidth())
        self.info_container.setSizePolicy(sizePolicy2)
        self.info_container.setFrameShape(QFrame.Shape.NoFrame)
        self.info_container.setFrameShadow(QFrame.Shadow.Plain)
        self.info_container_layout = QVBoxLayout(self.info_container)
        self.info_container_layout.setObjectName(u"info_container_layout")
        self.info_container_layout.setContentsMargins(5, 5, 5, 5)
        self.info_scroll = QScrollArea(self.info_container)
        self.info_scroll.setObjectName(u"info_scroll")
        sizePolicy2.setHeightForWidth(self.info_scroll.sizePolicy().hasHeightForWidth())
        self.info_scroll.setSizePolicy(sizePolicy2)
        self.info_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.info_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.info_scroll.setWidgetResizable(True)

        self.info_container_layout.addWidget(self.info_scroll)


        self.details_layout.addWidget(self.info_container)

        self.main_splitter.addWidget(self.details_widget)

        self.verticalLayout.addWidget(self.main_splitter)


        self.retranslateUi(MusicBrowser)

        QMetaObject.connectSlotsByName(MusicBrowser)
    # setupUi

    def retranslateUi(self, MusicBrowser):
        self.search_box.setPlaceholderText(QCoreApplication.translate("MusicBrowser", u"a:artista - b:\u00e1lbum - g:g\u00e9nero - l:sello - t:t\u00edtulo - aa:album-artist - br:bitrate - d:fecha - w:semanas - m:meses - y:a\u00f1os - am:mes/a\u00f1o - ay:a\u00f1o", None))
        self.advanced_settings_check.setText(QCoreApplication.translate("MusicBrowser", u"M\u00e1s", None))
        self.custom_button1.setText(QCoreApplication.translate("MusicBrowser", u"Reproduciendo", None))
        self.custom_button2.setText(QCoreApplication.translate("MusicBrowser", u"Script 2", None))
        self.custom_button3.setText(QCoreApplication.translate("MusicBrowser", u"Script 3", None))
        self.cover_label.setText(QCoreApplication.translate("MusicBrowser", u"No imagen", None))
        self.artist_image_label.setText(QCoreApplication.translate("MusicBrowser", u"No imagen de artista", None))
        self.play_button.setText("")
#if QT_CONFIG(shortcut)
        self.play_button.setShortcut(QCoreApplication.translate("MusicBrowser", u"Alt+Shift+R", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.spotify_button.setToolTip(QCoreApplication.translate("MusicBrowser", u"<html><head/><body><p>a\u00f1adir a playlist spotify</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.spotify_button.setText("")
        self.jaangle_button.setText("")
        self.folder_button.setText("")
        self.scrobble_button.setText("")
        self.extra_button.setText("")
        pass
    # retranslateUi

