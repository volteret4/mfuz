# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'conciertos_module.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QProgressBar, QPushButton, QSizePolicy, QStackedWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
    QWidget)
import rc_images

class Ui_ConciertosForm(object):
    def setupUi(self, ConciertosForm):
        if not ConciertosForm.objectName():
            ConciertosForm.setObjectName(u"ConciertosForm")
        ConciertosForm.resize(817, 600)
        self.main_layout = QVBoxLayout(ConciertosForm)
        self.main_layout.setObjectName(u"main_layout")
        self.groupBox_2 = QGroupBox(ConciertosForm)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.lineEdit = QLineEdit(self.groupBox_2)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setMinimumSize(QSize(0, 30))

        self.horizontalLayout_2.addWidget(self.lineEdit)

        self.buscar_searchbox = QPushButton(self.groupBox_2)
        self.buscar_searchbox.setObjectName(u"buscar_searchbox")
        self.buscar_searchbox.setMinimumSize(QSize(0, 30))
        self.buscar_searchbox.setMaximumSize(QSize(32, 32))
        icon = QIcon()
        icon.addFile(u":/services/musico", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.buscar_searchbox.setIcon(icon)
        self.buscar_searchbox.setIconSize(QSize(30, 30))
        self.buscar_searchbox.setFlat(True)

        self.horizontalLayout_2.addWidget(self.buscar_searchbox)

        self.advanced_settings = QCheckBox(self.groupBox_2)
        self.advanced_settings.setObjectName(u"advanced_settings")

        self.horizontalLayout_2.addWidget(self.advanced_settings)


        self.main_layout.addWidget(self.groupBox_2)

        self.global_config_group = QGroupBox(ConciertosForm)
        self.global_config_group.setObjectName(u"global_config_group")
        self.verticalLayout_8 = QVBoxLayout(self.global_config_group)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.widget_7 = QWidget(self.global_config_group)
        self.widget_7.setObjectName(u"widget_7")
        self.horizontalLayout_9 = QHBoxLayout(self.widget_7)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.widget_7)
        self.label.setObjectName(u"label")

        self.horizontalLayout_9.addWidget(self.label)

        self.country_code_input = QLineEdit(self.widget_7)
        self.country_code_input.setObjectName(u"country_code_input")
        self.country_code_input.setMaximumSize(QSize(50, 16777215))

        self.horizontalLayout_9.addWidget(self.country_code_input)

        self.source_combo = QComboBox(self.widget_7)
        icon1 = QIcon()
        icon1.addFile(u":/services/db_ol", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.source_combo.addItem(icon1, "")
        icon2 = QIcon()
        icon2.addFile(u":/services/cuernos", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.source_combo.addItem(icon2, "")
        icon3 = QIcon()
        icon3.addFile(u":/services/spotify_ol", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.source_combo.addItem(icon3, "")
        icon4 = QIcon()
        icon4.addFile(u":/services/lastfm_ol", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.source_combo.addItem(icon4, "")
        icon5 = QIcon()
        icon5.addFile(u":/services/musicbrainz", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.source_combo.addItem(icon5, "")
        self.source_combo.setObjectName(u"source_combo")
        self.source_combo.setMinimumSize(QSize(200, 30))

        self.horizontalLayout_9.addWidget(self.source_combo)

        self.pushButton = QPushButton(self.widget_7)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setMinimumSize(QSize(32, 32))
        self.pushButton.setMaximumSize(QSize(32, 32))
        icon6 = QIcon()
        icon6.addFile(u":/services/trompeta", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.pushButton.setIcon(icon6)
        self.pushButton.setIconSize(QSize(30, 30))
        self.pushButton.setFlat(True)

        self.horizontalLayout_9.addWidget(self.pushButton)

        self.add_to_cal = QPushButton(self.widget_7)
        self.add_to_cal.setObjectName(u"add_to_cal")
        self.add_to_cal.setMinimumSize(QSize(32, 32))
        self.add_to_cal.setMaximumSize(QSize(32, 32))
        icon7 = QIcon()
        icon7.addFile(u":/services/cal_Red", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.add_to_cal.setIcon(icon7)
        self.add_to_cal.setIconSize(QSize(30, 30))
        self.add_to_cal.setFlat(True)

        self.horizontalLayout_9.addWidget(self.add_to_cal)

        self.debug_btn_2 = QPushButton(self.widget_7)
        self.debug_btn_2.setObjectName(u"debug_btn_2")

        self.horizontalLayout_9.addWidget(self.debug_btn_2)

        self.debug_btn = QPushButton(self.widget_7)
        self.debug_btn.setObjectName(u"debug_btn")

        self.horizontalLayout_9.addWidget(self.debug_btn)

        self.clear_cache_btn = QPushButton(self.widget_7)
        self.clear_cache_btn.setObjectName(u"clear_cache_btn")

        self.horizontalLayout_9.addWidget(self.clear_cache_btn)

        self.paginas_btn = QPushButton(self.widget_7)
        self.paginas_btn.setObjectName(u"paginas_btn")

        self.horizontalLayout_9.addWidget(self.paginas_btn)

        self.select_file_btn = QPushButton(self.widget_7)
        self.select_file_btn.setObjectName(u"select_file_btn")
        self.select_file_btn.setMaximumSize(QSize(30, 16777215))

        self.horizontalLayout_9.addWidget(self.select_file_btn)


        self.verticalLayout_8.addWidget(self.widget_7)


        self.main_layout.addWidget(self.global_config_group)

        self.stackedWidget = QStackedWidget(ConciertosForm)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.page = QWidget()
        self.page.setObjectName(u"page")
        self.verticalLayout_2 = QVBoxLayout(self.page)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.groupBox = QGroupBox(self.page)
        self.groupBox.setObjectName(u"groupBox")
        self.horizontalLayout_3 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.concerts_tree = QTableWidget(self.groupBox)
        if (self.concerts_tree.columnCount() < 4):
            self.concerts_tree.setColumnCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        self.concerts_tree.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.concerts_tree.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.concerts_tree.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.concerts_tree.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        self.concerts_tree.setObjectName(u"concerts_tree")
        self.concerts_tree.setSortingEnabled(True)

        self.horizontalLayout_3.addWidget(self.concerts_tree)

        self.widget = QWidget(self.groupBox)
        self.widget.setObjectName(u"widget")
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.foto_label = QLabel(self.widget)
        self.foto_label.setObjectName(u"foto_label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.foto_label.sizePolicy().hasHeightForWidth())
        self.foto_label.setSizePolicy(sizePolicy)

        self.verticalLayout.addWidget(self.foto_label)

        self.info_area = QTextEdit(self.widget)
        self.info_area.setObjectName(u"info_area")
        self.info_area.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByKeyboard|Qt.TextInteractionFlag.LinksAccessibleByMouse|Qt.TextInteractionFlag.TextBrowserInteraction|Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)

        self.verticalLayout.addWidget(self.info_area)


        self.horizontalLayout_3.addWidget(self.widget)


        self.verticalLayout_2.addWidget(self.groupBox)

        self.stackedWidget.addWidget(self.page)
        self.page_2 = QWidget()
        self.page_2.setObjectName(u"page_2")
        self.horizontalLayout = QHBoxLayout(self.page_2)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.log_area = QTextEdit(self.page_2)
        self.log_area.setObjectName(u"log_area")

        self.horizontalLayout.addWidget(self.log_area)

        self.stackedWidget.addWidget(self.page_2)

        self.main_layout.addWidget(self.stackedWidget)

        self.progress_bar = QProgressBar(ConciertosForm)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)

        self.main_layout.addWidget(self.progress_bar)


        self.retranslateUi(ConciertosForm)

        self.stackedWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(ConciertosForm)
    # setupUi

    def retranslateUi(self, ConciertosForm):
        ConciertosForm.setWindowTitle(QCoreApplication.translate("ConciertosForm", u"Conciertos", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("ConciertosForm", u"Artista", None))
        self.lineEdit.setText("")
        self.buscar_searchbox.setText("")
        self.advanced_settings.setText(QCoreApplication.translate("ConciertosForm", u"M\u00e1s", None))
        self.global_config_group.setTitle("")
        self.label.setText(QCoreApplication.translate("ConciertosForm", u"Pa\u00eds (c\u00f3digo):", None))
        self.source_combo.setItemText(0, QCoreApplication.translate("ConciertosForm", u"Artistas de la base de datos", None))
        self.source_combo.setItemText(1, QCoreApplication.translate("ConciertosForm", u"Artistas de muspy", None))
        self.source_combo.setItemText(2, QCoreApplication.translate("ConciertosForm", u"Artisas Spotify", None))
        self.source_combo.setItemText(3, QCoreApplication.translate("ConciertosForm", u"Artistas de lastfm", None))
        self.source_combo.setItemText(4, QCoreApplication.translate("ConciertosForm", u"Artistas de musicbrainz", None))

        self.pushButton.setText("")
        self.add_to_cal.setText("")
        self.debug_btn_2.setText(QCoreApplication.translate("ConciertosForm", u"api", None))
        self.debug_btn.setText(QCoreApplication.translate("ConciertosForm", u"response", None))
        self.clear_cache_btn.setText(QCoreApplication.translate("ConciertosForm", u"borrar cache", None))
        self.paginas_btn.setText(QCoreApplication.translate("ConciertosForm", u"Log/Tabla", None))
        self.select_file_btn.setText(QCoreApplication.translate("ConciertosForm", u"...", None))
        self.groupBox.setTitle(QCoreApplication.translate("ConciertosForm", u"Conciertos", None))
        ___qtablewidgetitem = self.concerts_tree.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("ConciertosForm", u"cal", None));
        ___qtablewidgetitem1 = self.concerts_tree.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("ConciertosForm", u"artista", None));
        ___qtablewidgetitem2 = self.concerts_tree.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("ConciertosForm", u"ciudad", None));
        ___qtablewidgetitem3 = self.concerts_tree.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("ConciertosForm", u"fecha", None));
        self.foto_label.setText("")
    # retranslateUi

