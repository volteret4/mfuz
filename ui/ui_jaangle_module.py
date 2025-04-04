# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'jaangle_module.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_MusicQuiz(object):
    def setupUi(self, MusicQuiz):
        if not MusicQuiz.objectName():
            MusicQuiz.setObjectName(u"MusicQuiz")
        MusicQuiz.resize(800, 600)
        self.main_layout = QVBoxLayout(MusicQuiz)
        self.main_layout.setSpacing(20)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.scroll_area = QScrollArea(MusicQuiz)
        self.scroll_area.setObjectName(u"scroll_area")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName(u"scroll_content")
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

        self.filter_layout.addWidget(self.filter_artists_btn, 0, 0, 1, 1)

        self.filter_albums_btn = QPushButton(self.config_group)
        self.filter_albums_btn.setObjectName(u"filter_albums_btn")

        self.filter_layout.addWidget(self.filter_albums_btn, 0, 1, 1, 1)

        self.filter_folders_btn = QPushButton(self.config_group)
        self.filter_folders_btn.setObjectName(u"filter_folders_btn")

        self.filter_layout.addWidget(self.filter_folders_btn, 1, 0, 1, 1)

        self.filter_genres_btn = QPushButton(self.config_group)
        self.filter_genres_btn.setObjectName(u"filter_genres_btn")

        self.filter_layout.addWidget(self.filter_genres_btn, 1, 1, 1, 1)

        self.session_filters_btn = QPushButton(self.config_group)
        self.session_filters_btn.setObjectName(u"session_filters_btn")

        self.filter_layout.addWidget(self.session_filters_btn, 2, 0, 1, 1)

        self.clear_session_btn = QPushButton(self.config_group)
        self.clear_session_btn.setObjectName(u"clear_session_btn")

        self.filter_layout.addWidget(self.clear_session_btn, 2, 1, 1, 1)

        self.filter_sellos_btn = QPushButton(self.config_group)
        self.filter_sellos_btn.setObjectName(u"filter_sellos_btn")

        self.filter_layout.addWidget(self.filter_sellos_btn, 3, 0, 1, 1)


        self.config_layout.addLayout(self.filter_layout, 3, 0, 1, 2)


        self.scroll_layout.addWidget(self.config_group)

        self.timer_layout = QHBoxLayout()
        self.timer_layout.setObjectName(u"timer_layout")
        self.countdown_label = QLabel(self.scroll_content)
        self.countdown_label.setObjectName(u"countdown_label")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(18)
        font.setBold(True)
        self.countdown_label.setFont(font)

        self.timer_layout.addWidget(self.countdown_label)

        self.progress_bar = QProgressBar(self.scroll_content)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(100)

        self.timer_layout.addWidget(self.progress_bar)

        self.toggle_button = QPushButton(self.scroll_content)
        self.toggle_button.setObjectName(u"toggle_button")

        self.timer_layout.addWidget(self.toggle_button)

        self.config_button = QPushButton(self.scroll_content)
        self.config_button.setObjectName(u"config_button")
        self.config_button.setFixedWidth(40)

        self.timer_layout.addWidget(self.config_button)


        self.scroll_layout.addLayout(self.timer_layout)

        self.options_container = QWidget(self.scroll_content)
        self.options_container.setObjectName(u"options_container")
        self.options_grid = QGridLayout(self.options_container)
        self.options_grid.setObjectName(u"options_grid")
        self.options_grid.setContentsMargins(0, 0, 0, 0)

        self.scroll_layout.addWidget(self.options_container)

        self.stats_layout = QHBoxLayout()
        self.stats_layout.setObjectName(u"stats_layout")
        self.score_label = QLabel(self.scroll_content)
        self.score_label.setObjectName(u"score_label")
        self.score_label.setFixedHeight(20)

        self.stats_layout.addWidget(self.score_label)

        self.total_label = QLabel(self.scroll_content)
        self.total_label.setObjectName(u"total_label")
        self.total_label.setFixedHeight(20)

        self.stats_layout.addWidget(self.total_label)

        self.accuracy_label = QLabel(self.scroll_content)
        self.accuracy_label.setObjectName(u"accuracy_label")
        self.accuracy_label.setFixedHeight(20)

        self.stats_layout.addWidget(self.accuracy_label)


        self.scroll_layout.addLayout(self.stats_layout)

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
        self.filter_artists_btn.setStyleSheet(QCoreApplication.translate("MusicQuiz", u"QPushButton {\n"
"    border: none;\n"
"    padding: 5px;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgba(255, 0, 0, 0.2);\n"
"}", None))
        self.filter_albums_btn.setText(QCoreApplication.translate("MusicQuiz", u"Filtrar \u00c1lbumes", None))
        self.filter_albums_btn.setStyleSheet(QCoreApplication.translate("MusicQuiz", u"QPushButton {\n"
"    border: none;\n"
"    padding: 5px;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgba(255, 0, 0, 0.2);\n"
"}", None))
        self.filter_folders_btn.setText(QCoreApplication.translate("MusicQuiz", u"Filtrar Carpetas", None))
        self.filter_folders_btn.setStyleSheet(QCoreApplication.translate("MusicQuiz", u"QPushButton {\n"
"    border: none;\n"
"    padding: 5px;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgba(255, 0, 0, 0.2);\n"
"}", None))
        self.filter_genres_btn.setText(QCoreApplication.translate("MusicQuiz", u"Filtrar G\u00e9neros", None))
        self.filter_genres_btn.setStyleSheet(QCoreApplication.translate("MusicQuiz", u"QPushButton {\n"
"    border: none;\n"
"    padding: 5px;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgba(255, 0, 0, 0.2);\n"
"}", None))
        self.session_filters_btn.setText(QCoreApplication.translate("MusicQuiz", u"Filtros de Sesi\u00f3n \u2b50", None))
        self.clear_session_btn.setText(QCoreApplication.translate("MusicQuiz", u"Limpiar Filtros Sesi\u00f3n", None))
        self.filter_sellos_btn.setText(QCoreApplication.translate("MusicQuiz", u"Filtrar Sellos", None))
        self.countdown_label.setText(QCoreApplication.translate("MusicQuiz", u"30", None))
        self.progress_bar.setStyleSheet(QCoreApplication.translate("MusicQuiz", u"QProgressBar { border: none; background-color: transparent; }", None))
        self.toggle_button.setText(QCoreApplication.translate("MusicQuiz", u"Iniciar Quiz", None))
        self.config_button.setText(QCoreApplication.translate("MusicQuiz", u"\u2699\ufe0f", None))
        self.score_label.setText(QCoreApplication.translate("MusicQuiz", u"Aciertos: 0", None))
        self.total_label.setText(QCoreApplication.translate("MusicQuiz", u"Total: 0", None))
        self.accuracy_label.setText(QCoreApplication.translate("MusicQuiz", u"Precisi\u00f3n: 0%", None))
    # retranslateUi

