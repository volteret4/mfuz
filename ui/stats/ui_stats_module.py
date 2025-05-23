# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stats_module.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QSplitter, QStackedWidget,
    QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout,
    QWidget)
import rc_images

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(900, 700)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.stats_content = QWidget(Form)
        self.stats_content.setObjectName(u"stats_content")
        self.verticalLayout_2 = QVBoxLayout(self.stats_content)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.stacked_widget = QStackedWidget(self.stats_content)
        self.stacked_widget.setObjectName(u"stacked_widget")
        self.page_missing_data = QWidget()
        self.page_missing_data.setObjectName(u"page_missing_data")
        self.verticalLayout_missing_data = QVBoxLayout(self.page_missing_data)
        self.verticalLayout_missing_data.setObjectName(u"verticalLayout_missing_data")
        self.widget = QWidget(self.page_missing_data)
        self.widget.setObjectName(u"widget")
        self.verticalLayout_15 = QVBoxLayout(self.widget)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.widget_3 = QWidget(self.widget)
        self.widget_3.setObjectName(u"widget_3")
        self.horizontalLayout = QHBoxLayout(self.widget_3)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.widget_4 = QWidget(self.widget_3)
        self.widget_4.setObjectName(u"widget_4")
        self.verticalLayout_17 = QVBoxLayout(self.widget_4)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.label_missing_title = QLabel(self.widget_4)
        self.label_missing_title.setObjectName(u"label_missing_title")
        self.label_missing_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_17.addWidget(self.label_missing_title)

        self.table_missing_data = QTableWidget(self.widget_4)
        if (self.table_missing_data.columnCount() < 3):
            self.table_missing_data.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.table_missing_data.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.table_missing_data.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.table_missing_data.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.table_missing_data.setObjectName(u"table_missing_data")
        self.table_missing_data.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_missing_data.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout_17.addWidget(self.table_missing_data)

        self.ausentes_tabla_combo = QComboBox(self.widget_4)
        self.ausentes_tabla_combo.addItem("")
        self.ausentes_tabla_combo.addItem("")
        self.ausentes_tabla_combo.addItem("")
        self.ausentes_tabla_combo.addItem("")
        self.ausentes_tabla_combo.setObjectName(u"ausentes_tabla_combo")

        self.verticalLayout_17.addWidget(self.ausentes_tabla_combo)


        self.horizontalLayout.addWidget(self.widget_4)

        self.widget_chart_container_missing = QWidget(self.widget_3)
        self.widget_chart_container_missing.setObjectName(u"widget_chart_container_missing")
        self.verticalLayout_16 = QVBoxLayout(self.widget_chart_container_missing)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.label_worst_fields = QLabel(self.widget_chart_container_missing)
        self.label_worst_fields.setObjectName(u"label_worst_fields")

        self.verticalLayout_16.addWidget(self.label_worst_fields)

        self.chart_container_missing = QWidget(self.widget_chart_container_missing)
        self.chart_container_missing.setObjectName(u"chart_container_missing")
        self.chart_container_missing.setMinimumSize(QSize(0, 200))
        self.verticalLayout_11 = QVBoxLayout(self.chart_container_missing)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")

        self.verticalLayout_16.addWidget(self.chart_container_missing)


        self.horizontalLayout.addWidget(self.widget_chart_container_missing)


        self.verticalLayout_15.addWidget(self.widget_3)


        self.verticalLayout_missing_data.addWidget(self.widget)

        self.horizontalLayout_summary = QWidget(self.page_missing_data)
        self.horizontalLayout_summary.setObjectName(u"horizontalLayout_summary")
        self.verticalLayout_14 = QVBoxLayout(self.horizontalLayout_summary)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.verticalLayout_14.setContentsMargins(0, 0, 0, 0)
        self.label_summary = QLabel(self.horizontalLayout_summary)
        self.label_summary.setObjectName(u"label_summary")

        self.verticalLayout_14.addWidget(self.label_summary)


        self.verticalLayout_missing_data.addWidget(self.horizontalLayout_summary)

        self.stacked_widget.addWidget(self.page_missing_data)
        self.page_genres = QWidget()
        self.page_genres.setObjectName(u"page_genres")
        self.verticalLayout_genres = QVBoxLayout(self.page_genres)
        self.verticalLayout_genres.setObjectName(u"verticalLayout_genres")
        self.verticalLayout_genres.setContentsMargins(0, 0, 0, 0)
        self.splitter_genres = QSplitter(self.page_genres)
        self.splitter_genres.setObjectName(u"splitter_genres")
        self.splitter_genres.setOrientation(Qt.Orientation.Horizontal)

        self.verticalLayout_genres.addWidget(self.splitter_genres)

        self.scrollArea = QScrollArea(self.page_genres)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 880, 606))
        self.verticalLayout_24 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_24.setObjectName(u"verticalLayout_24")
        self.verticalLayout_24.setContentsMargins(0, 0, 0, 0)
        self.widget_5 = QWidget(self.scrollAreaWidgetContents)
        self.widget_5.setObjectName(u"widget_5")
        self.horizontalLayout_2 = QHBoxLayout(self.widget_5)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_genres_left = QWidget(self.widget_5)
        self.verticalLayout_genres_left.setObjectName(u"verticalLayout_genres_left")
        self.verticalLayout_19 = QVBoxLayout(self.verticalLayout_genres_left)
        self.verticalLayout_19.setObjectName(u"verticalLayout_19")
        self.verticalLayout_19.setContentsMargins(0, 0, 0, 0)
        self.label_genres_distribution = QLabel(self.verticalLayout_genres_left)
        self.label_genres_distribution.setObjectName(u"label_genres_distribution")

        self.verticalLayout_19.addWidget(self.label_genres_distribution)

        self.table_genres = QTableWidget(self.verticalLayout_genres_left)
        if (self.table_genres.columnCount() < 5):
            self.table_genres.setColumnCount(5)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.table_genres.setHorizontalHeaderItem(0, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.table_genres.setHorizontalHeaderItem(1, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.table_genres.setHorizontalHeaderItem(2, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.table_genres.setHorizontalHeaderItem(3, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.table_genres.setHorizontalHeaderItem(4, __qtablewidgetitem7)
        self.table_genres.setObjectName(u"table_genres")
        self.table_genres.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_genres.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.verticalLayout_19.addWidget(self.table_genres)


        self.horizontalLayout_2.addWidget(self.verticalLayout_genres_left)

        self.verticalLayout_genres_right = QWidget(self.widget_5)
        self.verticalLayout_genres_right.setObjectName(u"verticalLayout_genres_right")
        self.verticalLayout_18 = QVBoxLayout(self.verticalLayout_genres_right)
        self.verticalLayout_18.setObjectName(u"verticalLayout_18")
        self.verticalLayout_18.setContentsMargins(0, 0, 0, 0)
        self.label_genres_visualization = QLabel(self.verticalLayout_genres_right)
        self.label_genres_visualization.setObjectName(u"label_genres_visualization")
        sizePolicy.setHeightForWidth(self.label_genres_visualization.sizePolicy().hasHeightForWidth())
        self.label_genres_visualization.setSizePolicy(sizePolicy)

        self.verticalLayout_18.addWidget(self.label_genres_visualization)

        self.chart_container_genres = QWidget(self.verticalLayout_genres_right)
        self.chart_container_genres.setObjectName(u"chart_container_genres")
        self.chart_container_genres.setMinimumSize(QSize(0, 300))
        self.verticalLayout_6 = QVBoxLayout(self.chart_container_genres)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_18.addWidget(self.chart_container_genres)

        self.stacked_genre_charts = QStackedWidget(self.verticalLayout_genres_right)
        self.stacked_genre_charts.setObjectName(u"stacked_genre_charts")
        self.genres_table_page = QWidget()
        self.genres_table_page.setObjectName(u"genres_table_page")
        self.verticalLayout_25 = QVBoxLayout(self.genres_table_page)
        self.verticalLayout_25.setObjectName(u"verticalLayout_25")
        self.chart_container_artists_by_genre = QWidget(self.genres_table_page)
        self.chart_container_artists_by_genre.setObjectName(u"chart_container_artists_by_genre")
        self.verticalLayout_21 = QVBoxLayout(self.chart_container_artists_by_genre)
        self.verticalLayout_21.setObjectName(u"verticalLayout_21")

        self.verticalLayout_25.addWidget(self.chart_container_artists_by_genre)

        self.stacked_genre_charts.addWidget(self.genres_table_page)
        self.genres_charts_page = QWidget()
        self.genres_charts_page.setObjectName(u"genres_charts_page")
        self.verticalLayout_26 = QVBoxLayout(self.genres_charts_page)
        self.verticalLayout_26.setObjectName(u"verticalLayout_26")
        self.verticalLayout_26.setContentsMargins(0, 0, 0, 0)
        self.label_selected_genre_title = QLabel(self.genres_charts_page)
        self.label_selected_genre_title.setObjectName(u"label_selected_genre_title")
        sizePolicy.setHeightForWidth(self.label_selected_genre_title.sizePolicy().hasHeightForWidth())
        self.label_selected_genre_title.setSizePolicy(sizePolicy)

        self.verticalLayout_26.addWidget(self.label_selected_genre_title)

        self.chart_container_genres_year = QWidget(self.genres_charts_page)
        self.chart_container_genres_year.setObjectName(u"chart_container_genres_year")
        self.verticalLayout_27 = QVBoxLayout(self.chart_container_genres_year)
        self.verticalLayout_27.setObjectName(u"verticalLayout_27")
        self.verticalLayout_27.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_26.addWidget(self.chart_container_genres_year)

        self.stacked_genre_charts.addWidget(self.genres_charts_page)

        self.verticalLayout_18.addWidget(self.stacked_genre_charts)

        self.widget_8 = QWidget(self.verticalLayout_genres_right)
        self.widget_8.setObjectName(u"widget_8")
        sizePolicy.setHeightForWidth(self.widget_8.sizePolicy().hasHeightForWidth())
        self.widget_8.setSizePolicy(sizePolicy)
        self.horizontalLayout_6 = QHBoxLayout(self.widget_8)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.btn_artists_view = QPushButton(self.widget_8)
        self.btn_artists_view.setObjectName(u"btn_artists_view")

        self.horizontalLayout_6.addWidget(self.btn_artists_view)

        self.btn_decades_view = QPushButton(self.widget_8)
        self.btn_decades_view.setObjectName(u"btn_decades_view")

        self.horizontalLayout_6.addWidget(self.btn_decades_view)


        self.verticalLayout_18.addWidget(self.widget_8)


        self.horizontalLayout_2.addWidget(self.verticalLayout_genres_right)


        self.verticalLayout_24.addWidget(self.widget_5)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_genres.addWidget(self.scrollArea)

        self.stacked_widget.addWidget(self.page_genres)
        self.page_listening = QWidget()
        self.page_listening.setObjectName(u"page_listening")
        self.verticalLayout_listening = QVBoxLayout(self.page_listening)
        self.verticalLayout_listening.setObjectName(u"verticalLayout_listening")
        self.verticalLayout_listening.setContentsMargins(0, 0, 0, 0)
        self.label_listen_title = QLabel(self.page_listening)
        self.label_listen_title.setObjectName(u"label_listen_title")
        sizePolicy.setHeightForWidth(self.label_listen_title.sizePolicy().hasHeightForWidth())
        self.label_listen_title.setSizePolicy(sizePolicy)

        self.verticalLayout_listening.addWidget(self.label_listen_title)

        self.label_source = QLabel(self.page_listening)
        self.label_source.setObjectName(u"label_source")

        self.verticalLayout_listening.addWidget(self.label_source)

        self.combo_source = QComboBox(self.page_listening)
        self.combo_source.setObjectName(u"combo_source")

        self.verticalLayout_listening.addWidget(self.combo_source)

        self.label_stats_type = QLabel(self.page_listening)
        self.label_stats_type.setObjectName(u"label_stats_type")

        self.verticalLayout_listening.addWidget(self.label_stats_type)

        self.combo_stats_type = QComboBox(self.page_listening)
        self.combo_stats_type.addItem("")
        self.combo_stats_type.addItem("")
        self.combo_stats_type.addItem("")
        self.combo_stats_type.addItem("")
        self.combo_stats_type.addItem("")
        self.combo_stats_type.setObjectName(u"combo_stats_type")

        self.verticalLayout_listening.addWidget(self.combo_stats_type)

        self.stacked_listen_stats = QStackedWidget(self.page_listening)
        self.stacked_listen_stats.setObjectName(u"stacked_listen_stats")
        self.page_top_artists = QWidget()
        self.page_top_artists.setObjectName(u"page_top_artists")
        self.verticalLayout_top_artists = QVBoxLayout(self.page_top_artists)
        self.verticalLayout_top_artists.setObjectName(u"verticalLayout_top_artists")
        self.verticalLayout_top_artists.setContentsMargins(0, 0, 0, 0)
        self.splitter_artists = QSplitter(self.page_top_artists)
        self.splitter_artists.setObjectName(u"splitter_artists")
        self.splitter_artists.setOrientation(Qt.Orientation.Horizontal)
        self.widget_artists_table = QWidget(self.splitter_artists)
        self.widget_artists_table.setObjectName(u"widget_artists_table")
        self.verticalLayout_artists_table = QVBoxLayout(self.widget_artists_table)
        self.verticalLayout_artists_table.setObjectName(u"verticalLayout_artists_table")
        self.verticalLayout_artists_table.setContentsMargins(0, 0, 0, 0)
        self.table_artists = QTableWidget(self.widget_artists_table)
        if (self.table_artists.columnCount() < 2):
            self.table_artists.setColumnCount(2)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.table_artists.setHorizontalHeaderItem(0, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.table_artists.setHorizontalHeaderItem(1, __qtablewidgetitem9)
        self.table_artists.setObjectName(u"table_artists")

        self.verticalLayout_artists_table.addWidget(self.table_artists)

        self.splitter_artists.addWidget(self.widget_artists_table)
        self.widget_artists_chart = QWidget(self.splitter_artists)
        self.widget_artists_chart.setObjectName(u"widget_artists_chart")
        self.verticalLayout_artists_chart = QVBoxLayout(self.widget_artists_chart)
        self.verticalLayout_artists_chart.setObjectName(u"verticalLayout_artists_chart")
        self.verticalLayout_artists_chart.setContentsMargins(0, 0, 0, 0)
        self.chart_container_artists = QWidget(self.widget_artists_chart)
        self.chart_container_artists.setObjectName(u"chart_container_artists")
        self.verticalLayout_10 = QVBoxLayout(self.chart_container_artists)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")

        self.verticalLayout_artists_chart.addWidget(self.chart_container_artists)

        self.splitter_artists.addWidget(self.widget_artists_chart)

        self.verticalLayout_top_artists.addWidget(self.splitter_artists)

        self.stacked_listen_stats.addWidget(self.page_top_artists)
        self.page_top_albums = QWidget()
        self.page_top_albums.setObjectName(u"page_top_albums")
        self.verticalLayout_top_albums = QVBoxLayout(self.page_top_albums)
        self.verticalLayout_top_albums.setObjectName(u"verticalLayout_top_albums")
        self.verticalLayout_top_albums.setContentsMargins(0, 0, 0, 0)
        self.stacked_listen_stats.addWidget(self.page_top_albums)
        self.page_genre_listen = QWidget()
        self.page_genre_listen.setObjectName(u"page_genre_listen")
        self.verticalLayout_genre_listen = QVBoxLayout(self.page_genre_listen)
        self.verticalLayout_genre_listen.setObjectName(u"verticalLayout_genre_listen")
        self.verticalLayout_genre_listen.setContentsMargins(0, 0, 0, 0)
        self.stacked_listen_stats.addWidget(self.page_genre_listen)
        self.page_label_listen = QWidget()
        self.page_label_listen.setObjectName(u"page_label_listen")
        self.verticalLayout_label_listen = QVBoxLayout(self.page_label_listen)
        self.verticalLayout_label_listen.setObjectName(u"verticalLayout_label_listen")
        self.verticalLayout_label_listen.setContentsMargins(0, 0, 0, 0)
        self.stacked_listen_stats.addWidget(self.page_label_listen)
        self.page_temporal_listen = QWidget()
        self.page_temporal_listen.setObjectName(u"page_temporal_listen")
        self.verticalLayout_temporal_listen = QVBoxLayout(self.page_temporal_listen)
        self.verticalLayout_temporal_listen.setObjectName(u"verticalLayout_temporal_listen")
        self.verticalLayout_temporal_listen.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_time_unit = QWidget(self.page_temporal_listen)
        self.horizontalLayout_time_unit.setObjectName(u"horizontalLayout_time_unit")
        self.horizontalLayout_3 = QHBoxLayout(self.horizontalLayout_time_unit)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.label_time_unit = QLabel(self.horizontalLayout_time_unit)
        self.label_time_unit.setObjectName(u"label_time_unit")

        self.horizontalLayout_3.addWidget(self.label_time_unit)

        self.combo_time_unit = QComboBox(self.horizontalLayout_time_unit)
        self.combo_time_unit.addItem("")
        self.combo_time_unit.addItem("")
        self.combo_time_unit.addItem("")
        self.combo_time_unit.addItem("")
        self.combo_time_unit.setObjectName(u"combo_time_unit")

        self.horizontalLayout_3.addWidget(self.combo_time_unit)

        self.horizontalSpacer = QSpacerItem(707, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer)


        self.verticalLayout_temporal_listen.addWidget(self.horizontalLayout_time_unit)

        self.chart_container_temporal = QWidget(self.page_temporal_listen)
        self.chart_container_temporal.setObjectName(u"chart_container_temporal")
        self.verticalLayout_9 = QVBoxLayout(self.chart_container_temporal)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_temporal_listen.addWidget(self.chart_container_temporal)

        self.stacked_listen_stats.addWidget(self.page_temporal_listen)

        self.verticalLayout_listening.addWidget(self.stacked_listen_stats)

        self.stacked_widget.addWidget(self.page_listening)
        self.page_labels = QWidget()
        self.page_labels.setObjectName(u"page_labels")
        self.verticalLayout_labels = QVBoxLayout(self.page_labels)
        self.verticalLayout_labels.setObjectName(u"verticalLayout_labels")
        self.verticalLayout_labels.setContentsMargins(0, 0, 0, 0)
        self.widget_labels = QWidget(self.page_labels)
        self.widget_labels.setObjectName(u"widget_labels")
        self.verticalLayout_22 = QVBoxLayout(self.widget_labels)
        self.verticalLayout_22.setSpacing(6)
        self.verticalLayout_22.setObjectName(u"verticalLayout_22")
        self.verticalLayout_22.setContentsMargins(0, 0, 0, 0)
        self.stackedWidget = QStackedWidget(self.widget_labels)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.verticalLayout_labels_top = QWidget()
        self.verticalLayout_labels_top.setObjectName(u"verticalLayout_labels_top")
        self.verticalLayout_28 = QVBoxLayout(self.verticalLayout_labels_top)
        self.verticalLayout_28.setObjectName(u"verticalLayout_28")
        self.verticalLayout_28.setContentsMargins(0, 0, 0, 0)
        self.widget_7 = QWidget(self.verticalLayout_labels_top)
        self.widget_7.setObjectName(u"widget_7")
        self.horizontalLayout_5 = QHBoxLayout(self.widget_7)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.widget_10 = QWidget(self.widget_7)
        self.widget_10.setObjectName(u"widget_10")
        self.verticalLayout_30 = QVBoxLayout(self.widget_10)
        self.verticalLayout_30.setObjectName(u"verticalLayout_30")
        self.verticalLayout_30.setContentsMargins(0, 0, 0, 0)
        self.label_labels_title = QLabel(self.widget_10)
        self.label_labels_title.setObjectName(u"label_labels_title")

        self.verticalLayout_30.addWidget(self.label_labels_title)

        self.table_labels = QTableWidget(self.widget_10)
        if (self.table_labels.columnCount() < 4):
            self.table_labels.setColumnCount(4)
        __qtablewidgetitem10 = QTableWidgetItem()
        self.table_labels.setHorizontalHeaderItem(0, __qtablewidgetitem10)
        __qtablewidgetitem11 = QTableWidgetItem()
        self.table_labels.setHorizontalHeaderItem(1, __qtablewidgetitem11)
        __qtablewidgetitem12 = QTableWidgetItem()
        self.table_labels.setHorizontalHeaderItem(2, __qtablewidgetitem12)
        __qtablewidgetitem13 = QTableWidgetItem()
        self.table_labels.setHorizontalHeaderItem(3, __qtablewidgetitem13)
        self.table_labels.setObjectName(u"table_labels")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.table_labels.sizePolicy().hasHeightForWidth())
        self.table_labels.setSizePolicy(sizePolicy1)

        self.verticalLayout_30.addWidget(self.table_labels)


        self.horizontalLayout_5.addWidget(self.widget_10)

        self.widget_12 = QWidget(self.widget_7)
        self.widget_12.setObjectName(u"widget_12")
        self.verticalLayout_23 = QVBoxLayout(self.widget_12)
        self.verticalLayout_23.setObjectName(u"verticalLayout_23")
        self.chart_sello_stacked = QStackedWidget(self.widget_12)
        self.chart_sello_stacked.setObjectName(u"chart_sello_stacked")
        self.chart_sellos_porcentaje = QWidget()
        self.chart_sellos_porcentaje.setObjectName(u"chart_sellos_porcentaje")
        self.verticalLayout_8 = QVBoxLayout(self.chart_sellos_porcentaje)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.chart_container_labels = QWidget(self.chart_sellos_porcentaje)
        self.chart_container_labels.setObjectName(u"chart_container_labels")
        self.verticalLayout_31 = QVBoxLayout(self.chart_container_labels)
        self.verticalLayout_31.setObjectName(u"verticalLayout_31")
        self.verticalLayout_31.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_8.addWidget(self.chart_container_labels)

        self.chart_sello_stacked.addWidget(self.chart_sellos_porcentaje)
        self.chart_sello_artistas = QWidget()
        self.chart_sello_artistas.setObjectName(u"chart_sello_artistas")
        self.verticalLayout_32 = QVBoxLayout(self.chart_sello_artistas)
        self.verticalLayout_32.setObjectName(u"verticalLayout_32")
        self.chart_sello_stacked.addWidget(self.chart_sello_artistas)

        self.verticalLayout_23.addWidget(self.chart_sello_stacked)


        self.horizontalLayout_5.addWidget(self.widget_12)


        self.verticalLayout_28.addWidget(self.widget_7)

        self.stackedWidget.addWidget(self.verticalLayout_labels_top)
        self.verticalLayout_labels_bottom = QWidget()
        self.verticalLayout_labels_bottom.setObjectName(u"verticalLayout_labels_bottom")
        self.verticalLayout_29 = QVBoxLayout(self.verticalLayout_labels_bottom)
        self.verticalLayout_29.setObjectName(u"verticalLayout_29")
        self.verticalLayout_29.setContentsMargins(0, 0, 0, 0)
        self.widget_9 = QWidget(self.verticalLayout_labels_bottom)
        self.widget_9.setObjectName(u"widget_9")
        self.verticalLayout_20 = QVBoxLayout(self.widget_9)
        self.verticalLayout_20.setObjectName(u"verticalLayout_20")
        self.verticalLayout_20.setContentsMargins(0, 0, 0, 0)
        self.decade_chart_container = QWidget(self.widget_9)
        self.decade_chart_container.setObjectName(u"decade_chart_container")
        self.verticalLayout_7 = QVBoxLayout(self.decade_chart_container)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_20.addWidget(self.decade_chart_container)

        self.label_decade_title = QLabel(self.widget_9)
        self.label_decade_title.setObjectName(u"label_decade_title")

        self.verticalLayout_20.addWidget(self.label_decade_title)

        self.combo_decade = QComboBox(self.widget_9)
        self.combo_decade.setObjectName(u"combo_decade")

        self.verticalLayout_20.addWidget(self.combo_decade)


        self.verticalLayout_29.addWidget(self.widget_9)

        self.stackedWidget.addWidget(self.verticalLayout_labels_bottom)
        self.sellos_por_genero = QWidget()
        self.sellos_por_genero.setObjectName(u"sellos_por_genero")
        self.verticalLayout_33 = QVBoxLayout(self.sellos_por_genero)
        self.verticalLayout_33.setObjectName(u"verticalLayout_33")
        self.widget_13 = QWidget(self.sellos_por_genero)
        self.widget_13.setObjectName(u"widget_13")
        self.horizontalLayout_7 = QHBoxLayout(self.widget_13)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.table_labels_genres = QTableWidget(self.widget_13)
        if (self.table_labels_genres.columnCount() < 4):
            self.table_labels_genres.setColumnCount(4)
        __qtablewidgetitem14 = QTableWidgetItem()
        self.table_labels_genres.setHorizontalHeaderItem(0, __qtablewidgetitem14)
        __qtablewidgetitem15 = QTableWidgetItem()
        self.table_labels_genres.setHorizontalHeaderItem(1, __qtablewidgetitem15)
        __qtablewidgetitem16 = QTableWidgetItem()
        self.table_labels_genres.setHorizontalHeaderItem(2, __qtablewidgetitem16)
        __qtablewidgetitem17 = QTableWidgetItem()
        self.table_labels_genres.setHorizontalHeaderItem(3, __qtablewidgetitem17)
        self.table_labels_genres.setObjectName(u"table_labels_genres")
        sizePolicy1.setHeightForWidth(self.table_labels_genres.sizePolicy().hasHeightForWidth())
        self.table_labels_genres.setSizePolicy(sizePolicy1)

        self.horizontalLayout_7.addWidget(self.table_labels_genres)

        self.chart_label_genres = QWidget(self.widget_13)
        self.chart_label_genres.setObjectName(u"chart_label_genres")
        self.verticalLayout_37 = QVBoxLayout(self.chart_label_genres)
        self.verticalLayout_37.setObjectName(u"verticalLayout_37")

        self.horizontalLayout_7.addWidget(self.chart_label_genres)


        self.verticalLayout_33.addWidget(self.widget_13)

        self.stackedWidget.addWidget(self.sellos_por_genero)
        self.sellos_albumes = QWidget()
        self.sellos_albumes.setObjectName(u"sellos_albumes")
        self.horizontalLayout_8 = QHBoxLayout(self.sellos_albumes)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.widget_6 = QWidget(self.sellos_albumes)
        self.widget_6.setObjectName(u"widget_6")
        self.horizontalLayout_9 = QHBoxLayout(self.widget_6)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.sellos_tabla_albumes = QTableWidget(self.widget_6)
        if (self.sellos_tabla_albumes.columnCount() < 4):
            self.sellos_tabla_albumes.setColumnCount(4)
        __qtablewidgetitem18 = QTableWidgetItem()
        self.sellos_tabla_albumes.setHorizontalHeaderItem(0, __qtablewidgetitem18)
        __qtablewidgetitem19 = QTableWidgetItem()
        self.sellos_tabla_albumes.setHorizontalHeaderItem(1, __qtablewidgetitem19)
        __qtablewidgetitem20 = QTableWidgetItem()
        self.sellos_tabla_albumes.setHorizontalHeaderItem(2, __qtablewidgetitem20)
        __qtablewidgetitem21 = QTableWidgetItem()
        self.sellos_tabla_albumes.setHorizontalHeaderItem(3, __qtablewidgetitem21)
        self.sellos_tabla_albumes.setObjectName(u"sellos_tabla_albumes")
        sizePolicy1.setHeightForWidth(self.sellos_tabla_albumes.sizePolicy().hasHeightForWidth())
        self.sellos_tabla_albumes.setSizePolicy(sizePolicy1)

        self.horizontalLayout_9.addWidget(self.sellos_tabla_albumes)

        self.chart_sellos_albumes = QWidget(self.widget_6)
        self.chart_sellos_albumes.setObjectName(u"chart_sellos_albumes")
        self.verticalLayout_34 = QVBoxLayout(self.chart_sellos_albumes)
        self.verticalLayout_34.setObjectName(u"verticalLayout_34")

        self.horizontalLayout_9.addWidget(self.chart_sellos_albumes)


        self.horizontalLayout_8.addWidget(self.widget_6)

        self.stackedWidget.addWidget(self.sellos_albumes)
        self.labels_info = QWidget()
        self.labels_info.setObjectName(u"labels_info")
        self.verticalLayout_35 = QVBoxLayout(self.labels_info)
        self.verticalLayout_35.setObjectName(u"verticalLayout_35")
        self.labels_info_widget = QWidget(self.labels_info)
        self.labels_info_widget.setObjectName(u"labels_info_widget")
        self.horizontalLayout_10 = QHBoxLayout(self.labels_info_widget)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.labels_info_table = QTableWidget(self.labels_info_widget)
        if (self.labels_info_table.columnCount() < 3):
            self.labels_info_table.setColumnCount(3)
        __qtablewidgetitem22 = QTableWidgetItem()
        self.labels_info_table.setHorizontalHeaderItem(0, __qtablewidgetitem22)
        __qtablewidgetitem23 = QTableWidgetItem()
        self.labels_info_table.setHorizontalHeaderItem(1, __qtablewidgetitem23)
        __qtablewidgetitem24 = QTableWidgetItem()
        self.labels_info_table.setHorizontalHeaderItem(2, __qtablewidgetitem24)
        self.labels_info_table.setObjectName(u"labels_info_table")
        sizePolicy1.setHeightForWidth(self.labels_info_table.sizePolicy().hasHeightForWidth())
        self.labels_info_table.setSizePolicy(sizePolicy1)

        self.horizontalLayout_10.addWidget(self.labels_info_table)

        self.labels_info_chart = QWidget(self.labels_info_widget)
        self.labels_info_chart.setObjectName(u"labels_info_chart")
        self.verticalLayout_36 = QVBoxLayout(self.labels_info_chart)
        self.verticalLayout_36.setObjectName(u"verticalLayout_36")

        self.horizontalLayout_10.addWidget(self.labels_info_chart)


        self.verticalLayout_35.addWidget(self.labels_info_widget)

        self.stackedWidget.addWidget(self.labels_info)

        self.verticalLayout_22.addWidget(self.stackedWidget)

        self.widget_botones_labels = QWidget(self.widget_labels)
        self.widget_botones_labels.setObjectName(u"widget_botones_labels")
        self.horizontalLayout_4 = QHBoxLayout(self.widget_botones_labels)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.action_sellos_decade = QPushButton(self.widget_botones_labels)
        self.action_sellos_decade.setObjectName(u"action_sellos_decade")

        self.horizontalLayout_4.addWidget(self.action_sellos_decade)

        self.action_sellos_porcentajes = QPushButton(self.widget_botones_labels)
        self.action_sellos_porcentajes.setObjectName(u"action_sellos_porcentajes")

        self.horizontalLayout_4.addWidget(self.action_sellos_porcentajes)

        self.action_sellos_artistas = QPushButton(self.widget_botones_labels)
        self.action_sellos_artistas.setObjectName(u"action_sellos_artistas")

        self.horizontalLayout_4.addWidget(self.action_sellos_artistas)

        self.action_sellos_albumes = QPushButton(self.widget_botones_labels)
        self.action_sellos_albumes.setObjectName(u"action_sellos_albumes")

        self.horizontalLayout_4.addWidget(self.action_sellos_albumes)

        self.action_sellos_por_genero = QPushButton(self.widget_botones_labels)
        self.action_sellos_por_genero.setObjectName(u"action_sellos_por_genero")

        self.horizontalLayout_4.addWidget(self.action_sellos_por_genero)

        self.action_sellos_info = QPushButton(self.widget_botones_labels)
        self.action_sellos_info.setObjectName(u"action_sellos_info")

        self.horizontalLayout_4.addWidget(self.action_sellos_info)


        self.verticalLayout_22.addWidget(self.widget_botones_labels)


        self.verticalLayout_labels.addWidget(self.widget_labels)

        self.stacked_widget.addWidget(self.page_labels)
        self.page_time = QWidget()
        self.page_time.setObjectName(u"page_time")
        self.verticalLayout_time = QVBoxLayout(self.page_time)
        self.verticalLayout_time.setObjectName(u"verticalLayout_time")
        self.verticalLayout_time.setContentsMargins(0, 0, 0, 0)
        self.label_time_title = QLabel(self.page_time)
        self.label_time_title.setObjectName(u"label_time_title")

        self.verticalLayout_time.addWidget(self.label_time_title)

        self.stackedWidget_time = QStackedWidget(self.page_time)
        self.stackedWidget_time.setObjectName(u"stackedWidget_time")
        self.time_page_inicio = QWidget()
        self.time_page_inicio.setObjectName(u"time_page_inicio")
        self.verticalLayout_60 = QVBoxLayout(self.time_page_inicio)
        self.verticalLayout_60.setObjectName(u"verticalLayout_60")
        self.verticalLayout_60.setContentsMargins(0, 0, 0, 0)
        self.splitter_time = QSplitter(self.time_page_inicio)
        self.splitter_time.setObjectName(u"splitter_time")
        self.splitter_time.setOrientation(Qt.Orientation.Vertical)
        self.widget_time_top = QWidget(self.splitter_time)
        self.widget_time_top.setObjectName(u"widget_time_top")
        self.verticalLayout_time_top = QVBoxLayout(self.widget_time_top)
        self.verticalLayout_time_top.setObjectName(u"verticalLayout_time_top")
        self.verticalLayout_time_top.setContentsMargins(0, 0, 0, 0)
        self.label_year_title = QLabel(self.widget_time_top)
        self.label_year_title.setObjectName(u"label_year_title")

        self.verticalLayout_time_top.addWidget(self.label_year_title)

        self.chart_container_years = QWidget(self.widget_time_top)
        self.chart_container_years.setObjectName(u"chart_container_years")
        self.verticalLayout_13 = QVBoxLayout(self.chart_container_years)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.verticalLayout_13.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_time_top.addWidget(self.chart_container_years)

        self.splitter_time.addWidget(self.widget_time_top)
        self.widget_time_bottom = QWidget(self.splitter_time)
        self.widget_time_bottom.setObjectName(u"widget_time_bottom")
        self.horizontalLayout_25 = QHBoxLayout(self.widget_time_bottom)
        self.horizontalLayout_25.setObjectName(u"horizontalLayout_25")
        self.horizontalLayout_25.setContentsMargins(0, 0, 0, 0)
        self.chart_container_decades = QWidget(self.widget_time_bottom)
        self.chart_container_decades.setObjectName(u"chart_container_decades")
        self.verticalLayout_12 = QVBoxLayout(self.chart_container_decades)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.verticalLayout_12.setContentsMargins(0, 0, 0, 0)
        self.widget_17 = QWidget(self.chart_container_decades)
        self.widget_17.setObjectName(u"widget_17")
        self.verticalLayout_58 = QVBoxLayout(self.widget_17)
        self.verticalLayout_58.setObjectName(u"verticalLayout_58")
        self.verticalLayout_58.setContentsMargins(0, 0, 0, 0)
        self.label_decade_dist_title = QLabel(self.widget_17)
        self.label_decade_dist_title.setObjectName(u"label_decade_dist_title")

        self.verticalLayout_58.addWidget(self.label_decade_dist_title)

        self.table_decades = QTableWidget(self.widget_17)
        if (self.table_decades.columnCount() < 2):
            self.table_decades.setColumnCount(2)
        __qtablewidgetitem25 = QTableWidgetItem()
        self.table_decades.setHorizontalHeaderItem(0, __qtablewidgetitem25)
        __qtablewidgetitem26 = QTableWidgetItem()
        self.table_decades.setHorizontalHeaderItem(1, __qtablewidgetitem26)
        self.table_decades.setObjectName(u"table_decades")

        self.verticalLayout_58.addWidget(self.table_decades)


        self.verticalLayout_12.addWidget(self.widget_17)


        self.horizontalLayout_25.addWidget(self.chart_container_decades)

        self.widget_20 = QWidget(self.widget_time_bottom)
        self.widget_20.setObjectName(u"widget_20")
        self.verticalLayout_59 = QVBoxLayout(self.widget_20)
        self.verticalLayout_59.setObjectName(u"verticalLayout_59")
        self.verticalLayout_59.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_25.addWidget(self.widget_20)

        self.splitter_time.addWidget(self.widget_time_bottom)

        self.verticalLayout_60.addWidget(self.splitter_time)

        self.stackedWidget_time.addWidget(self.time_page_inicio)
        self.ads = QWidget()
        self.ads.setObjectName(u"ads")
        self.horizontalLayout_28 = QHBoxLayout(self.ads)
        self.horizontalLayout_28.setObjectName(u"horizontalLayout_28")
        self.horizontalLayout_28.setContentsMargins(0, -1, 0, 0)
        self.stackedWidget_time.addWidget(self.ads)
        self.time_page_artists = QWidget()
        self.time_page_artists.setObjectName(u"time_page_artists")
        self.verticalLayout_65 = QVBoxLayout(self.time_page_artists)
        self.verticalLayout_65.setObjectName(u"verticalLayout_65")
        self.verticalLayout_65.setContentsMargins(0, 0, 0, 0)
        self.widget_time_artists_top = QWidget(self.time_page_artists)
        self.widget_time_artists_top.setObjectName(u"widget_time_artists_top")
        self.horizontalLayout_36 = QHBoxLayout(self.widget_time_artists_top)
        self.horizontalLayout_36.setObjectName(u"horizontalLayout_36")
        self.widget_25 = QWidget(self.widget_time_artists_top)
        self.widget_25.setObjectName(u"widget_25")
        self.verticalLayout_77 = QVBoxLayout(self.widget_25)
        self.verticalLayout_77.setObjectName(u"verticalLayout_77")
        self.table_time_artists_top = QTableWidget(self.widget_25)
        self.table_time_artists_top.setObjectName(u"table_time_artists_top")

        self.verticalLayout_77.addWidget(self.table_time_artists_top)


        self.horizontalLayout_36.addWidget(self.widget_25)

        self.chart_time_artists_top = QWidget(self.widget_time_artists_top)
        self.chart_time_artists_top.setObjectName(u"chart_time_artists_top")
        self.verticalLayout_80 = QVBoxLayout(self.chart_time_artists_top)
        self.verticalLayout_80.setObjectName(u"verticalLayout_80")

        self.horizontalLayout_36.addWidget(self.chart_time_artists_top)


        self.verticalLayout_65.addWidget(self.widget_time_artists_top)

        self.widget_time_artists_bott = QWidget(self.time_page_artists)
        self.widget_time_artists_bott.setObjectName(u"widget_time_artists_bott")
        self.horizontalLayout_37 = QHBoxLayout(self.widget_time_artists_bott)
        self.horizontalLayout_37.setObjectName(u"horizontalLayout_37")
        self.horizontalLayout_37.setContentsMargins(0, 0, 0, 0)
        self.widget_27 = QWidget(self.widget_time_artists_bott)
        self.widget_27.setObjectName(u"widget_27")
        self.verticalLayout_78 = QVBoxLayout(self.widget_27)
        self.verticalLayout_78.setObjectName(u"verticalLayout_78")
        self.verticalLayout_78.setContentsMargins(0, 0, 0, 0)
        self.table_time_artists_bott = QTableWidget(self.widget_27)
        self.table_time_artists_bott.setObjectName(u"table_time_artists_bott")

        self.verticalLayout_78.addWidget(self.table_time_artists_bott)


        self.horizontalLayout_37.addWidget(self.widget_27)

        self.chart_time_artists_bott = QWidget(self.widget_time_artists_bott)
        self.chart_time_artists_bott.setObjectName(u"chart_time_artists_bott")
        self.verticalLayout_79 = QVBoxLayout(self.chart_time_artists_bott)
        self.verticalLayout_79.setObjectName(u"verticalLayout_79")
        self.verticalLayout_79.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_37.addWidget(self.chart_time_artists_bott)


        self.verticalLayout_65.addWidget(self.widget_time_artists_bott)

        self.stackedWidget_time.addWidget(self.time_page_artists)
        self.time_page_info = QWidget()
        self.time_page_info.setObjectName(u"time_page_info")
        self.horizontalLayout_31 = QHBoxLayout(self.time_page_info)
        self.horizontalLayout_31.setObjectName(u"horizontalLayout_31")
        self.horizontalLayout_31.setContentsMargins(0, 0, 0, 0)
        self.widget_time_info = QWidget(self.time_page_info)
        self.widget_time_info.setObjectName(u"widget_time_info")
        self.verticalLayout_71 = QVBoxLayout(self.widget_time_info)
        self.verticalLayout_71.setObjectName(u"verticalLayout_71")
        self.verticalLayout_71.setContentsMargins(0, 0, 0, 0)
        self.table_time_info = QTableWidget(self.widget_time_info)
        self.table_time_info.setObjectName(u"table_time_info")

        self.verticalLayout_71.addWidget(self.table_time_info)


        self.horizontalLayout_31.addWidget(self.widget_time_info)

        self.chart_time_info = QWidget(self.time_page_info)
        self.chart_time_info.setObjectName(u"chart_time_info")
        self.verticalLayout_72 = QVBoxLayout(self.chart_time_info)
        self.verticalLayout_72.setObjectName(u"verticalLayout_72")
        self.verticalLayout_72.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_31.addWidget(self.chart_time_info)

        self.stackedWidget_time.addWidget(self.time_page_info)
        self.time_page_listens = QWidget()
        self.time_page_listens.setObjectName(u"time_page_listens")
        self.horizontalLayout_33 = QHBoxLayout(self.time_page_listens)
        self.horizontalLayout_33.setObjectName(u"horizontalLayout_33")
        self.horizontalLayout_33.setContentsMargins(0, 0, 0, 0)
        self.widget_time_listens = QWidget(self.time_page_listens)
        self.widget_time_listens.setObjectName(u"widget_time_listens")
        self.verticalLayout_75 = QVBoxLayout(self.widget_time_listens)
        self.verticalLayout_75.setObjectName(u"verticalLayout_75")
        self.verticalLayout_75.setContentsMargins(0, 0, 0, 0)
        self.table_time_listens = QTableWidget(self.widget_time_listens)
        self.table_time_listens.setObjectName(u"table_time_listens")

        self.verticalLayout_75.addWidget(self.table_time_listens)


        self.horizontalLayout_33.addWidget(self.widget_time_listens)

        self.chart_time_listens = QWidget(self.time_page_listens)
        self.chart_time_listens.setObjectName(u"chart_time_listens")
        self.verticalLayout_76 = QVBoxLayout(self.chart_time_listens)
        self.verticalLayout_76.setObjectName(u"verticalLayout_76")
        self.verticalLayout_76.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_33.addWidget(self.chart_time_listens)

        self.stackedWidget_time.addWidget(self.time_page_listens)
        self.time_page_feeds = QWidget()
        self.time_page_feeds.setObjectName(u"time_page_feeds")
        self.horizontalLayout_29 = QHBoxLayout(self.time_page_feeds)
        self.horizontalLayout_29.setObjectName(u"horizontalLayout_29")
        self.horizontalLayout_29.setContentsMargins(0, 0, 0, 0)
        self.widget_time_feeds = QWidget(self.time_page_feeds)
        self.widget_time_feeds.setObjectName(u"widget_time_feeds")
        self.verticalLayout_67 = QVBoxLayout(self.widget_time_feeds)
        self.verticalLayout_67.setObjectName(u"verticalLayout_67")
        self.verticalLayout_67.setContentsMargins(0, 0, 0, 0)
        self.table_time_feeds = QTableWidget(self.widget_time_feeds)
        self.table_time_feeds.setObjectName(u"table_time_feeds")

        self.verticalLayout_67.addWidget(self.table_time_feeds)


        self.horizontalLayout_29.addWidget(self.widget_time_feeds)

        self.chart_time_feeds = QWidget(self.time_page_feeds)
        self.chart_time_feeds.setObjectName(u"chart_time_feeds")
        self.verticalLayout_68 = QVBoxLayout(self.chart_time_feeds)
        self.verticalLayout_68.setObjectName(u"verticalLayout_68")
        self.verticalLayout_68.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_29.addWidget(self.chart_time_feeds)

        self.stackedWidget_time.addWidget(self.time_page_feeds)
        self.time_page_labels = QWidget()
        self.time_page_labels.setObjectName(u"time_page_labels")
        self.verticalLayout_61 = QVBoxLayout(self.time_page_labels)
        self.verticalLayout_61.setObjectName(u"verticalLayout_61")
        self.verticalLayout_61.setContentsMargins(0, 0, 0, 0)
        self.widget_time_labels_top = QWidget(self.time_page_labels)
        self.widget_time_labels_top.setObjectName(u"widget_time_labels_top")
        self.horizontalLayout_40 = QHBoxLayout(self.widget_time_labels_top)
        self.horizontalLayout_40.setObjectName(u"horizontalLayout_40")
        self.horizontalLayout_40.setContentsMargins(0, 0, 0, 0)
        self.widget_29 = QWidget(self.widget_time_labels_top)
        self.widget_29.setObjectName(u"widget_29")
        self.verticalLayout_85 = QVBoxLayout(self.widget_29)
        self.verticalLayout_85.setObjectName(u"verticalLayout_85")
        self.verticalLayout_85.setContentsMargins(0, 0, 0, 0)
        self.table_time_labels_top = QTableWidget(self.widget_29)
        self.table_time_labels_top.setObjectName(u"table_time_labels_top")

        self.verticalLayout_85.addWidget(self.table_time_labels_top)


        self.horizontalLayout_40.addWidget(self.widget_29)

        self.chart_time_labels_top = QWidget(self.widget_time_labels_top)
        self.chart_time_labels_top.setObjectName(u"chart_time_labels_top")
        self.verticalLayout_86 = QVBoxLayout(self.chart_time_labels_top)
        self.verticalLayout_86.setObjectName(u"verticalLayout_86")
        self.verticalLayout_86.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_40.addWidget(self.chart_time_labels_top)


        self.verticalLayout_61.addWidget(self.widget_time_labels_top)

        self.widget_time_labels_bott = QWidget(self.time_page_labels)
        self.widget_time_labels_bott.setObjectName(u"widget_time_labels_bott")
        self.horizontalLayout_41 = QHBoxLayout(self.widget_time_labels_bott)
        self.horizontalLayout_41.setObjectName(u"horizontalLayout_41")
        self.horizontalLayout_41.setContentsMargins(0, 0, 0, 0)
        self.widget_30 = QWidget(self.widget_time_labels_bott)
        self.widget_30.setObjectName(u"widget_30")
        self.verticalLayout_87 = QVBoxLayout(self.widget_30)
        self.verticalLayout_87.setObjectName(u"verticalLayout_87")
        self.verticalLayout_87.setContentsMargins(0, 0, 0, 0)
        self.scrollArea_2 = QScrollArea(self.widget_30)
        self.scrollArea_2.setObjectName(u"scrollArea_2")
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 874, 285))
        self.verticalLayout_62 = QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_62.setObjectName(u"verticalLayout_62")
        self.verticalLayout_62.setContentsMargins(0, 0, 0, 0)
        self.table_time_labels_bott = QTableWidget(self.scrollAreaWidgetContents_2)
        self.table_time_labels_bott.setObjectName(u"table_time_labels_bott")

        self.verticalLayout_62.addWidget(self.table_time_labels_bott)

        self.scrollArea_2.setWidget(self.scrollAreaWidgetContents_2)

        self.verticalLayout_87.addWidget(self.scrollArea_2)


        self.horizontalLayout_41.addWidget(self.widget_30)

        self.chart_time_labels_bott = QWidget(self.widget_time_labels_bott)
        self.chart_time_labels_bott.setObjectName(u"chart_time_labels_bott")
        self.verticalLayout_88 = QVBoxLayout(self.chart_time_labels_bott)
        self.verticalLayout_88.setObjectName(u"verticalLayout_88")
        self.verticalLayout_88.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_41.addWidget(self.chart_time_labels_bott)


        self.verticalLayout_61.addWidget(self.widget_time_labels_bott)

        self.stackedWidget_time.addWidget(self.time_page_labels)
        self.time_page_genres = QWidget()
        self.time_page_genres.setObjectName(u"time_page_genres")
        self.verticalLayout_74 = QVBoxLayout(self.time_page_genres)
        self.verticalLayout_74.setObjectName(u"verticalLayout_74")
        self.verticalLayout_74.setContentsMargins(0, 0, 0, 0)
        self.widget_33 = QWidget(self.time_page_genres)
        self.widget_33.setObjectName(u"widget_33")
        self.horizontalLayout_43 = QHBoxLayout(self.widget_33)
        self.horizontalLayout_43.setObjectName(u"horizontalLayout_43")
        self.horizontalLayout_43.setContentsMargins(0, 0, 0, 0)
        self.table_time_genres = QTableWidget(self.widget_33)
        self.table_time_genres.setObjectName(u"table_time_genres")

        self.horizontalLayout_43.addWidget(self.table_time_genres)

        self.chart_time_genres = QWidget(self.widget_33)
        self.chart_time_genres.setObjectName(u"chart_time_genres")
        self.verticalLayout_70 = QVBoxLayout(self.chart_time_genres)
        self.verticalLayout_70.setObjectName(u"verticalLayout_70")
        self.verticalLayout_70.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_43.addWidget(self.chart_time_genres)


        self.verticalLayout_74.addWidget(self.widget_33)

        self.widget_32 = QWidget(self.time_page_genres)
        self.widget_32.setObjectName(u"widget_32")
        self.horizontalLayout_30 = QHBoxLayout(self.widget_32)
        self.horizontalLayout_30.setObjectName(u"horizontalLayout_30")
        self.horizontalLayout_30.setContentsMargins(0, 0, 0, 0)
        self.widget_time_genres = QWidget(self.widget_32)
        self.widget_time_genres.setObjectName(u"widget_time_genres")
        self.verticalLayout_69 = QVBoxLayout(self.widget_time_genres)
        self.verticalLayout_69.setObjectName(u"verticalLayout_69")
        self.verticalLayout_69.setContentsMargins(0, 0, 0, 0)
        self.table_time_genre_bott = QTableWidget(self.widget_time_genres)
        self.table_time_genre_bott.setObjectName(u"table_time_genre_bott")

        self.verticalLayout_69.addWidget(self.table_time_genre_bott)


        self.horizontalLayout_30.addWidget(self.widget_time_genres)

        self.chart_time_genres_bott = QWidget(self.widget_32)
        self.chart_time_genres_bott.setObjectName(u"chart_time_genres_bott")
        self.verticalLayout_92 = QVBoxLayout(self.chart_time_genres_bott)
        self.verticalLayout_92.setObjectName(u"verticalLayout_92")
        self.verticalLayout_92.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_30.addWidget(self.chart_time_genres_bott)


        self.verticalLayout_74.addWidget(self.widget_32)

        self.stackedWidget_time.addWidget(self.time_page_genres)
        self.time_page_albums = QWidget()
        self.time_page_albums.setObjectName(u"time_page_albums")
        self.verticalLayout_66 = QVBoxLayout(self.time_page_albums)
        self.verticalLayout_66.setObjectName(u"verticalLayout_66")
        self.verticalLayout_66.setContentsMargins(0, 0, 0, 0)
        self.widget_time_albums_top = QWidget(self.time_page_albums)
        self.widget_time_albums_top.setObjectName(u"widget_time_albums_top")
        self.horizontalLayout_38 = QHBoxLayout(self.widget_time_albums_top)
        self.horizontalLayout_38.setObjectName(u"horizontalLayout_38")
        self.horizontalLayout_38.setContentsMargins(0, 0, 0, 0)
        self.widget_26 = QWidget(self.widget_time_albums_top)
        self.widget_26.setObjectName(u"widget_26")
        self.verticalLayout_81 = QVBoxLayout(self.widget_26)
        self.verticalLayout_81.setObjectName(u"verticalLayout_81")
        self.verticalLayout_81.setContentsMargins(0, 0, 0, 0)
        self.table_time_albums_top = QTableWidget(self.widget_26)
        self.table_time_albums_top.setObjectName(u"table_time_albums_top")

        self.verticalLayout_81.addWidget(self.table_time_albums_top)


        self.horizontalLayout_38.addWidget(self.widget_26)

        self.chart_time_albums_top = QWidget(self.widget_time_albums_top)
        self.chart_time_albums_top.setObjectName(u"chart_time_albums_top")
        self.verticalLayout_82 = QVBoxLayout(self.chart_time_albums_top)
        self.verticalLayout_82.setObjectName(u"verticalLayout_82")
        self.verticalLayout_82.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_38.addWidget(self.chart_time_albums_top)


        self.verticalLayout_66.addWidget(self.widget_time_albums_top)

        self.widget_time_albums_bott = QWidget(self.time_page_albums)
        self.widget_time_albums_bott.setObjectName(u"widget_time_albums_bott")
        self.horizontalLayout_39 = QHBoxLayout(self.widget_time_albums_bott)
        self.horizontalLayout_39.setObjectName(u"horizontalLayout_39")
        self.horizontalLayout_39.setContentsMargins(0, 0, 0, 0)
        self.widget_28 = QWidget(self.widget_time_albums_bott)
        self.widget_28.setObjectName(u"widget_28")
        self.verticalLayout_83 = QVBoxLayout(self.widget_28)
        self.verticalLayout_83.setObjectName(u"verticalLayout_83")
        self.verticalLayout_83.setContentsMargins(0, 0, 0, 0)
        self.table_time_albums_bott = QTableWidget(self.widget_28)
        self.table_time_albums_bott.setObjectName(u"table_time_albums_bott")

        self.verticalLayout_83.addWidget(self.table_time_albums_bott)


        self.horizontalLayout_39.addWidget(self.widget_28)

        self.chart_time_albums_bott = QWidget(self.widget_time_albums_bott)
        self.chart_time_albums_bott.setObjectName(u"chart_time_albums_bott")
        self.verticalLayout_84 = QVBoxLayout(self.chart_time_albums_bott)
        self.verticalLayout_84.setObjectName(u"verticalLayout_84")
        self.verticalLayout_84.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_39.addWidget(self.chart_time_albums_bott)


        self.verticalLayout_66.addWidget(self.widget_time_albums_bott)

        self.stackedWidget_time.addWidget(self.time_page_albums)

        self.verticalLayout_time.addWidget(self.stackedWidget_time)

        self.widget_21 = QWidget(self.page_time)
        self.widget_21.setObjectName(u"widget_21")
        self.horizontalLayout_26 = QHBoxLayout(self.widget_21)
        self.horizontalLayout_26.setObjectName(u"horizontalLayout_26")
        self.horizontalLayout_26.setContentsMargins(0, 0, 0, 0)
        self.action_artist = QPushButton(self.widget_21)
        self.action_artist.setObjectName(u"action_artist")

        self.horizontalLayout_26.addWidget(self.action_artist)

        self.action_album = QPushButton(self.widget_21)
        self.action_album.setObjectName(u"action_album")

        self.horizontalLayout_26.addWidget(self.action_album)

        self.action_genres = QPushButton(self.widget_21)
        self.action_genres.setObjectName(u"action_genres")

        self.horizontalLayout_26.addWidget(self.action_genres)

        self.action_labels = QPushButton(self.widget_21)
        self.action_labels.setObjectName(u"action_labels")

        self.horizontalLayout_26.addWidget(self.action_labels)

        self.action_feeds = QPushButton(self.widget_21)
        self.action_feeds.setObjectName(u"action_feeds")

        self.horizontalLayout_26.addWidget(self.action_feeds)

        self.action_listens = QPushButton(self.widget_21)
        self.action_listens.setObjectName(u"action_listens")

        self.horizontalLayout_26.addWidget(self.action_listens)

        self.action_info = QPushButton(self.widget_21)
        self.action_info.setObjectName(u"action_info")

        self.horizontalLayout_26.addWidget(self.action_info)


        self.verticalLayout_time.addWidget(self.widget_21)

        self.stacked_widget.addWidget(self.page_time)
        self.page_artists = QWidget()
        self.page_artists.setObjectName(u"page_artists")
        self.verticalLayout_63 = QVBoxLayout(self.page_artists)
        self.verticalLayout_63.setObjectName(u"verticalLayout_63")
        self.verticalLayout_63.setContentsMargins(0, 0, 0, 0)
        self.widget_2 = QWidget(self.page_artists)
        self.widget_2.setObjectName(u"widget_2")
        self.verticalLayout_64 = QVBoxLayout(self.widget_2)
        self.verticalLayout_64.setObjectName(u"verticalLayout_64")
        self.verticalLayout_64.setContentsMargins(0, 0, 0, 0)
        self.widget_24 = QWidget(self.widget_2)
        self.widget_24.setObjectName(u"widget_24")
        sizePolicy.setHeightForWidth(self.widget_24.sizePolicy().hasHeightForWidth())
        self.widget_24.setSizePolicy(sizePolicy)
        self.horizontalLayout_35 = QHBoxLayout(self.widget_24)
        self.horizontalLayout_35.setObjectName(u"horizontalLayout_35")
        self.horizontalLayout_35.setContentsMargins(0, 0, 0, 0)
        self.artista_label = QLabel(self.widget_24)
        self.artista_label.setObjectName(u"artista_label")
        sizePolicy.setHeightForWidth(self.artista_label.sizePolicy().hasHeightForWidth())
        self.artista_label.setSizePolicy(sizePolicy)

        self.horizontalLayout_35.addWidget(self.artista_label)


        self.verticalLayout_64.addWidget(self.widget_24)

        self.widget_23 = QWidget(self.widget_2)
        self.widget_23.setObjectName(u"widget_23")
        self.horizontalLayout_32 = QHBoxLayout(self.widget_23)
        self.horizontalLayout_32.setObjectName(u"horizontalLayout_32")
        self.horizontalLayout_32.setContentsMargins(0, 0, 0, 0)
        self.stackedWidget_24 = QStackedWidget(self.widget_23)
        self.stackedWidget_24.setObjectName(u"stackedWidget_24")
        self.stackedWidget_24Page1_3 = QWidget()
        self.stackedWidget_24Page1_3.setObjectName(u"stackedWidget_24Page1_3")
        self.verticalLayout_89 = QVBoxLayout(self.stackedWidget_24Page1_3)
        self.verticalLayout_89.setObjectName(u"verticalLayout_89")
        self.verticalLayout_89.setContentsMargins(0, 0, 0, 0)
        self.tableWidget_3 = QTableWidget(self.stackedWidget_24Page1_3)
        if (self.tableWidget_3.columnCount() < 4):
            self.tableWidget_3.setColumnCount(4)
        __qtablewidgetitem27 = QTableWidgetItem()
        self.tableWidget_3.setHorizontalHeaderItem(0, __qtablewidgetitem27)
        __qtablewidgetitem28 = QTableWidgetItem()
        self.tableWidget_3.setHorizontalHeaderItem(1, __qtablewidgetitem28)
        __qtablewidgetitem29 = QTableWidgetItem()
        self.tableWidget_3.setHorizontalHeaderItem(2, __qtablewidgetitem29)
        __qtablewidgetitem30 = QTableWidgetItem()
        self.tableWidget_3.setHorizontalHeaderItem(3, __qtablewidgetitem30)
        self.tableWidget_3.setObjectName(u"tableWidget_3")
        self.tableWidget_3.setSortingEnabled(True)

        self.verticalLayout_89.addWidget(self.tableWidget_3)

        self.stackedWidget_24.addWidget(self.stackedWidget_24Page1_3)

        self.horizontalLayout_32.addWidget(self.stackedWidget_24)

        self.widget_31 = QWidget(self.widget_23)
        self.widget_31.setObjectName(u"widget_31")
        self.verticalLayout_90 = QVBoxLayout(self.widget_31)
        self.verticalLayout_90.setObjectName(u"verticalLayout_90")
        self.verticalLayout_90.setContentsMargins(0, 0, 0, 0)
        self.stackedWidget_artist = QStackedWidget(self.widget_31)
        self.stackedWidget_artist.setObjectName(u"stackedWidget_artist")
        self.page = QWidget()
        self.page.setObjectName(u"page")
        self.stackedWidget_artist.addWidget(self.page)
        self.page_2 = QWidget()
        self.page_2.setObjectName(u"page_2")
        self.stackedWidget_artist.addWidget(self.page_2)

        self.verticalLayout_90.addWidget(self.stackedWidget_artist)


        self.horizontalLayout_32.addWidget(self.widget_31)


        self.verticalLayout_64.addWidget(self.widget_23)


        self.verticalLayout_63.addWidget(self.widget_2)

        self.widget_artists = QWidget(self.page_artists)
        self.widget_artists.setObjectName(u"widget_artists")
        sizePolicy.setHeightForWidth(self.widget_artists.sizePolicy().hasHeightForWidth())
        self.widget_artists.setSizePolicy(sizePolicy)
        self.horizontalLayout_27 = QHBoxLayout(self.widget_artists)
        self.horizontalLayout_27.setObjectName(u"horizontalLayout_27")
        self.horizontalLayout_27.setContentsMargins(0, 0, 0, 0)
        self.action_artist_home = QPushButton(self.widget_artists)
        self.action_artist_home.setObjectName(u"action_artist_home")

        self.horizontalLayout_27.addWidget(self.action_artist_home)

        self.action_artist_time = QPushButton(self.widget_artists)
        self.action_artist_time.setObjectName(u"action_artist_time")

        self.horizontalLayout_27.addWidget(self.action_artist_time)

        self.action_artist_conciertos = QPushButton(self.widget_artists)
        self.action_artist_conciertos.setObjectName(u"action_artist_conciertos")

        self.horizontalLayout_27.addWidget(self.action_artist_conciertos)

        self.action_artist_genres = QPushButton(self.widget_artists)
        self.action_artist_genres.setObjectName(u"action_artist_genres")

        self.horizontalLayout_27.addWidget(self.action_artist_genres)

        self.action_artist_feeds = QPushButton(self.widget_artists)
        self.action_artist_feeds.setObjectName(u"action_artist_feeds")

        self.horizontalLayout_27.addWidget(self.action_artist_feeds)

        self.action_artist_label = QPushButton(self.widget_artists)
        self.action_artist_label.setObjectName(u"action_artist_label")

        self.horizontalLayout_27.addWidget(self.action_artist_label)

        self.action_artist_discog = QPushButton(self.widget_artists)
        self.action_artist_discog.setObjectName(u"action_artist_discog")

        self.horizontalLayout_27.addWidget(self.action_artist_discog)

        self.action_artist_scrobbles = QPushButton(self.widget_artists)
        self.action_artist_scrobbles.setObjectName(u"action_artist_scrobbles")

        self.horizontalLayout_27.addWidget(self.action_artist_scrobbles)

        self.action_artist_prod = QPushButton(self.widget_artists)
        self.action_artist_prod.setObjectName(u"action_artist_prod")

        self.horizontalLayout_27.addWidget(self.action_artist_prod)

        self.action_artist_collaborators = QPushButton(self.widget_artists)
        self.action_artist_collaborators.setObjectName(u"action_artist_collaborators")

        self.horizontalLayout_27.addWidget(self.action_artist_collaborators)


        self.verticalLayout_63.addWidget(self.widget_artists)

        self.stacked_widget.addWidget(self.page_artists)
        self.page_countries = QWidget()
        self.page_countries.setObjectName(u"page_countries")
        self.verticalLayout_countries = QVBoxLayout(self.page_countries)
        self.verticalLayout_countries.setObjectName(u"verticalLayout_countries")
        self.verticalLayout_countries.setContentsMargins(0, 0, 0, 0)
        self.label_countries_title = QLabel(self.page_countries)
        self.label_countries_title.setObjectName(u"label_countries_title")
        sizePolicy.setHeightForWidth(self.label_countries_title.sizePolicy().hasHeightForWidth())
        self.label_countries_title.setSizePolicy(sizePolicy)

        self.verticalLayout_countries.addWidget(self.label_countries_title)

        self.widget_11 = QWidget(self.page_countries)
        self.widget_11.setObjectName(u"widget_11")
        self.horizontalLayout_11 = QHBoxLayout(self.widget_11)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_countries_table = QWidget(self.widget_11)
        self.verticalLayout_countries_table.setObjectName(u"verticalLayout_countries_table")
        self.verticalLayout_38 = QVBoxLayout(self.verticalLayout_countries_table)
        self.verticalLayout_38.setObjectName(u"verticalLayout_38")
        self.verticalLayout_38.setContentsMargins(0, 0, 0, 0)
        self.table_countries = QTableWidget(self.verticalLayout_countries_table)
        if (self.table_countries.columnCount() < 2):
            self.table_countries.setColumnCount(2)
        __qtablewidgetitem31 = QTableWidgetItem()
        self.table_countries.setHorizontalHeaderItem(0, __qtablewidgetitem31)
        __qtablewidgetitem32 = QTableWidgetItem()
        self.table_countries.setHorizontalHeaderItem(1, __qtablewidgetitem32)
        self.table_countries.setObjectName(u"table_countries")
        sizePolicy1.setHeightForWidth(self.table_countries.sizePolicy().hasHeightForWidth())
        self.table_countries.setSizePolicy(sizePolicy1)

        self.verticalLayout_38.addWidget(self.table_countries)


        self.horizontalLayout_11.addWidget(self.verticalLayout_countries_table)

        self.splitter_countries = QSplitter(self.widget_11)
        self.splitter_countries.setObjectName(u"splitter_countries")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.splitter_countries.sizePolicy().hasHeightForWidth())
        self.splitter_countries.setSizePolicy(sizePolicy2)
        self.splitter_countries.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_11.addWidget(self.splitter_countries)

        self.widget_15 = QWidget(self.widget_11)
        self.widget_15.setObjectName(u"widget_15")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.widget_15.sizePolicy().hasHeightForWidth())
        self.widget_15.setSizePolicy(sizePolicy3)
        self.horizontalLayout_12 = QHBoxLayout(self.widget_15)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.horizontalLayout_12.setContentsMargins(0, 0, 0, 0)
        self.stackedWidget_countries = QStackedWidget(self.widget_15)
        self.stackedWidget_countries.setObjectName(u"stackedWidget_countries")
        sizePolicy3.setHeightForWidth(self.stackedWidget_countries.sizePolicy().hasHeightForWidth())
        self.stackedWidget_countries.setSizePolicy(sizePolicy3)
        self.verticalLayout_countries_chart = QWidget()
        self.verticalLayout_countries_chart.setObjectName(u"verticalLayout_countries_chart")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.verticalLayout_countries_chart.sizePolicy().hasHeightForWidth())
        self.verticalLayout_countries_chart.setSizePolicy(sizePolicy4)
        self.verticalLayout_40 = QVBoxLayout(self.verticalLayout_countries_chart)
        self.verticalLayout_40.setObjectName(u"verticalLayout_40")
        self.verticalLayout_40.setContentsMargins(0, 0, 0, 0)
        self.chart_container_countries = QWidget(self.verticalLayout_countries_chart)
        self.chart_container_countries.setObjectName(u"chart_container_countries")
        sizePolicy4.setHeightForWidth(self.chart_container_countries.sizePolicy().hasHeightForWidth())
        self.chart_container_countries.setSizePolicy(sizePolicy4)
        self.verticalLayout_3 = QVBoxLayout(self.chart_container_countries)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_40.addWidget(self.chart_container_countries)

        self.stackedWidget_countries.addWidget(self.verticalLayout_countries_chart)
        self.chart_countries_artists = QWidget()
        self.chart_countries_artists.setObjectName(u"chart_countries_artists")
        sizePolicy4.setHeightForWidth(self.chart_countries_artists.sizePolicy().hasHeightForWidth())
        self.chart_countries_artists.setSizePolicy(sizePolicy4)
        self.verticalLayout_39 = QVBoxLayout(self.chart_countries_artists)
        self.verticalLayout_39.setObjectName(u"verticalLayout_39")
        self.verticalLayout_39.setContentsMargins(0, 0, 0, 0)
        self.stackedWidget_countries.addWidget(self.chart_countries_artists)

        self.horizontalLayout_12.addWidget(self.stackedWidget_countries)


        self.horizontalLayout_11.addWidget(self.widget_15)


        self.verticalLayout_countries.addWidget(self.widget_11)

        self.widget_14 = QWidget(self.page_countries)
        self.widget_14.setObjectName(u"widget_14")
        self.horizontalLayout_13 = QHBoxLayout(self.widget_14)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.horizontalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.action_countries_artists = QPushButton(self.widget_14)
        self.action_countries_artists.setObjectName(u"action_countries_artists")

        self.horizontalLayout_13.addWidget(self.action_countries_artists)

        self.action_countries_album = QPushButton(self.widget_14)
        self.action_countries_album.setObjectName(u"action_countries_album")

        self.horizontalLayout_13.addWidget(self.action_countries_album)

        self.action_countries_labels = QPushButton(self.widget_14)
        self.action_countries_labels.setObjectName(u"action_countries_labels")

        self.horizontalLayout_13.addWidget(self.action_countries_labels)

        self.action_countries_feeds = QPushButton(self.widget_14)
        self.action_countries_feeds.setObjectName(u"action_countries_feeds")

        self.horizontalLayout_13.addWidget(self.action_countries_feeds)

        self.action_countries_genre = QPushButton(self.widget_14)
        self.action_countries_genre.setObjectName(u"action_countries_genre")

        self.horizontalLayout_13.addWidget(self.action_countries_genre)

        self.action_countries_time = QPushButton(self.widget_14)
        self.action_countries_time.setObjectName(u"action_countries_time")

        self.horizontalLayout_13.addWidget(self.action_countries_time)

        self.action_countries_listens = QPushButton(self.widget_14)
        self.action_countries_listens.setObjectName(u"action_countries_listens")

        self.horizontalLayout_13.addWidget(self.action_countries_listens)

        self.action_countries_info = QPushButton(self.widget_14)
        self.action_countries_info.setObjectName(u"action_countries_info")

        self.horizontalLayout_13.addWidget(self.action_countries_info)


        self.verticalLayout_countries.addWidget(self.widget_14)

        self.stacked_widget.addWidget(self.page_countries)
        self.page_feeds = QWidget()
        self.page_feeds.setObjectName(u"page_feeds")
        self.verticalLayout_feeds = QVBoxLayout(self.page_feeds)
        self.verticalLayout_feeds.setObjectName(u"verticalLayout_feeds")
        self.verticalLayout_feeds.setContentsMargins(0, 0, 0, 0)
        self.label_feeds_title = QLabel(self.page_feeds)
        self.label_feeds_title.setObjectName(u"label_feeds_title")

        self.verticalLayout_feeds.addWidget(self.label_feeds_title)

        self.stackedWidget_2 = QStackedWidget(self.page_feeds)
        self.stackedWidget_2.setObjectName(u"stackedWidget_2")
        self.feeds_entitys = QWidget()
        self.feeds_entitys.setObjectName(u"feeds_entitys")
        self.verticalLayout_44 = QVBoxLayout(self.feeds_entitys)
        self.verticalLayout_44.setObjectName(u"verticalLayout_44")
        self.verticalLayout_44.setContentsMargins(0, 0, 0, 0)
        self.splitter_feeds = QSplitter(self.feeds_entitys)
        self.splitter_feeds.setObjectName(u"splitter_feeds")
        self.splitter_feeds.setOrientation(Qt.Orientation.Vertical)
        self.widget_feeds_top = QWidget(self.splitter_feeds)
        self.widget_feeds_top.setObjectName(u"widget_feeds_top")
        self.horizontalLayout_14 = QHBoxLayout(self.widget_feeds_top)
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.horizontalLayout_14.setContentsMargins(0, 0, 0, 0)
        self.feed_entity_widget = QWidget(self.widget_feeds_top)
        self.feed_entity_widget.setObjectName(u"feed_entity_widget")
        sizePolicy2.setHeightForWidth(self.feed_entity_widget.sizePolicy().hasHeightForWidth())
        self.feed_entity_widget.setSizePolicy(sizePolicy2)
        self.verticalLayout_41 = QVBoxLayout(self.feed_entity_widget)
        self.verticalLayout_41.setObjectName(u"verticalLayout_41")
        self.verticalLayout_41.setContentsMargins(0, 0, 0, 0)
        self.label_entity_title = QLabel(self.feed_entity_widget)
        self.label_entity_title.setObjectName(u"label_entity_title")

        self.verticalLayout_41.addWidget(self.label_entity_title)

        self.table_entity = QTableWidget(self.feed_entity_widget)
        if (self.table_entity.columnCount() < 2):
            self.table_entity.setColumnCount(2)
        __qtablewidgetitem33 = QTableWidgetItem()
        self.table_entity.setHorizontalHeaderItem(0, __qtablewidgetitem33)
        __qtablewidgetitem34 = QTableWidgetItem()
        self.table_entity.setHorizontalHeaderItem(1, __qtablewidgetitem34)
        self.table_entity.setObjectName(u"table_entity")

        self.verticalLayout_41.addWidget(self.table_entity)


        self.horizontalLayout_14.addWidget(self.feed_entity_widget)

        self.chart_container_entity = QWidget(self.widget_feeds_top)
        self.chart_container_entity.setObjectName(u"chart_container_entity")
        self.verticalLayout_5 = QVBoxLayout(self.chart_container_entity)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_14.addWidget(self.chart_container_entity)

        self.splitter_feeds.addWidget(self.widget_feeds_top)
        self.widget_feeds_bottom = QWidget(self.splitter_feeds)
        self.widget_feeds_bottom.setObjectName(u"widget_feeds_bottom")
        self.horizontalLayout_15 = QHBoxLayout(self.widget_feeds_bottom)
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.horizontalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.feed_names_widget = QWidget(self.widget_feeds_bottom)
        self.feed_names_widget.setObjectName(u"feed_names_widget")
        self.verticalLayout_42 = QVBoxLayout(self.feed_names_widget)
        self.verticalLayout_42.setObjectName(u"verticalLayout_42")
        self.verticalLayout_42.setContentsMargins(0, 0, 0, 0)
        self.label_feeds_names = QLabel(self.feed_names_widget)
        self.label_feeds_names.setObjectName(u"label_feeds_names")

        self.verticalLayout_42.addWidget(self.label_feeds_names)

        self.table_feeds = QTableWidget(self.feed_names_widget)
        if (self.table_feeds.columnCount() < 2):
            self.table_feeds.setColumnCount(2)
        __qtablewidgetitem35 = QTableWidgetItem()
        self.table_feeds.setHorizontalHeaderItem(0, __qtablewidgetitem35)
        __qtablewidgetitem36 = QTableWidgetItem()
        self.table_feeds.setHorizontalHeaderItem(1, __qtablewidgetitem36)
        self.table_feeds.setObjectName(u"table_feeds")

        self.verticalLayout_42.addWidget(self.table_feeds)


        self.horizontalLayout_15.addWidget(self.feed_names_widget)

        self.chart_container_feeds = QWidget(self.widget_feeds_bottom)
        self.chart_container_feeds.setObjectName(u"chart_container_feeds")
        self.verticalLayout_4 = QVBoxLayout(self.chart_container_feeds)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_15.addWidget(self.chart_container_feeds)

        self.splitter_feeds.addWidget(self.widget_feeds_bottom)

        self.verticalLayout_44.addWidget(self.splitter_feeds)

        self.stackedWidget_2.addWidget(self.feeds_entitys)
        self.feeds_page_artists = QWidget()
        self.feeds_page_artists.setObjectName(u"feeds_page_artists")
        self.horizontalLayout_17 = QHBoxLayout(self.feeds_page_artists)
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.horizontalLayout_17.setContentsMargins(0, 0, 0, 0)
        self.feeds_artist_widget = QWidget(self.feeds_page_artists)
        self.feeds_artist_widget.setObjectName(u"feeds_artist_widget")
        self.verticalLayout_46 = QVBoxLayout(self.feeds_artist_widget)
        self.verticalLayout_46.setObjectName(u"verticalLayout_46")
        self.table_feeds_artists = QTableWidget(self.feeds_artist_widget)
        if (self.table_feeds_artists.columnCount() < 3):
            self.table_feeds_artists.setColumnCount(3)
        __qtablewidgetitem37 = QTableWidgetItem()
        self.table_feeds_artists.setHorizontalHeaderItem(0, __qtablewidgetitem37)
        __qtablewidgetitem38 = QTableWidgetItem()
        self.table_feeds_artists.setHorizontalHeaderItem(1, __qtablewidgetitem38)
        __qtablewidgetitem39 = QTableWidgetItem()
        self.table_feeds_artists.setHorizontalHeaderItem(2, __qtablewidgetitem39)
        self.table_feeds_artists.setObjectName(u"table_feeds_artists")

        self.verticalLayout_46.addWidget(self.table_feeds_artists)


        self.horizontalLayout_17.addWidget(self.feeds_artist_widget)

        self.chart_artists_widget = QWidget(self.feeds_page_artists)
        self.chart_artists_widget.setObjectName(u"chart_artists_widget")
        self.verticalLayout_45 = QVBoxLayout(self.chart_artists_widget)
        self.verticalLayout_45.setObjectName(u"verticalLayout_45")

        self.horizontalLayout_17.addWidget(self.chart_artists_widget)

        self.stackedWidget_2.addWidget(self.feeds_page_artists)
        self.feed_page_albums = QWidget()
        self.feed_page_albums.setObjectName(u"feed_page_albums")
        self.horizontalLayout_18 = QHBoxLayout(self.feed_page_albums)
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.horizontalLayout_18.setContentsMargins(0, 0, 0, 0)
        self.widget_16 = QWidget(self.feed_page_albums)
        self.widget_16.setObjectName(u"widget_16")
        self.verticalLayout_48 = QVBoxLayout(self.widget_16)
        self.verticalLayout_48.setObjectName(u"verticalLayout_48")
        self.verticalLayout_48.setContentsMargins(0, 0, 0, 0)
        self.table_feeds_albums = QTableWidget(self.widget_16)
        self.table_feeds_albums.setObjectName(u"table_feeds_albums")

        self.verticalLayout_48.addWidget(self.table_feeds_albums)


        self.horizontalLayout_18.addWidget(self.widget_16)

        self.charts_feeds_albums = QWidget(self.feed_page_albums)
        self.charts_feeds_albums.setObjectName(u"charts_feeds_albums")
        self.verticalLayout_47 = QVBoxLayout(self.charts_feeds_albums)
        self.verticalLayout_47.setObjectName(u"verticalLayout_47")
        self.verticalLayout_47.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_18.addWidget(self.charts_feeds_albums)

        self.stackedWidget_2.addWidget(self.feed_page_albums)
        self.feeds_page_genres = QWidget()
        self.feeds_page_genres.setObjectName(u"feeds_page_genres")
        self.horizontalLayout_19 = QHBoxLayout(self.feeds_page_genres)
        self.horizontalLayout_19.setObjectName(u"horizontalLayout_19")
        self.horizontalLayout_19.setContentsMargins(0, 0, 0, 0)
        self.widget_feeds_genres = QWidget(self.feeds_page_genres)
        self.widget_feeds_genres.setObjectName(u"widget_feeds_genres")
        self.verticalLayout_50 = QVBoxLayout(self.widget_feeds_genres)
        self.verticalLayout_50.setObjectName(u"verticalLayout_50")
        self.verticalLayout_50.setContentsMargins(0, 0, 0, 0)
        self.table_feeds_genres = QTableWidget(self.widget_feeds_genres)
        self.table_feeds_genres.setObjectName(u"table_feeds_genres")

        self.verticalLayout_50.addWidget(self.table_feeds_genres)


        self.horizontalLayout_19.addWidget(self.widget_feeds_genres)

        self.chart_feeds_genres = QWidget(self.feeds_page_genres)
        self.chart_feeds_genres.setObjectName(u"chart_feeds_genres")
        self.verticalLayout_49 = QVBoxLayout(self.chart_feeds_genres)
        self.verticalLayout_49.setObjectName(u"verticalLayout_49")
        self.verticalLayout_49.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_19.addWidget(self.chart_feeds_genres)

        self.stackedWidget_2.addWidget(self.feeds_page_genres)
        self.feeds_page_labels = QWidget()
        self.feeds_page_labels.setObjectName(u"feeds_page_labels")
        self.horizontalLayout_20 = QHBoxLayout(self.feeds_page_labels)
        self.horizontalLayout_20.setObjectName(u"horizontalLayout_20")
        self.horizontalLayout_20.setContentsMargins(0, 0, 0, 0)
        self.widget_feeds_labels = QWidget(self.feeds_page_labels)
        self.widget_feeds_labels.setObjectName(u"widget_feeds_labels")
        self.verticalLayout_51 = QVBoxLayout(self.widget_feeds_labels)
        self.verticalLayout_51.setObjectName(u"verticalLayout_51")
        self.verticalLayout_51.setContentsMargins(0, 0, 0, 0)
        self.table_feeds_labels = QTableWidget(self.widget_feeds_labels)
        self.table_feeds_labels.setObjectName(u"table_feeds_labels")

        self.verticalLayout_51.addWidget(self.table_feeds_labels)


        self.horizontalLayout_20.addWidget(self.widget_feeds_labels)

        self.chart_feeds_labels = QWidget(self.feeds_page_labels)
        self.chart_feeds_labels.setObjectName(u"chart_feeds_labels")
        self.horizontalLayout_21 = QHBoxLayout(self.chart_feeds_labels)
        self.horizontalLayout_21.setObjectName(u"horizontalLayout_21")
        self.horizontalLayout_21.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_20.addWidget(self.chart_feeds_labels)

        self.stackedWidget_2.addWidget(self.feeds_page_labels)
        self.feeds_page_time = QWidget()
        self.feeds_page_time.setObjectName(u"feeds_page_time")
        self.horizontalLayout_22 = QHBoxLayout(self.feeds_page_time)
        self.horizontalLayout_22.setObjectName(u"horizontalLayout_22")
        self.horizontalLayout_22.setContentsMargins(0, 0, 0, 0)
        self.widget_feeds_time = QWidget(self.feeds_page_time)
        self.widget_feeds_time.setObjectName(u"widget_feeds_time")
        self.verticalLayout_53 = QVBoxLayout(self.widget_feeds_time)
        self.verticalLayout_53.setObjectName(u"verticalLayout_53")
        self.verticalLayout_53.setContentsMargins(0, 0, 0, 0)
        self.table_feeds_time = QTableWidget(self.widget_feeds_time)
        self.table_feeds_time.setObjectName(u"table_feeds_time")

        self.verticalLayout_53.addWidget(self.table_feeds_time)


        self.horizontalLayout_22.addWidget(self.widget_feeds_time)

        self.charts_feeds_time = QWidget(self.feeds_page_time)
        self.charts_feeds_time.setObjectName(u"charts_feeds_time")
        self.verticalLayout_52 = QVBoxLayout(self.charts_feeds_time)
        self.verticalLayout_52.setObjectName(u"verticalLayout_52")
        self.verticalLayout_52.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_22.addWidget(self.charts_feeds_time)

        self.stackedWidget_2.addWidget(self.feeds_page_time)
        self.feeds_page_info = QWidget()
        self.feeds_page_info.setObjectName(u"feeds_page_info")
        self.horizontalLayout_24 = QHBoxLayout(self.feeds_page_info)
        self.horizontalLayout_24.setObjectName(u"horizontalLayout_24")
        self.horizontalLayout_24.setContentsMargins(0, 0, 0, 0)
        self.widget_feeds_info = QWidget(self.feeds_page_info)
        self.widget_feeds_info.setObjectName(u"widget_feeds_info")
        self.verticalLayout_57 = QVBoxLayout(self.widget_feeds_info)
        self.verticalLayout_57.setObjectName(u"verticalLayout_57")
        self.verticalLayout_57.setContentsMargins(0, 0, 0, 0)
        self.table_feeds_info = QTableWidget(self.widget_feeds_info)
        self.table_feeds_info.setObjectName(u"table_feeds_info")

        self.verticalLayout_57.addWidget(self.table_feeds_info)


        self.horizontalLayout_24.addWidget(self.widget_feeds_info)

        self.chart_feeds_info = QWidget(self.feeds_page_info)
        self.chart_feeds_info.setObjectName(u"chart_feeds_info")
        self.verticalLayout_56 = QVBoxLayout(self.chart_feeds_info)
        self.verticalLayout_56.setObjectName(u"verticalLayout_56")
        self.verticalLayout_56.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_24.addWidget(self.chart_feeds_info)

        self.stackedWidget_2.addWidget(self.feeds_page_info)
        self.feeds_page_listens = QWidget()
        self.feeds_page_listens.setObjectName(u"feeds_page_listens")
        self.horizontalLayout_23 = QHBoxLayout(self.feeds_page_listens)
        self.horizontalLayout_23.setObjectName(u"horizontalLayout_23")
        self.horizontalLayout_23.setContentsMargins(0, 0, 0, 0)
        self.widget_feeds_listens = QWidget(self.feeds_page_listens)
        self.widget_feeds_listens.setObjectName(u"widget_feeds_listens")
        self.verticalLayout_55 = QVBoxLayout(self.widget_feeds_listens)
        self.verticalLayout_55.setObjectName(u"verticalLayout_55")
        self.verticalLayout_55.setContentsMargins(0, 0, 0, 0)
        self.table_feeds_listens = QTableWidget(self.widget_feeds_listens)
        self.table_feeds_listens.setObjectName(u"table_feeds_listens")

        self.verticalLayout_55.addWidget(self.table_feeds_listens)


        self.horizontalLayout_23.addWidget(self.widget_feeds_listens)

        self.chart_feeds_listens = QWidget(self.feeds_page_listens)
        self.chart_feeds_listens.setObjectName(u"chart_feeds_listens")
        self.verticalLayout_54 = QVBoxLayout(self.chart_feeds_listens)
        self.verticalLayout_54.setObjectName(u"verticalLayout_54")
        self.verticalLayout_54.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_23.addWidget(self.chart_feeds_listens)

        self.stackedWidget_2.addWidget(self.feeds_page_listens)

        self.verticalLayout_feeds.addWidget(self.stackedWidget_2)

        self.widget_19 = QWidget(self.page_feeds)
        self.widget_19.setObjectName(u"widget_19")
        self.horizontalLayout_16 = QHBoxLayout(self.widget_19)
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.horizontalLayout_16.setContentsMargins(0, 0, 0, 0)
        self.action_feeds_artists = QPushButton(self.widget_19)
        self.action_feeds_artists.setObjectName(u"action_feeds_artists")

        self.horizontalLayout_16.addWidget(self.action_feeds_artists)

        self.action_feeds_albums = QPushButton(self.widget_19)
        self.action_feeds_albums.setObjectName(u"action_feeds_albums")

        self.horizontalLayout_16.addWidget(self.action_feeds_albums)

        self.action_feeds_genres = QPushButton(self.widget_19)
        self.action_feeds_genres.setObjectName(u"action_feeds_genres")

        self.horizontalLayout_16.addWidget(self.action_feeds_genres)

        self.action_feeds_labels = QPushButton(self.widget_19)
        self.action_feeds_labels.setObjectName(u"action_feeds_labels")

        self.horizontalLayout_16.addWidget(self.action_feeds_labels)

        self.action_feeds_time = QPushButton(self.widget_19)
        self.action_feeds_time.setObjectName(u"action_feeds_time")

        self.horizontalLayout_16.addWidget(self.action_feeds_time)

        self.action_feeds_listens = QPushButton(self.widget_19)
        self.action_feeds_listens.setObjectName(u"action_feeds_listens")

        self.horizontalLayout_16.addWidget(self.action_feeds_listens)

        self.action_feeds_info = QPushButton(self.widget_19)
        self.action_feeds_info.setObjectName(u"action_feeds_info")

        self.horizontalLayout_16.addWidget(self.action_feeds_info)


        self.verticalLayout_feeds.addWidget(self.widget_19)

        self.widget_18 = QWidget(self.page_feeds)
        self.widget_18.setObjectName(u"widget_18")
        self.verticalLayout_43 = QVBoxLayout(self.widget_18)
        self.verticalLayout_43.setObjectName(u"verticalLayout_43")
        self.verticalLayout_43.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_feeds.addWidget(self.widget_18)

        self.stacked_widget.addWidget(self.page_feeds)

        self.verticalLayout_2.addWidget(self.stacked_widget)


        self.verticalLayout.addWidget(self.stats_content)

        self.widget_22 = QWidget(Form)
        self.widget_22.setObjectName(u"widget_22")
        self.horizontalLayout_34 = QHBoxLayout(self.widget_22)
        self.horizontalLayout_34.setObjectName(u"horizontalLayout_34")
        self.horizontalLayout_34.setContentsMargins(0, 0, 0, 0)
        self.category_combo = QComboBox(self.widget_22)
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.addItem("")
        self.category_combo.setObjectName(u"category_combo")

        self.horizontalLayout_34.addWidget(self.category_combo)

        self.tool_2_button = QToolButton(self.widget_22)
        self.tool_2_button.setObjectName(u"tool_2_button")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy5.setHorizontalStretch(38)
        sizePolicy5.setVerticalStretch(38)
        sizePolicy5.setHeightForWidth(self.tool_2_button.sizePolicy().hasHeightForWidth())
        self.tool_2_button.setSizePolicy(sizePolicy5)
        self.tool_2_button.setMinimumSize(QSize(34, 34))
        self.tool_2_button.setMaximumSize(QSize(34, 34))
        icon = QIcon()
        icon.addFile(u":/services/b_download", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.tool_2_button.setIcon(icon)
        self.tool_2_button.setIconSize(QSize(30, 30))

        self.horizontalLayout_34.addWidget(self.tool_2_button)


        self.verticalLayout.addWidget(self.widget_22)


        self.retranslateUi(Form)

        self.stacked_widget.setCurrentIndex(4)
        self.stacked_genre_charts.setCurrentIndex(0)
        self.stacked_listen_stats.setCurrentIndex(2)
        self.stackedWidget.setCurrentIndex(1)
        self.stackedWidget_countries.setCurrentIndex(0)
        self.stackedWidget_2.setCurrentIndex(5)
        self.category_combo.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Estad\u00edsticas", None))
        self.label_missing_title.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 18px; font-weight: bold;", None))
        self.label_missing_title.setText(QCoreApplication.translate("Form", u"An\u00e1lisis de Datos Ausentes en la Base de Datos", None))
        ___qtablewidgetitem = self.table_missing_data.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("Form", u"Tabla", None));
        ___qtablewidgetitem1 = self.table_missing_data.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("Form", u"Campo", None));
        ___qtablewidgetitem2 = self.table_missing_data.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("Form", u"% Completitud", None));
        self.ausentes_tabla_combo.setItemText(0, QCoreApplication.translate("Form", u"Artistas", None))
        self.ausentes_tabla_combo.setItemText(1, QCoreApplication.translate("Form", u"\u00c1lbums", None))
        self.ausentes_tabla_combo.setItemText(2, QCoreApplication.translate("Form", u"Canciones", None))
        self.ausentes_tabla_combo.setItemText(3, QCoreApplication.translate("Form", u"Sellos", None))

        self.label_worst_fields.setStyleSheet(QCoreApplication.translate("Form", u"font-weight: bold;", None))
        self.label_worst_fields.setText(QCoreApplication.translate("Form", u"Campos con menor completitud:", None))
        self.label_summary.setText(QCoreApplication.translate("Form", u"Total de campos analizados: 0", None))
        self.label_genres_distribution.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 16px; font-weight: bold;", None))
        self.label_genres_distribution.setText(QCoreApplication.translate("Form", u"Distribuci\u00f3n de G\u00e9neros", None))
        ___qtablewidgetitem3 = self.table_genres.horizontalHeaderItem(0)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("Form", u"G\u00e9nero", None));
        ___qtablewidgetitem4 = self.table_genres.horizontalHeaderItem(1)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("Form", u"Canciones", None));
        ___qtablewidgetitem5 = self.table_genres.horizontalHeaderItem(2)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("Form", u"Porcentaje", None));
        ___qtablewidgetitem6 = self.table_genres.horizontalHeaderItem(3)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("Form", u"\u00c1lbumes", None));
        ___qtablewidgetitem7 = self.table_genres.horizontalHeaderItem(4)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("Form", u"Artistas", None));
        self.label_genres_visualization.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 16px; font-weight: bold;", None))
        self.label_genres_visualization.setText(QCoreApplication.translate("Form", u"Visualizaci\u00f3n de G\u00e9neros", None))
        self.label_selected_genre_title.setText(QCoreApplication.translate("Form", u"TextLabel", None))
        self.btn_artists_view.setText(QCoreApplication.translate("Form", u"Ver Artistas", None))
        self.btn_decades_view.setText(QCoreApplication.translate("Form", u"Ver por D\u00e9cadas", None))
        self.label_listen_title.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 18px; font-weight: bold;", None))
        self.label_listen_title.setText(QCoreApplication.translate("Form", u"Estad\u00edsticas de Escuchas", None))
        self.label_source.setText(QCoreApplication.translate("Form", u"Fuente de datos:", None))
        self.label_stats_type.setText(QCoreApplication.translate("Form", u"Tipo de estad\u00edstica:", None))
        self.combo_stats_type.setItemText(0, QCoreApplication.translate("Form", u"Top Artistas", None))
        self.combo_stats_type.setItemText(1, QCoreApplication.translate("Form", u"Top \u00c1lbumes", None))
        self.combo_stats_type.setItemText(2, QCoreApplication.translate("Form", u"Escuchas por G\u00e9nero", None))
        self.combo_stats_type.setItemText(3, QCoreApplication.translate("Form", u"Escuchas por Sello", None))
        self.combo_stats_type.setItemText(4, QCoreApplication.translate("Form", u"Tendencias Temporales", None))

        ___qtablewidgetitem8 = self.table_artists.horizontalHeaderItem(0)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("Form", u"Artista", None));
        ___qtablewidgetitem9 = self.table_artists.horizontalHeaderItem(1)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("Form", u"Escuchas", None));
        self.label_time_unit.setText(QCoreApplication.translate("Form", u"Agrupar por:", None))
        self.combo_time_unit.setItemText(0, QCoreApplication.translate("Form", u"D\u00eda", None))
        self.combo_time_unit.setItemText(1, QCoreApplication.translate("Form", u"Semana", None))
        self.combo_time_unit.setItemText(2, QCoreApplication.translate("Form", u"Mes", None))
        self.combo_time_unit.setItemText(3, QCoreApplication.translate("Form", u"A\u00f1o", None))

        self.label_labels_title.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 16px; font-weight: bold;", None))
        self.label_labels_title.setText(QCoreApplication.translate("Form", u"Distribuci\u00f3n de \u00c1lbumes por Sello", None))
        ___qtablewidgetitem10 = self.table_labels.horizontalHeaderItem(0)
        ___qtablewidgetitem10.setText(QCoreApplication.translate("Form", u"Sello", None));
        ___qtablewidgetitem11 = self.table_labels.horizontalHeaderItem(1)
        ___qtablewidgetitem11.setText(QCoreApplication.translate("Form", u"\u00c1lbumes", None));
        ___qtablewidgetitem12 = self.table_labels.horizontalHeaderItem(2)
        ___qtablewidgetitem12.setText(QCoreApplication.translate("Form", u"Artistas", None));
        ___qtablewidgetitem13 = self.table_labels.horizontalHeaderItem(3)
        ___qtablewidgetitem13.setText(QCoreApplication.translate("Form", u"Canciones", None));
        self.label_decade_title.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 16px; font-weight: bold;", None))
        self.label_decade_title.setText(QCoreApplication.translate("Form", u"Sellos por D\u00e9cada", None))
        ___qtablewidgetitem14 = self.table_labels_genres.horizontalHeaderItem(0)
        ___qtablewidgetitem14.setText(QCoreApplication.translate("Form", u"Sello", None));
        ___qtablewidgetitem15 = self.table_labels_genres.horizontalHeaderItem(1)
        ___qtablewidgetitem15.setText(QCoreApplication.translate("Form", u"\u00c1lbumes", None));
        ___qtablewidgetitem16 = self.table_labels_genres.horizontalHeaderItem(2)
        ___qtablewidgetitem16.setText(QCoreApplication.translate("Form", u"Artistas", None));
        ___qtablewidgetitem17 = self.table_labels_genres.horizontalHeaderItem(3)
        ___qtablewidgetitem17.setText(QCoreApplication.translate("Form", u"Canciones", None));
        ___qtablewidgetitem18 = self.sellos_tabla_albumes.horizontalHeaderItem(0)
        ___qtablewidgetitem18.setText(QCoreApplication.translate("Form", u"\u00c1lbumes", None));
        ___qtablewidgetitem19 = self.sellos_tabla_albumes.horizontalHeaderItem(1)
        ___qtablewidgetitem19.setText(QCoreApplication.translate("Form", u"Artistas", None));
        ___qtablewidgetitem20 = self.sellos_tabla_albumes.horizontalHeaderItem(2)
        ___qtablewidgetitem20.setText(QCoreApplication.translate("Form", u"Fecha", None));
        ___qtablewidgetitem21 = self.sellos_tabla_albumes.horizontalHeaderItem(3)
        ___qtablewidgetitem21.setText(QCoreApplication.translate("Form", u"Canciones", None));
        ___qtablewidgetitem22 = self.labels_info_table.horizontalHeaderItem(0)
        ___qtablewidgetitem22.setText(QCoreApplication.translate("Form", u"Sello", None));
        ___qtablewidgetitem23 = self.labels_info_table.horizontalHeaderItem(1)
        ___qtablewidgetitem23.setText(QCoreApplication.translate("Form", u"Pa\u00eds", None));
        ___qtablewidgetitem24 = self.labels_info_table.horizontalHeaderItem(2)
        ___qtablewidgetitem24.setText(QCoreApplication.translate("Form", u"Fundaci\u00f3n", None));
        self.action_sellos_decade.setText(QCoreApplication.translate("Form", u"d\u00e9cada", None))
        self.action_sellos_porcentajes.setText(QCoreApplication.translate("Form", u"porcentajes", None))
        self.action_sellos_artistas.setText(QCoreApplication.translate("Form", u"artistas", None))
        self.action_sellos_albumes.setText(QCoreApplication.translate("Form", u"albumes", None))
        self.action_sellos_por_genero.setText(QCoreApplication.translate("Form", u"g\u00e9neros", None))
        self.action_sellos_info.setText(QCoreApplication.translate("Form", u"info", None))
        self.label_time_title.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 18px; font-weight: bold;", None))
        self.label_time_title.setText(QCoreApplication.translate("Form", u"Distribuci\u00f3n Temporal de M\u00fasica", None))
        self.label_year_title.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 16px; font-weight: bold;", None))
        self.label_year_title.setText(QCoreApplication.translate("Form", u"Distribuci\u00f3n por A\u00f1o de Lanzamiento", None))
        self.label_decade_dist_title.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 16px; font-weight: bold;", None))
        self.label_decade_dist_title.setText(QCoreApplication.translate("Form", u"Distribuci\u00f3n por D\u00e9cada", None))
        ___qtablewidgetitem25 = self.table_decades.horizontalHeaderItem(0)
        ___qtablewidgetitem25.setText(QCoreApplication.translate("Form", u"D\u00e9cada", None));
        ___qtablewidgetitem26 = self.table_decades.horizontalHeaderItem(1)
        ___qtablewidgetitem26.setText(QCoreApplication.translate("Form", u"\u00c1lbumes", None));
        self.action_artist.setText(QCoreApplication.translate("Form", u"artistas", None))
        self.action_album.setText(QCoreApplication.translate("Form", u"\u00e1lbums", None))
        self.action_genres.setText(QCoreApplication.translate("Form", u"g\u00e9neros", None))
        self.action_labels.setText(QCoreApplication.translate("Form", u"sellos", None))
        self.action_feeds.setText(QCoreApplication.translate("Form", u"feeds", None))
        self.action_listens.setText(QCoreApplication.translate("Form", u"escuchas", None))
        self.action_info.setText(QCoreApplication.translate("Form", u"info", None))
        self.artista_label.setText(QCoreApplication.translate("Form", u"Artista", None))
        ___qtablewidgetitem27 = self.tableWidget_3.horizontalHeaderItem(0)
        ___qtablewidgetitem27.setText(QCoreApplication.translate("Form", u"Artista", None));
        ___qtablewidgetitem28 = self.tableWidget_3.horizontalHeaderItem(1)
        ___qtablewidgetitem28.setText(QCoreApplication.translate("Form", u"Origen", None));
        ___qtablewidgetitem29 = self.tableWidget_3.horizontalHeaderItem(2)
        ___qtablewidgetitem29.setText(QCoreApplication.translate("Form", u"A\u00f1o", None));
        ___qtablewidgetitem30 = self.tableWidget_3.horizontalHeaderItem(3)
        ___qtablewidgetitem30.setText(QCoreApplication.translate("Form", u"Albumes", None));
        self.action_artist_home.setText(QCoreApplication.translate("Form", u"artista", None))
        self.action_artist_time.setText(QCoreApplication.translate("Form", u"tiempo", None))
        self.action_artist_conciertos.setText(QCoreApplication.translate("Form", u"conciertos", None))
        self.action_artist_genres.setText(QCoreApplication.translate("Form", u"generos", None))
        self.action_artist_feeds.setText(QCoreApplication.translate("Form", u"feeds", None))
        self.action_artist_label.setText(QCoreApplication.translate("Form", u"sellos", None))
        self.action_artist_discog.setText(QCoreApplication.translate("Form", u"discografia", None))
        self.action_artist_scrobbles.setText(QCoreApplication.translate("Form", u"escuchas", None))
        self.action_artist_prod.setText(QCoreApplication.translate("Form", u"productores", None))
        self.action_artist_collaborators.setText(QCoreApplication.translate("Form", u"colaboradores", None))
        self.label_countries_title.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 18px; font-weight: bold;", None))
        self.label_countries_title.setText(QCoreApplication.translate("Form", u"Distribuci\u00f3n por Pa\u00eds de Origen", None))
        ___qtablewidgetitem31 = self.table_countries.horizontalHeaderItem(0)
        ___qtablewidgetitem31.setText(QCoreApplication.translate("Form", u"Pa\u00eds", None));
        ___qtablewidgetitem32 = self.table_countries.horizontalHeaderItem(1)
        ___qtablewidgetitem32.setText(QCoreApplication.translate("Form", u"Artistas", None));
        self.action_countries_artists.setText(QCoreApplication.translate("Form", u"artistas", None))
        self.action_countries_album.setText(QCoreApplication.translate("Form", u"album", None))
        self.action_countries_labels.setText(QCoreApplication.translate("Form", u"sellos", None))
        self.action_countries_feeds.setText(QCoreApplication.translate("Form", u"feeds", None))
        self.action_countries_genre.setText(QCoreApplication.translate("Form", u"genero", None))
        self.action_countries_time.setText(QCoreApplication.translate("Form", u"tiempo", None))
        self.action_countries_listens.setText(QCoreApplication.translate("Form", u"escuchas", None))
        self.action_countries_info.setText(QCoreApplication.translate("Form", u"info", None))
        self.label_feeds_title.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 18px; font-weight: bold;", None))
        self.label_feeds_title.setText(QCoreApplication.translate("Form", u"An\u00e1lisis de Feeds", None))
        self.label_entity_title.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 16px; font-weight: bold;", None))
        self.label_entity_title.setText(QCoreApplication.translate("Form", u"Feeds por Tipo de Entidad", None))
        ___qtablewidgetitem33 = self.table_entity.horizontalHeaderItem(0)
        ___qtablewidgetitem33.setText(QCoreApplication.translate("Form", u"Tipo de Entidad", None));
        ___qtablewidgetitem34 = self.table_entity.horizontalHeaderItem(1)
        ___qtablewidgetitem34.setText(QCoreApplication.translate("Form", u"Cantidad", None));
        self.label_feeds_names.setStyleSheet(QCoreApplication.translate("Form", u"font-size: 16px; font-weight: bold;", None))
        self.label_feeds_names.setText(QCoreApplication.translate("Form", u"Feeds por Nombre", None))
        ___qtablewidgetitem35 = self.table_feeds.horizontalHeaderItem(0)
        ___qtablewidgetitem35.setText(QCoreApplication.translate("Form", u"Nombre del Feed", None));
        ___qtablewidgetitem36 = self.table_feeds.horizontalHeaderItem(1)
        ___qtablewidgetitem36.setText(QCoreApplication.translate("Form", u"Publicaciones", None));
        ___qtablewidgetitem37 = self.table_feeds_artists.horizontalHeaderItem(0)
        ___qtablewidgetitem37.setText(QCoreApplication.translate("Form", u"Artistas", None));
        ___qtablewidgetitem38 = self.table_feeds_artists.horizontalHeaderItem(1)
        ___qtablewidgetitem38.setText(QCoreApplication.translate("Form", u"Albums", None));
        ___qtablewidgetitem39 = self.table_feeds_artists.horizontalHeaderItem(2)
        ___qtablewidgetitem39.setText(QCoreApplication.translate("Form", u"Reviews", None));
        self.action_feeds_artists.setText(QCoreApplication.translate("Form", u"artistas", None))
        self.action_feeds_albums.setText(QCoreApplication.translate("Form", u"albums", None))
        self.action_feeds_genres.setText(QCoreApplication.translate("Form", u"generos", None))
        self.action_feeds_labels.setText(QCoreApplication.translate("Form", u"sellos", None))
        self.action_feeds_time.setText(QCoreApplication.translate("Form", u"tiempo", None))
        self.action_feeds_listens.setText(QCoreApplication.translate("Form", u"escuchas", None))
        self.action_feeds_info.setText(QCoreApplication.translate("Form", u"info", None))
        self.category_combo.setItemText(0, QCoreApplication.translate("Form", u"Datos Ausentes", None))
        self.category_combo.setItemText(1, QCoreApplication.translate("Form", u"G\u00e9neros", None))
        self.category_combo.setItemText(2, QCoreApplication.translate("Form", u"Escuchas", None))
        self.category_combo.setItemText(3, QCoreApplication.translate("Form", u"Sellos", None))
        self.category_combo.setItemText(4, QCoreApplication.translate("Form", u"Tiempo", None))
        self.category_combo.setItemText(5, QCoreApplication.translate("Form", u"Pa\u00edses", None))
        self.category_combo.setItemText(6, QCoreApplication.translate("Form", u"Feeds", None))
        self.category_combo.setItemText(7, QCoreApplication.translate("Form", u"Bitrate", None))
        self.category_combo.setItemText(8, QCoreApplication.translate("Form", u"Letras", None))
        self.category_combo.setItemText(9, QCoreApplication.translate("Form", u"Productores", None))
        self.category_combo.setItemText(10, QCoreApplication.translate("Form", u"Colaboradores", None))
        self.category_combo.setItemText(11, QCoreApplication.translate("Form", u"Artistas", None))
        self.category_combo.setItemText(12, QCoreApplication.translate("Form", u"\u00c1lbums", None))
        self.category_combo.setItemText(13, QCoreApplication.translate("Form", u"Canciones", None))

        self.tool_2_button.setText("")
    # retranslateUi

