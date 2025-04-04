# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'music_fuzzy_advanced_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QSpinBox,
    QWidget)

class Ui_AdvancedSettings(object):
    def setupUi(self, AdvancedSettings):
        if not AdvancedSettings.objectName():
            AdvancedSettings.setObjectName(u"AdvancedSettings")
        AdvancedSettings.resize(800, 40)
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
        self.time_unit_frame = QFrame(AdvancedSettings)
        self.time_unit_frame.setObjectName(u"time_unit_frame")
        self.time_unit_frame.setFrameShape(QFrame.NoFrame)
        self.time_unit_layout = QHBoxLayout(self.time_unit_frame)
        self.time_unit_layout.setSpacing(5)
        self.time_unit_layout.setObjectName(u"time_unit_layout")
        self.time_unit_layout.setContentsMargins(0, 0, 0, 0)
        self.time_value = QSpinBox(self.time_unit_frame)
        self.time_value.setObjectName(u"time_value")
        self.time_value.setMinimum(1)
        self.time_value.setMaximum(999)
        self.time_value.setValue(1)

        self.time_unit_layout.addWidget(self.time_value)

        self.time_unit = QComboBox(self.time_unit_frame)
        self.time_unit.addItem("")
        self.time_unit.addItem("")
        self.time_unit.addItem("")
        self.time_unit.setObjectName(u"time_unit")

        self.time_unit_layout.addWidget(self.time_unit)

        self.apply_time_filter = QPushButton(self.time_unit_frame)
        self.apply_time_filter.setObjectName(u"apply_time_filter")

        self.time_unit_layout.addWidget(self.apply_time_filter)


        self.time_filters_layout.addWidget(self.time_unit_frame)

        self.separator1 = QLabel(AdvancedSettings)
        self.separator1.setObjectName(u"separator1")
        self.separator1.setStyleSheet(u"color: rgba(169, 177, 214, 0.5);")

        self.time_filters_layout.addWidget(self.separator1)

        self.month_year_frame = QFrame(AdvancedSettings)
        self.month_year_frame.setObjectName(u"month_year_frame")
        self.month_year_frame.setFrameShape(QFrame.NoFrame)
        self.month_year_layout = QHBoxLayout(self.month_year_frame)
        self.month_year_layout.setSpacing(5)
        self.month_year_layout.setObjectName(u"month_year_layout")
        self.month_year_layout.setContentsMargins(0, 0, 0, 0)
        self.month_combo = QComboBox(self.month_year_frame)
        self.month_combo.setObjectName(u"month_combo")

        self.month_year_layout.addWidget(self.month_combo)

        self.year_spin = QSpinBox(self.month_year_frame)
        self.year_spin.setObjectName(u"year_spin")
        self.year_spin.setMinimum(1900)
        self.year_spin.setMaximum(2100)

        self.month_year_layout.addWidget(self.year_spin)

        self.apply_month_year = QPushButton(self.month_year_frame)
        self.apply_month_year.setObjectName(u"apply_month_year")

        self.month_year_layout.addWidget(self.apply_month_year)


        self.time_filters_layout.addWidget(self.month_year_frame)

        self.separator2 = QLabel(AdvancedSettings)
        self.separator2.setObjectName(u"separator2")
        self.separator2.setStyleSheet(u"color: rgba(169, 177, 214, 0.5);")

        self.time_filters_layout.addWidget(self.separator2)

        self.year_frame = QFrame(AdvancedSettings)
        self.year_frame.setObjectName(u"year_frame")
        self.year_frame.setFrameShape(QFrame.NoFrame)
        self.year_layout = QHBoxLayout(self.year_frame)
        self.year_layout.setSpacing(5)
        self.year_layout.setObjectName(u"year_layout")
        self.year_layout.setContentsMargins(0, 0, 0, 0)
        self.year_only_spin = QSpinBox(self.year_frame)
        self.year_only_spin.setObjectName(u"year_only_spin")
        self.year_only_spin.setMinimum(1900)
        self.year_only_spin.setMaximum(2100)

        self.year_layout.addWidget(self.year_only_spin)

        self.apply_year = QPushButton(self.year_frame)
        self.apply_year.setObjectName(u"apply_year")

        self.year_layout.addWidget(self.apply_year)


        self.time_filters_layout.addWidget(self.year_frame)


        self.retranslateUi(AdvancedSettings)

        QMetaObject.connectSlotsByName(AdvancedSettings)
    # setupUi

    def retranslateUi(self, AdvancedSettings):
        self.time_unit.setItemText(0, QCoreApplication.translate("AdvancedSettings", u"Semanas", None))
        self.time_unit.setItemText(1, QCoreApplication.translate("AdvancedSettings", u"Meses", None))
        self.time_unit.setItemText(2, QCoreApplication.translate("AdvancedSettings", u"A\u00f1os", None))

        self.apply_time_filter.setText(QCoreApplication.translate("AdvancedSettings", u"Aplicar", None))
        self.separator1.setText(QCoreApplication.translate("AdvancedSettings", u"|", None))
        self.apply_month_year.setText(QCoreApplication.translate("AdvancedSettings", u"Filtrar por Mes/A\u00f1o", None))
        self.separator2.setText(QCoreApplication.translate("AdvancedSettings", u"|", None))
        self.apply_year.setText(QCoreApplication.translate("AdvancedSettings", u"Filtrar por A\u00f1o", None))
        pass
    # retranslateUi

