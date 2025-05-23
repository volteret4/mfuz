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
    QHBoxLayout, QLabel, QLineEdit, QRadioButton,
    QScrollArea, QSizePolicy, QSlider, QSpinBox,
    QVBoxLayout, QWidget)
import rc_images

class Ui_AdvancedSettings(object):
    def setupUi(self, AdvancedSettings):
        if not AdvancedSettings.objectName():
            AdvancedSettings.setObjectName(u"AdvancedSettings")
        AdvancedSettings.resize(1179, 952)
        AdvancedSettings.setMinimumSize(QSize(400, 300))
        AdvancedSettings.setStyleSheet(u"")
        self.horizontalLayout_12 = QHBoxLayout(AdvancedSettings)
        self.horizontalLayout_12.setSpacing(16)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.horizontalLayout_12.setContentsMargins(9, 9, 9, 9)
        self.add_sett_frame = QFrame(AdvancedSettings)
        self.add_sett_frame.setObjectName(u"add_sett_frame")
        self.add_sett_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.add_sett_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.add_sett_frame.setLineWidth(0)
        self.verticalLayout_2 = QVBoxLayout(self.add_sett_frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(self.add_sett_frame)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 1159, 902))
        self.verticalLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.widget_4 = QWidget(self.scrollAreaWidgetContents)
        self.widget_4.setObjectName(u"widget_4")
        self.verticalLayout_11 = QVBoxLayout(self.widget_4)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.num_servicios = QGroupBox(self.widget_4)
        self.num_servicios.setObjectName(u"num_servicios")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.num_servicios.sizePolicy().hasHeightForWidth())
        self.num_servicios.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(self.num_servicios)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.urlplaylist_only_local = QCheckBox(self.num_servicios)
        self.urlplaylist_only_local.setObjectName(u"urlplaylist_only_local")

        self.horizontalLayout.addWidget(self.urlplaylist_only_local)

        self.num_servicios_label = QLabel(self.num_servicios)
        self.num_servicios_label.setObjectName(u"num_servicios_label")

        self.horizontalLayout.addWidget(self.num_servicios_label)

        self.num_servicios_spinBox = QSpinBox(self.num_servicios)
        self.num_servicios_spinBox.setObjectName(u"num_servicios_spinBox")
        self.num_servicios_spinBox.setMinimum(5)
        self.num_servicios_spinBox.setMaximum(50)

        self.horizontalLayout.addWidget(self.num_servicios_spinBox)

        self.label = QLabel(self.num_servicios)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.tipo_combo = QComboBox(self.num_servicios)
        self.tipo_combo.addItem("")
        self.tipo_combo.addItem("")
        self.tipo_combo.addItem("")
        self.tipo_combo.addItem("")
        self.tipo_combo.setObjectName(u"tipo_combo")

        self.horizontalLayout.addWidget(self.tipo_combo)


        self.verticalLayout_11.addWidget(self.num_servicios)

        self.servicios_en_todos = QGroupBox(self.widget_4)
        self.servicios_en_todos.setObjectName(u"servicios_en_todos")
        sizePolicy.setHeightForWidth(self.servicios_en_todos.sizePolicy().hasHeightForWidth())
        self.servicios_en_todos.setSizePolicy(sizePolicy)
        self.verticalLayout_5 = QVBoxLayout(self.servicios_en_todos)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.frame_3 = QFrame(self.servicios_en_todos)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.serv_todos_label = QLabel(self.frame_3)
        self.serv_todos_label.setObjectName(u"serv_todos_label")

        self.horizontalLayout_3.addWidget(self.serv_todos_label)


        self.verticalLayout_5.addWidget(self.frame_3)

        self.frame = QFrame(self.servicios_en_todos)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.servicios_musica = QGroupBox(self.frame)
        self.servicios_musica.setObjectName(u"servicios_musica")
        self.verticalLayout_6 = QVBoxLayout(self.servicios_musica)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.lastfm_check = QCheckBox(self.servicios_musica)
        self.lastfm_check.setObjectName(u"lastfm_check")
        icon = QIcon()
        icon.addFile(u":/services/lastfm", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.lastfm_check.setIcon(icon)

        self.verticalLayout_6.addWidget(self.lastfm_check)

        self.bandcamp_check = QCheckBox(self.servicios_musica)
        self.bandcamp_check.setObjectName(u"bandcamp_check")
        icon1 = QIcon()
        icon1.addFile(u":/services/bandcamp", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.bandcamp_check.setIcon(icon1)

        self.verticalLayout_6.addWidget(self.bandcamp_check)

        self.soundcloud_check = QCheckBox(self.servicios_musica)
        self.soundcloud_check.setObjectName(u"soundcloud_check")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.soundcloud_check.sizePolicy().hasHeightForWidth())
        self.soundcloud_check.setSizePolicy(sizePolicy1)
        icon2 = QIcon()
        icon2.addFile(u":/services/soundcloud", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.soundcloud_check.setIcon(icon2)

        self.verticalLayout_6.addWidget(self.soundcloud_check)

        self.youtube_check = QCheckBox(self.servicios_musica)
        self.youtube_check.setObjectName(u"youtube_check")
        icon3 = QIcon()
        icon3.addFile(u":/services/youtube", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.youtube_check.setIcon(icon3)

        self.verticalLayout_6.addWidget(self.youtube_check)

        self.spotify_check = QCheckBox(self.servicios_musica)
        self.spotify_check.setObjectName(u"spotify_check")
        icon4 = QIcon()
        icon4.addFile(u":/services/spotify", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.spotify_check.setIcon(icon4)

        self.verticalLayout_6.addWidget(self.spotify_check)


        self.horizontalLayout_4.addWidget(self.servicios_musica)

        self.servicios_info = QGroupBox(self.frame)
        self.servicios_info.setObjectName(u"servicios_info")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.servicios_info.sizePolicy().hasHeightForWidth())
        self.servicios_info.setSizePolicy(sizePolicy2)
        self.verticalLayout_3 = QVBoxLayout(self.servicios_info)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.wikipedia_check = QCheckBox(self.servicios_info)
        self.wikipedia_check.setObjectName(u"wikipedia_check")
        icon5 = QIcon()
        icon5.addFile(u":/services/wiki", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.wikipedia_check.setIcon(icon5)

        self.verticalLayout_3.addWidget(self.wikipedia_check)

        self.discogs_check = QCheckBox(self.servicios_info)
        self.discogs_check.setObjectName(u"discogs_check")
        icon6 = QIcon()
        icon6.addFile(u":/services/discogs", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.discogs_check.setIcon(icon6)

        self.verticalLayout_3.addWidget(self.discogs_check)

        self.checkBox = QCheckBox(self.servicios_info)
        self.checkBox.setObjectName(u"checkBox")
        icon7 = QIcon()
        icon7.addFile(u":/services/mb", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.checkBox.setIcon(icon7)

        self.verticalLayout_3.addWidget(self.checkBox)


        self.horizontalLayout_4.addWidget(self.servicios_info)


        self.verticalLayout_5.addWidget(self.frame)


        self.verticalLayout_11.addWidget(self.servicios_en_todos)

        self.apariencia_playlists = QGroupBox(self.widget_4)
        self.apariencia_playlists.setObjectName(u"apariencia_playlists")
        sizePolicy.setHeightForWidth(self.apariencia_playlists.sizePolicy().hasHeightForWidth())
        self.apariencia_playlists.setSizePolicy(sizePolicy)
        self.horizontalLayout_5 = QHBoxLayout(self.apariencia_playlists)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, -1, 0, 0)
        self.radio_buttons = QFrame(self.apariencia_playlists)
        self.radio_buttons.setObjectName(u"radio_buttons")
        self.radio_buttons.setFrameShape(QFrame.Shape.StyledPanel)
        self.radio_buttons.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_7 = QVBoxLayout(self.radio_buttons)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.radio_buttons)
        self.label_2.setObjectName(u"label_2")
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)

        self.verticalLayout_7.addWidget(self.label_2)

        self.pl_unidas = QRadioButton(self.radio_buttons)
        self.pl_unidas.setObjectName(u"pl_unidas")

        self.verticalLayout_7.addWidget(self.pl_unidas)

        self.pl_separadas = QRadioButton(self.radio_buttons)
        self.pl_separadas.setObjectName(u"pl_separadas")

        self.verticalLayout_7.addWidget(self.pl_separadas)


        self.horizontalLayout_5.addWidget(self.radio_buttons)

        self.check_boxes = QFrame(self.apariencia_playlists)
        self.check_boxes.setObjectName(u"check_boxes")
        self.check_boxes.setFrameShape(QFrame.Shape.StyledPanel)
        self.check_boxes.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_8 = QVBoxLayout(self.check_boxes)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.check_boxes)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout_8.addWidget(self.label_3)

        self.blogs_checkbox = QCheckBox(self.check_boxes)
        self.blogs_checkbox.setObjectName(u"blogs_checkbox")
        icon8 = QIcon()
        icon8.addFile(u":/services/rss", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.blogs_checkbox.setIcon(icon8)

        self.verticalLayout_8.addWidget(self.blogs_checkbox)

        self.locale_checkbox = QCheckBox(self.check_boxes)
        self.locale_checkbox.setObjectName(u"locale_checkbox")
        icon9 = QIcon()
        icon9.addFile(u":/services/plslove", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.locale_checkbox.setIcon(icon9)

        self.verticalLayout_8.addWidget(self.locale_checkbox)

        self.sp_checkbox = QCheckBox(self.check_boxes)
        self.sp_checkbox.setObjectName(u"sp_checkbox")
        self.sp_checkbox.setIcon(icon4)

        self.verticalLayout_8.addWidget(self.sp_checkbox)

        self.lastfm_checkbox = QCheckBox(self.check_boxes)
        self.lastfm_checkbox.setObjectName(u"lastfm_checkbox")
        self.lastfm_checkbox.setIcon(icon)

        self.verticalLayout_8.addWidget(self.lastfm_checkbox)


        self.horizontalLayout_5.addWidget(self.check_boxes)


        self.verticalLayout_11.addWidget(self.apariencia_playlists)

        self.rss = QGroupBox(self.widget_4)
        self.rss.setObjectName(u"rss")
        self.verticalLayout_4 = QVBoxLayout(self.rss)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget(self.rss)
        self.widget.setObjectName(u"widget")
        self.horizontalLayout_6 = QHBoxLayout(self.widget)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.agents = QWidget(self.widget)
        self.agents.setObjectName(u"agents")
        self.verticalLayout_9 = QVBoxLayout(self.agents)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.lastfm_agent = QRadioButton(self.agents)
        self.lastfm_agent.setObjectName(u"lastfm_agent")
        self.lastfm_agent.setIcon(icon)

        self.verticalLayout_9.addWidget(self.lastfm_agent)

        self.listenbrainz_agent = QRadioButton(self.agents)
        self.listenbrainz_agent.setObjectName(u"listenbrainz_agent")
        self.listenbrainz_agent.setIcon(icon7)

        self.verticalLayout_9.addWidget(self.listenbrainz_agent)


        self.horizontalLayout_6.addWidget(self.agents)

        self.mostrar_scrobbles = QWidget(self.widget)
        self.mostrar_scrobbles.setObjectName(u"mostrar_scrobbles")
        self.verticalLayout_10 = QVBoxLayout(self.mostrar_scrobbles)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.scrobbles_reproducciones = QRadioButton(self.mostrar_scrobbles)
        self.scrobbles_reproducciones.setObjectName(u"scrobbles_reproducciones")

        self.verticalLayout_10.addWidget(self.scrobbles_reproducciones)

        self.scrobbles_fecha = QRadioButton(self.mostrar_scrobbles)
        self.scrobbles_fecha.setObjectName(u"scrobbles_fecha")

        self.verticalLayout_10.addWidget(self.scrobbles_fecha)


        self.horizontalLayout_6.addWidget(self.mostrar_scrobbles)


        self.verticalLayout_4.addWidget(self.widget)

        self.usuario_widget = QWidget(self.rss)
        self.usuario_widget.setObjectName(u"usuario_widget")
        self.horizontalLayout_10 = QHBoxLayout(self.usuario_widget)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.usuario_label = QLabel(self.usuario_widget)
        self.usuario_label.setObjectName(u"usuario_label")

        self.horizontalLayout_10.addWidget(self.usuario_label)

        self.entrada_usuario = QLineEdit(self.usuario_widget)
        self.entrada_usuario.setObjectName(u"entrada_usuario")

        self.horizontalLayout_10.addWidget(self.entrada_usuario)


        self.verticalLayout_4.addWidget(self.usuario_widget)

        self.widget_3 = QWidget(self.rss)
        self.widget_3.setObjectName(u"widget_3")
        self.horizontalLayout_8 = QHBoxLayout(self.widget_3)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.prim_label = QLabel(self.widget_3)
        self.prim_label.setObjectName(u"prim_label")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.prim_label.sizePolicy().hasHeightForWidth())
        self.prim_label.setSizePolicy(sizePolicy3)

        self.horizontalLayout_8.addWidget(self.prim_label)

        self.combobox_1 = QComboBox(self.widget_3)
        self.combobox_1.addItem(icon1, "")
        self.combobox_1.addItem(icon2, "")
        self.combobox_1.addItem(icon4, "")
        self.combobox_1.addItem(icon3, "")
        self.combobox_1.setObjectName(u"combobox_1")

        self.horizontalLayout_8.addWidget(self.combobox_1)

        self.seg_label = QLabel(self.widget_3)
        self.seg_label.setObjectName(u"seg_label")
        sizePolicy3.setHeightForWidth(self.seg_label.sizePolicy().hasHeightForWidth())
        self.seg_label.setSizePolicy(sizePolicy3)

        self.horizontalLayout_8.addWidget(self.seg_label)

        self.comboBox_2 = QComboBox(self.widget_3)
        self.comboBox_2.addItem(icon1, "")
        self.comboBox_2.addItem(icon2, "")
        self.comboBox_2.addItem(icon4, "")
        self.comboBox_2.addItem(icon3, "")
        self.comboBox_2.setObjectName(u"comboBox_2")

        self.horizontalLayout_8.addWidget(self.comboBox_2)

        self.terc_label = QLabel(self.widget_3)
        self.terc_label.setObjectName(u"terc_label")
        sizePolicy3.setHeightForWidth(self.terc_label.sizePolicy().hasHeightForWidth())
        self.terc_label.setSizePolicy(sizePolicy3)

        self.horizontalLayout_8.addWidget(self.terc_label)

        self.comboBox_3 = QComboBox(self.widget_3)
        self.comboBox_3.addItem(icon1, "")
        self.comboBox_3.addItem(icon2, "")
        self.comboBox_3.addItem(icon4, "")
        self.comboBox_3.addItem(icon3, "")
        self.comboBox_3.setObjectName(u"comboBox_3")

        self.horizontalLayout_8.addWidget(self.comboBox_3)

        self.cuar_label = QLabel(self.widget_3)
        self.cuar_label.setObjectName(u"cuar_label")
        sizePolicy3.setHeightForWidth(self.cuar_label.sizePolicy().hasHeightForWidth())
        self.cuar_label.setSizePolicy(sizePolicy3)

        self.horizontalLayout_8.addWidget(self.cuar_label)

        self.comboBox_4 = QComboBox(self.widget_3)
        self.comboBox_4.addItem(icon1, "")
        self.comboBox_4.addItem(icon2, "")
        self.comboBox_4.addItem(icon4, "")
        self.comboBox_4.addItem(icon3, "")
        self.comboBox_4.setObjectName(u"comboBox_4")

        self.horizontalLayout_8.addWidget(self.comboBox_4)


        self.verticalLayout_4.addWidget(self.widget_3)

        self.widget_2 = QWidget(self.rss)
        self.widget_2.setObjectName(u"widget_2")
        self.horizontalLayout_7 = QHBoxLayout(self.widget_2)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.scrobbles_mostrados = QLabel(self.widget_2)
        self.scrobbles_mostrados.setObjectName(u"scrobbles_mostrados")

        self.horizontalLayout_7.addWidget(self.scrobbles_mostrados)

        self.scrobbles_slider = QSlider(self.widget_2)
        self.scrobbles_slider.setObjectName(u"scrobbles_slider")
        self.scrobbles_slider.setMinimum(25)
        self.scrobbles_slider.setMaximum(1000)
        self.scrobbles_slider.setSingleStep(10)
        self.scrobbles_slider.setPageStep(100)
        self.scrobbles_slider.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_7.addWidget(self.scrobbles_slider)

        self.scrobblers_spinBox = QSpinBox(self.widget_2)
        self.scrobblers_spinBox.setObjectName(u"scrobblers_spinBox")
        self.scrobblers_spinBox.setMaximum(10000)

        self.horizontalLayout_7.addWidget(self.scrobblers_spinBox)


        self.verticalLayout_4.addWidget(self.widget_2)


        self.verticalLayout_11.addWidget(self.rss)


        self.verticalLayout.addWidget(self.widget_4)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_2.addWidget(self.scrollArea)

        self.adv_sett_buttonBox = QDialogButtonBox(self.add_sett_frame)
        self.adv_sett_buttonBox.setObjectName(u"adv_sett_buttonBox")
        self.adv_sett_buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout_2.addWidget(self.adv_sett_buttonBox)


        self.horizontalLayout_12.addWidget(self.add_sett_frame)


        self.retranslateUi(AdvancedSettings)

        self.comboBox_2.setCurrentIndex(1)
        self.comboBox_3.setCurrentIndex(3)
        self.comboBox_4.setCurrentIndex(2)


        QMetaObject.connectSlotsByName(AdvancedSettings)
    # setupUi

    def retranslateUi(self, AdvancedSettings):
        AdvancedSettings.setWindowTitle(QCoreApplication.translate("AdvancedSettings", u"Filtrar \u00c1lbumes", None))
        self.num_servicios.setTitle("")
        self.urlplaylist_only_local.setText(QCoreApplication.translate("AdvancedSettings", u"Solo buscar en local", None))
        self.num_servicios_label.setText(QCoreApplication.translate("AdvancedSettings", u"N\u00famero de resultados por servicio:", None))
        self.label.setText(QCoreApplication.translate("AdvancedSettings", u"Elemento a buscar", None))
        self.tipo_combo.setItemText(0, QCoreApplication.translate("AdvancedSettings", u"Artista", None))
        self.tipo_combo.setItemText(1, QCoreApplication.translate("AdvancedSettings", u"\u00c1lbum", None))
        self.tipo_combo.setItemText(2, QCoreApplication.translate("AdvancedSettings", u"Canciones", None))
        self.tipo_combo.setItemText(3, QCoreApplication.translate("AdvancedSettings", u"Todo", None))

        self.servicios_en_todos.setTitle("")
        self.serv_todos_label.setText(QCoreApplication.translate("AdvancedSettings", u"Se\u00f1ala qu\u00e9 servicios deseas incluir cuando buscas en \"Todos\"", None))
        self.servicios_musica.setTitle("")
        self.lastfm_check.setText(QCoreApplication.translate("AdvancedSettings", u"l&astfm", None))
        self.bandcamp_check.setText(QCoreApplication.translate("AdvancedSettings", u"&bancamp", None))
        self.soundcloud_check.setText(QCoreApplication.translate("AdvancedSettings", u"soun&cloud", None))
        self.youtube_check.setText(QCoreApplication.translate("AdvancedSettings", u"&youtube", None))
        self.spotify_check.setText(QCoreApplication.translate("AdvancedSettings", u"sp&otify", None))
        self.servicios_info.setTitle("")
        self.wikipedia_check.setText(QCoreApplication.translate("AdvancedSettings", u"&Wikipedia", None))
        self.discogs_check.setText(QCoreApplication.translate("AdvancedSettings", u"&Discogs", None))
        self.checkBox.setText(QCoreApplication.translate("AdvancedSettings", u"&MusicBrainz", None))
        self.apariencia_playlists.setTitle("")
        self.label_2.setText(QCoreApplication.translate("AdvancedSettings", u"Apariencia de playlists", None))
        self.pl_unidas.setText(QCoreApplication.translate("AdvancedSettings", u"Listas de reproducci\u00f3n &unidas", None))
        self.pl_separadas.setText(QCoreApplication.translate("AdvancedSettings", u"Listas de reproducci\u00f3n por &separado", None))
        self.label_3.setText(QCoreApplication.translate("AdvancedSettings", u"Listas de reproducci\u00f3n visibles", None))
        self.blogs_checkbox.setText(QCoreApplication.translate("AdvancedSettings", u"Blo&gs", None))
        self.locale_checkbox.setText(QCoreApplication.translate("AdvancedSettings", u"&Locales", None))
        self.sp_checkbox.setText(QCoreApplication.translate("AdvancedSettings", u"&Spotify", None))
        self.lastfm_checkbox.setText(QCoreApplication.translate("AdvancedSettings", u"&Lastfm Scrobbles", None))
        self.rss.setTitle(QCoreApplication.translate("AdvancedSettings", u"Categorias aceptadas en el RSS", None))
        self.lastfm_agent.setText(QCoreApplication.translate("AdvancedSettings", u"Lastfm", None))
        self.listenbrainz_agent.setText(QCoreApplication.translate("AdvancedSettings", u"Listenbrainz", None))
        self.scrobbles_reproducciones.setText(QCoreApplication.translate("AdvancedSettings", u"Mostrar Scrobbles por &reproducciones (\u00fanicos)", None))
        self.scrobbles_fecha.setText(QCoreApplication.translate("AdvancedSettings", u"Mostrar scrobbles por &fecha", None))
        self.usuario_label.setText(QCoreApplication.translate("AdvancedSettings", u"Usuario Lastfm", None))
        self.entrada_usuario.setText("")
        self.prim_label.setText(QCoreApplication.translate("AdvancedSettings", u"1", None))
        self.combobox_1.setItemText(0, QCoreApplication.translate("AdvancedSettings", u"Bandcamp", None))
        self.combobox_1.setItemText(1, QCoreApplication.translate("AdvancedSettings", u"Soundcloud", None))
        self.combobox_1.setItemText(2, QCoreApplication.translate("AdvancedSettings", u"Spotify", None))
        self.combobox_1.setItemText(3, QCoreApplication.translate("AdvancedSettings", u"Youtube", None))

        self.seg_label.setText(QCoreApplication.translate("AdvancedSettings", u"2", None))
        self.comboBox_2.setItemText(0, QCoreApplication.translate("AdvancedSettings", u"Bandcamp", None))
        self.comboBox_2.setItemText(1, QCoreApplication.translate("AdvancedSettings", u"Soundcloud", None))
        self.comboBox_2.setItemText(2, QCoreApplication.translate("AdvancedSettings", u"Spotify", None))
        self.comboBox_2.setItemText(3, QCoreApplication.translate("AdvancedSettings", u"Youtube", None))

        self.terc_label.setText(QCoreApplication.translate("AdvancedSettings", u"3", None))
        self.comboBox_3.setItemText(0, QCoreApplication.translate("AdvancedSettings", u"Bandcamp", None))
        self.comboBox_3.setItemText(1, QCoreApplication.translate("AdvancedSettings", u"Soundcloud", None))
        self.comboBox_3.setItemText(2, QCoreApplication.translate("AdvancedSettings", u"Spotify", None))
        self.comboBox_3.setItemText(3, QCoreApplication.translate("AdvancedSettings", u"Youtube", None))

        self.cuar_label.setText(QCoreApplication.translate("AdvancedSettings", u"4", None))
        self.comboBox_4.setItemText(0, QCoreApplication.translate("AdvancedSettings", u"Bandcamp", None))
        self.comboBox_4.setItemText(1, QCoreApplication.translate("AdvancedSettings", u"Soundcloud", None))
        self.comboBox_4.setItemText(2, QCoreApplication.translate("AdvancedSettings", u"Spotify", None))
        self.comboBox_4.setItemText(3, QCoreApplication.translate("AdvancedSettings", u"Youtube", None))

        self.scrobbles_mostrados.setText(QCoreApplication.translate("AdvancedSettings", u"Scrobbles a mostrar", None))
    # retranslateUi

