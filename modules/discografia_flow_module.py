"""
Pestaña Flujo: embebe el mapa de discografía de tumtumpa
(services/mapa_discos), un grafo artista -> álbumes / EPs / géneros ->
otros artistas.

La web avisa con un mensaje de consola "mfuz://open?artist=...&album=..."
cuando se pide abrir un disco propio; aquí se intercepta para lanzar la
búsqueda en Music Browser. Los enlaces externos (MusicBrainz) se abren en el
navegador.
"""
from PyQt6.QtCore import Qt, QUrl, QUrlQuery, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from base_module import BaseModule

DEFAULT_URL = "http://192.168.1.133:8779"


class _ExternalLinkPage(QWebEnginePage):
    """Página para target=_blank: abre la URL en el navegador del sistema."""

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        QDesktopServices.openUrl(url)
        self.deleteLater()
        return False


class _MapPage(QWebEnginePage):
    open_requested = pyqtSignal(str, str)

    def javaScriptConsoleMessage(self, level, message, line, source):
        if message.startswith("mfuz://open?"):
            query = QUrlQuery(QUrl(message))
            decoded = QUrl.ComponentFormattingOption.FullyDecoded
            self.open_requested.emit(query.queryItemValue("artist", decoded),
                                     query.queryItemValue("album", decoded))

    def createWindow(self, window_type):
        return _ExternalLinkPage(self)


class DiscografiaFlowModule(BaseModule):
    def __init__(self, url=DEFAULT_URL, parent=None, theme='Tokyo Night', **kwargs):
        self.map_url = QUrl(url)
        query = QUrlQuery(self.map_url)
        query.addQueryItem("embed", "mfuz")
        self.map_url.setQuery(query)
        self._loaded = False
        super().__init__(parent, theme, **kwargs)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.view = QWebEngineView()
        self.page = _MapPage(self.view)
        self.page.open_requested.connect(self.open_in_music_browser)
        self.view.setPage(self.page)
        self.view.loadFinished.connect(self._on_load_finished)
        self.stack.addWidget(self.view)

        error = QWidget()
        error_layout = QVBoxLayout(error)
        error_layout.addStretch()
        self.error_label = QLabel()
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        error_layout.addWidget(self.error_label)
        retry = QPushButton("Reintentar")
        retry.clicked.connect(self._load)
        error_layout.addWidget(retry, 0, Qt.AlignmentFlag.AlignCenter)
        error_layout.addStretch()
        self.stack.addWidget(error)

    def showEvent(self, event):
        super().showEvent(event)
        # Carga diferida: no retrasa el arranque de la app
        if not self._loaded:
            self._loaded = True
            self._load()

    def _load(self):
        self.stack.setCurrentWidget(self.view)
        self.view.load(self.map_url)

    def _on_load_finished(self, ok):
        if not ok:
            self.error_label.setText(
                f"No se pudo cargar el mapa de discos en {self.map_url.toString()}.\n\n"
                "Comprueba que el servicio mapa_discos de tumtumpa está levantado, "
                "o cambia 'url' en los args de esta pestaña.")
            self.stack.setCurrentIndex(1)

    def music_browser(self):
        tabs = getattr(self.tab_manager, 'tabs', None) or {}
        for module in tabs.values():
            if hasattr(module, 'search_box') and hasattr(module, 'search_handler') and module is not self:
                return module
        return None

    def open_in_music_browser(self, artist_name, album_title=""):
        browser = self.music_browser()
        if not browser or not artist_name:
            return
        query = f"a:{artist_name}"
        if album_title:
            query += f" d:{album_title}"
        self.tab_manager.tab_widget.setCurrentWidget(browser)
        browser.search_box.setText(query)
        browser.search_handler.perform_search()
