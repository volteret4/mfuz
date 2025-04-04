# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'conciertos_module.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QSplitter, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_ConciertosForm(object):
    def setupUi(self, ConciertosForm):
        if not ConciertosForm.objectName():
            ConciertosForm.setObjectName(u"ConciertosForm")
        ConciertosForm.resize(800, 600)
        self.main_layout = QVBoxLayout(ConciertosForm)
        self.main_layout.setObjectName(u"main_layout")
        self.global_config_group = QGroupBox(ConciertosForm)
        self.global_config_group.setObjectName(u"global_config_group")
        self.global_form = QFormLayout(self.global_config_group)
        self.global_form.setObjectName(u"global_form")
        self.label = QLabel(self.global_config_group)
        self.label.setObjectName(u"label")

        self.global_form.setWidget(0, QFormLayout.LabelRole, self.label)

        self.country_code_input = QLineEdit(self.global_config_group)
        self.country_code_input.setObjectName(u"country_code_input")
        self.country_code_input.setMaximumSize(QSize(50, 16777215))

        self.global_form.setWidget(0, QFormLayout.FieldRole, self.country_code_input)

        self.label_2 = QLabel(self.global_config_group)
        self.label_2.setObjectName(u"label_2")

        self.global_form.setWidget(1, QFormLayout.LabelRole, self.label_2)

        self.artists_file_layout = QHBoxLayout()
        self.artists_file_layout.setObjectName(u"artists_file_layout")
        self.artists_file_input = QLineEdit(self.global_config_group)
        self.artists_file_input.setObjectName(u"artists_file_input")

        self.artists_file_layout.addWidget(self.artists_file_input)

        self.select_file_btn = QPushButton(self.global_config_group)
        self.select_file_btn.setObjectName(u"select_file_btn")
        self.select_file_btn.setMaximumSize(QSize(30, 16777215))

        self.artists_file_layout.addWidget(self.select_file_btn)


        self.global_form.setLayout(1, QFormLayout.FieldRole, self.artists_file_layout)


        self.main_layout.addWidget(self.global_config_group)

        self.tabs = QTabWidget(ConciertosForm)
        self.tabs.setObjectName(u"tabs")

        self.main_layout.addWidget(self.tabs)

        self.fetch_all_btn = QPushButton(ConciertosForm)
        self.fetch_all_btn.setObjectName(u"fetch_all_btn")

        self.main_layout.addWidget(self.fetch_all_btn)

        self.concerts_label = QLabel(ConciertosForm)
        self.concerts_label.setObjectName(u"concerts_label")

        self.main_layout.addWidget(self.concerts_label)

        self.splitter = QSplitter(ConciertosForm)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Vertical)
        self.concerts_list = QListWidget(self.splitter)
        self.concerts_list.setObjectName(u"concerts_list")
        self.concerts_list.setMinimumSize(QSize(0, 200))
        self.splitter.addWidget(self.concerts_list)
        self.log_area = QTextEdit(self.splitter)
        self.log_area.setObjectName(u"log_area")
        self.log_area.setMaximumSize(QSize(16777215, 150))
        self.log_area.setReadOnly(True)
        self.splitter.addWidget(self.log_area)

        self.main_layout.addWidget(self.splitter)


        self.retranslateUi(ConciertosForm)

        QMetaObject.connectSlotsByName(ConciertosForm)
    # setupUi

    def retranslateUi(self, ConciertosForm):
        ConciertosForm.setWindowTitle(QCoreApplication.translate("ConciertosForm", u"Conciertos", None))
        self.global_config_group.setTitle(QCoreApplication.translate("ConciertosForm", u"Configuraci\u00f3n global", None))
        self.label.setText(QCoreApplication.translate("ConciertosForm", u"Pa\u00eds (c\u00f3digo):", None))
        self.label_2.setText(QCoreApplication.translate("ConciertosForm", u"Archivo de artistas:", None))
        self.select_file_btn.setText(QCoreApplication.translate("ConciertosForm", u"...", None))
        self.fetch_all_btn.setText(QCoreApplication.translate("ConciertosForm", u"Buscar en Todos los Servicios", None))
        self.concerts_label.setText(QCoreApplication.translate("ConciertosForm", u"Resultados de conciertos:", None))
    # retranslateUi

