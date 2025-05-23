# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'url_player.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QHeaderView, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QStackedWidget, QTabWidget, QTextEdit, QToolButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
import rc_images

class Ui_UrlPlaylist(object):
    def setupUi(self, UrlPlaylist):
        if not UrlPlaylist.objectName():
            UrlPlaylist.setObjectName(u"UrlPlaylist")
        UrlPlaylist.resize(1200, 800)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(UrlPlaylist.sizePolicy().hasHeightForWidth())
        UrlPlaylist.setSizePolicy(sizePolicy)
        UrlPlaylist.setStyleSheet(u"/* Base Styles */\n"
"QWidget {\n"
"    background-color: #1a1b26;\n"
"    color: #a9b1d6;\n"
"    font-family: \"Segoe UI\", Arial, sans-serif;\n"
"    font-size: 10pt;\n"
"}\n"
"\n"
"/* Remove borders from all frames */\n"
"QFrame, QGroupBox {\n"
"    border: none;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"/* Text input fields */\n"
"QLineEdit, QTextEdit {\n"
"    border: 1px solid #414868;\n"
"    border-radius: 4px;\n"
"    padding: 8px;\n"
"    background-color: #24283b;\n"
"}\n"
"/* Buttons */\n"
"QPushButton {{\n"
"	background-color: {theme['bg']};\n"
"    color: {theme['fg']};\n"
"    border: none;\n"
"    border-radius: 4px;\n"
"    padding: 8px 16px;\n"
"    font-weight: bold;\n"
"}}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #535d8c;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #7aa2f7;\n"
"    color: #1a1b26;\n"
"}\n"
"\n"
"/* Lists and Trees */\n"
"QTreeWidget, QListWidget {\n"
"    background-color: #24283b;\n"
"    border: none;\n"
"    border-radius: 4px;\n"
"}\n"
""
                        "\n"
"QTreeWidget::item, QListWidget::item {\n"
"    padding: 4px;\n"
"}\n"
"\n"
"QTreeWidget::item:selected, QListWidget::item:selected {\n"
"    background-color: #364A82;\n"
"}\n"
"\n"
"/* Tab Widget */\n"
"QTabWidget::pane {\n"
"    border: none;\n"
"    background-color: #24283b;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QTabBar::tab {\n"
"    background-color: #1a1b26;\n"
"    color: #a9b1d6;\n"
"    border: none;\n"
"    padding: 8px 16px;\n"
"    border-top-left-radius: 4px;\n"
"    border-top-right-radius: 4px;\n"
"}\n"
"\n"
"QTabBar::tab:selected {\n"
"    background-color: #24283b;\n"
"    color: #7aa2f7;\n"
"}\n"
"\n"
"QTabBar::tab:hover:!selected {\n"
"    background-color: #364A82;\n"
"}\n"
"\n"
"/* Scroll Areas */\n"
"QScrollArea {\n"
"    border: none;\n"
"}\n"
"\n"
"/* Progress Bar */\n"
"QProgressBar {\n"
"    border: none;\n"
"    background-color: #24283b;\n"
"    border-radius: 4px;\n"
"    text-align: center;\n"
"}\n"
"\n"
"QProgressBar::chunk {\n"
"    background-color: #7aa2f7;\n"
"    "
                        "border-radius: 4px;\n"
"}")
        self.verticalLayout = QVBoxLayout(UrlPlaylist)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.busqueda = QFrame(UrlPlaylist)
        self.busqueda.setObjectName(u"busqueda")
        self.busqueda.setMinimumSize(QSize(0, 60))
        self.busqueda.setMaximumSize(QSize(16777215, 50))
        self.busqueda.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.busqueda.setFrameShape(QFrame.Shape.NoFrame)
        self.busqueda.setFrameShadow(QFrame.Shadow.Raised)
        self.busqueda.setLineWidth(0)
        self.horizontalLayout_4 = QHBoxLayout(self.busqueda)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.lineEdit = QLineEdit(self.busqueda)
        self.lineEdit.setObjectName(u"lineEdit")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.lineEdit.sizePolicy().hasHeightForWidth())
        self.lineEdit.setSizePolicy(sizePolicy1)

        self.horizontalLayout_4.addWidget(self.lineEdit)

        self.searchButton = QPushButton(self.busqueda)
        self.searchButton.setObjectName(u"searchButton")
        icon = QIcon()
        icon.addFile(u":/services/search_ol", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.searchButton.setIcon(icon)
        self.searchButton.setIconSize(QSize(30, 30))

        self.horizontalLayout_4.addWidget(self.searchButton)

        self.servicios = QComboBox(self.busqueda)
        self.servicios.addItem("")
        self.servicios.addItem("")
        self.servicios.addItem("")
        self.servicios.addItem("")
        self.servicios.setObjectName(u"servicios")
        self.servicios.setMinimumSize(QSize(130, 30))
        self.servicios.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.servicios.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.servicios.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.servicios)

        self.ajustes_avanzados = QToolButton(self.busqueda)
        self.ajustes_avanzados.setObjectName(u"ajustes_avanzados")
        self.ajustes_avanzados.setMinimumSize(QSize(0, 30))

        self.horizontalLayout_4.addWidget(self.ajustes_avanzados)


        self.verticalLayout.addWidget(self.busqueda)

        self.cajon_principal = QFrame(UrlPlaylist)
        self.cajon_principal.setObjectName(u"cajon_principal")
        self.cajon_principal.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.cajon_principal.setFrameShape(QFrame.Shape.NoFrame)
        self.cajon_principal.setFrameShadow(QFrame.Shadow.Raised)
        self.cajon_principal.setLineWidth(0)
        self.horizontalLayout = QHBoxLayout(self.cajon_principal)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.tree_container = QFrame(self.cajon_principal)
        self.tree_container.setObjectName(u"tree_container")
        self.tree_container.setStyleSheet(u"")
        self.tree_container.setLocale(QLocale(QLocale.Spanish, QLocale.Spain))
        self.tree_container.setFrameShape(QFrame.Shape.StyledPanel)
        self.tree_container.setFrameShadow(QFrame.Shadow.Raised)
        self.tree_container.setLineWidth(1)
        self.verticalLayout_5 = QVBoxLayout(self.tree_container)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, -1, 0, 0)
        self.resultados_container = QFrame(self.tree_container)
        self.resultados_container.setObjectName(u"resultados_container")
        self.resultados_container.setFrameShape(QFrame.Shape.StyledPanel)
        self.resultados_container.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_15 = QVBoxLayout(self.resultados_container)
        self.verticalLayout_15.setSpacing(6)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.verticalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.treeWidget = QTreeWidget(self.resultados_container)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"Titulo");
        self.treeWidget.setHeaderItem(__qtreewidgetitem)
        self.treeWidget.setObjectName(u"treeWidget")
        self.treeWidget.setFrameShape(QFrame.Shape.StyledPanel)
        self.treeWidget.setFrameShadow(QFrame.Shadow.Plain)
        self.treeWidget.setLineWidth(0)
        self.treeWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.treeWidget.setColumnCount(4)
        self.treeWidget.header().setVisible(True)

        self.verticalLayout_15.addWidget(self.treeWidget)

        self.tree_container_frame = QFrame(self.resultados_container)
        self.tree_container_frame.setObjectName(u"tree_container_frame")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.tree_container_frame.sizePolicy().hasHeightForWidth())
        self.tree_container_frame.setSizePolicy(sizePolicy2)
        self.tree_container_frame.setMaximumSize(QSize(16777215, 16777215))
        self.tree_container_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.tree_container_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_6 = QHBoxLayout(self.tree_container_frame)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.playlist_stack = QStackedWidget(self.tree_container_frame)
        self.playlist_stack.setObjectName(u"playlist_stack")
        sizePolicy.setHeightForWidth(self.playlist_stack.sizePolicy().hasHeightForWidth())
        self.playlist_stack.setSizePolicy(sizePolicy)
        self.playlist_stack.setMaximumSize(QSize(16777215, 40))
        self.separate_page_stacked = QWidget()
        self.separate_page_stacked.setObjectName(u"separate_page_stacked")
        sizePolicy.setHeightForWidth(self.separate_page_stacked.sizePolicy().hasHeightForWidth())
        self.separate_page_stacked.setSizePolicy(sizePolicy)
        self.verticalLayout_10 = QVBoxLayout(self.separate_page_stacked)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.separate_page = QWidget(self.separate_page_stacked)
        self.separate_page.setObjectName(u"separate_page")
        self.horizontalLayout_5 = QHBoxLayout(self.separate_page)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 3)
        self.colecciones_mb_menu = QPushButton(self.separate_page)
        self.colecciones_mb_menu.setObjectName(u"colecciones_mb_menu")
        self.colecciones_mb_menu.setMaximumSize(QSize(16777215, 30))
        icon1 = QIcon()
        icon1.addFile(u":/services/mb", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.colecciones_mb_menu.setIcon(icon1)

        self.horizontalLayout_5.addWidget(self.colecciones_mb_menu)

        self.scrobbles_menu = QPushButton(self.separate_page)
        self.scrobbles_menu.setObjectName(u"scrobbles_menu")
        self.scrobbles_menu.setMaximumSize(QSize(16777215, 30))
        icon2 = QIcon()
        icon2.addFile(u":/services/lastfm", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.scrobbles_menu.setIcon(icon2)

        self.horizontalLayout_5.addWidget(self.scrobbles_menu)

        self.playlist_rss_comboBox = QComboBox(self.separate_page)
        icon3 = QIcon()
        icon3.addFile(u":/services/rss", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.playlist_rss_comboBox.addItem(icon3, "")
        self.playlist_rss_comboBox.setObjectName(u"playlist_rss_comboBox")
        self.playlist_rss_comboBox.setMinimumSize(QSize(0, 30))

        self.horizontalLayout_5.addWidget(self.playlist_rss_comboBox)

        self.playlist_spotify_comboBox = QComboBox(self.separate_page)
        icon4 = QIcon()
        icon4.addFile(u":/services/b_plus_cross", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.playlist_spotify_comboBox.addItem(icon4, "")
        icon5 = QIcon()
        icon5.addFile(u":/services/spotify", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.playlist_spotify_comboBox.addItem(icon5, "")
        self.playlist_spotify_comboBox.setObjectName(u"playlist_spotify_comboBox")
        self.playlist_spotify_comboBox.setMinimumSize(QSize(0, 30))

        self.horizontalLayout_5.addWidget(self.playlist_spotify_comboBox)

        self.playlist_local_comboBox = QComboBox(self.separate_page)
        icon6 = QIcon()
        icon6.addFile(u":/services/plslove", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.playlist_local_comboBox.addItem(icon6, "")
        self.playlist_local_comboBox.setObjectName(u"playlist_local_comboBox")
        self.playlist_local_comboBox.setMinimumSize(QSize(0, 30))

        self.horizontalLayout_5.addWidget(self.playlist_local_comboBox)

        self.favoritos_menu_button = QPushButton(self.separate_page)
        self.favoritos_menu_button.setObjectName(u"favoritos_menu_button")
        self.favoritos_menu_button.setMaximumSize(QSize(34, 34))
        icon7 = QIcon()
        icon7.addFile(u":/services/chicken", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.favoritos_menu_button.setIcon(icon7)
        self.favoritos_menu_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_5.addWidget(self.favoritos_menu_button)


        self.verticalLayout_10.addWidget(self.separate_page)

        self.playlist_stack.addWidget(self.separate_page_stacked)
        self.unified_page_stacked = QWidget()
        self.unified_page_stacked.setObjectName(u"unified_page_stacked")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.unified_page_stacked.sizePolicy().hasHeightForWidth())
        self.unified_page_stacked.setSizePolicy(sizePolicy3)
        self.verticalLayout_11 = QVBoxLayout(self.unified_page_stacked)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.unified_page = QWidget(self.unified_page_stacked)
        self.unified_page.setObjectName(u"unified_page")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.unified_page.sizePolicy().hasHeightForWidth())
        self.unified_page.setSizePolicy(sizePolicy4)
        self.horizontalLayout_7 = QHBoxLayout(self.unified_page)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.action_unified_playlist = QPushButton(self.unified_page)
        self.action_unified_playlist.setObjectName(u"action_unified_playlist")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.action_unified_playlist.sizePolicy().hasHeightForWidth())
        self.action_unified_playlist.setSizePolicy(sizePolicy5)
        self.action_unified_playlist.setMaximumSize(QSize(16777215, 30))
        self.action_unified_playlist.setStyleSheet(u"")

        self.horizontalLayout_7.addWidget(self.action_unified_playlist)


        self.verticalLayout_11.addWidget(self.unified_page)

        self.playlist_stack.addWidget(self.unified_page_stacked)
        self.busqueda_page_stacked = QWidget()
        self.busqueda_page_stacked.setObjectName(u"busqueda_page_stacked")
        self.horizontalLayout_12 = QHBoxLayout(self.busqueda_page_stacked)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.horizontalLayout_12.setContentsMargins(0, 0, 0, 0)
        self.busqueda_widget = QWidget(self.busqueda_page_stacked)
        self.busqueda_widget.setObjectName(u"busqueda_widget")
        self.horizontalLayout_13 = QHBoxLayout(self.busqueda_widget)
        self.horizontalLayout_13.setSpacing(0)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.horizontalLayout_13.setContentsMargins(0, 0, 0, 3)
        self.busqueda_textedit = QTextEdit(self.busqueda_widget)
        self.busqueda_textedit.setObjectName(u"busqueda_textedit")
        self.busqueda_textedit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.horizontalLayout_13.addWidget(self.busqueda_textedit)


        self.horizontalLayout_12.addWidget(self.busqueda_widget)

        self.playlist_stack.addWidget(self.busqueda_page_stacked)

        self.horizontalLayout_6.addWidget(self.playlist_stack)


        self.verticalLayout_15.addWidget(self.tree_container_frame)


        self.verticalLayout_5.addWidget(self.resultados_container)


        self.horizontalLayout.addWidget(self.tree_container)

        self.player_container = QFrame(self.cajon_principal)
        self.player_container.setObjectName(u"player_container")
        self.player_container.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.player_container.setFrameShape(QFrame.Shape.NoFrame)
        self.player_container.setFrameShadow(QFrame.Shadow.Raised)
        self.player_container.setLineWidth(0)
        self.verticalLayout_2 = QVBoxLayout(self.player_container)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(2, 0, 0, 0)
        self.botones_player = QFrame(self.player_container)
        self.botones_player.setObjectName(u"botones_player")
        self.botones_player.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.botones_player.setFrameShape(QFrame.Shape.NoFrame)
        self.botones_player.setFrameShadow(QFrame.Shadow.Plain)
        self.botones_player.setLineWidth(0)
        self.botones_player.setMidLineWidth(0)
        self.horizontalLayout_2 = QHBoxLayout(self.botones_player)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.tabWidget = QTabWidget(self.botones_player)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.tabWidget.setMovable(False)
        self.tabWidget.setTabBarAutoHide(False)
        self.playlists = QWidget()
        self.playlists.setObjectName(u"playlists")
        self.playlists.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.playlists.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.verticalLayout_6 = QVBoxLayout(self.playlists)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.playlist_scrollArea = QScrollArea(self.playlists)
        self.playlist_scrollArea.setObjectName(u"playlist_scrollArea")
        self.playlist_scrollArea.setAutoFillBackground(False)
        self.playlist_scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_5 = QWidget()
        self.scrollAreaWidgetContents_5.setObjectName(u"scrollAreaWidgetContents_5")
        self.scrollAreaWidgetContents_5.setGeometry(QRect(0, 0, 489, 643))
        self.verticalLayout_16 = QVBoxLayout(self.scrollAreaWidgetContents_5)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.verticalLayout_16.setContentsMargins(0, 0, 0, 0)
        self.listWidget = QListWidget(self.scrollAreaWidgetContents_5)
        self.listWidget.setObjectName(u"listWidget")
        self.listWidget.setStyleSheet(u"QListWidget {{\n"
"	background-color: {theme['secondary_bg']};\n"
"}}")
        self.listWidget.setFrameShape(QFrame.Shape.NoFrame)
        self.listWidget.setLineWidth(0)
        self.listWidget.setIconSize(QSize(16, 16))
        self.listWidget.setSortingEnabled(False)

        self.verticalLayout_16.addWidget(self.listWidget)

        self.playlist_scrollArea.setWidget(self.scrollAreaWidgetContents_5)

        self.verticalLayout_6.addWidget(self.playlist_scrollArea)

        self.botones_reproductor_frame = QFrame(self.playlists)
        self.botones_reproductor_frame.setObjectName(u"botones_reproductor_frame")
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setPointSize(10)
        self.botones_reproductor_frame.setFont(font)
        self.botones_reproductor_frame.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.botones_reproductor_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.botones_reproductor_frame.setFrameShadow(QFrame.Shadow.Plain)
        self.botones_reproductor_frame.setLineWidth(0)
        self.horizontalLayout_3 = QHBoxLayout(self.botones_reproductor_frame)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_6.addWidget(self.botones_reproductor_frame)

        self.tabWidget.addTab(self.playlists, "")
        self.info_text = QWidget()
        self.info_text.setObjectName(u"info_text")
        self.info_text.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.verticalLayout_7 = QVBoxLayout(self.info_text)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(self.info_text)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setLineWidth(0)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 489, 649))
        self.scrollAreaWidgetContents.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.verticalLayout_8 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.textEdit = QTextEdit(self.scrollAreaWidgetContents)
        self.textEdit.setObjectName(u"textEdit")
        self.textEdit.setFrameShape(QFrame.Shape.StyledPanel)
        self.textEdit.setFrameShadow(QFrame.Shadow.Plain)
        self.textEdit.setLineWidth(0)

        self.verticalLayout_8.addWidget(self.textEdit)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_7.addWidget(self.scrollArea)

        self.tabWidget.addTab(self.info_text, "")
        self.info_wiki = QWidget()
        self.info_wiki.setObjectName(u"info_wiki")
        self.verticalLayout_3 = QVBoxLayout(self.info_wiki)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.info_wiki_scroll = QScrollArea(self.info_wiki)
        self.info_wiki_scroll.setObjectName(u"info_wiki_scroll")
        self.info_wiki_scroll.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 489, 649))
        self.verticalLayout_9 = QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.info_wiki_textedit = QTextEdit(self.scrollAreaWidgetContents_2)
        self.info_wiki_textedit.setObjectName(u"info_wiki_textedit")
        self.info_wiki_textedit.setReadOnly(True)
        self.info_wiki_textedit.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByKeyboard|Qt.TextInteractionFlag.LinksAccessibleByMouse|Qt.TextInteractionFlag.TextBrowserInteraction|Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)

        self.verticalLayout_9.addWidget(self.info_wiki_textedit)

        self.info_wiki_scroll.setWidget(self.scrollAreaWidgetContents_2)

        self.verticalLayout_3.addWidget(self.info_wiki_scroll)

        self.tabWidget.addTab(self.info_wiki, "")

        self.horizontalLayout_2.addWidget(self.tabWidget)


        self.verticalLayout_2.addWidget(self.botones_player)

        self.info_panel = QFrame(self.player_container)
        self.info_panel.setObjectName(u"info_panel")
        self.info_panel.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}\n"
