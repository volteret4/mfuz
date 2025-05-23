# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'jaangle_module.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_MusicQuiz(object):
    def setupUi(self, MusicQuiz):
        if not MusicQuiz.objectName():
            MusicQuiz.setObjectName(u"MusicQuiz")
        MusicQuiz.resize(800, 600)
        MusicQuiz.setStyleSheet(u"/* Estilo general */\n"
"QWidget {\n"
"    font-family: 'Segoe UI', Arial, sans-serif;\n"
"    font-size: 10pt;\n"
"}\n"
"\n"
"/* Botones */\n"
"QPushButton {\n"
"    background-color: #607D8B;\n"
"    color: white;\n"
"    border: none;\n"
"    border-radius: 4px;\n"
"    padding: 6px 12px;\n"
"    font-weight: bold;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #78909C;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #546E7A;\n"
"}\n"
"\n"
"/* Botones de acci\u00f3n (Iniciar/Detener) */\n"
"#toggle_button {\n"
"    background-color: #4CAF50;\n"
"    padding: 8px 16px;\n"
"    font-size: 11pt;\n"
"}\n"
"\n"
"#toggle_button:hover {\n"
"    background-color: #66BB6A;\n"
"}\n"
"\n"
"#toggle_button:pressed {\n"
"    background-color: #43A047;\n"
"}\n"
"\n"
"/* Bot\u00f3n de configuraci\u00f3n */\n"
"#config_button {\n"
"    background-color: #607D8B;\n"
"    border-radius: 20px;\n"
"    font-size: 16px;\n"
"}\n"
"\n"
"/* GroupBox */\n"
"QGroupBox {\n"
"    border: 1px solid #E0E0E0;\n"
""
                        "    border-radius: 6px;\n"
"    margin-top: 12px;\n"
"    background-color: rgba(236, 239, 241, 0.5);\n"
"}\n"
"\n"
"QGroupBox::title {\n"
"    subcontrol-origin: margin;\n"
"    subcontrol-position: top left;\n"
"    background-color: transparent;\n"
"    padding: 0 5px;\n"
"    color: #37474F;\n"
"}\n"
"\n"
"/* ProgressBar */\n"
"QProgressBar {\n"
"    border: none;\n"
"    border-radius: 3px;\n"
"    text-align: center;\n"
"    background-color: #E0E0E0;\n"
"}\n"
"\n"
"QProgressBar::chunk {\n"
"    background-color: #4CAF50;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"/* ComboBox */\n"
"QComboBox {\n"
"    border: 1px solid #E0E0E0;\n"
"    border-radius: 4px;\n"
"    padding: 5px;\n"
"    background-color: #F5F5F5;\n"
"}\n"
"\n"
"QComboBox:hover, QComboBox:focus {\n"
"    border: 1px solid #78909C;\n"
"    background-color: #FFFFFF;\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    border: none;\n"
"    border-left: 1px solid #E0E0E0;\n"
"    width: 20px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12"
                        "px;\n"
"    height: 12px;\n"
"}\n"
"\n"
"/* Labels */\n"
"QLabel {\n"
"    color: #455A64;\n"
"}\n"
"\n"
"#countdown_label {\n"
"    color: #607D8B;\n"
"    font-weight: bold;\n"
"    font-size: 18pt;\n"
"}\n"
"\n"
"/* Scroll Area */\n"
"QScrollArea {\n"
"    border: none;\n"
"    background-color: transparent;\n"
"}\n"
"\n"
"/* Botones de Filtro */\n"
"QPushButton[filter_button=true] {\n"
"    background-color: transparent;\n"
"    color: #607D8B;\n"
"    border: 1px solid #B0BEC5;\n"
"    border-radius: 4px;\n"
"    padding: 6px;\n"
"    font-weight: normal;\n"
"}\n"
"\n"
"QPushButton[filter_button=true]:hover {\n"
"    background-color: rgba(96, 125, 139, 0.1);\n"
"    border-color: #607D8B;\n"
"}\n"
"\n"
"/* Contenedor de opciones */\n"
"#options_container {\n"
"    background-color: transparent;\n"
"}")
        self.main_layout = QVBoxLayout(MusicQuiz)
        self.main_layout.setSpacing(20)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.scroll_area = QScrollArea(MusicQuiz)
        self.scroll_area.setObjectName(u"scroll_area")
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName(u"scroll_content")
        self.scroll_content.setGeometry(QRect(0, 0, 760, 560))
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(20)
        self.scroll_layout.setObjectName(u"scroll_layout")
        self.config_group = QGroupBox(self.scroll_content)
        self.config_group.setObjectName(u"config_group")
        self.config_group.setVisible(False)
        self.config_layout = QGridLayout(self.config_group)
        self.config_layout.setObjectName(u"config_layout")
        self.quiz_duration_label = QLabel(self.config_group)
        self.quiz_duration_label.setObjectName(u"quiz_duration_label")

        self.config_layout.addWidget(self.quiz_duration_label, 0, 0, 1, 1)

        self.quiz_duration_combo = QComboBox(self.config_group)
        self.quiz_duration_combo.addItem("")
        self.quiz_duration_combo.addItem("")
        self.quiz_duration_combo.addItem("")
        self.quiz_duration_combo.addItem("")
        self.quiz_duration_combo.setObjectName(u"quiz_duration_combo")

        self.config_layout.addWidget(self.quiz_duration_combo, 0, 1, 1, 1)

        self.song_duration_label = QLabel(self.config_group)
        self.song_duration_label.setObjectName(u"song_duration_label")

        self.config_layout.addWidget(self.song_duration_label, 1, 0, 1, 1)

        self.song_duration_combo = QComboBox(self.config_group)
        self.song_duration_combo.addItem("")
        self.song_duration_combo.addItem("")
        self.song_duration_combo.addItem("")
        self.song_duration_combo.addItem("")
        self.song_duration_combo.addItem("")
        self.song_duration_combo.setObjectName(u"song_duration_combo")

        self.config_layout.addWidget(self.song_duration_combo, 1, 1, 1, 1)

        self.pause_duration_label = QLabel(self.config_group)
        self.pause_duration_label.setObjectName(u"pause_duration_label")

        self.config_layout.addWidget(self.pause_duration_label, 2, 0, 1, 1)

        self.pause_duration_combo = QComboBox(self.config_group)
        self.pause_duration_combo.addItem("")
        self.pause_duration_combo.addItem("")
        self.pause_duration_combo.addItem("")
        self.pause_duration_combo.addItem("")
        self.pause_duration_combo.addItem("")
        self.pause_duration_combo.addItem("")
        self.pause_duration_combo.setObjectName(u"pause_duration_combo")

        self.config_layout.addWidget(self.pause_duration_combo, 2, 1, 1, 1)

        self.options_count_label = QLabel(self.config_group)
        self.options_count_label.setObjectName(u"options_count_label")

        self.config_layout.addWidget(self.options_count_label, 3, 0, 1, 1)

        self.options_count_combo = QComboBox(self.config_group)
        self.options_count_combo.addItem("")
        self.options_count_combo.addItem("")
        self.options_count_combo.addItem("")
        self.options_count_combo.addItem("")
        self.options_count_combo.setObjectName(u"options_count_combo")

        self.config_layout.addWidget(self.options_count_combo, 3, 1, 1, 1)

        self.filter_layout = QGridLayout()
        self.filter_layout.setObjectName(u"filter_layout")
        self.filter_artists_btn = QPushButton(self.config_group)
        self.filter_artists_btn.setObjectName(u"filter_artists_btn")
        icon = QIcon()
        icon.addFile(u"icons/artist.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.filter_artists_btn.setIcon(icon)
        self.filter_artists_btn.setProperty(u"filter_button", True)

        self.filter_layout.addWidget(self.filter_artists_btn, 0, 0, 1, 1)

        self.filter_albums_btn = QPushButton(self.config_group)
        self.filter_albums_btn.setObjectName(u"filter_albums_btn")
        icon1 = QIcon()
        icon1.addFile(u"icons/album.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.filter_albums_btn.setIcon(icon1)
        self.filter_albums_btn.setProperty(u"filter_button", True)

        self.filter_layout.addWidget(self.filter_albums_btn, 0, 1, 1, 1)

        self.filter_folders_btn = QPushButton(self.config_group)
        self.filter_folders_btn.setObjectName(u"filter_folders_btn")
        icon2 = QIcon()
        icon2.addFile(u"icons/folder.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.filter_folders_btn.setIcon(icon2)
        self.filter_folders_btn.setProperty(u"filter_button", True)

        self.filter_layout.addWidget(self.filter_folders_btn, 1, 0, 1, 1)

        self.filter_genres_btn = QPushButton(self.config_group)
        self.filter_genres_btn.setObjectName(u"filter_genres_btn")
        icon3 = QIcon()
        icon3.addFile(u"icons/genre.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.filter_genres_btn.setIcon(icon3)
        self.filter_genres_btn.setProperty(u"filter_button", True)

        self.filter_layout.addWidget(self.filter_genres_btn, 1, 1, 1, 1)

        self.session_filters_btn = QPushButton(self.config_group)
        self.session_filters_btn.setObjectName(u"session_filters_btn")
        icon4 = QIcon()
        icon4.addFile(u"icons/session.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.session_filters_btn.setIcon(icon4)
        self.session_filters_btn.setProperty(u"filter_button", True)

        self.filter_layout.addWidget(self.session_filters_btn, 2, 0, 1, 1)

        self.clear_session_btn = QPushButton(self.config_group)
        self.clear_session_btn.setObjectName(u"clear_session_btn")
        icon5 = QIcon()
        icon5.addFile(u"icons/clear.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.clear_session_btn.setIcon(icon5)
        self.clear_session_btn.setProperty(u"filter_button", True)

        self.filter_layout.addWidget(self.clear_session_btn, 2, 1, 1, 1)

        self.filter_sellos_btn = QPushButton(self.config_group)
        self.filter_sellos_btn.setObjectName(u"filter_sellos_btn")
        icon6 = QIcon()
        icon6.addFile(u"icons/label.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.filter_sellos_btn.setIcon(icon6)
        self.filter_sellos_btn.setProperty(u"filter_button", True)

        self.filter_layout.addWidget(self.filter_sellos_btn, 3, 0, 1, 1)


        self.config_layout.addLayout(self.filter_layout, 4, 0, 1, 2)


        self.scroll_layout.addWidget(self.config_group)

        self.widget = QWidget(self.scroll_content)
        self.widget.setObjectName(u"widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.timer_layout = QHBoxLayout(self.widget)
        self.timer_layout.setObjectName(u"timer_layout")
        self.countdown_label = QLabel(self.widget)
        self.countdown_label.setObjectName(u"countdown_label")
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setPointSize(18)
        font.setBold(True)
        self.countdown_label.setFont(font)
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.timer_layout.addWidget(self.countdown_label)

        self.progress_bar = QProgressBar(self.widget)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(100)

        self.timer_layout.addWidget(self.progress_bar)

        self.action_toggle = QPushButton(self.widget)
        self.action_toggle.setObjectName(u"action_toggle")

        self.timer_layout.addWidget(self.action_toggle)

        self.config_button = QPushButton(self.widget)
        self.config_button.setObjectName(u"config_button")
        self.config_button.setProperty(u"fixedWidth", 40)

        self.timer_layout.addWidget(self.config_button)


        self.scroll_layout.addWidget(self.widget)

        self.options_container = QWidget(self.scroll_content)
        self.options_container.setObjectName(u"options_container")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.options_container.sizePolicy().hasHeightForWidth())
        self.options_container.setSizePolicy(sizePolicy1)
        self.options_grid = QGridLayout(self.options_container)
        self.options_grid.setObjectName(u"options_grid")
        self.options_grid.setContentsMargins(1, 1, 1, 1)

        self.scroll_layout.addWidget(self.options_container)

        self.widget1 = QWidget(self.scroll_content)
        self.widget1.setObjectName(u"widget1")
        sizePolicy.setHeightForWidth(self.widget1.sizePolicy().hasHeightForWidth())
        self.widget1.setSizePolicy(sizePolicy)
        self.stats_layout = QHBoxLayout(self.widget1)
        self.stats_layout.setObjectName(u"stats_layout")
        self.score_label = QLabel(self.widget1)
        self.score_label.setObjectName(u"score_label")
        self.score_label.setProperty(u"fixedHeight", 20)

        self.stats_layout.addWidget(self.score_label)

        self.total_label = QLabel(self.widget1)
        self.total_label.setObjectName(u"total_label")
        self.total_label.setProperty(u"fixedHeight", 20)

        self.stats_layout.addWidget(self.total_label)

        self.accuracy_label = QLabel(self.widget1)
        self.accuracy_label.setObjectName(u"accuracy_label")
        self.accuracy_label.setProperty(u"fixedHeight", 20)

        self.stats_layout.addWidget(self.accuracy_label)


        self.scroll_layout.addWidget(self.widget1)

        self.scroll_area.setWidget(self.scroll_content)

        self.main_layout.addWidget(self.scroll_area)


        self.retranslateUi(MusicQuiz)

        self.options_count_combo.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(MusicQuiz)
    # setupUi

    def retranslateUi(self, MusicQuiz):
        MusicQuiz.setWindowTitle(QCoreApplication.translate("MusicQuiz", u"Music Quiz", None))
        self.config_group.setTitle(QCoreApplication.translate("MusicQuiz", u"Configuraci\u00f3n", None))
        self.quiz_duration_label.setText(QCoreApplication.translate("MusicQuiz", u"Duraci\u00f3n del quiz:", None))
        self.quiz_duration_combo.setItemText(0, QCoreApplication.translate("MusicQuiz", u"1 min", None))
        self.quiz_duration_combo.setItemText(1, QCoreApplication.translate("MusicQuiz", u"3 min", None))
        self.quiz_duration_combo.setItemText(2, QCoreApplication.translate("MusicQuiz", u"5 min", None))
        self.quiz_duration_combo.setItemText(3, QCoreApplication.translate("MusicQuiz", u"10 min", None))

        self.song_duration_label.setText(QCoreApplication.translate("MusicQuiz", u"Tiempo por canci\u00f3n:", None))
        self.song_duration_combo.setItemText(0, QCoreApplication.translate("MusicQuiz", u"5 seg", None))
        self.song_duration_combo.setItemText(1, QCoreApplication.translate("MusicQuiz", u"10 seg", None))
        self.song_duration_combo.setItemText(2, QCoreApplication.translate("MusicQuiz", u"20 seg", None))
        self.song_duration_combo.setItemText(3, QCoreApplication.translate("MusicQuiz", u"30 seg", None))
        self.song_duration_combo.setItemText(4, QCoreApplication.translate("MusicQuiz", u"60 seg", None))

        self.pause_duration_label.setText(QCoreApplication.translate("MusicQuiz", u"Pausa entre canciones:", None))
        self.pause_duration_combo.setItemText(0, QCoreApplication.translate("MusicQuiz", u"0 seg", None))
        self.pause_duration_combo.setItemText(1, QCoreApplication.translate("MusicQuiz", u"1 seg", None))
        self.pause_duration_combo.setItemText(2, QCoreApplication.translate("MusicQuiz", u"2 seg", None))
        self.pause_duration_combo.setItemText(3, QCoreApplication.translate("MusicQuiz", u"3 seg", None))
        self.pause_duration_combo.setItemText(4, QCoreApplication.translate("MusicQuiz", u"5 seg", None))
        self.pause_duration_combo.setItemText(5, QCoreApplication.translate("MusicQuiz", u"10 seg", None))

        self.options_count_label.setText(QCoreApplication.translate("MusicQuiz", u"N\u00famero de opciones:", None))
        self.options_count_combo.setItemText(0, QCoreApplication.translate("MusicQuiz", u"2", None))
        self.options_count_combo.setItemText(1, QCoreApplication.translate("MusicQuiz", u"4", None))
        self.options_count_combo.setItemText(2, QCoreApplication.translate("MusicQuiz", u"6", None))
        self.options_count_combo.setItemText(3, QCoreApplication.translate("MusicQuiz", u"8", None))

        self.filter_artists_btn.setText(QCoreApplication.translate("MusicQuiz", u"Filtrar Artistas", None))
        self.filter_albums_btn.setText(QCoreApplication.translate("MusicQuiz", u"Filtrar \u00c1lbumes", None))
        self.filter_folders_btn.setText(QCoreApplication.translate("MusicQuiz", u"Filtrar Carpetas", None))
        self.filter_genres_btn.setText(QCoreApplication.translate("MusicQuiz", u"Filtrar G\u00e9neros", None))
        self.session_filters_btn.setText(QCoreApplication.translate("MusicQuiz", u"Filtros de Sesi\u00f3n \u2b50", None))
        self.clear_session_btn.setText(QCoreApplication.translate("MusicQuiz", u"Limpiar Filtros Sesi\u00f3n", None))
        self.filter_sellos_btn.setText(QCoreApplication.translate("MusicQuiz", u"Filtrar Sellos", None))
        self.countdown_label.setText(QCoreApplication.translate("MusicQuiz", u"30", None))
        self.action_toggle.setText(QCoreApplication.translate("MusicQuiz", u"Iniciar Quiz", None))
        self.config_button.setText(QCoreApplication.translate("MusicQuiz", u"\u2699\ufe0f", None))
        self.score_label.setText(QCoreApplication.translate("MusicQuiz", u"Aciertos: 0", None))
        self.total_label.setText(QCoreApplication.translate("MusicQuiz", u"Total: 0", None))
        self.accuracy_label.setText(QCoreApplication.translate("MusicQuiz", u"Precisi\u00f3n: 0%", None))
    # retranslateUi

