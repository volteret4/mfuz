# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'muspy_releases_table.ui'
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
from PySide6.QtWidgets import (QApplication, QHeaderView, QLabel, QPushButton,
    QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_ReleasesTable(object):
    def setupUi(self, ReleasesTable):
        if not ReleasesTable.objectName():
            ReleasesTable.setObjectName(u"ReleasesTable")
        ReleasesTable.resize(800, 500)
        self.verticalLayout = QVBoxLayout(ReleasesTable)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.count_label = QLabel(ReleasesTable)
        self.count_label.setObjectName(u"count_label")

        self.verticalLayout.addWidget(self.count_label)

        self.table = QTableWidget(ReleasesTable)
        if (self.table.columnCount() < 6):
            self.table.setColumnCount(6)
        __qtablewidgetitem = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        self.table.setObjectName(u"table")
        self.table.setSortingEnabled(True)
        self.table.setColumnCount(6)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.verticalLayout.addWidget(self.table)

        self.add_follow_button = QPushButton(ReleasesTable)
        self.add_follow_button.setObjectName(u"add_follow_button")

        self.verticalLayout.addWidget(self.add_follow_button)


        self.retranslateUi(ReleasesTable)

        QMetaObject.connectSlotsByName(ReleasesTable)
    # setupUi

    def retranslateUi(self, ReleasesTable):
        self.count_label.setText(QCoreApplication.translate("ReleasesTable", u"Showing 0 upcoming releases", None))
        ___qtablewidgetitem = self.table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("ReleasesTable", u"Artist", None));
        ___qtablewidgetitem1 = self.table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("ReleasesTable", u"Release Title", None));
        ___qtablewidgetitem2 = self.table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("ReleasesTable", u"Type", None));
        ___qtablewidgetitem3 = self.table.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("ReleasesTable", u"Date", None));
        ___qtablewidgetitem4 = self.table.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("ReleasesTable", u"Disambiguation", None));
        ___qtablewidgetitem5 = self.table.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("ReleasesTable", u"Calendario", None));
        self.add_follow_button.setText(QCoreApplication.translate("ReleasesTable", u"Seguir artista en Muspy", None))
        pass
    # retranslateUi