"            QTabWidget::pane {{\n"
"				border: none;\n"
"			}}\n"
"			QWidget {{\n"
"			border: none\n"
"			}}")
        self.info_panel.setFrameShape(QFrame.Shape.NoFrame)
        self.info_panel.setFrameShadow(QFrame.Shadow.Plain)
        self.info_panel.setLineWidth(0)
        self.verticalLayout_4 = QVBoxLayout(self.info_panel)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.widget_2 = QWidget(self.info_panel)
        self.widget_2.setObjectName(u"widget_2")
        self.horizontalLayout_11 = QHBoxLayout(self.widget_2)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget(self.widget_2)
        self.widget.setObjectName(u"widget")
        self.horizontalLayout_8 = QHBoxLayout(self.widget)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.add_button = QPushButton(self.widget)
        self.add_button.setObjectName(u"add_button")
        self.add_button.setMinimumSize(QSize(36, 36))
        self.add_button.setMaximumSize(QSize(34, 34))
        font1 = QFont()
        font1.setFamilies([u"Segoe UI"])
        font1.setPointSize(10)
        font1.setBold(True)
        self.add_button.setFont(font1)
        self.add_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon8 = QIcon()
        icon8.addFile(u":/services/addstar", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.add_button.setIcon(icon8)
        self.add_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_8.addWidget(self.add_button)

        self.del_button = QPushButton(self.widget)
        self.del_button.setObjectName(u"del_button")
        self.del_button.setMinimumSize(QSize(0, 0))
        self.del_button.setMaximumSize(QSize(34, 34))
        self.del_button.setFont(font1)
        self.del_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon9 = QIcon()
        icon9.addFile(u":/services/b_minus_star", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.del_button.setIcon(icon9)
        self.del_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_8.addWidget(self.del_button)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_4)


        self.horizontalLayout_11.addWidget(self.widget)

        self.widget_3 = QWidget(self.widget_2)
        self.widget_3.setObjectName(u"widget_3")
        self.horizontalLayout_9 = QHBoxLayout(self.widget_3)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.rew_button = QPushButton(self.widget_3)
        self.rew_button.setObjectName(u"rew_button")
        self.rew_button.setMinimumSize(QSize(0, 0))
        self.rew_button.setMaximumSize(QSize(34, 34))
        self.rew_button.setFont(font1)
        icon10 = QIcon()
        icon10.addFile(u":/services/b_prev", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.rew_button.setIcon(icon10)
        self.rew_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_9.addWidget(self.rew_button)

        self.play_button = QPushButton(self.widget_3)
        self.play_button.setObjectName(u"play_button")
        self.play_button.setMinimumSize(QSize(0, 0))
        self.play_button.setMaximumSize(QSize(34, 34))
        self.play_button.setFont(font1)
        icon11 = QIcon()
        icon11.addFile(u":/services/b_play", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.play_button.setIcon(icon11)
        self.play_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_9.addWidget(self.play_button)

        self.ff_button = QPushButton(self.widget_3)
        self.ff_button.setObjectName(u"ff_button")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.ff_button.sizePolicy().hasHeightForWidth())
        self.ff_button.setSizePolicy(sizePolicy6)
        self.ff_button.setMinimumSize(QSize(36, 36))
        self.ff_button.setMaximumSize(QSize(34, 34))
        self.ff_button.setFont(font1)
        self.ff_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.ff_button.setStyleSheet(u"QPushButton {{\n"
"	border-radius: 20\n"
"}}")
        icon12 = QIcon()
        icon12.addFile(u":/services/b_ff", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.ff_button.setIcon(icon12)
        self.ff_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_9.addWidget(self.ff_button)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_3)


        self.horizontalLayout_11.addWidget(self.widget_3)

        self.widget_4 = QWidget(self.widget_2)
        self.widget_4.setObjectName(u"widget_4")
        self.horizontalLayout_10 = QHBoxLayout(self.widget_4)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.guardar_playlist_comboBox = QComboBox(self.widget_4)
        self.guardar_playlist_comboBox.addItem(icon6, "")
        self.guardar_playlist_comboBox.addItem(icon5, "")
        icon13 = QIcon()
        icon13.addFile(u":/services/yt", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.guardar_playlist_comboBox.addItem(icon13, "")
        self.guardar_playlist_comboBox.setObjectName(u"guardar_playlist_comboBox")
        self.guardar_playlist_comboBox.setMinimumSize(QSize(0, 30))
        self.guardar_playlist_comboBox.setFont(font)

        self.horizontalLayout_10.addWidget(self.guardar_playlist_comboBox)

        self.mark_as_listened_button = QPushButton(self.widget_4)
        self.mark_as_listened_button.setObjectName(u"mark_as_listened_button")
        self.mark_as_listened_button.setMaximumSize(QSize(34, 34))
        icon14 = QIcon()
        icon14.addFile(u":/services/succes", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.mark_as_listened_button.setIcon(icon14)
        self.mark_as_listened_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_10.addWidget(self.mark_as_listened_button)

        self.GuardarPlaylist_button = QPushButton(self.widget_4)
        self.GuardarPlaylist_button.setObjectName(u"GuardarPlaylist_button")
        self.GuardarPlaylist_button.setMaximumSize(QSize(34, 34))
        self.GuardarPlaylist_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon15 = QIcon()
        icon15.addFile(u":/services/b_save", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.GuardarPlaylist_button.setIcon(icon15)
        self.GuardarPlaylist_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_10.addWidget(self.GuardarPlaylist_button)

        self.VaciarPlaylist_button = QPushButton(self.widget_4)
        self.VaciarPlaylist_button.setObjectName(u"VaciarPlaylist_button")
        self.VaciarPlaylist_button.setMaximumSize(QSize(34, 34))
        self.VaciarPlaylist_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon16 = QIcon()
        icon16.addFile(u":/services/error", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.VaciarPlaylist_button.setIcon(icon16)
        self.VaciarPlaylist_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_10.addWidget(self.VaciarPlaylist_button)


        self.horizontalLayout_11.addWidget(self.widget_4)


        self.verticalLayout_4.addWidget(self.widget_2)


        self.verticalLayout_2.addWidget(self.info_panel)


        self.horizontalLayout.addWidget(self.player_container)


        self.verticalLayout.addWidget(self.cajon_principal)


        self.retranslateUi(UrlPlaylist)

        self.playlist_stack.setCurrentIndex(1)
        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(UrlPlaylist)
    # setupUi

    def retranslateUi(self, UrlPlaylist):
#if QT_CONFIG(tooltip)
        self.searchButton.setToolTip(QCoreApplication.translate("UrlPlaylist", u"Buscar", None))
#endif // QT_CONFIG(tooltip)
        self.searchButton.setText("")
        self.servicios.setItemText(0, QCoreApplication.translate("UrlPlaylist", u"Soundcloud", None))
        self.servicios.setItemText(1, QCoreApplication.translate("UrlPlaylist", u"Youtube", None))
        self.servicios.setItemText(2, QCoreApplication.translate("UrlPlaylist", u"Bandcamp", None))
        self.servicios.setItemText(3, QCoreApplication.translate("UrlPlaylist", u"Spotify", None))

#if QT_CONFIG(tooltip)
        self.servicios.setToolTip(QCoreApplication.translate("UrlPlaylist", u"Servicios en los que buscar", None))
#endif // QT_CONFIG(tooltip)
        self.ajustes_avanzados.setText(QCoreApplication.translate("UrlPlaylist", u"...", None))
        ___qtreewidgetitem = self.treeWidget.headerItem()
        ___qtreewidgetitem.setText(3, QCoreApplication.translate("UrlPlaylist", u"Duraci\u00f3n", None));
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("UrlPlaylist", u"Tipo", None));
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("UrlPlaylist", u"Artista", None));
        self.colecciones_mb_menu.setText(QCoreApplication.translate("UrlPlaylist", u"Colecciones MB", None))
        self.scrobbles_menu.setText(QCoreApplication.translate("UrlPlaylist", u"Scrobbles", None))
        self.playlist_rss_comboBox.setItemText(0, QCoreApplication.translate("UrlPlaylist", u"Fresh Rss", None))

#if QT_CONFIG(tooltip)
        self.playlist_rss_comboBox.setToolTip(QCoreApplication.translate("UrlPlaylist", u"Carga playlist del lector rss", None))
#endif // QT_CONFIG(tooltip)
        self.playlist_spotify_comboBox.setItemText(0, QCoreApplication.translate("UrlPlaylist", u"Nueva Playlist Spotify", None))
        self.playlist_spotify_comboBox.setItemText(1, QCoreApplication.translate("UrlPlaylist", u"Playlist Spotify 1", None))

#if QT_CONFIG(tooltip)
        self.playlist_spotify_comboBox.setToolTip(QCoreApplication.translate("UrlPlaylist", u"Carga playlist spotify", None))
#endif // QT_CONFIG(tooltip)
        self.playlist_local_comboBox.setItemText(0, QCoreApplication.translate("UrlPlaylist", u"Playlist local 1", None))

#if QT_CONFIG(tooltip)
        self.playlist_local_comboBox.setToolTip(QCoreApplication.translate("UrlPlaylist", u"Carga playlist local", None))
#endif // QT_CONFIG(tooltip)
        self.favoritos_menu_button.setText("")
        self.action_unified_playlist.setText(QCoreApplication.translate("UrlPlaylist", u"Listas de reproducci\u00f3n", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.playlists), QCoreApplication.translate("UrlPlaylist", u"Playlist", None))
        self.textEdit.setPlaceholderText(QCoreApplication.translate("UrlPlaylist", u"En esta pesta\u00f1a se mostrar\u00e1 un log sobre la b\u00fasqueda y reproducci\u00f3n de elementos en esta ventana", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.info_text), QCoreApplication.translate("UrlPlaylist", u"Informaci\u00f3n", None))
        self.info_wiki_textedit.setPlaceholderText(QCoreApplication.translate("UrlPlaylist", u"Aqui se mostrar\u00e1 informaci\u00f3n sobre el elemento buscado", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.info_wiki), QCoreApplication.translate("UrlPlaylist", u"Info Wiki", None))
#if QT_CONFIG(tooltip)
        self.add_button.setToolTip(QCoreApplication.translate("UrlPlaylist", u"A\u00f1adir al creador de playlists", None))
#endif // QT_CONFIG(tooltip)
        self.add_button.setText("")
#if QT_CONFIG(tooltip)
        self.del_button.setToolTip(QCoreApplication.translate("UrlPlaylist", u"Eliminar del creador de playlists", None))
#endif // QT_CONFIG(tooltip)
        self.del_button.setText("")
#if QT_CONFIG(tooltip)
        self.rew_button.setToolTip(QCoreApplication.translate("UrlPlaylist", u"Canci\u00f3n anterior", None))
#endif // QT_CONFIG(tooltip)
        self.rew_button.setText("")
#if QT_CONFIG(tooltip)
        self.play_button.setToolTip(QCoreApplication.translate("UrlPlaylist", u"Reproducir/Pausar", None))
#endif // QT_CONFIG(tooltip)
        self.play_button.setText("")
#if QT_CONFIG(tooltip)
        self.ff_button.setToolTip(QCoreApplication.translate("UrlPlaylist", u"Canci\u00f3n pr\u00f3sima", None))
#endif // QT_CONFIG(tooltip)
        self.ff_button.setText("")
        self.guardar_playlist_comboBox.setItemText(0, QCoreApplication.translate("UrlPlaylist", u"Playlist local", None))
        self.guardar_playlist_comboBox.setItemText(1, QCoreApplication.translate("UrlPlaylist", u"Spotify", None))
        self.guardar_playlist_comboBox.setItemText(2, QCoreApplication.translate("UrlPlaylist", u"Youtube", None))

#if QT_CONFIG(tooltip)
        self.guardar_playlist_comboBox.setToolTip(QCoreApplication.translate("UrlPlaylist", u"Selecciona tipo de playlist a guardar", None))
#endif // QT_CONFIG(tooltip)
        self.mark_as_listened_button.setText("")
#if QT_CONFIG(tooltip)
        self.GuardarPlaylist_button.setToolTip(QCoreApplication.translate("UrlPlaylist", u"Guardar lista", None))
#endif // QT_CONFIG(tooltip)
        self.GuardarPlaylist_button.setText("")
#if QT_CONFIG(tooltip)
        self.VaciarPlaylist_button.setToolTip(QCoreApplication.translate("UrlPlaylist", u"Vaciar lista", None))
#endif // QT_CONFIG(tooltip)
        self.VaciarPlaylist_button.setText("")
        pass
    # retranslateUi

