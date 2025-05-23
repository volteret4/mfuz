# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'jaangle_folder_filter_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_FolderFilterDialog(object):
    def setupUi(self, FolderFilterDialog):
        if not FolderFilterDialog.objectName():
            FolderFilterDialog.setObjectName(u"FolderFilterDialog")
        FolderFilterDialog.resize(500, 500)
        FolderFilterDialog.setMinimumSize(QSize(400, 500))
        self.verticalLayout = QVBoxLayout(FolderFilterDialog)
        self.verticalLayout.setSpacing(16)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(16, 16, 16, 16)
        self.searchLayout = QHBoxLayout()
        self.searchLayout.setObjectName(u"searchLayout")
        self.searchLabel = QLabel(FolderFilterDialog)
        self.searchLabel.setObjectName(u"searchLabel")

        self.searchLayout.addWidget(self.searchLabel)

        self.search_edit = QLineEdit(FolderFilterDialog)
        self.search_edit.setObjectName(u"search_edit")
        self.search_edit.setClearButtonEnabled(True)

        self.searchLayout.addWidget(self.search_edit)


        self.verticalLayout.addLayout(self.searchLayout)

        self.folderScrollArea = QScrollArea(FolderFilterDialog)
        self.folderScrollArea.setObjectName(u"folderScrollArea")
        self.folderScrollArea.setWidgetResizable(True)
        self.scrollAreaContent = QWidget()
        self.scrollAreaContent.setObjectName(u"scrollAreaContent")
        self.scrollAreaContent.setGeometry(QRect(0, 0, 466, 382))
        self.checkboxLayout = QVBoxLayout(self.scrollAreaContent)
        self.checkboxLayout.setSpacing(8)
        self.checkboxLayout.setObjectName(u"checkboxLayout")
        self.checkboxLayout.setContentsMargins(12, 12, 12, 12)
        self.folderScrollArea.setWidget(self.scrollAreaContent)

        self.verticalLayout.addWidget(self.folderScrollArea)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.action_select_all_btn = QPushButton(FolderFilterDialog)
        self.action_select_all_btn.setObjectName(u"action_select_all_btn")
        icon = QIcon()
        icon.addFile(u"icons/select_all.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.action_select_all_btn.setIcon(icon)

        self.buttonLayout.addWidget(self.action_select_all_btn)

        self.action_deselect_all_btn = QPushButton(FolderFilterDialog)
        self.action_deselect_all_btn.setObjectName(u"action_deselect_all_btn")
        icon1 = QIcon()
        icon1.addFile(u"icons/deselect_all.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.action_deselect_all_btn.setIcon(icon1)

        self.buttonLayout.addWidget(self.action_deselect_all_btn)

        self.action_save_btn = QPushButton(FolderFilterDialog)
        self.action_save_btn.setObjectName(u"action_save_btn")
        icon2 = QIcon()
        icon2.addFile(u"icons/save.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.action_save_btn.setIcon(icon2)

        self.buttonLayout.addWidget(self.action_save_btn)

        self.action_cancel_btn = QPushButton(FolderFilterDialog)
        self.action_cancel_btn.setObjectName(u"action_cancel_btn")
        icon3 = QIcon()
        icon3.addFile(u"icons/cancel.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.action_cancel_btn.setIcon(icon3)

        self.buttonLayout.addWidget(self.action_cancel_btn)


        self.verticalLayout.addLayout(self.buttonLayout)


        self.retranslateUi(FolderFilterDialog)

        QMetaObject.connectSlotsByName(FolderFilterDialog)
    # setupUi

    def retranslateUi(self, FolderFilterDialog):
        FolderFilterDialog.setWindowTitle(QCoreApplication.translate("FolderFilterDialog", u"Filtrar Carpetas", None))
        self.searchLabel.setText(QCoreApplication.translate("FolderFilterDialog", u"Buscar:", None))
        self.search_edit.setPlaceholderText(QCoreApplication.translate("FolderFilterDialog", u"Escribe para filtrar...", None))
        self.action_select_all_btn.setText(QCoreApplication.translate("FolderFilterDialog", u"Seleccionar Todos", None))
        self.action_deselect_all_btn.setText(QCoreApplication.translate("FolderFilterDialog", u"Deseleccionar Todos", None))
        self.action_save_btn.setText(QCoreApplication.translate("FolderFilterDialog", u"Guardar", None))
        self.action_cancel_btn.setText(QCoreApplication.translate("FolderFilterDialog", u"Cancelar", None))
    # retranslateUi

