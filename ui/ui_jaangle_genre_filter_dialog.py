# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'jaangle_genre_filter_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_GenreFilterDialog(object):
    def setupUi(self, GenreFilterDialog):
        if not GenreFilterDialog.objectName():
            GenreFilterDialog.setObjectName(u"GenreFilterDialog")
        GenreFilterDialog.resize(700, 550)
        GenreFilterDialog.setMinimumSize(QSize(700, 500))
        GenreFilterDialog.setStyleSheet(u"QDialog {\n"
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
"QTableWidget {\n"
"	border: 1px solid #E0E0E0;\n"
"	background-color: #FFFFFF;\n"
"	alternate-background-color: #F5F5F5;\n"
"	selection-background-color: #CFD8DC;\n"
"}\n"
"\n"
"QTableWidget::item {\n"
"	padding: 4px;\n"
"	border-bottom: 1px solid #E0E0E0;\n"
"}\n"
"\n"
"QHeaderView::section {\n"
"	background-color: #ECEFF1;\n"
"	c"
                        "olor: #37474F;\n"
"	padding: 5px;\n"
"	border: none;\n"
"	border-right: 1px solid #E0E0E0;\n"
"	border-bottom: 1px solid #E0E0E0;\n"
"	font-weight: bold;\n"
"}")
        self.verticalLayout = QVBoxLayout(GenreFilterDialog)
        self.verticalLayout.setSpacing(16)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(16, 16, 16, 16)
        self.searchLayout = QHBoxLayout()
        self.searchLayout.setObjectName(u"searchLayout")
        self.searchLabel = QLabel(GenreFilterDialog)
        self.searchLabel.setObjectName(u"searchLabel")

        self.searchLayout.addWidget(self.searchLabel)

        self.search_edit = QLineEdit(GenreFilterDialog)
        self.search_edit.setObjectName(u"search_edit")
        self.search_edit.setClearButtonEnabled(True)

        self.searchLayout.addWidget(self.search_edit)


        self.verticalLayout.addLayout(self.searchLayout)

        self.genres_table = QTableWidget(GenreFilterDialog)
        if (self.genres_table.columnCount() < 3):
            self.genres_table.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.genres_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.genres_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.genres_table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.genres_table.setObjectName(u"genres_table")
        self.genres_table.setAlternatingRowColors(True)
        self.genres_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.genres_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.genres_table.setSortingEnabled(True)
        self.genres_table.horizontalHeader().setStretchLastSection(False)

        self.verticalLayout.addWidget(self.genres_table)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.select_all_btn = QPushButton(GenreFilterDialog)
        self.select_all_btn.setObjectName(u"select_all_btn")
        icon = QIcon()
        icon.addFile(u"icons/select_all.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.select_all_btn.setIcon(icon)

        self.buttonLayout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton(GenreFilterDialog)
        self.deselect_all_btn.setObjectName(u"deselect_all_btn")
        icon1 = QIcon()
        icon1.addFile(u"icons/deselect_all.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.deselect_all_btn.setIcon(icon1)

        self.buttonLayout.addWidget(self.deselect_all_btn)

        self.save_btn = QPushButton(GenreFilterDialog)
        self.save_btn.setObjectName(u"save_btn")
        icon2 = QIcon()
        icon2.addFile(u"icons/save.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_btn.setIcon(icon2)

        self.buttonLayout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton(GenreFilterDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")
        icon3 = QIcon()
        icon3.addFile(u"icons/cancel.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.cancel_btn.setIcon(icon3)

        self.buttonLayout.addWidget(self.cancel_btn)


        self.verticalLayout.addLayout(self.buttonLayout)


        self.retranslateUi(GenreFilterDialog)

        QMetaObject.connectSlotsByName(GenreFilterDialog)
    # setupUi

    def retranslateUi(self, GenreFilterDialog):
        GenreFilterDialog.setWindowTitle(QCoreApplication.translate("GenreFilterDialog", u"Filtrar G\u00e9neros", None))
        self.searchLabel.setText(QCoreApplication.translate("GenreFilterDialog", u"Buscar:", None))
        self.search_edit.setPlaceholderText(QCoreApplication.translate("GenreFilterDialog", u"Escribe para filtrar...", None))
        ___qtablewidgetitem = self.genres_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("GenreFilterDialog", u"G\u00e9nero", None));
        ___qtablewidgetitem1 = self.genres_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("GenreFilterDialog", u"Artistas", None));
        ___qtablewidgetitem2 = self.genres_table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("GenreFilterDialog", u"Sellos", None));
        self.select_all_btn.setText(QCoreApplication.translate("GenreFilterDialog", u"Seleccionar Todos", None))
        self.deselect_all_btn.setText(QCoreApplication.translate("GenreFilterDialog", u"Deseleccionar Todos", None))
        self.save_btn.setText(QCoreApplication.translate("GenreFilterDialog", u"Guardar", None))
        self.cancel_btn.setText(QCoreApplication.translate("GenreFilterDialog", u"Cancelar", None))
    # retranslateUi

