# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'music_fuzzy_results_tree.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QAbstractScrollArea, QApplication, QHeaderView,
    QSizePolicy, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget)

class Ui_ResultsTree(object):
    def setupUi(self, ResultsTree):
        if not ResultsTree.objectName():
            ResultsTree.setObjectName(u"ResultsTree")
        ResultsTree.resize(400, 600)
        self.verticalLayout = QVBoxLayout(ResultsTree)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.results_tree = QTreeWidget(ResultsTree)
        self.results_tree.setObjectName(u"results_tree")
        self.results_tree.setLineWidth(0)
        self.results_tree.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.results_tree.setIndentation(20)
        self.results_tree.setRootIsDecorated(True)
        self.results_tree.setUniformRowHeights(True)
        self.results_tree.setItemsExpandable(True)
        self.results_tree.setSortingEnabled(True)
        self.results_tree.setAnimated(True)
        self.results_tree.setAllColumnsShowFocus(True)
        self.results_tree.setHeaderHidden(False)
        self.results_tree.setExpandsOnDoubleClick(True)

        self.verticalLayout.addWidget(self.results_tree)


        self.retranslateUi(ResultsTree)

        QMetaObject.connectSlotsByName(ResultsTree)
    # setupUi

    def retranslateUi(self, ResultsTree):
        ___qtreewidgetitem = self.results_tree.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("ResultsTree", u"G\u00e9nero", None));
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("ResultsTree", u"A\u00f1o", None));
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("ResultsTree", u"Artistas / \u00c1lbumes / Canciones", None));
        self.results_tree.setStyleSheet(QCoreApplication.translate("ResultsTree", u"QTreeWidget {\n"
"  border: none;\n"
"}\n"
"QTreeWidget::item {\n"
"  padding: 4px;\n"
"  border-bottom: 1px solid rgba(65, 72, 104, 0.2);\n"
"}\n"
"QTreeWidget::item:selected {\n"
"  background-color: rgba(54, 74, 130, 0.7);\n"
"  color: white;\n"
"}\n"
"QHeaderView::section {\n"
"  background-color: transparent;\n"
"  padding: 5px;\n"
"  border: none;\n"
"  border-bottom: 1px solid rgba(65, 72, 104, 0.5);\n"
"}", None))
        pass
    # retranslateUi

