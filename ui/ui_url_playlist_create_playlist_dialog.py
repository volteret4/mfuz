# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'url_playlist_create_playlist_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QFrame, QHBoxLayout, QLabel, QLineEdit,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

class Ui_CreatePlaylistDialog(object):
    def setupUi(self, CreatePlaylistDialog):
        if not CreatePlaylistDialog.objectName():
            CreatePlaylistDialog.setObjectName(u"CreatePlaylistDialog")
        CreatePlaylistDialog.resize(400, 220)
        CreatePlaylistDialog.setStyleSheet(u"QDialog {background-color: #1a1b26;}\n"
"QLabel {color: #a9b1d6;}\n"
"QLineEdit {\n"
"    background-color: #24283b;\n"
"    border: 1px solid #3d59a1;\n"
"    border-radius: 4px;\n"
"    padding: 4px;\n"
"    color: #a9b1d6;\n"
"}\n"
"QPushButton {\n"
"    background-color: #3d59a1;\n"
"    color: white;\n"
"    border: none;\n"
"    border-radius: 4px;\n"
"    padding: 6px 12px;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #5d78c1;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #2d3981;\n"
"}")
        self.verticalLayout = QVBoxLayout(CreatePlaylistDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.playlist_icon_label = QLabel(CreatePlaylistDialog)
        self.playlist_icon_label.setObjectName(u"playlist_icon_label")
        self.playlist_icon_label.setMinimumSize(QSize(32, 32))
        self.playlist_icon_label.setMaximumSize(QSize(32, 32))

        self.horizontalLayout.addWidget(self.playlist_icon_label)

        self.title_label = QLabel(CreatePlaylistDialog)
        self.title_label.setObjectName(u"title_label")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.title_label.setFont(font)

        self.horizontalLayout.addWidget(self.title_label)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.frame = QFrame(CreatePlaylistDialog)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.HLine)
        self.frame.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.frame)

        self.verticalSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.name_label = QLabel(CreatePlaylistDialog)
        self.name_label.setObjectName(u"name_label")

        self.verticalLayout.addWidget(self.name_label)

        self.playlist_name_edit = QLineEdit(CreatePlaylistDialog)
        self.playlist_name_edit.setObjectName(u"playlist_name_edit")

        self.verticalLayout.addWidget(self.playlist_name_edit)

        self.description_label = QLabel(CreatePlaylistDialog)
        self.description_label.setObjectName(u"description_label")

        self.verticalLayout.addWidget(self.description_label)

        self.description_edit = QLineEdit(CreatePlaylistDialog)
        self.description_edit.setObjectName(u"description_edit")

        self.verticalLayout.addWidget(self.description_edit)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.buttonBox = QDialogButtonBox(CreatePlaylistDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(CreatePlaylistDialog)
        self.buttonBox.accepted.connect(CreatePlaylistDialog.accept)
        self.buttonBox.rejected.connect(CreatePlaylistDialog.reject)

        QMetaObject.connectSlotsByName(CreatePlaylistDialog)
    # setupUi

    def retranslateUi(self, CreatePlaylistDialog):
        CreatePlaylistDialog.setWindowTitle(QCoreApplication.translate("CreatePlaylistDialog", u"Crear Playlist", None))
        self.playlist_icon_label.setText("")
        self.title_label.setText(QCoreApplication.translate("CreatePlaylistDialog", u"Crear nueva playlist", None))
        self.name_label.setText(QCoreApplication.translate("CreatePlaylistDialog", u"Nombre de la playlist:", None))
        self.playlist_name_edit.setPlaceholderText(QCoreApplication.translate("CreatePlaylistDialog", u"Introduce un nombre para la playlist", None))
        self.description_label.setText(QCoreApplication.translate("CreatePlaylistDialog", u"Descripci\u00f3n (opcional):", None))
        self.description_edit.setPlaceholderText(QCoreApplication.translate("CreatePlaylistDialog", u"Breve descripci\u00f3n de la playlist", None))
    # retranslateUi

