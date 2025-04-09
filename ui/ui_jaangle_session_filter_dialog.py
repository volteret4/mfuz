# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'jaangle_session_filter_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_SessionFilterDialog(object):
    def setupUi(self, SessionFilterDialog):
        if not SessionFilterDialog.objectName():
            SessionFilterDialog.setObjectName(u"SessionFilterDialog")
        SessionFilterDialog.resize(500, 600)
        SessionFilterDialog.setMinimumSize(QSize(450, 550))
        SessionFilterDialog.setStyleSheet(u"QDialog {\n"
"	background-color: #FFFFFF;\n"
"}\n"
"\n"
"QLabel {\n"
"	font-family: 'Segoe UI', Arial, sans-serif;\n"
"	font-size: 10pt;\n"
"}\n"
"\n"
"QLineEdit, QComboBox {\n"
"	border: 1px solid #E0E0E0;\n"
"	border-radius: 4px;\n"
"	padding: 5px;\n"
"	background-color: #F5F5F5;\n"
"}\n"
"\n"
"QLineEdit:focus, QComboBox:focus {\n"
"	border: 1px solid #78909C;\n"
"	background-color: #FFFFFF;\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"	border: none;\n"
"	border-left: 1px solid #E0E0E0;\n"
"	width: 20px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"	image: url(icons/down_arrow.png);\n"
"	width: 12px;\n"
"	height: 12px;\n"
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
"	widt"
                        "h: 18px;\n"
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
"	background-color: #607D8B;\n"
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
        self.verticalLayout = QVBoxLayout(SessionFilterDialog)
        self.verticalLayout.setSpacing(16)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(16, 16, 16, 16)
        self.filterTypeLayout = QHBoxLayout()
        self.filterTypeLayout.setObjectName(u"filterTypeLayout")
        self.filterTypeLabel = QLabel(SessionFilterDialog)
        self.filterTypeLabel.setObjectName(u"filterTypeLabel")

        self.filterTypeLayout.addWidget(self.filterTypeLabel)

        self.filter_type_combo = QComboBox(SessionFilterDialog)
        self.filter_type_combo.addItem("")
        self.filter_type_combo.addItem("")
        self.filter_type_combo.addItem("")
        self.filter_type_combo.addItem("")
        self.filter_type_combo.setObjectName(u"filter_type_combo")

        self.filterTypeLayout.addWidget(self.filter_type_combo)


        self.verticalLayout.addLayout(self.filterTypeLayout)

        self.searchLayout = QHBoxLayout()
        self.searchLayout.setObjectName(u"searchLayout")
        self.searchLabel = QLabel(SessionFilterDialog)
        self.searchLabel.setObjectName(u"searchLabel")

        self.searchLayout.addWidget(self.searchLabel)

        self.search_edit = QLineEdit(SessionFilterDialog)
        self.search_edit.setObjectName(u"search_edit")
        self.search_edit.setClearButtonEnabled(True)

        self.searchLayout.addWidget(self.search_edit)


        self.verticalLayout.addLayout(self.searchLayout)

        self.itemScrollArea = QScrollArea(SessionFilterDialog)
        self.itemScrollArea.setObjectName(u"itemScrollArea")
        self.itemScrollArea.setWidgetResizable(True)
        self.scrollAreaContent = QWidget()
        self.scrollAreaContent.setObjectName(u"scrollAreaContent")
        self.scrollAreaContent.setGeometry(QRect(0, 0, 466, 392))
        self.checkboxLayout = QVBoxLayout(self.scrollAreaContent)
        self.checkboxLayout.setSpacing(8)
        self.checkboxLayout.setObjectName(u"checkboxLayout")
        self.checkboxLayout.setContentsMargins(12, 12, 12, 12)
        self.itemScrollArea.setWidget(self.scrollAreaContent)

        self.verticalLayout.addWidget(self.itemScrollArea)

        self.sessionLayout = QHBoxLayout()
        self.sessionLayout.setObjectName(u"sessionLayout")
        self.sessionLabel = QLabel(SessionFilterDialog)
        self.sessionLabel.setObjectName(u"sessionLabel")

        self.sessionLayout.addWidget(self.sessionLabel)

        self.session_edit = QLineEdit(SessionFilterDialog)
        self.session_edit.setObjectName(u"session_edit")
        self.session_edit.setClearButtonEnabled(True)

        self.sessionLayout.addWidget(self.session_edit)


        self.verticalLayout.addLayout(self.sessionLayout)

        self.sessionOpsLayout = QHBoxLayout()
        self.sessionOpsLayout.setObjectName(u"sessionOpsLayout")
        self.save_session_btn = QPushButton(SessionFilterDialog)
        self.save_session_btn.setObjectName(u"save_session_btn")
        icon = QIcon()
        icon.addFile(u"icons/save_session.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_session_btn.setIcon(icon)

        self.sessionOpsLayout.addWidget(self.save_session_btn)

        self.load_session_btn = QPushButton(SessionFilterDialog)
        self.load_session_btn.setObjectName(u"load_session_btn")
        icon1 = QIcon()
        icon1.addFile(u"icons/load_session.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.load_session_btn.setIcon(icon1)

        self.sessionOpsLayout.addWidget(self.load_session_btn)


        self.verticalLayout.addLayout(self.sessionOpsLayout)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.select_all_btn = QPushButton(SessionFilterDialog)
        self.select_all_btn.setObjectName(u"select_all_btn")
        icon2 = QIcon()
        icon2.addFile(u"icons/select_all.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.select_all_btn.setIcon(icon2)

        self.buttonLayout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton(SessionFilterDialog)
        self.deselect_all_btn.setObjectName(u"deselect_all_btn")
        icon3 = QIcon()
        icon3.addFile(u"icons/deselect_all.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.deselect_all_btn.setIcon(icon3)

        self.buttonLayout.addWidget(self.deselect_all_btn)

        self.apply_btn = QPushButton(SessionFilterDialog)
        self.apply_btn.setObjectName(u"apply_btn")
        icon4 = QIcon()
        icon4.addFile(u"icons/apply.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.apply_btn.setIcon(icon4)

        self.buttonLayout.addWidget(self.apply_btn)

        self.cancel_btn = QPushButton(SessionFilterDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")
        icon5 = QIcon()
        icon5.addFile(u"icons/cancel.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.cancel_btn.setIcon(icon5)

        self.buttonLayout.addWidget(self.cancel_btn)


        self.verticalLayout.addLayout(self.buttonLayout)


        self.retranslateUi(SessionFilterDialog)

        QMetaObject.connectSlotsByName(SessionFilterDialog)
    # setupUi

    def retranslateUi(self, SessionFilterDialog):
        SessionFilterDialog.setWindowTitle(QCoreApplication.translate("SessionFilterDialog", u"Filtros de Sesi\u00f3n", None))
        self.filterTypeLabel.setText(QCoreApplication.translate("SessionFilterDialog", u"Tipo de filtro:", None))
        self.filter_type_combo.setItemText(0, QCoreApplication.translate("SessionFilterDialog", u"Artistas", None))
        self.filter_type_combo.setItemText(1, QCoreApplication.translate("SessionFilterDialog", u"\u00c1lbumes", None))
        self.filter_type_combo.setItemText(2, QCoreApplication.translate("SessionFilterDialog", u"G\u00e9neros", None))
        self.filter_type_combo.setItemText(3, QCoreApplication.translate("SessionFilterDialog", u"Carpetas", None))

        self.searchLabel.setText(QCoreApplication.translate("SessionFilterDialog", u"Buscar:", None))
        self.search_edit.setPlaceholderText(QCoreApplication.translate("SessionFilterDialog", u"Escribe para filtrar...", None))
        self.scrollAreaContent.setObjectName(QCoreApplication.translate("SessionFilterDialog", u"scrollAreaContent", None))
        self.sessionLabel.setText(QCoreApplication.translate("SessionFilterDialog", u"Nombre de la sesi\u00f3n:", None))
        self.session_edit.setPlaceholderText(QCoreApplication.translate("SessionFilterDialog", u"Mi sesi\u00f3n personalizada", None))
        self.save_session_btn.setText(QCoreApplication.translate("SessionFilterDialog", u"Guardar Sesi\u00f3n", None))
        self.load_session_btn.setText(QCoreApplication.translate("SessionFilterDialog", u"Cargar Sesi\u00f3n", None))
        self.select_all_btn.setText(QCoreApplication.translate("SessionFilterDialog", u"Seleccionar Todos", None))
        self.deselect_all_btn.setText(QCoreApplication.translate("SessionFilterDialog", u"Deseleccionar Todos", None))
        self.apply_btn.setText(QCoreApplication.translate("SessionFilterDialog", u"Aplicar", None))
        self.cancel_btn.setText(QCoreApplication.translate("SessionFilterDialog", u"Cancelar", None))
    # retranslateUi

