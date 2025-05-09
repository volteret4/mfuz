# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'config_editor.ui'
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
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_ConfigEditor(object):
    def setupUi(self, ConfigEditor):
        if not ConfigEditor.objectName():
            ConfigEditor.setObjectName(u"ConfigEditor")
        ConfigEditor.resize(800, 600)
        self.main_layout = QVBoxLayout(ConfigEditor)
        self.main_layout.setSpacing(0)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea(ConfigEditor)
        self.scroll_area.setObjectName(u"scroll_area")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.container = QWidget()
        self.container.setObjectName(u"container")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setSpacing(10)
        self.container_layout.setObjectName(u"container_layout")
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.global_group = QGroupBox(self.container)
        self.global_group.setObjectName(u"global_group")
        self.global_layout = QVBoxLayout(self.global_group)
        self.global_layout.setObjectName(u"global_layout")
        self.enable_individual_themes = QCheckBox(self.global_group)
        self.enable_individual_themes.setObjectName(u"enable_individual_themes")

        self.global_layout.addWidget(self.enable_individual_themes)

        self.shared_db_group = QGroupBox(self.global_group)
        self.shared_db_group.setObjectName(u"shared_db_group")
        self.shared_db_layout = QVBoxLayout(self.shared_db_group)
        self.shared_db_layout.setObjectName(u"shared_db_layout")
        self.db_path_layout = QHBoxLayout()
        self.db_path_layout.setObjectName(u"db_path_layout")
        self.db_path_label = QLabel(self.shared_db_group)
        self.db_path_label.setObjectName(u"db_path_label")

        self.db_path_layout.addWidget(self.db_path_label)

        self.db_paths_dropdown = QComboBox(self.shared_db_group)
        self.db_paths_dropdown.setObjectName(u"db_paths_dropdown")

        self.db_path_layout.addWidget(self.db_paths_dropdown)

        self.db_path_input = QLineEdit(self.shared_db_group)
        self.db_path_input.setObjectName(u"db_path_input")

        self.db_path_layout.addWidget(self.db_path_input)

        self.add_path_button = QPushButton(self.shared_db_group)
        self.add_path_button.setObjectName(u"add_path_button")

        self.db_path_layout.addWidget(self.add_path_button)

        self.remove_path_button = QPushButton(self.shared_db_group)
        self.remove_path_button.setObjectName(u"remove_path_button")

        self.db_path_layout.addWidget(self.remove_path_button)


        self.shared_db_layout.addLayout(self.db_path_layout)


        self.global_layout.addWidget(self.shared_db_group)


        self.container_layout.addWidget(self.global_group)

        self.active_modules_group = QGroupBox(self.container)
        self.active_modules_group.setObjectName(u"active_modules_group")
        self.active_modules_layout = QVBoxLayout(self.active_modules_group)
        self.active_modules_layout.setObjectName(u"active_modules_layout")

        self.container_layout.addWidget(self.active_modules_group)

        self.disabled_modules_group = QGroupBox(self.container)
        self.disabled_modules_group.setObjectName(u"disabled_modules_group")
        self.disabled_modules_layout = QVBoxLayout(self.disabled_modules_group)
        self.disabled_modules_layout.setObjectName(u"disabled_modules_layout")

        self.container_layout.addWidget(self.disabled_modules_group)

        self.action_save_all = QPushButton(self.container)
        self.action_save_all.setObjectName(u"action_save_all")

        self.container_layout.addWidget(self.action_save_all)

        self.action_reload = QPushButton(self.container)
        self.action_reload.setObjectName(u"action_reload")

        self.container_layout.addWidget(self.action_reload)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.container_layout.addItem(self.verticalSpacer)

        self.scroll_area.setWidget(self.container)

        self.main_layout.addWidget(self.scroll_area)


        self.retranslateUi(ConfigEditor)

        QMetaObject.connectSlotsByName(ConfigEditor)
    # setupUi

    def retranslateUi(self, ConfigEditor):
        ConfigEditor.setWindowTitle(QCoreApplication.translate("ConfigEditor", u"Configuration Editor", None))
        self.global_group.setTitle(QCoreApplication.translate("ConfigEditor", u"Global Configuration", None))
        self.global_group.setStyleSheet(QCoreApplication.translate("ConfigEditor", u"QGroupBox { font-weight: bold; }", None))
        self.enable_individual_themes.setText(QCoreApplication.translate("ConfigEditor", u"Enable Individual Module Themes", None))
        self.shared_db_group.setTitle(QCoreApplication.translate("ConfigEditor", u"Shared Database Paths", None))
        self.db_path_label.setText(QCoreApplication.translate("ConfigEditor", u"Database Path:", None))
        self.db_path_input.setPlaceholderText(QCoreApplication.translate("ConfigEditor", u"Enter database path", None))
        self.add_path_button.setText(QCoreApplication.translate("ConfigEditor", u"Add Path", None))
        self.remove_path_button.setText(QCoreApplication.translate("ConfigEditor", u"Remove Path", None))
        self.active_modules_group.setTitle(QCoreApplication.translate("ConfigEditor", u"Active Modules", None))
        self.active_modules_group.setStyleSheet(QCoreApplication.translate("ConfigEditor", u"QGroupBox { font-weight: bold; color: #4CAF50; }", None))
        self.disabled_modules_group.setTitle(QCoreApplication.translate("ConfigEditor", u"Disabled Modules", None))
        self.disabled_modules_group.setStyleSheet(QCoreApplication.translate("ConfigEditor", u"QGroupBox { font-weight: bold; color: #F44336; }", None))
        self.action_save_all.setText(QCoreApplication.translate("ConfigEditor", u"Save All Changes", None))
        self.action_save_all.setStyleSheet(QCoreApplication.translate("ConfigEditor", u"background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;", None))
        self.action_reload.setText(QCoreApplication.translate("ConfigEditor", u"Reload Configuration", None))
        self.action_reload.setStyleSheet(QCoreApplication.translate("ConfigEditor", u"background-color: #2196F3; color: white; padding: 8px;", None))
    # retranslateUi

