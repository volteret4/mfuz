# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'music_fuzzy_advanced_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QGroupBox, QHBoxLayout, QPushButton, QRadioButton,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget)
import rc_images

class Ui_AdvancedSettings(object):
    def setupUi(self, AdvancedSettings):
        if not AdvancedSettings.objectName():
            AdvancedSettings.setObjectName(u"AdvancedSettings")
        AdvancedSettings.resize(931, 188)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(AdvancedSettings.sizePolicy().hasHeightForWidth())
        AdvancedSettings.setSizePolicy(sizePolicy)
        AdvancedSettings.setStyleSheet(u"QSpinBox, QComboBox {\n"
"  border: 1px solid rgba(65, 72, 104, 0.5);\n"
"  border-radius: 3px;\n"
"  padding: 3px;\n"
"  background-color: rgba(36, 40, 59, 0.6);\n"
"}\n"
"QSpinBox::up-button, QSpinBox::down-button {\n"
"  width: 16px;\n"
"  border-left: 1px solid rgba(65, 72, 104, 0.5);\n"
"}\n"
"QPushButton {\n"
"  background-color: rgba(61, 89, 161, 0.8);\n"
"  color: white;\n"
"  border-radius: 3px;\n"
"  padding: 5px;\n"
"}\n"
"QPushButton:hover {\n"
"  background-color: rgba(77, 105, 177, 0.9);\n"
"}")
        self.time_filters_layout = QHBoxLayout(AdvancedSettings)
        self.time_filters_layout.setSpacing(8)
        self.time_filters_layout.setObjectName(u"time_filters_layout")
        self.time_filters_layout.setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget(AdvancedSettings)
        self.widget.setObjectName(u"widget")
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.fechas_widget = QWidget(self.widget)
        self.fechas_widget.setObjectName(u"fechas_widget")
        self.horizontalLayout_2 = QHBoxLayout(self.fechas_widget)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.time_unit_groupBox = QGroupBox(self.fechas_widget)
        self.time_unit_groupBox.setObjectName(u"time_unit_groupBox")
        sizePolicy.setHeightForWidth(self.time_unit_groupBox.sizePolicy().hasHeightForWidth())
        self.time_unit_groupBox.setSizePolicy(sizePolicy)
        self.time_unit_layout = QHBoxLayout(self.time_unit_groupBox)
        self.time_unit_layout.setSpacing(5)
        self.time_unit_layout.setObjectName(u"time_unit_layout")
        self.time_unit_layout.setContentsMargins(0, 0, 0, 0)
        self.show_time_unit_check = QCheckBox(self.time_unit_groupBox)
        self.show_time_unit_check.setObjectName(u"show_time_unit_check")
        icon = QIcon()
        icon.addFile(u":/services/ads", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.show_time_unit_check.setIcon(icon)
        self.show_time_unit_check.setIconSize(QSize(32, 32))

        self.time_unit_layout.addWidget(self.show_time_unit_check)

        self.time_value = QSpinBox(self.time_unit_groupBox)
        self.time_value.setObjectName(u"time_value")
        self.time_value.setMinimum(1)
        self.time_value.setMaximum(999)
        self.time_value.setValue(1)

        self.time_unit_layout.addWidget(self.time_value)

        self.time_unit = QComboBox(self.time_unit_groupBox)
        self.time_unit.addItem("")
        self.time_unit.addItem("")
        self.time_unit.addItem("")
        self.time_unit.setObjectName(u"time_unit")

        self.time_unit_layout.addWidget(self.time_unit)

        self.apply_time_filter = QPushButton(self.time_unit_groupBox)
        self.apply_time_filter.setObjectName(u"apply_time_filter")

        self.time_unit_layout.addWidget(self.apply_time_filter)


        self.horizontalLayout_2.addWidget(self.time_unit_groupBox)

        self.month_year_groupBox = QGroupBox(self.fechas_widget)
        self.month_year_groupBox.setObjectName(u"month_year_groupBox")
        sizePolicy.setHeightForWidth(self.month_year_groupBox.sizePolicy().hasHeightForWidth())
        self.month_year_groupBox.setSizePolicy(sizePolicy)
        self.month_year_layout = QHBoxLayout(self.month_year_groupBox)
        self.month_year_layout.setSpacing(5)
        self.month_year_layout.setObjectName(u"month_year_layout")
        self.month_year_layout.setContentsMargins(0, 0, 0, 0)
        self.show_month_year_check = QCheckBox(self.month_year_groupBox)
        self.show_month_year_check.setObjectName(u"show_month_year_check")
        self.show_month_year_check.setIcon(icon)
        self.show_month_year_check.setIconSize(QSize(32, 32))

        self.month_year_layout.addWidget(self.show_month_year_check)

        self.year_spin_begin = QSpinBox(self.month_year_groupBox)
        self.year_spin_begin.setObjectName(u"year_spin_begin")
        self.year_spin_begin.setMinimum(0)
        self.year_spin_begin.setMaximum(2100)
        self.year_spin_begin.setSingleStep(10)
        self.year_spin_begin.setValue(1950)

        self.month_year_layout.addWidget(self.year_spin_begin)

        self.year_spin_end = QSpinBox(self.month_year_groupBox)
        self.year_spin_end.setObjectName(u"year_spin_end")
        self.year_spin_end.setMinimum(0)
        self.year_spin_end.setMaximum(2100)
        self.year_spin_end.setSingleStep(10)
        self.year_spin_end.setValue(2020)

        self.month_year_layout.addWidget(self.year_spin_end)

        self.apply_month_year = QPushButton(self.month_year_groupBox)
        self.apply_month_year.setObjectName(u"apply_month_year")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.apply_month_year.sizePolicy().hasHeightForWidth())
        self.apply_month_year.setSizePolicy(sizePolicy1)

        self.month_year_layout.addWidget(self.apply_month_year)


        self.horizontalLayout_2.addWidget(self.month_year_groupBox)

        self.year_groupBox = QGroupBox(self.fechas_widget)
        self.year_groupBox.setObjectName(u"year_groupBox")
        sizePolicy.setHeightForWidth(self.year_groupBox.sizePolicy().hasHeightForWidth())
        self.year_groupBox.setSizePolicy(sizePolicy)
        self.year_layout = QHBoxLayout(self.year_groupBox)
        self.year_layout.setSpacing(5)
        self.year_layout.setObjectName(u"year_layout")
        self.year_layout.setContentsMargins(0, 0, 0, 0)
        self.show_year_check = QCheckBox(self.year_groupBox)
        self.show_year_check.setObjectName(u"show_year_check")
        self.show_year_check.setIcon(icon)
        self.show_year_check.setIconSize(QSize(32, 32))

        self.year_layout.addWidget(self.show_year_check)

        self.year_only_spin = QSpinBox(self.year_groupBox)
        self.year_only_spin.setObjectName(u"year_only_spin")
        self.year_only_spin.setMinimum(1900)
        self.year_only_spin.setMaximum(2100)

        self.year_layout.addWidget(self.year_only_spin)

        self.apply_year = QPushButton(self.year_groupBox)
        self.apply_year.setObjectName(u"apply_year")

        self.year_layout.addWidget(self.apply_year)


        self.horizontalLayout_2.addWidget(self.year_groupBox)


        self.verticalLayout.addWidget(self.fechas_widget)

        self.botones_widget = QWidget(self.widget)
        self.botones_widget.setObjectName(u"botones_widget")
        self.horizontalLayout = QHBoxLayout(self.botones_widget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.groupBox_2 = QGroupBox(self.botones_widget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.only_local_files = QRadioButton(self.groupBox_2)
        self.only_local_files.setObjectName(u"only_local_files")

        self.verticalLayout_2.addWidget(self.only_local_files)

        self.show_all = QRadioButton(self.groupBox_2)
        self.show_all.setObjectName(u"show_all")

        self.verticalLayout_2.addWidget(self.show_all)


        self.horizontalLayout.addWidget(self.groupBox_2)

        self.groupBox_3 = QGroupBox(self.botones_widget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout = QGridLayout(self.groupBox_3)
        self.gridLayout.setObjectName(u"gridLayout")
        self.discografia_check = QCheckBox(self.groupBox_3)
        self.discografia_check.setObjectName(u"discografia_check")

        self.gridLayout.addWidget(self.discografia_check, 0, 0, 1, 1)

        self.spotify_check = QCheckBox(self.groupBox_3)
        self.spotify_check.setObjectName(u"spotify_check")

        self.gridLayout.addWidget(self.spotify_check, 0, 1, 1, 1)

        self.listenbrainz_check = QCheckBox(self.groupBox_3)
        self.listenbrainz_check.setObjectName(u"listenbrainz_check")

        self.gridLayout.addWidget(self.listenbrainz_check, 0, 2, 1, 1)

        self.scrobbles_check = QCheckBox(self.groupBox_3)
        self.scrobbles_check.setObjectName(u"scrobbles_check")

        self.gridLayout.addWidget(self.scrobbles_check, 1, 2, 1, 1)

        self.local_check = QCheckBox(self.groupBox_3)
        self.local_check.setObjectName(u"local_check")

        self.gridLayout.addWidget(self.local_check, 1, 0, 1, 1)

        self.musicbrainz_check = QCheckBox(self.groupBox_3)
        self.musicbrainz_check.setObjectName(u"musicbrainz_check")

        self.gridLayout.addWidget(self.musicbrainz_check, 1, 1, 1, 1)


        self.horizontalLayout.addWidget(self.groupBox_3)

        self.edit_buttons = QPushButton(self.botones_widget)
        self.edit_buttons.setObjectName(u"edit_buttons")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.edit_buttons.sizePolicy().hasHeightForWidth())
        self.edit_buttons.setSizePolicy(sizePolicy2)
        icon1 = QIcon()
        icon1.addFile(u":/services/b_ghost", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.edit_buttons.setIcon(icon1)
        self.edit_buttons.setIconSize(QSize(32, 32))
        self.edit_buttons.setFlat(True)

        self.horizontalLayout.addWidget(self.edit_buttons)


        self.verticalLayout.addWidget(self.botones_widget)


        self.time_filters_layout.addWidget(self.widget)


        self.retranslateUi(AdvancedSettings)

        QMetaObject.connectSlotsByName(AdvancedSettings)
    # setupUi

    def retranslateUi(self, AdvancedSettings):
        self.time_unit_groupBox.setTitle(QCoreApplication.translate("AdvancedSettings", u"Discos Recientes", None))
        self.show_time_unit_check.setText("")
        self.time_unit.setItemText(0, QCoreApplication.translate("AdvancedSettings", u"Semanas", None))
        self.time_unit.setItemText(1, QCoreApplication.translate("AdvancedSettings", u"Meses", None))
        self.time_unit.setItemText(2, QCoreApplication.translate("AdvancedSettings", u"A\u00f1os", None))

        self.apply_time_filter.setText(QCoreApplication.translate("AdvancedSettings", u"Aplicar", None))
        self.month_year_groupBox.setTitle(QCoreApplication.translate("AdvancedSettings", u"Mes del a\u00f1o", None))
        self.show_month_year_check.setText("")
        self.apply_month_year.setText(QCoreApplication.translate("AdvancedSettings", u"Filtrar por Mes/A\u00f1o", None))
        self.year_groupBox.setTitle(QCoreApplication.translate("AdvancedSettings", u"A\u00f1o", None))
        self.show_year_check.setText("")
        self.apply_year.setText(QCoreApplication.translate("AdvancedSettings", u"Filtrar por A\u00f1o", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("AdvancedSettings", u"Origen de lo mostrado", None))
        self.only_local_files.setText(QCoreApplication.translate("AdvancedSettings", u"Mostrar solo m\u00fasical local", None))
        self.show_all.setText(QCoreApplication.translate("AdvancedSettings", u"Mostrar todo", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("AdvancedSettings", u"Filtrar origen", None))
        self.discografia_check.setText(QCoreApplication.translate("AdvancedSettings", u"Mostrar discografias", None))
        self.spotify_check.setText(QCoreApplication.translate("AdvancedSettings", u"Mostrar spotify", None))
        self.listenbrainz_check.setText(QCoreApplication.translate("AdvancedSettings", u"Mostrar listenbrainz", None))
        self.scrobbles_check.setText(QCoreApplication.translate("AdvancedSettings", u"Mostrar scrobbles", None))
        self.local_check.setText(QCoreApplication.translate("AdvancedSettings", u"Mostrar local", None))
        self.musicbrainz_check.setText(QCoreApplication.translate("AdvancedSettings", u"Mostrar musicbrainz", None))
#if QT_CONFIG(tooltip)
        self.edit_buttons.setToolTip(QCoreApplication.translate("AdvancedSettings", u"Personalizar botones", None))
#endif // QT_CONFIG(tooltip)
        self.edit_buttons.setText("")
        pass
    # retranslateUi

