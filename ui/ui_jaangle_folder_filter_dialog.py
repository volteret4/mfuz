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
        FolderFilterDialog.setStyleSheet(u"QDialog {\n"
"	background-color: #FFFFFF;\n"
"}\n"
"\n"
"QLabel {\n"
"	font-family: 'Segoe UI', Arial, sans-serif;\n"
"	font-size: 10pt;\n"
"}\n"
"\n"
"QLineEdit {\n"
"	border: 1px solid #E0E0E0;\n"
"	border-radius: 4px;\n"
"	padding: 5px;\n"
"	background-color: #F5F5F5;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"	border: 1px solid #78909C;\n"
"	background-color: #FFFFFF;\n"
"}\n"
"\n"
"QPushButton {\n"
"	background-color: #607D8B;\n"
"	color: white;\n"
"	border: none;\n"
"	border-radius: 4px;\n"
"	padding: 6px 12px;\n"
"	font-weight: bold;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"	background-color: #78909C;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"	background-color: #546E7A;\n"
"}\n"
"\n"
"QCheckBox {\n"
"	spacing: 8px;\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"	width: 18px;\n"
"	height: 18px;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"	border: 2px solid #B0BEC5;\n"
"	background-color: #FFFFFF;\n"
"	border-radius: 3px;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"	border: 2px solid #607D8B;\n"
"	backgro"
                        "und-color: #607D8B;\n"
"	border-radius: 3px;\n"
"}\n"
"\n"
"QScrollArea {\n"
"	border: 1px solid #E0E0E0;\n"
"	background-color: #FFFFFF;\n"
"}\n"
"\n"
"QWidget#scrollAreaContent {\n"
"	background-color: #FFFFFF;\n"
"}")
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
        self.scrollAreaContent.setGeometry(QRect(0, 0, 466, 392))
        self.checkboxLayout = QVBoxLayout(self.scrollAreaContent)
        self.checkboxLayout.setSpacing(8)
        self.checkboxLayout.setObjectName(u"checkboxLayout")
        self.checkboxLayout.setContentsMargins(12, 12, 12, 12)
        self.folderScrollArea.setWidget(self.scrollAreaContent)

        self.verticalLayout.addWidget(self.folderScrollArea)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.select_all_btn = QPushButton(FolderFilterDialog)
        self.select_all_btn.setObjectName(u"select_all_btn")
        icon = QIcon()
        icon.addFile(u"icons/select_all.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.select_all_btn.setIcon(icon)

        self.buttonLayout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton(FolderFilterDialog)
        self.deselect_all_btn.setObjectName(u"deselect_all_btn")
        icon1 = QIcon()
        icon1.addFile(u"icons/deselect_all.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.deselect_all_btn.setIcon(icon1)

        self.buttonLayout.addWidget(self.deselect_all_btn)

        self.save_btn = QPushButton(FolderFilterDialog)
        self.save_btn.setObjectName(u"save_btn")
        icon2 = QIcon()
        icon2.addFile(u"icons/save.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_btn.setIcon(icon2)

        self.buttonLayout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton(FolderFilterDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")
        icon3 = QIcon()
        icon3.addFile(u"icons/cancel.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.cancel_btn.setIcon(icon3)

        self.buttonLayout.addWidget(self.cancel_btn)


        self.verticalLayout.addLayout(self.buttonLayout)


        self.retranslateUi(FolderFilterDialog)

        QMetaObject.connectSlotsByName(FolderFilterDialog)
    # setupUi

    def retranslateUi(self, FolderFilterDialog):
        FolderFilterDialog.setWindowTitle(QCoreApplication.translate("FolderFilterDialog", u"Filtrar Carpetas", None))
        self.searchLabel.setText(QCoreApplication.translate("FolderFilterDialog", u"Buscar:", None))
        self.search_edit.setPlaceholderText(QCoreApplication.translate("FolderFilterDialog", u"Escribe para filtrar...", None))
        self.scrollAreaContent.setObjectName(QCoreApplication.translate("FolderFilterDialog", u"scrollAreaContent", None))
        self.select_all_btn.setText(QCoreApplication.translate("FolderFilterDialog", u"Seleccionar Todos", None))
        self.deselect_all_btn.setText(QCoreApplication.translate("FolderFilterDialog", u"Deseleccionar Todos", None))
        self.save_btn.setText(QCoreApplication.translate("FolderFilterDialog", u"Guardar", None))
        self.cancel_btn.setText(QCoreApplication.translate("FolderFilterDialog", u"Cancelar", None))
    # retranslateUi

