# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'url_playlist_advanced_settings_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QSizePolicy, QSpacerItem,
    QSpinBox, QVBoxLayout, QWidget)
import rc_images

class Ui_AdvancedSettings(object):
    def setupUi(self, AdvancedSettings):
        if not AdvancedSettings.objectName():
            AdvancedSettings.setObjectName(u"AdvancedSettings")
        AdvancedSettings.resize(700, 550)
        AdvancedSettings.setMinimumSize(QSize(400, 300))
        AdvancedSettings.setStyleSheet(u"QDialog {\n"
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
        self.verticalLayout = QVBoxLayout(AdvancedSettings)
        self.verticalLayout.setSpacing(16)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.add_sett_frame = QFrame(AdvancedSettings)
        self.add_sett_frame.setObjectName(u"add_sett_frame")
        self.add_sett_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.add_sett_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.add_sett_frame.setLineWidth(0)
        self.verticalLayout_2 = QVBoxLayout(self.add_sett_frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.num_servicios = QGroupBox(self.add_sett_frame)
        self.num_servicios.setObjectName(u"num_servicios")
        self.horizontalLayout = QHBoxLayout(self.num_servicios)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.num_servicios_label = QLabel(self.num_servicios)
        self.num_servicios_label.setObjectName(u"num_servicios_label")

        self.horizontalLayout.addWidget(self.num_servicios_label)

        self.num_servicios_spinBox = QSpinBox(self.num_servicios)
        self.num_servicios_spinBox.setObjectName(u"num_servicios_spinBox")
        self.num_servicios_spinBox.setMinimum(5)
        self.num_servicios_spinBox.setMaximum(50)

        self.horizontalLayout.addWidget(self.num_servicios_spinBox)


        self.verticalLayout_2.addWidget(self.num_servicios)

        self.tipo_group = QGroupBox(self.add_sett_frame)
        self.tipo_group.setObjectName(u"tipo_group")
        self.horizontalLayout_2 = QHBoxLayout(self.tipo_group)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label = QLabel(self.tipo_group)
        self.label.setObjectName(u"label")

        self.horizontalLayout_2.addWidget(self.label)

        self.tipo_combo = QComboBox(self.tipo_group)
        self.tipo_combo.addItem("")
        self.tipo_combo.addItem("")
        self.tipo_combo.addItem("")
        self.tipo_combo.addItem("")
        self.tipo_combo.setObjectName(u"tipo_combo")

        self.horizontalLayout_2.addWidget(self.tipo_combo)


        self.verticalLayout_2.addWidget(self.tipo_group)

        self.servicios_en_todos = QGroupBox(self.add_sett_frame)
        self.servicios_en_todos.setObjectName(u"servicios_en_todos")
        self.verticalLayout_3 = QVBoxLayout(self.servicios_en_todos)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.serv_todos_label = QLabel(self.servicios_en_todos)
        self.serv_todos_label.setObjectName(u"serv_todos_label")

        self.verticalLayout_3.addWidget(self.serv_todos_label)

        self.bandcamp_check = QCheckBox(self.servicios_en_todos)
        self.bandcamp_check.setObjectName(u"bandcamp_check")
        icon = QIcon()
        icon.addFile(u":/services/bandcamp", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.bandcamp_check.setIcon(icon)

        self.verticalLayout_3.addWidget(self.bandcamp_check)

        self.lastfm_check = QCheckBox(self.servicios_en_todos)
        self.lastfm_check.setObjectName(u"lastfm_check")
        icon1 = QIcon()
        icon1.addFile(u":/services/lastfm", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.lastfm_check.setIcon(icon1)

        self.verticalLayout_3.addWidget(self.lastfm_check)

        self.soundcloud_check = QCheckBox(self.servicios_en_todos)
        self.soundcloud_check.setObjectName(u"soundcloud_check")
        icon2 = QIcon()
        icon2.addFile(u":/services/soundcloud", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.soundcloud_check.setIcon(icon2)

        self.verticalLayout_3.addWidget(self.soundcloud_check)

        self.spotify_check = QCheckBox(self.servicios_en_todos)
        self.spotify_check.setObjectName(u"spotify_check")
        icon3 = QIcon()
        icon3.addFile(u":/services/spotify", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.spotify_check.setIcon(icon3)

        self.verticalLayout_3.addWidget(self.spotify_check)

        self.youtube_check = QCheckBox(self.servicios_en_todos)
        self.youtube_check.setObjectName(u"youtube_check")
        icon4 = QIcon()
        icon4.addFile(u":/services/youtube", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.youtube_check.setIcon(icon4)

        self.verticalLayout_3.addWidget(self.youtube_check)


        self.verticalLayout_2.addWidget(self.servicios_en_todos)

        self.rss = QGroupBox(self.add_sett_frame)
        self.rss.setObjectName(u"rss")
        self.verticalLayout_4 = QVBoxLayout(self.rss)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.rss_label = QLabel(self.rss)
        self.rss_label.setObjectName(u"rss_label")

        self.verticalLayout_4.addWidget(self.rss_label)

        self.rss_check_1 = QCheckBox(self.rss)
        self.rss_check_1.setObjectName(u"rss_check_1")

        self.verticalLayout_4.addWidget(self.rss_check_1)


        self.verticalLayout_2.addWidget(self.rss)

        self.verticalSpacer = QSpacerItem(20, 122, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer)

        self.adv_sett_buttonBox = QDialogButtonBox(self.add_sett_frame)
        self.adv_sett_buttonBox.setObjectName(u"adv_sett_buttonBox")
        self.adv_sett_buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout_2.addWidget(self.adv_sett_buttonBox)


        self.verticalLayout.addWidget(self.add_sett_frame)


        self.retranslateUi(AdvancedSettings)

        QMetaObject.connectSlotsByName(AdvancedSettings)
    # setupUi

    def retranslateUi(self, AdvancedSettings):
        AdvancedSettings.setWindowTitle(QCoreApplication.translate("AdvancedSettings", u"Filtrar \u00c1lbumes", None))
        self.num_servicios.setTitle("")
        self.num_servicios_label.setText(QCoreApplication.translate("AdvancedSettings", u"N\u00famero de resultados por servicio:", None))
        self.tipo_group.setTitle(QCoreApplication.translate("AdvancedSettings", u"GroupBox", None))
        self.label.setText(QCoreApplication.translate("AdvancedSettings", u"Elemento a buscar", None))
        self.tipo_combo.setItemText(0, QCoreApplication.translate("AdvancedSettings", u"Artista", None))
        self.tipo_combo.setItemText(1, QCoreApplication.translate("AdvancedSettings", u"\u00c1lbum", None))
        self.tipo_combo.setItemText(2, QCoreApplication.translate("AdvancedSettings", u"Canciones", None))
        self.tipo_combo.setItemText(3, QCoreApplication.translate("AdvancedSettings", u"Todo", None))

        self.servicios_en_todos.setTitle("")
        self.serv_todos_label.setText(QCoreApplication.translate("AdvancedSettings", u"Se\u00f1ala qu\u00e9 servicios deseas incluir cuando buscas en \"Todos\"", None))
        self.bandcamp_check.setText(QCoreApplication.translate("AdvancedSettings", u"bancamp", None))
        self.lastfm_check.setText(QCoreApplication.translate("AdvancedSettings", u"lastfm", None))
        self.soundcloud_check.setText(QCoreApplication.translate("AdvancedSettings", u"souncloud", None))
        self.spotify_check.setText(QCoreApplication.translate("AdvancedSettings", u"spotify", None))
        self.youtube_check.setText(QCoreApplication.translate("AdvancedSettings", u"youtube", None))
        self.rss.setTitle("")
        self.rss_label.setText(QCoreApplication.translate("AdvancedSettings", u"Selecciona desde tus servidor rss en qu\u00e9 categor\u00edas buscar", None))
        self.rss_check_1.setText(QCoreApplication.translate("AdvancedSettings", u"CheckBox", None))
    # retranslateUi

