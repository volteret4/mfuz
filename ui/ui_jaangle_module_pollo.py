# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'jaangle_module_pollo.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QHBoxLayout, QLabel, QSizePolicy, QSpacerItem,
    QSpinBox, QToolButton, QVBoxLayout, QWidget)

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
        self.widget = QWidget(MusicQuiz)
        self.widget.setObjectName(u"widget")
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.widget_2 = QWidget(self.widget)
        self.widget_2.setObjectName(u"widget_2")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_2.sizePolicy().hasHeightForWidth())
        self.widget_2.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(self.widget_2)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(self.widget_2)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.spinBox = QSpinBox(self.widget_2)
        self.spinBox.setObjectName(u"spinBox")

        self.horizontalLayout.addWidget(self.spinBox)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.comboBox = QComboBox(self.widget_2)
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")

        self.horizontalLayout.addWidget(self.comboBox)

        self.checkBox_2 = QCheckBox(self.widget_2)
        self.checkBox_2.setObjectName(u"checkBox_2")

        self.horizontalLayout.addWidget(self.checkBox_2)

        self.checkBox = QCheckBox(self.widget_2)
        self.checkBox.setObjectName(u"checkBox")

        self.horizontalLayout.addWidget(self.checkBox)

        self.checkBox_3 = QCheckBox(self.widget_2)
        self.checkBox_3.setObjectName(u"checkBox_3")

        self.horizontalLayout.addWidget(self.checkBox_3)

        self.checkBox_4 = QCheckBox(self.widget_2)
        self.checkBox_4.setObjectName(u"checkBox_4")

        self.horizontalLayout.addWidget(self.checkBox_4)

        self.toolButton = QToolButton(self.widget_2)
        self.toolButton.setObjectName(u"toolButton")

        self.horizontalLayout.addWidget(self.toolButton)


        self.verticalLayout.addWidget(self.widget_2)

        self.widget_4 = QWidget(self.widget)
        self.widget_4.setObjectName(u"widget_4")
        self.horizontalLayout_3 = QHBoxLayout(self.widget_4)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, -1, -1)
        self.widget_10 = QWidget(self.widget_4)
        self.widget_10.setObjectName(u"widget_10")
        self.horizontalLayout_10 = QHBoxLayout(self.widget_10)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.opcion_2 = QWidget(self.widget_10)
        self.opcion_2.setObjectName(u"opcion_2")
        self.horizontalLayout_11 = QHBoxLayout(self.opcion_2)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.portada_2 = QFrame(self.opcion_2)
        self.portada_2.setObjectName(u"portada_2")
        self.portada_2.setMinimumSize(QSize(200, 200))
        self.portada_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.portada_2.setFrameShadow(QFrame.Shadow.Raised)

        self.horizontalLayout_11.addWidget(self.portada_2)

        self.metadata_2 = QWidget(self.opcion_2)
        self.metadata_2.setObjectName(u"metadata_2")
        self.verticalLayout_3 = QVBoxLayout(self.metadata_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.widget_11 = QWidget(self.metadata_2)
        self.widget_11.setObjectName(u"widget_11")
        self.horizontalLayout_12 = QHBoxLayout(self.widget_11)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.cancion_1p_2 = QLabel(self.widget_11)
        self.cancion_1p_2.setObjectName(u"cancion_1p_2")

        self.horizontalLayout_12.addWidget(self.cancion_1p_2)

        self.cancion_2 = QLabel(self.widget_11)
        self.cancion_2.setObjectName(u"cancion_2")

        self.horizontalLayout_12.addWidget(self.cancion_2)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_12.addItem(self.horizontalSpacer_2)


        self.verticalLayout_3.addWidget(self.widget_11)

        self.widget_12 = QWidget(self.metadata_2)
        self.widget_12.setObjectName(u"widget_12")
        self.horizontalLayout_13 = QHBoxLayout(self.widget_12)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.album_1p_2 = QLabel(self.widget_12)
        self.album_1p_2.setObjectName(u"album_1p_2")

        self.horizontalLayout_13.addWidget(self.album_1p_2)

        self.album_2 = QLabel(self.widget_12)
        self.album_2.setObjectName(u"album_2")

        self.horizontalLayout_13.addWidget(self.album_2)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_13.addItem(self.horizontalSpacer_3)


        self.verticalLayout_3.addWidget(self.widget_12)

        self.widget_13 = QWidget(self.metadata_2)
        self.widget_13.setObjectName(u"widget_13")
        self.horizontalLayout_14 = QHBoxLayout(self.widget_13)
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.artista_1p_2 = QLabel(self.widget_13)
        self.artista_1p_2.setObjectName(u"artista_1p_2")

        self.horizontalLayout_14.addWidget(self.artista_1p_2)

        self.artista_2 = QLabel(self.widget_13)
        self.artista_2.setObjectName(u"artista_2")

        self.horizontalLayout_14.addWidget(self.artista_2)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_4)


        self.verticalLayout_3.addWidget(self.widget_13)

        self.widget_14 = QWidget(self.metadata_2)
        self.widget_14.setObjectName(u"widget_14")
        self.horizontalLayout_15 = QHBoxLayout(self.widget_14)
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.genero_1p_2 = QLabel(self.widget_14)
        self.genero_1p_2.setObjectName(u"genero_1p_2")

        self.horizontalLayout_15.addWidget(self.genero_1p_2)

        self.genero_2 = QLabel(self.widget_14)
        self.genero_2.setObjectName(u"genero_2")

        self.horizontalLayout_15.addWidget(self.genero_2)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_5)


        self.verticalLayout_3.addWidget(self.widget_14)

        self.widget_15 = QWidget(self.metadata_2)
        self.widget_15.setObjectName(u"widget_15")
        self.horizontalLayout_16 = QHBoxLayout(self.widget_15)
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.sello_2 = QLabel(self.widget_15)
        self.sello_2.setObjectName(u"sello_2")

        self.horizontalLayout_16.addWidget(self.sello_2)

        self.sello_1_p_2 = QLabel(self.widget_15)
        self.sello_1_p_2.setObjectName(u"sello_1_p_2")

        self.horizontalLayout_16.addWidget(self.sello_1_p_2)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_16.addItem(self.horizontalSpacer_6)


        self.verticalLayout_3.addWidget(self.widget_15)


        self.horizontalLayout_11.addWidget(self.metadata_2)


        self.horizontalLayout_10.addWidget(self.opcion_2)


        self.horizontalLayout_3.addWidget(self.widget_10)

        self.opcion_1 = QWidget(self.widget_4)
        self.opcion_1.setObjectName(u"opcion_1")
        self.horizontalLayout_4 = QHBoxLayout(self.opcion_1)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, -1, -1)
        self.portada_1 = QFrame(self.opcion_1)
        self.portada_1.setObjectName(u"portada_1")
        self.portada_1.setMinimumSize(QSize(200, 200))
        self.portada_1.setFrameShape(QFrame.Shape.StyledPanel)
        self.portada_1.setFrameShadow(QFrame.Shadow.Raised)

        self.horizontalLayout_4.addWidget(self.portada_1)

        self.metadata_1 = QWidget(self.opcion_1)
        self.metadata_1.setObjectName(u"metadata_1")
        self.verticalLayout_2 = QVBoxLayout(self.metadata_1)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, -1, -1)
        self.widget_5 = QWidget(self.metadata_1)
        self.widget_5.setObjectName(u"widget_5")
        self.horizontalLayout_5 = QHBoxLayout(self.widget_5)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, -1, 0)
        self.cancion_1p = QLabel(self.widget_5)
        self.cancion_1p.setObjectName(u"cancion_1p")

        self.horizontalLayout_5.addWidget(self.cancion_1p)

        self.cancion_1 = QLabel(self.widget_5)
        self.cancion_1.setObjectName(u"cancion_1")

        self.horizontalLayout_5.addWidget(self.cancion_1)

        self.horizontalSpacer_13 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_13)


        self.verticalLayout_2.addWidget(self.widget_5)

        self.widget_6 = QWidget(self.metadata_1)
        self.widget_6.setObjectName(u"widget_6")
        self.horizontalLayout_6 = QHBoxLayout(self.widget_6)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, -1, 0)
        self.album_1p = QLabel(self.widget_6)
        self.album_1p.setObjectName(u"album_1p")

        self.horizontalLayout_6.addWidget(self.album_1p)

        self.album_1 = QLabel(self.widget_6)
        self.album_1.setObjectName(u"album_1")

        self.horizontalLayout_6.addWidget(self.album_1)

        self.horizontalSpacer_12 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer_12)


        self.verticalLayout_2.addWidget(self.widget_6)

        self.widget_7 = QWidget(self.metadata_1)
        self.widget_7.setObjectName(u"widget_7")
        self.horizontalLayout_7 = QHBoxLayout(self.widget_7)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(0, 0, -1, 0)
        self.artista_1p = QLabel(self.widget_7)
        self.artista_1p.setObjectName(u"artista_1p")

        self.horizontalLayout_7.addWidget(self.artista_1p)

        self.artista_1 = QLabel(self.widget_7)
        self.artista_1.setObjectName(u"artista_1")

        self.horizontalLayout_7.addWidget(self.artista_1)

        self.horizontalSpacer_9 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_9)


        self.verticalLayout_2.addWidget(self.widget_7)

        self.widget_8 = QWidget(self.metadata_1)
        self.widget_8.setObjectName(u"widget_8")
        self.horizontalLayout_8 = QHBoxLayout(self.widget_8)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, -1, 0)
        self.genero_1p = QLabel(self.widget_8)
        self.genero_1p.setObjectName(u"genero_1p")

        self.horizontalLayout_8.addWidget(self.genero_1p)

        self.genero_1 = QLabel(self.widget_8)
        self.genero_1.setObjectName(u"genero_1")

        self.horizontalLayout_8.addWidget(self.genero_1)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_8)


        self.verticalLayout_2.addWidget(self.widget_8)

        self.widget_9 = QWidget(self.metadata_1)
        self.widget_9.setObjectName(u"widget_9")
        self.horizontalLayout_9 = QHBoxLayout(self.widget_9)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(0, 0, -1, 0)
        self.sello_1 = QLabel(self.widget_9)
        self.sello_1.setObjectName(u"sello_1")

        self.horizontalLayout_9.addWidget(self.sello_1)

        self.sello_1_p = QLabel(self.widget_9)
        self.sello_1_p.setObjectName(u"sello_1_p")

        self.horizontalLayout_9.addWidget(self.sello_1_p)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_7)


        self.verticalLayout_2.addWidget(self.widget_9)


        self.horizontalLayout_4.addWidget(self.metadata_1)


        self.horizontalLayout_3.addWidget(self.opcion_1)


        self.verticalLayout.addWidget(self.widget_4)

        self.widget_3 = QWidget(self.widget)
        self.widget_3.setObjectName(u"widget_3")
        sizePolicy.setHeightForWidth(self.widget_3.sizePolicy().hasHeightForWidth())
        self.widget_3.setSizePolicy(sizePolicy)
        self.horizontalLayout_2 = QHBoxLayout(self.widget_3)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_4 = QLabel(self.widget_3)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_2.addWidget(self.label_4)

        self.label_3 = QLabel(self.widget_3)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_2.addWidget(self.label_3)

        self.label_2 = QLabel(self.widget_3)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_2.addWidget(self.label_2)


        self.verticalLayout.addWidget(self.widget_3)


        self.main_layout.addWidget(self.widget)


        self.retranslateUi(MusicQuiz)

        QMetaObject.connectSlotsByName(MusicQuiz)
    # setupUi

    def retranslateUi(self, MusicQuiz):
        MusicQuiz.setWindowTitle(QCoreApplication.translate("MusicQuiz", u"Music Quiz", None))
        self.label.setText(QCoreApplication.translate("MusicQuiz", u"Tiempo", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("MusicQuiz", u"2", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("MusicQuiz", u"4", None))
        self.comboBox.setItemText(2, QCoreApplication.translate("MusicQuiz", u"6", None))
        self.comboBox.setItemText(3, QCoreApplication.translate("MusicQuiz", u"8", None))

        self.checkBox_2.setText(QCoreApplication.translate("MusicQuiz", u"Artistas", None))
        self.checkBox.setText(QCoreApplication.translate("MusicQuiz", u"\u00c1lbums", None))
        self.checkBox_3.setText(QCoreApplication.translate("MusicQuiz", u"G\u00e9nero", None))
        self.checkBox_4.setText(QCoreApplication.translate("MusicQuiz", u"Sello", None))
        self.toolButton.setText(QCoreApplication.translate("MusicQuiz", u"...", None))
        self.cancion_1p_2.setText(QCoreApplication.translate("MusicQuiz", u"Canci\u00f3n", None))
        self.cancion_2.setText(QCoreApplication.translate("MusicQuiz", u"placeholder", None))
        self.album_1p_2.setText(QCoreApplication.translate("MusicQuiz", u"\u00c1lbum", None))
        self.album_2.setText(QCoreApplication.translate("MusicQuiz", u"TextLabel", None))
        self.artista_1p_2.setText(QCoreApplication.translate("MusicQuiz", u"Artista", None))
        self.artista_2.setText(QCoreApplication.translate("MusicQuiz", u"TextLabel", None))
        self.genero_1p_2.setText(QCoreApplication.translate("MusicQuiz", u"G\u00e9nero", None))
        self.genero_2.setText(QCoreApplication.translate("MusicQuiz", u"TextLabel", None))
        self.sello_2.setText(QCoreApplication.translate("MusicQuiz", u"Sello", None))
        self.sello_1_p_2.setText(QCoreApplication.translate("MusicQuiz", u"TextLabel", None))
        self.cancion_1p.setText(QCoreApplication.translate("MusicQuiz", u"Canci\u00f3n", None))
        self.cancion_1.setText(QCoreApplication.translate("MusicQuiz", u"placeholder", None))
        self.album_1p.setText(QCoreApplication.translate("MusicQuiz", u"\u00c1lbum", None))
        self.album_1.setText(QCoreApplication.translate("MusicQuiz", u"TextLabel", None))
        self.artista_1p.setText(QCoreApplication.translate("MusicQuiz", u"Artista", None))
        self.artista_1.setText(QCoreApplication.translate("MusicQuiz", u"TextLabel", None))
        self.genero_1p.setText(QCoreApplication.translate("MusicQuiz", u"G\u00e9nero", None))
        self.genero_1.setText(QCoreApplication.translate("MusicQuiz", u"TextLabel", None))
        self.sello_1.setText(QCoreApplication.translate("MusicQuiz", u"Sello", None))
        self.sello_1_p.setText(QCoreApplication.translate("MusicQuiz", u"TextLabel", None))
        self.label_4.setText(QCoreApplication.translate("MusicQuiz", u"TextLabel", None))
        self.label_3.setText(QCoreApplication.translate("MusicQuiz", u"TextLabel", None))
        self.label_2.setText(QCoreApplication.translate("MusicQuiz", u"TextLabel", None))
    # retranslateUi

