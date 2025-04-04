# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'menu_blogs_module.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_BlogPlaylists(object):
    def setupUi(self, BlogPlaylists):
        if not BlogPlaylists.objectName():
            BlogPlaylists.setObjectName(u"BlogPlaylists")
        BlogPlaylists.resize(900, 600)
        self.verticalLayout = QVBoxLayout(BlogPlaylists)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.main_panel = QHBoxLayout()
        self.main_panel.setObjectName(u"main_panel")
        self.left_panel = QWidget(BlogPlaylists)
        self.left_panel.setObjectName(u"left_panel")
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setObjectName(u"left_layout")
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.blog_label = QLabel(self.left_panel)
        self.blog_label.setObjectName(u"blog_label")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.blog_label.setFont(font)

        self.left_layout.addWidget(self.blog_label)

        self.blog_list = QListWidget(self.left_panel)
        self.blog_list.setObjectName(u"blog_list")

        self.left_layout.addWidget(self.blog_list)

        self.local_label = QLabel(self.left_panel)
        self.local_label.setObjectName(u"local_label")
        self.local_label.setFont(font)

        self.left_layout.addWidget(self.local_label)

        self.local_list = QListWidget(self.left_panel)
        self.local_list.setObjectName(u"local_list")

        self.left_layout.addWidget(self.local_list)


        self.main_panel.addWidget(self.left_panel)

        self.middle_panel = QWidget(BlogPlaylists)
        self.middle_panel.setObjectName(u"middle_panel")
        self.middle_layout = QVBoxLayout(self.middle_panel)
        self.middle_layout.setObjectName(u"middle_layout")
        self.middle_layout.setContentsMargins(0, 0, 0, 0)
        self.playlist_label = QLabel(self.middle_panel)
        self.playlist_label.setObjectName(u"playlist_label")
        self.playlist_label.setFont(font)

        self.middle_layout.addWidget(self.playlist_label)

        self.playlist_list = QListWidget(self.middle_panel)
        self.playlist_list.setObjectName(u"playlist_list")

        self.middle_layout.addWidget(self.playlist_list)

        self.play_button = QPushButton(self.middle_panel)
        self.play_button.setObjectName(u"play_button")

        self.middle_layout.addWidget(self.play_button)


        self.main_panel.addWidget(self.middle_panel)

        self.right_panel = QWidget(BlogPlaylists)
        self.right_panel.setObjectName(u"right_panel")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setObjectName(u"right_layout")
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.content_label = QLabel(self.right_panel)
        self.content_label.setObjectName(u"content_label")
        self.content_label.setFont(font)

        self.right_layout.addWidget(self.content_label)

        self.content_list = QListWidget(self.right_panel)
        self.content_list.setObjectName(u"content_list")

        self.right_layout.addWidget(self.content_list)


        self.main_panel.addWidget(self.right_panel)


        self.verticalLayout.addLayout(self.main_panel)

        self.url_layout = QHBoxLayout()
        self.url_layout.setObjectName(u"url_layout")
        self.url_process_input = QLineEdit(BlogPlaylists)
        self.url_process_input.setObjectName(u"url_process_input")

        self.url_layout.addWidget(self.url_process_input)

        self.process_url_button = QPushButton(BlogPlaylists)
        self.process_url_button.setObjectName(u"process_url_button")

        self.url_layout.addWidget(self.process_url_button)


        self.verticalLayout.addLayout(self.url_layout)


        self.retranslateUi(BlogPlaylists)

        QMetaObject.connectSlotsByName(BlogPlaylists)
    # setupUi

    def retranslateUi(self, BlogPlaylists):
        self.blog_label.setText(QCoreApplication.translate("BlogPlaylists", u"Blogs:", None))
        self.local_label.setText(QCoreApplication.translate("BlogPlaylists", u"Listas Locales:", None))
        self.playlist_label.setText(QCoreApplication.translate("BlogPlaylists", u"Playlists:", None))
        self.play_button.setText(QCoreApplication.translate("BlogPlaylists", u"Reproducir Seleccionado", None))
        self.content_label.setText(QCoreApplication.translate("BlogPlaylists", u"Contenido:", None))
        self.url_process_input.setPlaceholderText(QCoreApplication.translate("BlogPlaylists", u"Ingrese URL del blog para procesar", None))
        self.process_url_button.setText(QCoreApplication.translate("BlogPlaylists", u"Procesar URL", None))
        pass
    # retranslateUi

