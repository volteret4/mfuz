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
    QTabWidget, QTextEdit, QToolButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget)
import rc_images

class Ui_UrlPlaylist(object):
    def setupUi(self, UrlPlaylist):
        if not UrlPlaylist.objectName():
            UrlPlaylist.setObjectName(u"UrlPlaylist")
        UrlPlaylist.resize(1200, 800)
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
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
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
        self.horizontalLayout_4.setContentsMargins(20, 15, 20, 15)
        self.lineEdit = QLineEdit(self.busqueda)
        self.lineEdit.setObjectName(u"lineEdit")

        self.horizontalLayout_4.addWidget(self.lineEdit)

        self.searchButton = QPushButton(self.busqueda)
        self.searchButton.setObjectName(u"searchButton")
        icon = QIcon()
        icon.addFile(u":/services/blue_tape", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.searchButton.setIcon(icon)
        self.searchButton.setIconSize(QSize(30, 30))

        self.horizontalLayout_4.addWidget(self.searchButton)

        self.horizontalSpacer = QSpacerItem(10, 20, QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer)

        self.servicios = QComboBox(self.busqueda)
        self.servicios.setObjectName(u"servicios")
        self.servicios.setMinimumSize(QSize(130, 30))
        self.servicios.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.servicios.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.servicios.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.servicios)

        self.ajustes_avanzados = QToolButton(self.busqueda)
        self.ajustes_avanzados.setObjectName(u"ajustes_avanzados")

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
        self.tree_container = QFrame(self.cajon_principal)
        self.tree_container.setObjectName(u"tree_container")
        self.tree_container.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.tree_container.setFrameShape(QFrame.Shape.NoFrame)
        self.tree_container.setFrameShadow(QFrame.Shadow.Raised)
        self.tree_container.setLineWidth(0)
        self.verticalLayout_5 = QVBoxLayout(self.tree_container)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(12, -1, 2, -1)
        self.treeWidget = QTreeWidget(self.tree_container)
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

        self.verticalLayout_5.addWidget(self.treeWidget)


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
        self.verticalLayout_2.setContentsMargins(2, 0, 12, 9)
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
        self.info_panel.setFrameShadow(QFrame.Shadow.Raised)
        self.info_panel.setLineWidth(0)
        self.verticalLayout_4 = QVBoxLayout(self.info_panel)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.tabWidget = QTabWidget(self.info_panel)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
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
        self.listWidget = QListWidget(self.playlists)
        self.listWidget.setObjectName(u"listWidget")
        self.listWidget.setFrameShape(QFrame.Shape.NoFrame)
        self.listWidget.setLineWidth(0)

        self.verticalLayout_6.addWidget(self.listWidget)

        self.frame = QFrame(self.playlists)
        self.frame.setObjectName(u"frame")
        self.frame.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.frame.setFrameShape(QFrame.Shape.NoFrame)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.frame.setLineWidth(0)
        self.horizontalLayout_3 = QHBoxLayout(self.frame)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.add_button = QPushButton(self.frame)
        self.add_button.setObjectName(u"add_button")
        self.add_button.setMinimumSize(QSize(36, 36))
        self.add_button.setMaximumSize(QSize(36, 36))
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setPointSize(10)
        font.setBold(True)
        self.add_button.setFont(font)
        icon1 = QIcon()
        icon1.addFile(u":/services/addstar", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.add_button.setIcon(icon1)
        self.add_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_3.addWidget(self.add_button)

        self.del_button = QPushButton(self.frame)
        self.del_button.setObjectName(u"del_button")
        self.del_button.setMinimumSize(QSize(0, 0))
        self.del_button.setMaximumSize(QSize(36, 36))
        self.del_button.setFont(font)
        icon2 = QIcon()
        icon2.addFile(u":/services/b_minus_star", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.del_button.setIcon(icon2)
        self.del_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_3.addWidget(self.del_button)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_2)

        self.rew_button = QPushButton(self.frame)
        self.rew_button.setObjectName(u"rew_button")
        self.rew_button.setMinimumSize(QSize(0, 0))
        self.rew_button.setMaximumSize(QSize(36, 36))
        self.rew_button.setFont(font)
        icon3 = QIcon()
        icon3.addFile(u":/services/b_prev", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.rew_button.setIcon(icon3)
        self.rew_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_3.addWidget(self.rew_button)

        self.play_button = QPushButton(self.frame)
        self.play_button.setObjectName(u"play_button")
        self.play_button.setMinimumSize(QSize(0, 0))
        self.play_button.setMaximumSize(QSize(36, 36))
        self.play_button.setFont(font)
        icon4 = QIcon()
        icon4.addFile(u":/services/b_play", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.play_button.setIcon(icon4)
        self.play_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_3.addWidget(self.play_button)

        self.ff_button = QPushButton(self.frame)
        self.ff_button.setObjectName(u"ff_button")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.ff_button.sizePolicy().hasHeightForWidth())
        self.ff_button.setSizePolicy(sizePolicy)
        self.ff_button.setMinimumSize(QSize(36, 36))
        self.ff_button.setMaximumSize(QSize(36, 36))
        self.ff_button.setFont(font)
        self.ff_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.ff_button.setStyleSheet(u"QPushButton {{\n"
"	border-radius: 20\n"
"}}")
        icon5 = QIcon()
        icon5.addFile(u":/services/b_ff", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.ff_button.setIcon(icon5)
        self.ff_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_3.addWidget(self.ff_button)


        self.verticalLayout_6.addWidget(self.frame)

        self.tabWidget.addTab(self.playlists, "")
        self.info_text = QWidget()
        self.info_text.setObjectName(u"info_text")
        self.info_text.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.verticalLayout_7 = QVBoxLayout(self.info_text)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.scrollArea = QScrollArea(self.info_text)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setLineWidth(0)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 552, 660))
        self.scrollAreaWidgetContents.setStyleSheet(u"            QFrame {{\n"
"                border: none\n"
"                border-radius: 3px;\n"
"            }}")
        self.verticalLayout_8 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.textEdit = QTextEdit(self.scrollAreaWidgetContents)
        self.textEdit.setObjectName(u"textEdit")
        self.textEdit.setFrameShape(QFrame.Shape.StyledPanel)
        self.textEdit.setFrameShadow(QFrame.Shadow.Plain)
        self.textEdit.setLineWidth(0)

        self.verticalLayout_8.addWidget(self.textEdit)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_7.addWidget(self.scrollArea)

        self.tabWidget.addTab(self.info_text, "")

        self.verticalLayout_4.addWidget(self.tabWidget)


        self.verticalLayout_2.addWidget(self.info_panel)


        self.horizontalLayout.addWidget(self.player_container)


        self.verticalLayout.addWidget(self.cajon_principal)


        self.retranslateUi(UrlPlaylist)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(UrlPlaylist)
    # setupUi

    def retranslateUi(self, UrlPlaylist):
        self.searchButton.setText("")
        self.ajustes_avanzados.setText(QCoreApplication.translate("UrlPlaylist", u"...", None))
        ___qtreewidgetitem = self.treeWidget.headerItem()
        ___qtreewidgetitem.setText(3, QCoreApplication.translate("UrlPlaylist", u"Duraci\u00f3n", None));
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("UrlPlaylist", u"Tipo", None));
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("UrlPlaylist", u"Artista", None));
        self.add_button.setText("")
        self.del_button.setText("")
        self.rew_button.setText("")
        self.play_button.setText("")
        self.ff_button.setText("")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.playlists), QCoreApplication.translate("UrlPlaylist", u"Playlist", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.info_text), QCoreApplication.translate("UrlPlaylist", u"Informaci\u00f3n", None))
        pass
    # retranslateUi

