# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'database_editor.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFormLayout,
    QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_DatabaseEditorForm(object):
    def setupUi(self, DatabaseEditorForm):
        if not DatabaseEditorForm.objectName():
            DatabaseEditorForm.setObjectName(u"DatabaseEditorForm")
        DatabaseEditorForm.resize(800, 600)
        self.verticalLayout = QVBoxLayout(DatabaseEditorForm)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.search_panel = QWidget(DatabaseEditorForm)
        self.search_panel.setObjectName(u"search_panel")
        self.search_layout = QHBoxLayout(self.search_panel)
        self.search_layout.setObjectName(u"search_layout")
        self.label = QLabel(self.search_panel)
        self.label.setObjectName(u"label")

        self.search_layout.addWidget(self.label)

        self.table_selector = QComboBox(self.search_panel)
        self.table_selector.setObjectName(u"table_selector")

        self.search_layout.addWidget(self.table_selector)

        self.label_2 = QLabel(self.search_panel)
        self.label_2.setObjectName(u"label_2")

        self.search_layout.addWidget(self.label_2)

        self.search_field = QComboBox(self.search_panel)
        self.search_field.setObjectName(u"search_field")

        self.search_layout.addWidget(self.search_field)

        self.search_input = QLineEdit(self.search_panel)
        self.search_input.setObjectName(u"search_input")

        self.search_layout.addWidget(self.search_input)

        self.search_button = QPushButton(self.search_panel)
        self.search_button.setObjectName(u"search_button")

        self.search_layout.addWidget(self.search_button)


        self.verticalLayout.addWidget(self.search_panel)

        self.tab_widget = QTabWidget(DatabaseEditorForm)
        self.tab_widget.setObjectName(u"tab_widget")
        self.results_tab = QWidget()
        self.results_tab.setObjectName(u"results_tab")
        self.results_layout = QVBoxLayout(self.results_tab)
        self.results_layout.setObjectName(u"results_layout")
        self.results_table = QTableWidget(self.results_tab)
        self.results_table.setObjectName(u"results_table")
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.results_layout.addWidget(self.results_table)

        self.frame = QFrame(self.results_tab)
        self.frame.setObjectName(u"frame")
        self.frame.setLineWidth(0)
        self.buttons_layout = QHBoxLayout(self.frame)
        self.buttons_layout.setObjectName(u"buttons_layout")
        self.edit_button = QPushButton(self.frame)
        self.edit_button.setObjectName(u"edit_button")

        self.buttons_layout.addWidget(self.edit_button)

        self.new_button = QPushButton(self.frame)
        self.new_button.setObjectName(u"new_button")

        self.buttons_layout.addWidget(self.new_button)

        self.delete_button = QPushButton(self.frame)
        self.delete_button.setObjectName(u"delete_button")

        self.buttons_layout.addWidget(self.delete_button)

        self.save_layout_button = QPushButton(self.frame)
        self.save_layout_button.setObjectName(u"save_layout_button")

        self.buttons_layout.addWidget(self.save_layout_button)


        self.results_layout.addWidget(self.frame)

        self.tab_widget.addTab(self.results_tab, "")
        self.edit_tab = QWidget()
        self.edit_tab.setObjectName(u"edit_tab")
        self.edit_tab_layout = QVBoxLayout(self.edit_tab)
        self.edit_tab_layout.setObjectName(u"edit_tab_layout")
        self.edit_scroll_area = QScrollArea(self.edit_tab)
        self.edit_scroll_area.setObjectName(u"edit_scroll_area")
        self.edit_scroll_area.setWidgetResizable(True)
        self.edit_container = QWidget()
        self.edit_container.setObjectName(u"edit_container")
        self.edit_container.setGeometry(QRect(0, 0, 758, 484))
        self.edit_layout = QFormLayout(self.edit_container)
        self.edit_layout.setObjectName(u"edit_layout")
        self.edit_buttons = QWidget(self.edit_container)
        self.edit_buttons.setObjectName(u"edit_buttons")
        self.horizontalLayout = QHBoxLayout(self.edit_buttons)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.save_button = QPushButton(self.edit_buttons)
        self.save_button.setObjectName(u"save_button")

        self.horizontalLayout.addWidget(self.save_button)

        self.cancel_button = QPushButton(self.edit_buttons)
        self.cancel_button.setObjectName(u"cancel_button")

        self.horizontalLayout.addWidget(self.cancel_button)


        self.edit_layout.setWidget(0, QFormLayout.SpanningRole, self.edit_buttons)

        self.edit_scroll_area.setWidget(self.edit_container)

        self.edit_tab_layout.addWidget(self.edit_scroll_area)

        self.tab_widget.addTab(self.edit_tab, "")

        self.verticalLayout.addWidget(self.tab_widget)


        self.retranslateUi(DatabaseEditorForm)

        self.tab_widget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(DatabaseEditorForm)
    # setupUi

    def retranslateUi(self, DatabaseEditorForm):
        DatabaseEditorForm.setWindowTitle(QCoreApplication.translate("DatabaseEditorForm", u"Database Editor", None))
        self.label.setText(QCoreApplication.translate("DatabaseEditorForm", u"Tabla:", None))
        self.label_2.setText(QCoreApplication.translate("DatabaseEditorForm", u"Campo:", None))
        self.search_input.setPlaceholderText(QCoreApplication.translate("DatabaseEditorForm", u"T\u00e9rmino de b\u00fasqueda...", None))
        self.search_button.setText(QCoreApplication.translate("DatabaseEditorForm", u"Buscar", None))
        self.edit_button.setText(QCoreApplication.translate("DatabaseEditorForm", u"Editar Seleccionado", None))
        self.new_button.setText(QCoreApplication.translate("DatabaseEditorForm", u"Nuevo Item", None))
        self.delete_button.setText(QCoreApplication.translate("DatabaseEditorForm", u"Eliminar Seleccionado", None))
        self.save_layout_button.setText(QCoreApplication.translate("DatabaseEditorForm", u"Guardar Orden de Columnas", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.results_tab), QCoreApplication.translate("DatabaseEditorForm", u"Resultados de B\u00fasqueda", None))
        self.save_button.setText(QCoreApplication.translate("DatabaseEditorForm", u"Guardar Cambios", None))
        self.cancel_button.setText(QCoreApplication.translate("DatabaseEditorForm", u"Cancelar", None))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.edit_tab), QCoreApplication.translate("DatabaseEditorForm", u"Editar Item", None))
    # retranslateUi

