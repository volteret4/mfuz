# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'db_creator_base.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QStackedWidget, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget)
import rc_images

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(914, 704)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.panel_widget = QWidget(Form)
        self.panel_widget.setObjectName(u"panel_widget")
        self.verticalLayout_2 = QVBoxLayout(self.panel_widget)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.stackedWidget = QStackedWidget(self.panel_widget)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.A_db_path = QWidget()
        self.A_db_path.setObjectName(u"A_db_path")
        self.verticalLayout_3 = QVBoxLayout(self.A_db_path)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.titulo_widget = QWidget(self.A_db_path)
        self.titulo_widget.setObjectName(u"titulo_widget")
        self.horizontalLayout_3 = QHBoxLayout(self.titulo_widget)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.titulo_label = QLabel(self.titulo_widget)
        self.titulo_label.setObjectName(u"titulo_label")
        font = QFont()
        font.setFamilies([u"Roboto Mono Thin [GOOG]"])
        font.setPointSize(12)
        self.titulo_label.setFont(font)

        self.horizontalLayout_3.addWidget(self.titulo_label)


        self.verticalLayout_3.addWidget(self.titulo_widget)

        self.rutaSelector_widget = QWidget(self.A_db_path)
        self.rutaSelector_widget.setObjectName(u"rutaSelector_widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.rutaSelector_widget.sizePolicy().hasHeightForWidth())
        self.rutaSelector_widget.setSizePolicy(sizePolicy)
        self.horizontalLayout_2 = QHBoxLayout(self.rutaSelector_widget)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.rutaSelector_label = QLabel(self.rutaSelector_widget)
        self.rutaSelector_label.setObjectName(u"rutaSelector_label")
        font1 = QFont()
        font1.setPointSize(11)
        self.rutaSelector_label.setFont(font1)

        self.horizontalLayout_2.addWidget(self.rutaSelector_label)

        self.rutaSelector_line = QLineEdit(self.rutaSelector_widget)
        self.rutaSelector_line.setObjectName(u"rutaSelector_line")
        self.rutaSelector_line.setMinimumSize(QSize(0, 30))

        self.horizontalLayout_2.addWidget(self.rutaSelector_line)

        self.music_browse_button = QPushButton(self.rutaSelector_widget)
        self.music_browse_button.setObjectName(u"music_browse_button")
        icon = QIcon()
        icon.addFile(u":/services/folder", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.music_browse_button.setIcon(icon)
        self.music_browse_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_2.addWidget(self.music_browse_button)


        self.verticalLayout_3.addWidget(self.rutaSelector_widget)

        self.rutaSelector_widget_2 = QWidget(self.A_db_path)
        self.rutaSelector_widget_2.setObjectName(u"rutaSelector_widget_2")
        sizePolicy.setHeightForWidth(self.rutaSelector_widget_2.sizePolicy().hasHeightForWidth())
        self.rutaSelector_widget_2.setSizePolicy(sizePolicy)
        self.horizontalLayout_4 = QHBoxLayout(self.rutaSelector_widget_2)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.db_path_label = QLabel(self.rutaSelector_widget_2)
        self.db_path_label.setObjectName(u"db_path_label")
        self.db_path_label.setFont(font1)

        self.horizontalLayout_4.addWidget(self.db_path_label)

        self.db_path_line = QLineEdit(self.rutaSelector_widget_2)
        self.db_path_line.setObjectName(u"db_path_line")
        self.db_path_line.setMinimumSize(QSize(0, 30))

        self.horizontalLayout_4.addWidget(self.db_path_line)

        self.db_path_button = QPushButton(self.rutaSelector_widget_2)
        self.db_path_button.setObjectName(u"db_path_button")
        self.db_path_button.setIcon(icon)
        self.db_path_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_4.addWidget(self.db_path_button)


        self.verticalLayout_3.addWidget(self.rutaSelector_widget_2)

        self.opciones = QGroupBox(self.A_db_path)
        self.opciones.setObjectName(u"opciones")
        self.gridLayout = QGridLayout(self.opciones)
        self.gridLayout.setObjectName(u"gridLayout")
        self.checkbox_optimize = QCheckBox(self.opciones)
        self.checkbox_optimize.setObjectName(u"checkbox_optimize")

        self.gridLayout.addWidget(self.checkbox_optimize, 1, 1, 1, 1)

        self.checkbox_update_schema = QCheckBox(self.opciones)
        self.checkbox_update_schema.setObjectName(u"checkbox_update_schema")

        self.gridLayout.addWidget(self.checkbox_update_schema, 1, 0, 1, 1)

        self.checkbox_update_bitrates = QCheckBox(self.opciones)
        self.checkbox_update_bitrates.setObjectName(u"checkbox_update_bitrates")

        self.gridLayout.addWidget(self.checkbox_update_bitrates, 2, 0, 1, 1)

        self.checkbox_quick_scan = QCheckBox(self.opciones)
        self.checkbox_quick_scan.setObjectName(u"checkbox_quick_scan")

        self.gridLayout.addWidget(self.checkbox_quick_scan, 2, 1, 1, 1)

        self.checkbox_force_update = QCheckBox(self.opciones)
        self.checkbox_force_update.setObjectName(u"checkbox_force_update")

        self.gridLayout.addWidget(self.checkbox_force_update, 0, 0, 1, 1)

        self.checkbox_update_replay_gain = QCheckBox(self.opciones)
        self.checkbox_update_replay_gain.setObjectName(u"checkbox_update_replay_gain")

        self.gridLayout.addWidget(self.checkbox_update_replay_gain, 0, 1, 1, 1)

        self.stats_folders_label = QLabel(self.opciones)
        self.stats_folders_label.setObjectName(u"stats_folders_label")

        self.gridLayout.addWidget(self.stats_folders_label, 0, 2, 1, 1)

        self.stats_files_label = QLabel(self.opciones)
        self.stats_files_label.setObjectName(u"stats_files_label")

        self.gridLayout.addWidget(self.stats_files_label, 1, 2, 1, 1)

        self.stats_size_label = QLabel(self.opciones)
        self.stats_size_label.setObjectName(u"stats_size_label")

        self.gridLayout.addWidget(self.stats_size_label, 2, 2, 1, 1)


        self.verticalLayout_3.addWidget(self.opciones)

        self.widget_8 = QWidget(self.A_db_path)
        self.widget_8.setObjectName(u"widget_8")
        self.horizontalLayout_13 = QHBoxLayout(self.widget_8)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.run_button = QPushButton(self.widget_8)
        self.run_button.setObjectName(u"run_button")

        self.horizontalLayout_13.addWidget(self.run_button)

        self.create_db_button = QPushButton(self.widget_8)
        self.create_db_button.setObjectName(u"create_db_button")

        self.horizontalLayout_13.addWidget(self.create_db_button)

        self.create_db_button_2 = QPushButton(self.widget_8)
        self.create_db_button_2.setObjectName(u"create_db_button_2")

        self.horizontalLayout_13.addWidget(self.create_db_button_2)


        self.verticalLayout_3.addWidget(self.widget_8)

        self.stackedWidget.addWidget(self.A_db_path)
        self.B_scrobbles = QWidget()
        self.B_scrobbles.setObjectName(u"B_scrobbles")
        self.verticalLayout_6 = QVBoxLayout(self.B_scrobbles)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.titulo_lastfm_widget = QWidget(self.B_scrobbles)
        self.titulo_lastfm_widget.setObjectName(u"titulo_lastfm_widget")
        self.titulo_lastfm_widget.setMinimumSize(QSize(0, 20))
        self.titulo_lastfm_widget.setMaximumSize(QSize(16777215, 40))
        self.horizontalLayout_5 = QHBoxLayout(self.titulo_lastfm_widget)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.titulo_lastfm_widget_2 = QLabel(self.titulo_lastfm_widget)
        self.titulo_lastfm_widget_2.setObjectName(u"titulo_lastfm_widget_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.titulo_lastfm_widget_2.sizePolicy().hasHeightForWidth())
        self.titulo_lastfm_widget_2.setSizePolicy(sizePolicy1)
        font2 = QFont()
        font2.setPointSize(12)
        self.titulo_lastfm_widget_2.setFont(font2)

        self.horizontalLayout_5.addWidget(self.titulo_lastfm_widget_2)


        self.verticalLayout_6.addWidget(self.titulo_lastfm_widget)

        self.widget_3 = QWidget(self.B_scrobbles)
        self.widget_3.setObjectName(u"widget_3")
        sizePolicy1.setHeightForWidth(self.widget_3.sizePolicy().hasHeightForWidth())
        self.widget_3.setSizePolicy(sizePolicy1)
        self.formLayout = QFormLayout(self.widget_3)
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setContentsMargins(0, 0, 0, 0)
        self.lastfm_user_label = QLabel(self.widget_3)
        self.lastfm_user_label.setObjectName(u"lastfm_user_label")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lastfm_user_label)

        self.lastfm_user_line = QLineEdit(self.widget_3)
        self.lastfm_user_line.setObjectName(u"lastfm_user_line")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.lastfm_user_line)

        self.lastfm_apikey_label = QLabel(self.widget_3)
        self.lastfm_apikey_label.setObjectName(u"lastfm_apikey_label")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lastfm_apikey_label)

        self.lastfm_apikey_line = QLineEdit(self.widget_3)
        self.lastfm_apikey_line.setObjectName(u"lastfm_apikey_line")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.lastfm_apikey_line)

        self.verificar_apikey_button = QPushButton(self.widget_3)
        self.verificar_apikey_button.setObjectName(u"verificar_apikey_button")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.verificar_apikey_button)


        self.verticalLayout_6.addWidget(self.widget_3)

        self.tabWidget = QTabWidget(self.B_scrobbles)
        self.tabWidget.setObjectName(u"tabWidget")
        self.escuchas_tab = QWidget()
        self.escuchas_tab.setObjectName(u"escuchas_tab")
        sizePolicy.setHeightForWidth(self.escuchas_tab.sizePolicy().hasHeightForWidth())
        self.escuchas_tab.setSizePolicy(sizePolicy)
        self.verticalLayout_7 = QVBoxLayout(self.escuchas_tab)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.widget_4 = QWidget(self.escuchas_tab)
        self.widget_4.setObjectName(u"widget_4")
        self.horizontalLayout_6 = QHBoxLayout(self.widget_4)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.add_items_check = QCheckBox(self.widget_4)
        self.add_items_check.setObjectName(u"add_items_check")

        self.horizontalLayout_6.addWidget(self.add_items_check)

        self.complete_relationships_check = QCheckBox(self.widget_4)
        self.complete_relationships_check.setObjectName(u"complete_relationships_check")

        self.horizontalLayout_6.addWidget(self.complete_relationships_check)

        self.force_update_check = QCheckBox(self.widget_4)
        self.force_update_check.setObjectName(u"force_update_check")

        self.horizontalLayout_6.addWidget(self.force_update_check)


        self.verticalLayout_7.addWidget(self.widget_4)

        self.output_json_widget = QWidget(self.escuchas_tab)
        self.output_json_widget.setObjectName(u"output_json_widget")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.output_json_widget.sizePolicy().hasHeightForWidth())
        self.output_json_widget.setSizePolicy(sizePolicy2)
        self.horizontalLayout_7 = QHBoxLayout(self.output_json_widget)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(0, 0, -1, 0)
        self.output_json_label = QLabel(self.output_json_widget)
        self.output_json_label.setObjectName(u"output_json_label")
        self.output_json_label.setMinimumSize(QSize(0, 28))

        self.horizontalLayout_7.addWidget(self.output_json_label)

        self.output_json_line = QLineEdit(self.output_json_widget)
        self.output_json_line.setObjectName(u"output_json_line")
        self.output_json_line.setMinimumSize(QSize(0, 28))

        self.horizontalLayout_7.addWidget(self.output_json_line)

        self.output_json_button = QPushButton(self.output_json_widget)
        self.output_json_button.setObjectName(u"output_json_button")
        self.output_json_button.setMaximumSize(QSize(32, 32))
        self.output_json_button.setIcon(icon)
        self.output_json_button.setIconSize(QSize(30, 30))
        self.output_json_button.setFlat(True)

        self.horizontalLayout_7.addWidget(self.output_json_button)


        self.verticalLayout_7.addWidget(self.output_json_widget)

        self.widget_9 = QWidget(self.escuchas_tab)
        self.widget_9.setObjectName(u"widget_9")
        self.horizontalLayout_14 = QHBoxLayout(self.widget_9)
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.horizontalLayout_14.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_4 = QSpacerItem(373, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_4)

        self.ejecutar_escuchas_button = QPushButton(self.widget_9)
        self.ejecutar_escuchas_button.setObjectName(u"ejecutar_escuchas_button")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.ejecutar_escuchas_button.sizePolicy().hasHeightForWidth())
        self.ejecutar_escuchas_button.setSizePolicy(sizePolicy3)

        self.horizontalLayout_14.addWidget(self.ejecutar_escuchas_button)

        self.horizontalSpacer_3 = QSpacerItem(372, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_3)


        self.verticalLayout_7.addWidget(self.widget_9)

        self.tabWidget.addTab(self.escuchas_tab, "")
        self.info_tab = QWidget()
        self.info_tab.setObjectName(u"info_tab")
        self.verticalLayout_8 = QVBoxLayout(self.info_tab)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.widget_5 = QWidget(self.info_tab)
        self.widget_5.setObjectName(u"widget_5")
        self.horizontalLayout_9 = QHBoxLayout(self.widget_5)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.info_add_items_check = QCheckBox(self.widget_5)
        self.info_add_items_check.setObjectName(u"info_add_items_check")

        self.horizontalLayout_9.addWidget(self.info_add_items_check)

        self.info_complete_relationships_check = QCheckBox(self.widget_5)
        self.info_complete_relationships_check.setObjectName(u"info_complete_relationships_check")

        self.horizontalLayout_9.addWidget(self.info_complete_relationships_check)

        self.info_force_update_check = QCheckBox(self.widget_5)
        self.info_force_update_check.setObjectName(u"info_force_update_check")

        self.horizontalLayout_9.addWidget(self.info_force_update_check)


        self.verticalLayout_8.addWidget(self.widget_5)

        self.widget_6 = QWidget(self.info_tab)
        self.widget_6.setObjectName(u"widget_6")
        self.horizontalLayout_8 = QHBoxLayout(self.widget_6)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.info_output_json_label = QLabel(self.widget_6)
        self.info_output_json_label.setObjectName(u"info_output_json_label")
        self.info_output_json_label.setMinimumSize(QSize(0, 28))

        self.horizontalLayout_8.addWidget(self.info_output_json_label)

        self.info_output_json_line = QLineEdit(self.widget_6)
        self.info_output_json_line.setObjectName(u"info_output_json_line")
        self.info_output_json_line.setMinimumSize(QSize(0, 28))

        self.horizontalLayout_8.addWidget(self.info_output_json_line)

        self.info_output_json_button = QPushButton(self.widget_6)
        self.info_output_json_button.setObjectName(u"info_output_json_button")
        self.info_output_json_button.setIcon(icon)
        self.info_output_json_button.setIconSize(QSize(28, 28))
        self.info_output_json_button.setFlat(True)

        self.horizontalLayout_8.addWidget(self.info_output_json_button)


        self.verticalLayout_8.addWidget(self.widget_6)

        self.widget_10 = QWidget(self.info_tab)
        self.widget_10.setObjectName(u"widget_10")
        self.horizontalLayout_15 = QHBoxLayout(self.widget_10)
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_6)

        self.ejecutar_info_button = QPushButton(self.widget_10)
        self.ejecutar_info_button.setObjectName(u"ejecutar_info_button")
        sizePolicy3.setHeightForWidth(self.ejecutar_info_button.sizePolicy().hasHeightForWidth())
        self.ejecutar_info_button.setSizePolicy(sizePolicy3)

        self.horizontalLayout_15.addWidget(self.ejecutar_info_button)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_5)


        self.verticalLayout_8.addWidget(self.widget_10)

        self.tabWidget.addTab(self.info_tab, "")

        self.verticalLayout_6.addWidget(self.tabWidget)

        self.widget_7 = QWidget(self.B_scrobbles)
        self.widget_7.setObjectName(u"widget_7")
        self.verticalLayout_9 = QVBoxLayout(self.widget_7)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.lastfm_stats_widget = QWidget(self.widget_7)
        self.lastfm_stats_widget.setObjectName(u"lastfm_stats_widget")
        self.horizontalLayout_10 = QHBoxLayout(self.lastfm_stats_widget)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.scrobbles_guardados_label = QLabel(self.lastfm_stats_widget)
        self.scrobbles_guardados_label.setObjectName(u"scrobbles_guardados_label")

        self.horizontalLayout_10.addWidget(self.scrobbles_guardados_label)

        self.scrobbles_guardados_value = QLabel(self.lastfm_stats_widget)
        self.scrobbles_guardados_value.setObjectName(u"scrobbles_guardados_value")

        self.horizontalLayout_10.addWidget(self.scrobbles_guardados_value)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_10.addItem(self.horizontalSpacer)

        self.scrobbles_unicos_label = QLabel(self.lastfm_stats_widget)
        self.scrobbles_unicos_label.setObjectName(u"scrobbles_unicos_label")

        self.horizontalLayout_10.addWidget(self.scrobbles_unicos_label)

        self.scrobbles_unicos_value = QLabel(self.lastfm_stats_widget)
        self.scrobbles_unicos_value.setObjectName(u"scrobbles_unicos_value")

        self.horizontalLayout_10.addWidget(self.scrobbles_unicos_value)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_10.addItem(self.horizontalSpacer_2)

        self.scrobbles_totales_label = QLabel(self.lastfm_stats_widget)
        self.scrobbles_totales_label.setObjectName(u"scrobbles_totales_label")

        self.horizontalLayout_10.addWidget(self.scrobbles_totales_label)

        self.scrobbles_totales_value = QLabel(self.lastfm_stats_widget)
        self.scrobbles_totales_value.setObjectName(u"scrobbles_totales_value")

        self.horizontalLayout_10.addWidget(self.scrobbles_totales_value)


        self.verticalLayout_9.addWidget(self.lastfm_stats_widget)

        self.lastfm_actions_widget = QWidget(self.widget_7)
        self.lastfm_actions_widget.setObjectName(u"lastfm_actions_widget")
        self.horizontalLayout_11 = QHBoxLayout(self.lastfm_actions_widget)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_9.addWidget(self.lastfm_actions_widget)


        self.verticalLayout_6.addWidget(self.widget_7)

        self.stackedWidget.addWidget(self.B_scrobbles)

        self.verticalLayout_2.addWidget(self.stackedWidget)


        self.verticalLayout.addWidget(self.panel_widget)

        self.progress_widget = QWidget(Form)
        self.progress_widget.setObjectName(u"progress_widget")
        self.verticalLayout_5 = QVBoxLayout(self.progress_widget)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.widget_2 = QWidget(self.progress_widget)
        self.widget_2.setObjectName(u"widget_2")
        self.horizontalLayout_12 = QHBoxLayout(self.widget_2)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.horizontalLayout_12.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_5.addWidget(self.widget_2)

        self.scrollArea_output_text = QScrollArea(self.progress_widget)
        self.scrollArea_output_text.setObjectName(u"scrollArea_output_text")
        self.scrollArea_output_text.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 894, 269))
        self.verticalLayout_10 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.output_text = QTextEdit(self.scrollAreaWidgetContents)
        self.output_text.setObjectName(u"output_text")

        self.verticalLayout_10.addWidget(self.output_text)

        self.scrollArea_output_text.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_5.addWidget(self.scrollArea_output_text)

        self.widget = QWidget(self.progress_widget)
        self.widget.setObjectName(u"widget")
        sizePolicy1.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy1)
        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.anterior_button = QPushButton(self.widget)
        self.anterior_button.setObjectName(u"anterior_button")
        self.anterior_button.setMaximumSize(QSize(32, 32))
        icon1 = QIcon()
        icon1.addFile(u":/services/b_prev", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.anterior_button.setIcon(icon1)
        self.anterior_button.setIconSize(QSize(30, 30))
        self.anterior_button.setFlat(True)

        self.horizontalLayout.addWidget(self.anterior_button)

        self.progressBar = QProgressBar(self.widget)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setMinimumSize(QSize(0, 30))
        self.progressBar.setValue(24)

        self.horizontalLayout.addWidget(self.progressBar)

        self.siguiente_button = QPushButton(self.widget)
        self.siguiente_button.setObjectName(u"siguiente_button")
        self.siguiente_button.setMaximumSize(QSize(32, 32))
        icon2 = QIcon()
        icon2.addFile(u":/services/b_ff", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.siguiente_button.setIcon(icon2)
        self.siguiente_button.setIconSize(QSize(30, 30))
        self.siguiente_button.setFlat(True)

        self.horizontalLayout.addWidget(self.siguiente_button)


        self.verticalLayout_5.addWidget(self.widget)


        self.verticalLayout.addWidget(self.progress_widget)


        self.retranslateUi(Form)

        self.stackedWidget.setCurrentIndex(0)
        self.tabWidget.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.titulo_label.setText(QCoreApplication.translate("Form", u"Creaci\u00f3n de la base de datos", None))
        self.rutaSelector_label.setText(QCoreApplication.translate("Form", u"Introduce la ruta a tu m\u00fasica", None))
        self.music_browse_button.setText("")
        self.db_path_label.setText(QCoreApplication.translate("Form", u"Introduce la ruta para la db", None))
        self.db_path_button.setText("")
        self.opciones.setTitle(QCoreApplication.translate("Form", u"Opciones", None))
        self.checkbox_optimize.setText(QCoreApplication.translate("Form", u"Optimizar", None))
        self.checkbox_update_schema.setText(QCoreApplication.translate("Form", u"Actualizar esquema", None))
        self.checkbox_update_bitrates.setText(QCoreApplication.translate("Form", u"Actualizar bitrates", None))
        self.checkbox_quick_scan.setText(QCoreApplication.translate("Form", u"Escaneo r\u00e1pido", None))
        self.checkbox_force_update.setText(QCoreApplication.translate("Form", u"Force update", None))
        self.checkbox_update_replay_gain.setText(QCoreApplication.translate("Form", u"Actualizar Replaygain", None))
        self.stats_folders_label.setText("")
        self.stats_files_label.setText("")
        self.stats_size_label.setText("")
        self.run_button.setText(QCoreApplication.translate("Form", u"Analizar carpeta", None))
        self.create_db_button.setText(QCoreApplication.translate("Form", u"Crear db", None))
        self.create_db_button_2.setText(QCoreApplication.translate("Form", u"Guardar configuraci\u00f3n", None))
        self.titulo_lastfm_widget_2.setText(QCoreApplication.translate("Form", u"Scrobbles", None))
        self.lastfm_user_label.setText(QCoreApplication.translate("Form", u"Lastfm usuario", None))
        self.lastfm_apikey_label.setText(QCoreApplication.translate("Form", u"Lastfm api key", None))
        self.verificar_apikey_button.setText(QCoreApplication.translate("Form", u"Verificar API Key", None))
        self.add_items_check.setText(QCoreApplication.translate("Form", u"A\u00f1adir elementos a base de datos", None))
        self.complete_relationships_check.setText(QCoreApplication.translate("Form", u"Completar informaci\u00f3n", None))
        self.force_update_check.setText(QCoreApplication.translate("Form", u"Forzar actualizaci\u00f3n (sobreescribe)", None))
        self.output_json_label.setText(QCoreApplication.translate("Form", u"JSON Output", None))
        self.output_json_button.setText("")
        self.ejecutar_escuchas_button.setText(QCoreApplication.translate("Form", u"Obtener Escuchas", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.escuchas_tab), QCoreApplication.translate("Form", u"Escuchas", None))
        self.info_add_items_check.setText(QCoreApplication.translate("Form", u"A\u00f1adir", None))
        self.info_complete_relationships_check.setText(QCoreApplication.translate("Form", u"info", None))
        self.info_force_update_check.setText(QCoreApplication.translate("Form", u"Forzar actualizaci\u00f3n", None))
        self.info_output_json_label.setText(QCoreApplication.translate("Form", u"TextLabel", None))
        self.info_output_json_button.setText("")
        self.ejecutar_info_button.setText(QCoreApplication.translate("Form", u"Obtener Info Artistas/\u00c1lbumes", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.info_tab), QCoreApplication.translate("Form", u"Info", None))
        self.scrobbles_guardados_label.setText(QCoreApplication.translate("Form", u"Scrobbles guardados:", None))
        self.scrobbles_guardados_value.setText(QCoreApplication.translate("Form", u"0", None))
        self.scrobbles_unicos_label.setText(QCoreApplication.translate("Form", u"Scrobbles \u00fanicos:", None))
        self.scrobbles_unicos_value.setText(QCoreApplication.translate("Form", u"0", None))
        self.scrobbles_totales_label.setText(QCoreApplication.translate("Form", u"Scrobbles totales:", None))
        self.scrobbles_totales_value.setText(QCoreApplication.translate("Form", u"0", None))
        self.anterior_button.setText("")
        self.siguiente_button.setText("")
    # retranslateUi

