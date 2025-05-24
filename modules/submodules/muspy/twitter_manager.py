import os
import sys
import json
import logging
import yaml
from pathlib import Path
from PyQt6.QtWidgets import (QMessageBox, QInputDialog, QLineEdit, QDialog,
                          QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                          QDialogButtonBox, QComboBox, QProgressDialog,
                          QApplication, QMenu, QSpinBox, QCheckBox,
                          QTableWidget, QTableWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6 import uic
import subprocess
from base_module import PROJECT_ROOT
from modules.submodules.muspy import progress_utils


class NumericTableWidgetItem(QTableWidgetItem):
    """
    Item para tablas con formato numérico y ordenamiento correcto
    """
    def __init__(self, text):
        super().__init__(text)
        
    def __lt__(self, other):
        """
        Implementación personalizada para ordenamiento numérico
        
        Args:
            other (QTableWidgetItem): Otro ítem para comparar
            
        Returns:
            bool: True si este ítem es menor que el otro
        """
        if not other:
            return False
            
        # Convertir textos a números para la comparación
        try:
            # Eliminar comas y otros caracteres no numéricos
            self_text = self.text().replace(',', '').replace('.', '').strip()
            other_text = other.text().replace(',', '').replace('.', '').strip()
            
            # Si los textos están vacíos, usar 0
            self_value = float(self_text) if self_text else 0
            other_value = float(other_text) if other_text else 0
            
            return self_value < other_value
        except (ValueError, TypeError):
            # Si no se pueden convertir a números, usar comparación de texto
            return self.text() < other.text()


class TwitterManager:
    def __init__(self, 
            parent, 
            project_root, 
            twitter_client_id=None,
            twitter_client_secret=None, 
            twitter_redirect_uri=None, 
            ui_callback=None, 
            progress_utils=None,
            display_manager=None,
            cache_manager=None,
            muspy_manager=None,
            spotify_manager=None,
            lastfm_manager=None,
            musicbrainz_manager=None,
            utils=None
            ):
        self.parent = parent
        self.project_root = project_root
        self.twitter_client_id = twitter_client_id
        self.twitter_client_secret = twitter_client_secret
        self.twitter_redirect_uri = twitter_redirect_uri
        self.logger = logging.getLogger(__name__)
        self.twitter_auth = None
        
        # DIAGNÓSTICO: Mostrar credenciales recibidas
        self.logger.info("=== CREDENCIALES RECIBIDAS EN TwitterManager ===")
        self.logger.info(f"twitter_client_id recibido: {twitter_client_id}")
        self.logger.info(f"twitter_client_secret recibido: {twitter_client_secret[:10] if twitter_client_secret else 'None'}...")
        self.logger.info(f"twitter_redirect_uri recibido: {twitter_redirect_uri}")
        
        # Verificar credenciales en el parent también
        if hasattr(parent, 'twitter_client_id'):
            self.logger.info(f"parent.twitter_client_id: {parent.twitter_client_id}")
        if hasattr(parent, 'twitter_client_secret'):
            self.logger.info(f"parent.twitter_client_secret: {parent.twitter_client_secret[:10] if parent.twitter_client_secret else 'None'}...")
        
        # Inicializar twitter_auth
        try:
            # Verificar y configurar credenciales
            self._check_and_setup_credentials()
            
            # Importar y crear el gestor de autenticación
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from tools.twitter_login import TwitterAuthManager
            
            # ASEGURAR que usamos las credenciales correctas
            if not self.twitter_client_id or not self.twitter_client_secret:
                self.logger.warning("Credenciales faltantes, usando las del parent si están disponibles")
                if hasattr(parent, 'twitter_client_id') and parent.twitter_client_id:
                    self.twitter_client_id = parent.twitter_client_id
                if hasattr(parent, 'twitter_client_secret') and parent.twitter_client_secret:
                    self.twitter_client_secret = parent.twitter_client_secret
                if hasattr(parent, 'twitter_redirect_uri') and parent.twitter_redirect_uri:
                    self.twitter_redirect_uri = parent.twitter_redirect_uri
            
            # Verificar una vez más antes de crear TwitterAuthManager
            self.logger.info(f"Credenciales finales para TwitterAuthManager:")
            self.logger.info(f"  client_id: {self.twitter_client_id}")
            self.logger.info(f"  client_secret: {self.twitter_client_secret[:10] if self.twitter_client_secret else 'None'}...")
            self.logger.info(f"  redirect_uri: {self.twitter_redirect_uri}")
            
            self.twitter_auth = TwitterAuthManager(
                client_id=self.twitter_client_id,
                client_secret=self.twitter_client_secret,
                redirect_uri=self.twitter_redirect_uri,
                parent_widget=self.parent,
                project_root=self.project_root
            )
            self.twitter_enabled = self.twitter_auth is not None and bool(self.twitter_client_id and self.twitter_client_secret)
            
            # Diagnóstico final
            self._debug_twitter_credentials()
            
        except ImportError as e:
            self.logger.error(f"Error importando TwitterAuthManager: {e}")
            self.twitter_auth = None
            self.twitter_enabled = False

        # Resto de inicializaciones...
        self.ui_callback = ui_callback
        self.progress_utils = progress_utils
        self.display_manager = display_manager
        self.cache_manager = cache_manager
        self.muspy_manager = muspy_manager
        self.spotify_manager = spotify_manager
        self.lastfm_manager = lastfm_manager
        self.musicbrainz_manager = musicbrainz_manager
        self.utils = utils

        # Verificar proactivamente la autenticación
        if self.twitter_enabled and self.twitter_auth:
            self.logger.info("Twitter habilitado, se intentará autenticación en segundo plano al iniciar")
        else:
            self.logger.info(f"Twitter no habilitado o auth manager no inicializado correctamente")
            if not self.twitter_client_id or not self.twitter_client_secret:
                self.logger.info(f"Faltan credenciales: client_id={bool(self.twitter_client_id)}, client_secret={bool(self.twitter_client_secret)}")
                
    def _check_and_setup_credentials(self):
        """
        Verifica si se tienen las credenciales necesarias para Twitter
        y si no, muestra un diálogo para configurarlas
        """
        # Si ya tenemos las credenciales, no hacer nada
        if self.twitter_client_id and self.twitter_client_secret and self.twitter_redirect_uri:
            return True
            
        # Verificar si estamos en un contexto interactivo (con parent widget)
        if not self.parent:
            self.logger.warning("No hay widget padre disponible para mostrar el diálogo de credenciales")
            return False
            
        # Mostrar el diálogo de configuración
        if self.show_credentials_dialog():
            return True
            
        return False

    def show_credentials_dialog(self):
        """
        Muestra un diálogo para configurar las credenciales de Twitter
        
        Returns:
            bool: True si las credenciales se configuraron correctamente
        """
        try:
            # Intentar cargar el archivo UI
            ui_file_path = Path(self.project_root, "ui", "muspy", "muspy_credentials.ui")
            
            if os.path.exists(ui_file_path):
                # Crear diálogo y cargar UI
                dialog = QDialog(self.parent)
                uic.loadUi(ui_file_path, dialog)
                
                # Configurar valores actuales si existen
                if hasattr(dialog, 'client_id_line') and self.twitter_client_id:
                    dialog.client_id_line.setText(self.twitter_client_id)
                
                if hasattr(dialog, 'client_secret_line') and self.twitter_client_secret:
                    dialog.client_secret_line.setText(self.twitter_client_secret)
                
                if hasattr(dialog, 'callback_url_line') and self.twitter_redirect_uri:
                    dialog.callback_url_line.setText(self.twitter_redirect_uri)
                elif hasattr(dialog, 'callback_url_line'):
                    # Valor por defecto
                    dialog.callback_url_line.setText("http://localhost:8080/callback")
            else:
                # Crear diálogo manualmente si no existe el archivo UI
                dialog = QDialog(self.parent)
                dialog.setWindowTitle("Configurar Twitter API")
                dialog.setMinimumWidth(400)
                
                layout = QVBoxLayout(dialog)
                
                # Client ID
                client_id_layout = QHBoxLayout()
                client_id_label = QLabel("Client ID:")
                client_id_line = QLineEdit()
                client_id_line.setObjectName("client_id_line")
                if self.twitter_client_id:
                    client_id_line.setText(self.twitter_client_id)
                client_id_layout.addWidget(client_id_label)
                client_id_layout.addWidget(client_id_line)
                layout.addLayout(client_id_layout)
                
                # Client Secret
                client_secret_layout = QHBoxLayout()
                client_secret_label = QLabel("Client Secret:")
                client_secret_line = QLineEdit()
                client_secret_line.setObjectName("client_secret_line")
                if self.twitter_client_secret:
                    client_secret_line.setText(self.twitter_client_secret)
                client_secret_layout.addWidget(client_secret_label)
                client_secret_layout.addWidget(client_secret_line)
                layout.addLayout(client_secret_layout)
                
                # Callback URL
                callback_url_layout = QHBoxLayout()
                callback_url_label = QLabel("Callback URL:")
                callback_url_line = QLineEdit()
                callback_url_line.setObjectName("callback_url_line")
                if self.twitter_redirect_uri:
                    callback_url_line.setText(self.twitter_redirect_uri)
                else:
                    callback_url_line.setText("http://localhost:8080/callback")
                callback_url_layout.addWidget(callback_url_label)
                callback_url_layout.addWidget(callback_url_line)
                layout.addLayout(callback_url_layout)
                
                # Botones
                button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)
                layout.addWidget(button_box)
                
                # Almacenar referencias
                dialog.client_id_line = client_id_line
                dialog.client_secret_line = client_secret_line
                dialog.callback_url_line = callback_url_line
            
            # Mostrar el diálogo
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Guardar credenciales obtenidas
                self.twitter_client_id = dialog.client_id_line.text().strip()
                self.twitter_client_secret = dialog.client_secret_line.text().strip()
                self.twitter_redirect_uri = dialog.callback_url_line.text().strip()
                
                # Validar que tenemos lo necesario
                if not self.twitter_client_id or not self.twitter_client_secret:
                    QMessageBox.warning(
                        self.parent,
                        "Credenciales incompletas",
                        "Se requieren al menos Client ID y Client Secret para la autenticación con Twitter."
                    )
                    return False
                
                # Guardar en archivo de configuración
                self._save_twitter_credentials_to_config()
                
                # Reinicializar TwitterAuth con las nuevas credenciales
                self._reinitialize_twitter_auth()
                
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error mostrando diálogo de credenciales: {e}", exc_info=True)
            QMessageBox.critical(
                self.parent,
                "Error",
                f"Error al configurar credenciales: {str(e)}"
            )
            return False

    def _save_twitter_credentials_to_config(self):
        """
        Guarda las credenciales de Twitter en el archivo de configuración
        """
        config_path = Path(self.project_root, "config", "config.yml")
        
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # Cargar configuración existente si existe
            config_data = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
            
            # Asegurar que existen las secciones necesarias
            if 'global_theme_config' not in config_data:
                config_data['global_theme_config'] = {}
            
            # Actualizar credenciales
            config_data['global_theme_config']['twitter_client_id'] = self.twitter_client_id
            config_data['global_theme_config']['twitter_client_secret'] = self.twitter_client_secret
            config_data['global_theme_config']['twitter_redirect_uri'] = self.twitter_redirect_uri
            
            # Guardar configuración
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False)
                
            self.logger.info("Credenciales de Twitter guardadas correctamente en config.yml")
            return True
            
        except Exception as e:
            self.logger.error(f"Error guardando credenciales en config.yml: {e}", exc_info=True)
            return False

    def _reinitialize_twitter_auth(self):
        """
        Reinicializa el gestor de autenticación de Twitter con las nuevas credenciales
        """
        try:
            # Diagnóstico antes de reinicializar
            self.logger.info("=== REINICIALIZANDO TWITTER AUTH ===")
            self.logger.info(f"Usando client_id: {self.twitter_client_id}")
            self.logger.info(f"Usando client_secret: {self.twitter_client_secret[:10] if self.twitter_client_secret else 'None'}...")
            
            from tools.twitter_login import TwitterAuthManager
            self.twitter_auth = TwitterAuthManager(
                client_id=self.twitter_client_id,
                client_secret=self.twitter_client_secret,
                redirect_uri=self.twitter_redirect_uri,
                parent_widget=self.parent,
                project_root=self.project_root
            )
            self.twitter_enabled = self.twitter_auth is not None and bool(self.twitter_client_id and self.twitter_client_secret)
            
            # Verificar que TwitterAuthManager tiene las credenciales correctas
            if hasattr(self.twitter_auth, 'client_id'):
                self.logger.info(f"TwitterAuthManager inicializado con client_id: {self.twitter_auth.client_id}")
            
            self.logger.info("TwitterAuthManager reinicializado correctamente")
            return True
        except Exception as e:
            self.logger.error(f"Error reinicializando TwitterAuthManager: {e}", exc_info=True)
            self.twitter_enabled = False
            return False

    def ensure_twitter_auth(self, silent=True):
        """
        Asegura que la autenticación de Twitter esté disponible
        
        Args:
            silent (bool): Si es True, no mostrará diálogos interactivos
                
        Returns:
            bool: True si está autenticado, False en caso contrario
        """
        # Verificar si TwitterAuthManager está inicializado correctamente
        if not hasattr(self, 'twitter_auth') or self.twitter_auth is None:
            self.logger.error("TwitterAuthManager no inicializado")
            
            # Reinicializar TwitterAuth si es posible
            try:
                # Verificar y configurar credenciales si faltan
                if not self.twitter_client_id or not self.twitter_client_secret:
                    if silent:
                        self.logger.error("Faltan credenciales de Twitter y silent=True")
                        return False
                    else:
                        # Mostrar diálogo de configuración
                        if not self.show_credentials_dialog():
                            return False
                
                # Importar y crear el gestor de autenticación
                from tools.twitter_login import TwitterAuthManager
                self.twitter_auth = TwitterAuthManager(
                    client_id=self.twitter_client_id,
                    client_secret=self.twitter_client_secret,
                    redirect_uri=self.twitter_redirect_uri,
                    parent_widget=self.parent,
                    project_root=self.project_root
                )
                self.twitter_enabled = self.twitter_auth is not None and bool(self.twitter_client_id and self.twitter_client_secret)
                self.logger.info("TwitterAuthManager reinicializado con éxito")
            except ImportError as e:
                self.logger.error(f"Error importando TwitterAuthManager: {e}")
                
                if not silent:
                    QMessageBox.warning(
                        self.parent,
                        "Error de Twitter",
                        "No se pudo cargar el módulo de Twitter. Verifica la instalación."
                    )
                return False
            except Exception as e:
                self.logger.error(f"Error inicializando TwitterAuthManager: {e}")
                
                if not silent:
                    QMessageBox.warning(
                        self.parent,
                        "Error de Twitter",
                        f"Error inicializando el gestor de Twitter: {str(e)}"
                    )
                return False
        
        # Verificar si tenemos las credenciales necesarias
        if not self.twitter_client_id or not self.twitter_client_secret:
            if silent:
                return False
            else:
                # Mostrar diálogo de configuración
                if not self.show_credentials_dialog():
                    return False
                # Reinicializar después de configurar
                self._reinitialize_twitter_auth()
        
        if not self.twitter_enabled:
            if not silent:
                QMessageBox.warning(self.parent, "Twitter deshabilitado", "Twitter no está habilitado. Verifica la configuración.")
            return False
        
        # MODIFICACIÓN: Probar primero si ya hay un token válido
        is_authenticated = False
        try:
            is_authenticated = self.twitter_auth.is_authenticated()
        except Exception as e:
            self.logger.warning(f"Error verificando autenticación: {e}")
        
        if is_authenticated:
            self.logger.info("Twitter ya autenticado con token existente")
            # NUEVA VALIDACIÓN: Probar que el token funciona con una petición simple
            try:
                twitter_client = self.twitter_auth.get_client()
                if twitter_client:
                    # Hacer una petición de prueba para verificar que las credenciales funcionan
                    test_result = twitter_client.get_user_info()
                    if test_result and "data" in test_result:
                        self.logger.info("Token de Twitter validado correctamente")
                        return True
                    else:
                        self.logger.warning("Token existe pero no funciona correctamente")
                        is_authenticated = False
            except Exception as e:
                self.logger.error(f"Error validando token de Twitter: {e}")
                is_authenticated = False
        
        # Si no hay token válido o falló la validación, intentar autenticación completa
        if not is_authenticated:
            self.logger.info("Iniciando autenticación explícita de Twitter...")
            try:
                result = self.twitter_auth.authenticate(silent=False)
                if result:
                    self.logger.info("Autenticación de Twitter exitosa")
                    # Validar nuevamente después de la autenticación
                    try:
                        twitter_client = self.twitter_auth.get_client()
                        if twitter_client:
                            test_result = twitter_client.get_user_info()
                            if test_result and "data" in test_result:
                                return True
                            else:
                                self.logger.error("Autenticación exitosa pero el token no funciona")
                                if not silent:
                                    self._show_project_association_error()
                                return False
                    except Exception as e:
                        self.logger.error(f"Error validando token después de autenticación: {e}")
                        if not silent:
                            self._show_project_association_error()
                        return False
                else:
                    self.logger.warning("Autenticación de Twitter fallida")
                    if not silent:
                        self._show_project_association_error()
                    return False
            except Exception as e:
                self.logger.error(f"Error en authenticate: {e}")
                if not silent:
                    self._show_project_association_error()
                return False
        
        return True

    def _show_project_association_error(self):
        """
        Muestra un mensaje específico sobre el error de asociación de proyecto
        """
        QMessageBox.critical(
            self.parent,
            "Error de configuración de Twitter",
            "Error: Tu aplicación de Twitter no está asociada a un Proyecto.\n\n"
            "Para solucionarlo:\n"
            "1. Ve al Developer Portal de Twitter\n"
            "2. Busca tu proyecto (Default project-1913964885072830464)\n"
            "3. Asocia tu aplicación a este proyecto\n"
            "4. O crea un nuevo proyecto y asocia la aplicación\n\n"
            "La API v2 de Twitter requiere que las aplicaciones estén asociadas a un proyecto."
        )

    def _validate_twitter_token(self):
        """
        Valida que el token de Twitter funcione correctamente
        
        Returns:
            bool: True si el token es válido y funciona
        """
        try:
            if not hasattr(self, 'twitter_auth') or not self.twitter_auth:
                return False
                
            twitter_client = self.twitter_auth.get_client()
            if not twitter_client:
                return False
                
            # Hacer una petición simple para probar el token
            test_result = twitter_client.get_user_info()
            
            if test_result and "data" in test_result:
                return True
            else:
                self.logger.warning("Token de Twitter no devuelve datos válidos")
                return False
                
        except Exception as e:
            # Verificar si es el error específico de proyecto
            if "client-not-enrolled" in str(e) or "Client Forbidden" in str(e):
                self.logger.error(f"Error de asociación de proyecto: {e}")
            else:
                self.logger.error(f"Error validando token de Twitter: {e}")
            return False

    def _debug_twitter_credentials(self):
        """
        Función de diagnóstico para verificar qué credenciales se están usando
        """
        self.logger.info("=== DIAGNÓSTICO DE CREDENCIALES TWITTER ===")
        self.logger.info(f"twitter_client_id en self: {self.twitter_client_id}")
        self.logger.info(f"twitter_client_secret en self: {self.twitter_client_secret[:10]}... (truncado)")
        self.logger.info(f"twitter_redirect_uri en self: {self.twitter_redirect_uri}")
        
        # Verificar en twitter_auth si existe
        if hasattr(self, 'twitter_auth') and self.twitter_auth:
            self.logger.info(f"twitter_auth.client_id: {getattr(self.twitter_auth, 'client_id', 'NO DISPONIBLE')}")
            self.logger.info(f"twitter_auth.client_secret: {getattr(self.twitter_auth, 'client_secret', 'NO DISPONIBLE')[:10] if getattr(self.twitter_auth, 'client_secret', None) else 'NO DISPONIBLE'}...")
            
            # Verificar cliente interno
            try:
                client = self.twitter_auth.get_client()
                if hasattr(client, 'client_id'):
                    self.logger.info(f"client.client_id: {client.client_id}")
            except Exception as e:
                self.logger.error(f"Error obteniendo cliente para diagnóstico: {e}")
        else:
            self.logger.info("twitter_auth no existe o es None")
        
        self.logger.info("=== FIN DIAGNÓSTICO ===")

    def get_twitter_client(self):
        """Obtiene un cliente de Twitter autenticado bajo demanda"""
        if hasattr(self, 'twitter_auth'):
            return self.twitter_auth.get_client()
        return None

    def show_twitter_menu(self):
        """
        Muestra un menú con opciones de Twitter
        """
        if not self.ensure_twitter_auth(silent=False):
            QMessageBox.warning(self.parent, "Error", "Se requiere autenticación de Twitter")
            return
        
        # Create menu
        menu = QMenu(self.parent)
        
        # Add menu actions
        show_users_action = QAction("Mostrar usuarios seguidos", self.parent)
        show_search_action = QAction("Buscar usuarios", self.parent)
        show_tweets_action = QAction("Ver tweets recientes de artistas", self.parent)
        
        # Connect actions to their respective functions
        show_users_action.triggered.connect(self.show_twitter_followed_users)
        show_search_action.triggered.connect(self.show_twitter_search_dialog)
        show_tweets_action.triggered.connect(self.show_twitter_artist_tweets)
        
        # Add actions to menu
        menu.addAction(show_users_action)
        menu.addAction(show_search_action)
        menu.addAction(show_tweets_action)
        
        # Add separator and extra options
        menu.addSeparator()
        
        sync_action = QAction("Sincronizar artistas con Twitter", self.parent)
        sync_action.triggered.connect(self.sync_artists_with_twitter)
        menu.addAction(sync_action)
        
        # Add separator and cache management option
        menu.addSeparator()
        clear_cache_action = QAction("Limpiar caché de Twitter", self.parent)
        clear_cache_action.triggered.connect(self.clear_twitter_cache)
        menu.addAction(clear_cache_action)
        
        # Add option to configure Twitter credentials
        menu.addSeparator()
        config_action = QAction("Configurar credenciales de Twitter", self.parent)
        config_action.triggered.connect(self.show_credentials_dialog)
        menu.addAction(config_action)
        
        # Show menu at cursor position
        from PyQt6.QtGui import QCursor
        menu.exec(QCursor.pos())

    def show_twitter_followed_users(self):
        """
        Muestra los usuarios seguidos en Twitter con caché
        """
        if not self.ensure_twitter_auth():
            QMessageBox.warning(self.parent, "Error", "Twitter credentials not configured")
            return
        
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        
        # Try to get from cache first
        cache_key = "followed_users"
        cached_data = self.cache_manager.cache_manager(cache_key, None, expiry_hours=24)
        if cached_data:
            self.ui_callback.append("Showing cached followed users data...")
            self.display_twitter_users_in_stacked_widget(cached_data)
            return
        
        self.ui_callback.append("Retrieving users you follow on Twitter...")
        QApplication.processEvents()
        
        # Get Twitter client
        twitter_client = self.twitter_auth.get_client()
        if not twitter_client:
            self.ui_callback.append("Failed to get Twitter client. Please check authentication.")
            return
        
        # Función de operación con progreso
        def fetch_twitter_users(update_progress):
            try:
                update_progress(0, 100, "Connecting to Twitter API...")
                
                all_users = []
                pagination_token = None
                total_users = 0
                page = 1
                
                # Get user info to get authenticated user ID
                user_info = twitter_client.get_user_info()
                if not user_info or "data" not in user_info:
                    return {
                        "success": False,
                        "error": "Could not get user information"
                    }
                
                # Initialize progress
                update_progress(10, 100, "Fetching followed users...")
                
                # Paginate through all followed users
                while True:
                    # Fetch current page of users
                    results = twitter_client.get_followed_users(
                        max_results=100,
                        pagination_token=pagination_token
                    )
                    
                    if not results or "data" not in results:
                        break
                    
                    # Get users from this page
                    users_page = results.get("data", [])
                    all_users.extend(users_page)
                    
                    # Update total count for progress
                    total_users = len(all_users)
                    
                    # Update progress (scale to 10-90%)
                    progress_value = 10 + int((page * 100 / (page + 10)) * 80)
                    update_progress(progress_value, 100, f"Page {page}: Found {len(users_page)} users...")
                    
                    # Check pagination
                    meta = results.get("meta", {})
                    pagination_token = meta.get("next_token")
                    
                    # If no pagination token, we're done
                    if not pagination_token:
                        break
                        
                    # Increment page counter
                    page += 1
                
                # Process users data
                update_progress(90, 100, f"Processing {total_users} users...")
                
                # Format user data for display
                processed_users = []
                for user in all_users:
                    public_metrics = user.get("public_metrics", {})
                    
                    processed_users.append({
                        'id': user.get('id', ''),
                        'name': user.get('name', 'Unknown'),
                        'username': user.get('username', ''),
                        'profile_image_url': user.get('profile_image_url', ''),
                        'description': user.get('description', ''),
                        'followers_count': public_metrics.get('followers_count', 0),
                        'following_count': public_metrics.get('following_count', 0),
                        'tweet_count': public_metrics.get('tweet_count', 0)
                    })
                
                # Cache the processed users
                self.cache_manager.cache_manager(cache_key, processed_users)
                
                update_progress(100, 100, "Complete!")
                
                return {
                    "success": True,
                    "users": processed_users,
                    "total": total_users
                }
                
            except Exception as e:
                self.logger.error(f"Error fetching Twitter users: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Execute with progress dialog
        result = self.progress_utils.show_progress_operation(
            fetch_twitter_users,
            title="Loading Twitter Users",
            label_format="{status}"
        )
        
        progress_function = self._get_progress_function()
        result = progress_function(
            fetch_twitter_users,
            title="Loading Twitter Users",
            label_format="{status}"
        )
        
        # Process results (mantén el resto igual)
        if result and result.get("success"):
            users = result.get("users", [])
            
            if not users:
                self.ui_callback.append("You don't follow any users on Twitter.")
                return
            
            # Display users in the stack widget table
            self.display_twitter_users_in_stacked_widget(users)
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.ui_callback.append(f"Error: {error_msg}")
            QMessageBox.warning(self.parent, "Error", f"Could not load Twitter users: {error_msg}")

    def display_twitter_users_in_stacked_widget(self, users):
        """
        Muestra usuarios de Twitter en el widget apilado con checkboxes para selección
        
        Args:
            users (list): Lista de diccionarios de usuarios de Twitter
        """
        # Encontrar el widget apilado
        stack_widget = self.parent.findChild(QStackedWidget, "stackedWidget")
        if not stack_widget:
            self.logger.error("No se pudo encontrar stackedWidget")
            # Fallback a visualización de texto
            self._display_twitter_users_as_text(users)
            return
        
        # Buscar o crear la página de usuarios de Twitter
        twitter_page = None
        
        # Primero intentar encontrar la página existente
        for i in range(stack_widget.count()):
            widget = stack_widget.widget(i)
            if widget and widget.objectName() == "twitter_users_page":
                twitter_page = widget
                break
        
        # Si no se encuentra la página, usamos visualización de texto como respaldo
        if not twitter_page:
            self.logger.warning("twitter_users_page no encontrada en stackedWidget, buscando cualquier página...")
            
            # Intento alternativo: buscar tabla en cualquier página
            for i in range(stack_widget.count()):
                widget = stack_widget.widget(i)
                if widget:
                    table = widget.findChild(QTableWidget, "twitter_users_table")
                    if table:
                        twitter_page = widget
                        self.logger.info(f"Encontrada tabla twitter_users_table en página {widget.objectName()}")
                        break
                        
            if not twitter_page:
                self.logger.warning("No se encontró tabla twitter_users_table en ninguna página")
                self._display_twitter_users_as_text(users)
                return
        
        # Buscar la tabla en la página
        table = twitter_page.findChild(QTableWidget, "twitter_users_table")
        if not table:
            self.logger.error("twitter_users_table no encontrada en twitter_users_page")
            self._display_twitter_users_as_text(users)
            return
        
        # Obtener etiqueta de conteo si existe
        count_label = twitter_page.findChild(QLabel, "twitter_users_count_label")
        if count_label:
            count_label.setText(f"Mostrando {len(users)} usuarios en Twitter")
        
        # Configurar tabla
        table.setRowCount(0)  # Limpiar la tabla primero
        table.setRowCount(len(users))
        table.setSortingEnabled(False)  # Deshabilitar ordenamiento mientras se actualiza
        
        # Asegurarnos de que tenemos suficientes columnas
        header_labels = ["Seleccionar", "Nombre", "Usuario", "Seguidores", "Tweets", "Descripción"]
        if table.columnCount() < len(header_labels):
            table.setColumnCount(len(header_labels))
            table.setHorizontalHeaderLabels(header_labels)
        
        # Llenar la tabla con datos
        for i, user in enumerate(users):
            try:
                # Crear checkbox en primera columna con layout apropiado
                checkbox = QCheckBox()
                checkbox.setProperty("user_data", user)
                
                # Crear widget para contener el checkbox y centrarlo
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                checkbox_layout.setContentsMargins(4, 4, 4, 4)
                
                # Añadir el widget del checkbox a la celda
                table.setCellWidget(i, 0, checkbox_widget)
                
                # Columna de nombre
                name_item = QTableWidgetItem(user.get('name', user.get('twitter_name', 'Unknown')))
                table.setItem(i, 1, name_item)
                
                # Columna de username
                username = user.get('username', user.get('twitter_username', 'unknown'))
                username_item = QTableWidgetItem(f"@{username}")
                table.setItem(i, 2, username_item)
                
                # Columna de seguidores - usar NumericTableWidgetItem
                followers_count = 0
                if 'followers_count' in user:
                    followers_count = user.get('followers_count', 0)
                elif 'public_metrics' in user:
                    followers_count = user.get('public_metrics', {}).get('followers_count', 0)
                    
                followers_text = f"{followers_count:,}" if followers_count else "0"
                followers_item = NumericTableWidgetItem(str(followers_count))
                followers_item.setText(followers_text)
                followers_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(i, 3, followers_item)
                    
                # Columna de tweets
                tweet_count = 0
                if 'tweet_count' in user:
                    tweet_count = user.get('tweet_count', 0)
                elif 'public_metrics' in user:
                    tweet_count = user.get('public_metrics', {}).get('tweet_count', 0)
                    
                tweet_count_text = f"{tweet_count:,}" if tweet_count else "0"
                tweet_count_item = NumericTableWidgetItem(str(tweet_count))
                tweet_count_item.setText(tweet_count_text)
                tweet_count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(i, 4, tweet_count_item)
                
                # Columna de descripción (opcional)
                if table.columnCount() > 5:
                    description = user.get('description', '')
                    description_item = QTableWidgetItem(description)
                    table.setItem(i, 5, description_item)
                
                # Almacenar datos de usuario para cada ítem
                for col in range(1, table.columnCount()):
                    if table.item(i, col):
                        table.item(i, col).setData(Qt.ItemDataRole.UserRole, user)
            except Exception as e:
                self.logger.error(f"Error al añadir fila {i} a la tabla: {e}")
                # Continuar con la siguiente fila
        
        # Reactivar ordenamiento
        table.setSortingEnabled(True)

        # Redimensionar columnas para ajustar contenido
        table.resizeColumnsToContents()
        
        # Conectar el botón de seguir si existe
        follow_button = twitter_page.findChild(QPushButton, "twitter_follow_button")
        if follow_button:
            # Desconectar cualquier conexión previa
            try:
                follow_button.clicked.disconnect()
            except:
                pass
            # Conectar a la función de seguir
            follow_button.clicked.connect(lambda: self.follow_selected_twitter_users(table))
        
        # Configurar menú contextual para la tabla
        if table.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(self.show_twitter_user_context_menu)
        
        # Cambiar a la página de usuarios de Twitter
        stack_widget.setCurrentWidget(twitter_page)

    def _display_twitter_users_as_text(self, users):
        """
        Muestra usuarios de Twitter como texto en el área de resultados
        
        Args:
            users (list): Lista de diccionarios de usuarios de Twitter
        """
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"You follow {len(users)} users on Twitter")
        self.ui_callback.append("-" * 50)
        
        # Sort by name
        sorted_users = sorted(users, key=lambda x: x.get('name', '').lower())
        
        for i, user in enumerate(sorted_users):
            name = user.get('name', 'Unknown')
            username = user.get('username', '')
            followers = user.get('followers_count', 0)
            following = user.get('following_count', 0)
            tweets = user.get('tweet_count', 0)
            description = user.get('description', '')
            
            self.ui_callback.append(f"{i+1}. {name} (@{username})")
            self.ui_callback.append(f"   Followers: {followers:,} • Following: {following:,} • Tweets: {tweets:,}")
            if description:
                self.ui_callback.append(f"   {description}")
            self.ui_callback.append("")
        
        self.ui_callback.append("-" * 50)

    def show_twitter_user_context_menu(self, position):
        """
        Muestra menú contextual para usuarios de Twitter en la tabla
        
        Args:
            position (QPoint): Posición donde se solicitó el menú contextual
        """
        table = self.parent.sender()
        if not table:
            return
        
        item = table.itemAt(position)
        if not item:
            return
        
        # Get the user data from the item
        user_data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(user_data, dict):
            return
        
        user_id = user_data.get('id', '')
        name = user_data.get('name', '')
        username = user_data.get('username', '')
        
        if not user_id or not username:
            return
        
        # Create the context menu
        menu = QMenu(self.parent)
        
        # Add actions
        view_profile_action = QAction(f"View @{username} on Twitter", self.parent)
        view_profile_action.triggered.connect(lambda: self.utils.open_url(f"https://twitter.com/{username}"))
        menu.addAction(view_profile_action)
        
        # Add unfollow option
        unfollow_action = QAction(f"Unfollow @{username}", self.parent)
        unfollow_action.triggered.connect(lambda: self.unfollow_twitter_user_with_confirm(user_id, name, username))
        menu.addAction(unfollow_action)
        
        # Add option to view recent tweets
        view_tweets_action = QAction(f"View recent tweets from @{username}", self.parent)
        view_tweets_action.triggered.connect(lambda: self.show_user_tweets(user_id, name, username))
        menu.addAction(view_tweets_action)
        
        # If this is an artist, add option to follow on Muspy
        if self.muspy_manager:
            menu.addSeparator()
            follow_muspy_action = QAction(f"Follow '{name}' on Muspy", self.parent)
            follow_muspy_action.triggered.connect(lambda: self.muspy_manager.follow_artist_from_name(name))
            menu.addAction(follow_muspy_action)
        
        # Show the menu
        menu.exec(table.mapToGlobal(position))

    def unfollow_twitter_user_with_confirm(self, user_id, name, username):
        """
        Deja de seguir un usuario de Twitter con confirmación
        
        Args:
            user_id (str): ID del usuario
            name (str): Nombre del usuario
            username (str): Nombre de usuario
        """
        reply = QMessageBox.question(
            self.parent,
            "Confirm Unfollow",
            f"Are you sure you want to unfollow {name} (@{username})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Get Twitter client
            twitter_client = self.twitter_auth.get_client()
            if not twitter_client:
                QMessageBox.warning(self.parent, "Error", "Failed to get Twitter client")
                return
                
            # Try to unfollow
            if twitter_client.unfollow_user(user_id):
                QMessageBox.information(self.parent, "Success", f"Successfully unfollowed {name}")
                
                # Ask user if they want to refresh the list
                refresh_reply = QMessageBox.question(
                    self.parent,
                    "Refresh List",
                    "Do you want to refresh your followed users list?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if refresh_reply == QMessageBox.StandardButton.Yes:
                    # Clear cache and refresh
                    self.clear_twitter_cache()
                    self.show_twitter_followed_users()
            else:
                QMessageBox.warning(self.parent, "Error", f"Failed to unfollow {name}")

    def show_user_tweets(self, user_id, name, username):
        """
        Muestra tweets recientes de un usuario
        
        Args:
            user_id (str): ID del usuario
            name (str): Nombre del usuario
            username (str): Nombre de usuario
        """
        if not self.ensure_twitter_auth():
            QMessageBox.warning(self.parent, "Error", "Twitter authentication required")
            return
            
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Loading recent tweets from {name} (@{username})...")
        QApplication.processEvents()
        
        # Get Twitter client
        twitter_client = self.twitter_auth.get_client()
        if not twitter_client:
            self.ui_callback.append("Failed to get Twitter client. Please check authentication.")
            return
            
        try:
            # Get recent tweets
            tweets_data = twitter_client.get_user_tweets(
                user_id, 
                max_results=20,
                exclude_replies=True,
                exclude_retweets=True
            )
            
            if not tweets_data or "data" not in tweets_data:
                self.ui_callback.append(f"No tweets found for {name} (@{username})")
                return
                
            tweets = tweets_data["data"]
            
            # Show tweets
            self.ui_callback.clear()
            self.ui_callback.append(f"Recent tweets from {name} (@{username})")
            self.ui_callback.append("-" * 50)
            
            for i, tweet in enumerate(tweets):
                # Format date
                created_at = tweet.get("created_at", "")
                if created_at:
                    from datetime import datetime
                    date_obj = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
                    date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                else:
                    date_str = "Unknown date"
                
                # Get metrics
                metrics = tweet.get("public_metrics", {})
                likes = metrics.get("like_count", 0)
                retweets = metrics.get("retweet_count", 0)
                
                # Show tweet
                self.ui_callback.append(f"{i+1}. [{date_str}]")
                self.ui_callback.append(f"{tweet.get('text', '')}")
                self.ui_callback.append(f"♥ {likes} • RT {retweets}")
                self.ui_callback.append("")
                
        except Exception as e:
            self.ui_callback.append(f"Error getting tweets: {str(e)}")
            
    def show_twitter_search_dialog(self):
        """
        Muestra un diálogo para buscar usuarios en Twitter
        """
        if not self.ensure_twitter_auth():
            QMessageBox.warning(self.parent, "Error", "Twitter authentication required")
            return
            
        # Create input dialog
        search_term, ok = QInputDialog.getText(
            self.parent,
            "Search Twitter Users",
            "Enter name or username to search:",
            QLineEdit.EchoMode.Normal
        )
        
        if not ok or not search_term.strip():
            return
            
        # Search for users
        self.search_twitter_users(search_term.strip())
            
    def search_twitter_users(self, query):
        """
        Busca usuarios en Twitter
        
        Args:
            query (str): Término de búsqueda
        """
        if not self.ensure_twitter_auth():
            QMessageBox.warning(self.parent, "Error", "Twitter authentication required")
            return
            
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Searching for '{query}' on Twitter...")
        QApplication.processEvents()
        
        # Get Twitter client
        twitter_client = self.twitter_auth.get_client()
        if not twitter_client:
            self.ui_callback.append("Failed to get Twitter client. Please check authentication.")
            return
            
        try:
            # Search for users
            result = twitter_client.search_users(query)
            
            if not result or "data" not in result:
                self.ui_callback.append(f"No users found for '{query}'")
                return
                
            users = result["data"]
            
            # Format and display the users
            self.ui_callback.clear()
            self.ui_callback.append(f"Search results for '{query}'")
            self.ui_callback.append("-" * 50)
            
            for i, user in enumerate(users):
                name = user.get("name", "Unknown")
                username = user.get("username", "")
                description = user.get("description", "")
                metrics = user.get("public_metrics", {})
                followers = metrics.get("followers_count", 0)
                
                self.ui_callback.append(f"{i+1}. {name} (@{username})")
                self.ui_callback.append(f"   Followers: {followers:,}")
                if description:
                    self.ui_callback.append(f"   {description}")
                    
                # Add follow button with HTML
                user_id = user.get("id", "")
                if user_id:
                    self.ui_callback.append(f'   <a href="follow:{user_id}:{name}:{username}">Follow</a> | <a href="view:{username}">View Profile</a>')
                
                self.ui_callback.append("")
                
            # Add follow ability functionality
            self.ui_callback.anchorClicked.connect(self._handle_search_result_link)
            
        except Exception as e:
            self.ui_callback.append(f"Error searching users: {str(e)}")
            
    def _handle_search_result_link(self, url):
        """
        Maneja clics en enlaces en resultados de búsqueda
        
        Args:
            url (QUrl): URL del enlace
        """
        url_str = url.toString()
        
        if url_str.startswith("follow:"):
            # Follow user action
            _, user_id, name, username = url_str.split(":", 3)
            self.follow_twitter_user(user_id, name, username)
            
        elif url_str.startswith("view:"):
            # View profile action
            _, username = url_str.split(":", 1)
            self.utils.open_url(f"https://twitter.com/{username}")
            
    def follow_twitter_user(self, user_id, name, username):
        """
        Sigue a un usuario en Twitter
        
        Args:
            user_id (str): ID del usuario
            name (str): Nombre del usuario
            username (str): Nombre de usuario
        """
        if not self.ensure_twitter_auth():
            QMessageBox.warning(self.parent, "Error", "Twitter authentication required")
            return
            
        # Get Twitter client
        twitter_client = self.twitter_auth.get_client()
        if not twitter_client:
            QMessageBox.warning(self.parent, "Error", "Failed to get Twitter client")
            return
            
        try:
            # Try to follow user
            result = twitter_client.follow_user(user_id)
            
            if result and "data" in result and result["data"].get("following"):
                QMessageBox.information(self.parent, "Success", f"You are now following {name} (@{username})")
                
                # Clear cache to refresh followed users list
                cache_key = "followed_users"
                self.cache_manager.cache_manager(cache_key, None, force_refresh=True)
            else:
                QMessageBox.warning(self.parent, "Error", f"Failed to follow {name} (@{username})")
                
        except Exception as e:
            QMessageBox.warning(self.parent, "Error", f"Error following user: {str(e)}")
            
    def clear_twitter_cache(self):
        """
        Limpia la caché de Twitter
        """
        try:
            # Clear user cache
            self.cache_manager.cache_manager("followed_users", None, force_refresh=True)
            
            # Clear other Twitter caches you might have
            
            # Show confirmation
            QMessageBox.information(self.parent, "Cache Cleared", "Twitter cache has been cleared")
            
        except Exception as e:
            QMessageBox.warning(self.parent, "Error", f"Error clearing cache: {str(e)}")
            
    def show_twitter_artist_tweets(self):
        """
        Muestra tweets recientes de artistas seleccionados
        """
        # Verificar autenticación
        if not self.ensure_twitter_auth():
            QMessageBox.warning(self.parent, "Error", "Twitter authentication required")
            return
            
        # Cargar artistas seleccionados
        json_path = Path(self.project_root, ".content", "cache", "artists_selected.json")
        
        if not os.path.exists(json_path):
            QMessageBox.warning(self.parent, "Error", "No selected artists found. Please load artists first.")
            return
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                artists_data = json.load(f)
                
            if not artists_data:
                QMessageBox.warning(self.parent, "Error", "No artists found in the selection file.")
                return
        except Exception as e:
            QMessageBox.warning(self.parent, "Error", f"Error loading artists: {str(e)}")
            return
            
        # Mostrar diálogo de selección de artistas
        artist_names = [artist.get("nombre", "") for artist in artists_data if artist.get("nombre")]
        
        # Ordenar alfabéticamente
        artist_names.sort()
        
        # Crear diálogo de selección
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Select Artists")
        dialog.setMinimumWidth(400)
        
        # Crear layout
        layout = QVBoxLayout(dialog)
        
        # Añadir instrucciones
        layout.addWidget(QLabel("Select artists to view their recent tweets:"))
        
        # Crear lista de checkboxes para artistas
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        checkboxes = []
        for artist_name in artist_names:
            checkbox = QCheckBox(artist_name)
            checkboxes.append(checkbox)
            scroll_layout.addWidget(checkbox)
            
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # Añadir botones de selección
        button_layout = QHBoxLayout()
        select_all = QPushButton("Select All")
        deselect_all = QPushButton("Deselect All")
        
        select_all.clicked.connect(lambda: [cb.setChecked(True) for cb in checkboxes])
        deselect_all.clicked.connect(lambda: [cb.setChecked(False) for cb in checkboxes])
        
        button_layout.addWidget(select_all)
        button_layout.addWidget(deselect_all)
        layout.addLayout(button_layout)
        
        # Añadir botones de aceptar/cancelar
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        # Mostrar diálogo
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        # Obtener artistas seleccionados
        selected_artists = [cb.text() for cb in checkboxes if cb.isChecked()]
        
        if not selected_artists:
            QMessageBox.warning(self.parent, "No Selection", "No artists selected")
            return
            
        # Buscar tweets de los artistas seleccionados
        self.fetch_artists_tweets(selected_artists)
        
    def fetch_artists_tweets(self, artist_names):
        """
        Busca tweets recientes de artistas
        
        Args:
            artist_names (list): Lista de nombres de artistas
        """
        if not self.ensure_twitter_auth():
            QMessageBox.warning(self.parent, "Error", "Twitter authentication required")
            return
            
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Searching for tweets from {len(artist_names)} artists...")
        QApplication.processEvents()
        
        # Get Twitter client
        twitter_client = self.twitter_auth.get_client()
        if not twitter_client:
            self.ui_callback.append("Failed to get Twitter client. Please check authentication.")
            return
            
        # Function to search with progress dialog
        def search_artist_tweets(update_progress):
            try:
                all_artist_results = []
                
                # Process each artist
                for i, artist_name in enumerate(artist_names):
                    # Update progress
                    progress = int((i / len(artist_names)) * 100)
                    update_progress(progress, 100, f"Searching for {artist_name} ({i+1}/{len(artist_names)})...")
                    
                    # Search for the artist
                    search_result = twitter_client.search_users(artist_name, max_results=3)
                    
                    if not search_result or "data" not in search_result:
                        continue
                        
                    users = search_result["data"]
                    
                    # Find best match
                    best_match = None
                    
                    for user in users:
                        user_name = user.get("name", "").lower()
                        username = user.get("username", "").lower()
                        
                        # Check for exact or close match
                        artist_lower = artist_name.lower()
                        if (artist_lower == user_name or
                            artist_lower in user_name or
                            artist_lower == username or
                            artist_lower in username):
                            best_match = user
                            break
                    
                    if not best_match:
                        continue
                        
                    # Get user ID
                    user_id = best_match.get("id")
                    if not user_id:
                        continue
                        
                    # Get recent tweets
                    tweets_data = twitter_client.get_user_tweets(
                        user_id, 
                        max_results=5,
                        exclude_replies=True,
                        exclude_retweets=True
                    )
                    
                    if not tweets_data or "data" not in tweets_data:
                        continue
                        
                    # Add to results
                    all_artist_results.append({
                        'artist': artist_name,
                        'user': best_match,
                        'tweets': tweets_data["data"]
                    })
                    
                update_progress(100, 100, "Processing results...")
                
                return {
                    "success": True,
                    "results": all_artist_results
                }
                
            except Exception as e:
                self.logger.error(f"Error searching artist tweets: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
                
        # Execute with progress dialog
        result = self.progress_utils.show_progress_operation(
            search_artist_tweets,
            title="Searching Artist Tweets",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            artist_results = result.get("results", [])
            
            if not artist_results:
                self.ui_callback.append("No tweets found for any of the selected artists")
                return
                
            # Display results
            self.ui_callback.clear()
            self.ui_callback.append(f"Recent tweets from artists ({len(artist_results)}/{len(artist_names)} found)")
            self.ui_callback.append("=" * 70)
            
            for artist_result in artist_results:
                artist_name = artist_result['artist']
                user = artist_result['user']
                tweets = artist_result['tweets']
                
                username = user.get("username", "")
                
                self.ui_callback.append(f"\n## {artist_name} (@{username})")
                self.ui_callback.append("-" * 50)
                
                if not tweets:
                    self.ui_callback.append("No recent tweets found")
                    continue
                    
                for tweet in tweets:
                    # Format date
                    created_at = tweet.get("created_at", "")
                    if created_at:
                        from datetime import datetime
                        date_obj = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
                        date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                    else:
                        date_str = "Unknown date"
                    
                    # Get metrics
                    metrics = tweet.get("public_metrics", {})
                    likes = metrics.get("like_count", 0)
                    retweets = metrics.get("retweet_count", 0)
                    
                    # Show tweet
                    self.ui_callback.append(f"[{date_str}]")
                    self.ui_callback.append(f"{tweet.get('text', '')}")
                    self.ui_callback.append(f"♥ {likes} • RT {retweets}")
                    self.ui_callback.append("")
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.ui_callback.append(f"Error: {error_msg}")
            
    def sync_artists_with_twitter(self):
        """
        Sincroniza artistas seleccionados con Twitter (seguir artistas)
        """
        # Verificar autenticación
        if not self.ensure_twitter_auth():
            QMessageBox.warning(self.parent, "Error", "Twitter authentication required")
            return
            
        # Cargar artistas seleccionados
        json_path = Path(self.project_root, ".content", "cache", "artists_selected.json")
        
        if not os.path.exists(json_path):
            QMessageBox.warning(self.parent, "Error", "No selected artists found. Please load artists first.")
            return
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                artists_data = json.load(f)
                
            if not artists_data:
                QMessageBox.warning(self.parent, "Error", "No artists found in the selection file.")
                return
        except Exception as e:
            QMessageBox.warning(self.parent, "Error", f"Error loading artists: {str(e)}")
            return
        
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Preparing to sync {len(artists_data)} artists with Twitter...")
        QApplication.processEvents()
        
        # Get Twitter client
        twitter_client = self.twitter_auth.get_client()
        if not twitter_client:
            self.ui_callback.append("Failed to get Twitter client. Please check authentication.")
            return
        
        # Function to sync with progress dialog
        def sync_artists_to_twitter(update_progress):
            try:
                # Prepare counters for results
                results = {
                    "successful_follows": 0,
                    "already_following": 0,
                    "not_found": 0,
                    "failed": 0,
                    "processed": 0,
                    "details": []
                }
                
                # Process each artist
                for i, artist_data in enumerate(artists_data):
                    artist_name = artist_data.get("nombre", "")
                    
                    if not artist_name:
                        results["failed"] += 1
                        continue
                    
                    # Update progress
                    progress = int((i / len(artists_data)) * 100)
                    update_progress(progress, 100, f"Processing {artist_name} ({i+1}/{len(artists_data)})...")
                    
                    # Search for the artist on Twitter
                    search_result = twitter_client.search_users(artist_name, max_results=3)
                    
                    if not search_result or "data" not in search_result:
                        # Artist not found
                        results["not_found"] += 1
                        results["details"].append({
                            "artist": artist_name,
                            "status": "not_found",
                            "message": "No results found on Twitter"
                        })
                        continue
                    
                    users = search_result["data"]
                    
                    # Find best match
                    best_match = None
                    
                    for user in users:
                        user_name = user.get("name", "").lower()
                        username = user.get("username", "").lower()
                        
                        # Check for exact or close match
                        artist_lower = artist_name.lower()
                        if (artist_lower == user_name or
                            artist_lower in user_name or
                            artist_lower == username or
                            artist_lower in username):
                            best_match = user
                            break
                    
                    if not best_match:
                        # No good match found
                        results["not_found"] += 1
                        results["details"].append({
                            "artist": artist_name,
                            "status": "no_match",
                            "message": "No suitable match found on Twitter"
                        })
                        continue
                    
                    # Get user ID
                    user_id = best_match.get("id")
                    if not user_id:
                        results["failed"] += 1
                        continue
                    
                    # Try to follow the artist
                    try:
                        follow_result = twitter_client.follow_user(user_id)
                        
                        if follow_result and "data" in follow_result:
                            if follow_result["data"].get("following"):
                                # Successfully followed
                                results["successful_follows"] += 1
                                results["details"].append({
                                    "artist": artist_name,
                                    "status": "followed",
                                    "twitter_name": best_match.get("name", ""),
                                    "twitter_username": best_match.get("username", "")
                                })
                            else:
                                # Already following or other status
                                results["already_following"] += 1
                                results["details"].append({
                                    "artist": artist_name,
                                    "status": "already_following",
                                    "twitter_name": best_match.get("name", ""),
                                    "twitter_username": best_match.get("username", "")
                                })
                        else:
                            # Failed to follow
                            results["failed"] += 1
                            results["details"].append({
                                "artist": artist_name,
                                "status": "failed",
                                "message": "API request failed"
                            })
                    except Exception as e:
                        # Exception during follow request
                        results["failed"] += 1
                        results["details"].append({
                            "artist": artist_name,
                            "status": "error",
                            "message": str(e)
                        })
                    
                    # Update processed count
                    results["processed"] += 1
                
                # Completion
                update_progress(100, 100, "Sync completed")
                
                return {
                    "success": True,
                    "results": results
                }
                
            except Exception as e:
                self.logger.error(f"Error syncing artists with Twitter: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Execute with progress dialog
        result = self.progress_utils.show_progress_operation(
            sync_artists_to_twitter,
            title="Syncing Artists with Twitter",
            label_format="{status}"
        )
        
        # Process results
        if result and result.get("success"):
            sync_results = result.get("results", {})
            
            # Display results
            self.ui_callback.clear()
            self.ui_callback.append("Twitter Synchronization Results")
            self.ui_callback.append("=" * 50)
            self.ui_callback.append(f"Artists processed: {sync_results.get('processed', 0)}/{len(artists_data)}")
            self.ui_callback.append(f"Successfully followed: {sync_results.get('successful_follows', 0)}")
            self.ui_callback.append(f"Already following: {sync_results.get('already_following', 0)}")
            self.ui_callback.append(f"Not found on Twitter: {sync_results.get('not_found', 0)}")
            self.ui_callback.append(f"Failed to follow: {sync_results.get('failed', 0)}")
            
            # Display details for successful follows
            if sync_results.get("successful_follows", 0) > 0:
                self.ui_callback.append("\nSuccessfully followed artists:")
                for detail in sync_results.get("details", []):
                    if detail.get("status") == "followed":
                        artist = detail.get("artist", "Unknown")
                        twitter_name = detail.get("twitter_name", "")
                        twitter_username = detail.get("twitter_username", "")
                        self.ui_callback.append(f"- {artist} → {twitter_name} (@{twitter_username})")
            
            # Show summary in a message box
            QMessageBox.information(
                self.parent, 
                "Twitter Sync Complete",
                f"Successfully followed {sync_results.get('successful_follows', 0)} artists on Twitter.\n" +
                f"Already following: {sync_results.get('already_following', 0)}\n" +
                f"Not found: {sync_results.get('not_found', 0)}\n" +
                f"Failed: {sync_results.get('failed', 0)}"
            )
            
            # Refresh the cache for followed users
            self.cache_manager.cache_manager("followed_users", None, force_refresh=True)
            
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.ui_callback.append(f"Error: {error_msg}")
            QMessageBox.warning(self.parent, "Error", f"Could not sync artists with Twitter: {error_msg}")



    def follow_selected_twitter_users(self, table):
        """
        Sigue a los usuarios seleccionados mediante checkboxes en la tabla
        
        Args:
            table (QTableWidget): Tabla con los usuarios
        """
        if not self.ensure_twitter_auth():
            QMessageBox.warning(self.parent, "Error", "Twitter authentication required")
            return
        
        # Recolectar usuarios seleccionados
        selected_users = []
        
        for row in range(table.rowCount()):
            # Obtener el checkbox de la primera columna
            checkbox_widget = table.cellWidget(row, 0)
            if not checkbox_widget:
                continue
            
            # Buscar el checkbox dentro del widget
            checkbox = None
            for child in checkbox_widget.findChildren(QCheckBox):
                checkbox = child
                break
            
            if checkbox and checkbox.isChecked():
                # Obtener datos del usuario
                user_data = checkbox.property("user_data")
                if user_data and 'id' in user_data:
                    selected_users.append(user_data)
        
        if not selected_users:
            QMessageBox.warning(self.parent, "No Selection", "No users selected")
            return
        
        # Confirmar la operación
        reply = QMessageBox.question(
            self.parent,
            "Confirm Follow",
            f"Are you sure you want to follow {len(selected_users)} selected Twitter users?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Get Twitter client
        twitter_client = self.twitter_auth.get_client()
        if not twitter_client:
            QMessageBox.warning(self.parent, "Error", "Failed to get Twitter client")
            return
        
        # Crear diálogo de progreso
        progress = QProgressDialog("Following selected users...", "Cancel", 0, len(selected_users), self.parent)
        progress.setWindowTitle("Following Users")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        # Contadores para resultados
        success_count = 0
        already_following = 0
        error_count = 0
        results = []
        
        # Seguir a cada usuario
        for i, user in enumerate(selected_users):
            # Comprobar si el usuario canceló
            if progress.wasCanceled():
                break
            
            # Actualizar progreso
            user_name = user.get('name', 'Unknown')
            username = user.get('username', '')
            progress.setValue(i)
            progress.setLabelText(f"Following {user_name} (@{username})...")
            QApplication.processEvents()
            
            try:
                # Intentar seguir al usuario
                result = twitter_client.follow_user(user['id'])
                
                if result and "data" in result:
                    if result["data"].get("following"):
                        # Successfully followed
                        success_count += 1
                        results.append({
                            "name": user_name,
                            "username": username,
                            "status": "followed"
                        })
                    else:
                        # Already following or other status
                        already_following += 1
                        results.append({
                            "name": user_name,
                            "username": username,
                            "status": "already_following"
                        })
                else:
                    # Failed to follow
                    error_count += 1
                    results.append({
                        "name": user_name,
                        "username": username,
                        "status": "error",
                        "message": "API request failed"
                    })
            except Exception as e:
                error_count += 1
                results.append({
                    "name": user_name,
                    "username": username,
                    "status": "error",
                    "message": str(e)
                })
        
        # Cerrar diálogo
        progress.setValue(len(selected_users))
        
        # Mostrar resultados
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append("Follow Results")
        self.ui_callback.append("=" * 50)
        self.ui_callback.append(f"Successfully followed: {success_count}")
        self.ui_callback.append(f"Already following: {already_following}")
        self.ui_callback.append(f"Failed: {error_count}")
        self.ui_callback.append("\nDetails:")
        
        for result in results:
            status = result["status"]
            name = result["name"]
            username = result["username"]
            
            if status == "followed":
                self.ui_callback.append(f"✓ Now following {name} (@{username})")
            elif status == "already_following":
                self.ui_callback.append(f"• Already following {name} (@{username})")
            else:
                message = result.get("message", "Unknown error")
                self.ui_callback.append(f"✗ Error following {name} (@{username}): {message}")
        
        # Mostrar mensaje de éxito
        QMessageBox.information(
            self.parent,
            "Follow Complete",
            f"Successfully followed {success_count} users.\n" +
            f"Already following: {already_following}\n" +
            f"Failed: {error_count}"
        )
        
        # Actualizar la caché
        self.cache_manager.cache_manager("followed_users", None, force_refresh=True)


    def _sync_artists_list_with_twitter(self, artists_data, source_name=""):
        """
        Sincroniza una lista de artistas con Twitter
        
        Args:
            artists_data (list): Lista de diccionarios con datos de artistas
            source_name (str): Nombre de la fuente de datos (ej: "Spotify", "base de datos")
        """
        # Verificar que tenemos un cliente de Twitter
        twitter_client = None
        if hasattr(self, 'twitter_auth'):
            twitter_client = self.twitter_auth.get_client()
        
        if not twitter_client:
            # No tenemos cliente, intentar autenticación
            if not self.ensure_twitter_auth(silent=False):
                QMessageBox.warning(self.parent, "Error", "Twitter authentication required")
                return
            twitter_client = self.twitter_auth.get_client()
            if not twitter_client:
                QMessageBox.warning(self.parent, "Error", "Failed to get Twitter client")
                return
        
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Preparando para sincronizar {len(artists_data)} artistas de {source_name} con Twitter...")
        QApplication.processEvents()
        
        # Function to sync with progress dialog
        def sync_artists_to_twitter(update_progress):
            try:
                # Prepare counters for results
                results = {
                    "successful_follows": 0,
                    "already_following": 0,
                    "not_found": 0,
                    "failed": 0,
                    "processed": 0,
                    "details": []
                }
                
                # Process each artist
                for i, artist_data in enumerate(artists_data):
                    # Get artist name based on the data structure
                    if isinstance(artist_data, dict):
                        if "nombre" in artist_data:
                            artist_name = artist_data.get("nombre", "")
                        elif "name" in artist_data:
                            artist_name = artist_data.get("name", "")
                        else:
                            # Try to find any key that might contain the name
                            name_keys = ["artist_name", "artist", "nombre_artista"]
                            artist_name = ""
                            for key in name_keys:
                                if key in artist_data:
                                    artist_name = artist_data.get(key, "")
                                    break
                    elif isinstance(artist_data, str):
                        artist_name = artist_data
                    else:
                        # Skip this item if we can't determine the artist name
                        results["failed"] += 1
                        continue
                    
                    if not artist_name:
                        results["failed"] += 1
                        continue
                    
                    # Update progress
                    progress = int((i / len(artists_data)) * 100)
                    update_progress(progress, 100, f"Processing {artist_name} ({i+1}/{len(artists_data)})...")
                    
                    # Search for the artist on Twitter
                    search_result = twitter_client.search_users(artist_name, max_results=3)
                    
                    if not search_result or "data" not in search_result:
                        # Artist not found
                        results["not_found"] += 1
                        results["details"].append({
                            "artist": artist_name,
                            "status": "not_found",
                            "message": "No results found on Twitter"
                        })
                        continue
                    
                    users = search_result["data"]
                    
                    # Find best match
                    best_match = None
                    
                    for user in users:
                        user_name = user.get("name", "").lower()
                        username = user.get("username", "").lower()
                        
                        # Check for exact or close match
                        artist_lower = artist_name.lower()
                        if (artist_lower == user_name or
                            artist_lower in user_name or
                            artist_lower == username or
                            artist_lower in username):
                            best_match = user
                            break
                    
                    if not best_match:
                        # No good match found
                        results["not_found"] += 1
                        results["details"].append({
                            "artist": artist_name,
                            "status": "no_match",
                            "message": "No suitable match found on Twitter"
                        })
                        continue
                    
                    # Get user ID
                    user_id = best_match.get("id")
                    if not user_id:
                        results["failed"] += 1
                        continue
                    
                    # Try to follow the artist
                    try:
                        follow_result = twitter_client.follow_user(user_id)
                        
                        if follow_result and "data" in follow_result:
                            if follow_result["data"].get("following"):
                                # Successfully followed
                                results["successful_follows"] += 1
                                results["details"].append({
                                    "artist": artist_name,
                                    "status": "followed",
                                    "twitter_name": best_match.get("name", ""),
                                    "twitter_username": best_match.get("username", "")
                                })
                            else:
                                # Already following or other status
                                results["already_following"] += 1
                                results["details"].append({
                                    "artist": artist_name,
                                    "status": "already_following",
                                    "twitter_name": best_match.get("name", ""),
                                    "twitter_username": best_match.get("username", "")
                                })
                        else:
                            # Failed to follow
                            results["failed"] += 1
                            results["details"].append({
                                "artist": artist_name,
                                "status": "failed",
                                "message": "API request failed"
                            })
                    except Exception as e:
                        # Exception during follow request
                        results["failed"] += 1
                        results["details"].append({
                            "artist": artist_name,
                            "status": "error",
                            "message": str(e)
                        })
                    
                    # Update processed count
                    results["processed"] += 1
                
                # Completion
                update_progress(100, 100, "Sync completed")
                
                return {
                    "success": True,
                    "results": results
                }
                
            except Exception as e:
                self.logger.error(f"Error syncing artists with Twitter: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Intentar diferentes opciones para acceder a la función show_progress_operation
        # (En orden de preferencia)
        try:
            # Opción 1: Usar desde el módulo progress_utils directamente
            from modules.submodules.muspy.progress_utils import show_progress_operation
            result = show_progress_operation(
                self.parent,  # Pasar parent como primer argumento
                sync_artists_to_twitter,
                title=f"Syncing {source_name} Artists with Twitter",
                label_format="{status}"
            )
        except Exception as e1:
            try:
                # Opción 2: Intentar usar el método en parent
                result = self.parent.show_progress_operation(
                    sync_artists_to_twitter,
                    title=f"Syncing {source_name} Artists with Twitter",
                    label_format="{status}"
                )
            except Exception as e2:
                try:
                    # Opción 3: Si hay progress_utils disponible en self
                    if hasattr(self, 'progress_utils') and self.progress_utils is not None:
                        result = self.progress_utils.show_progress_operation(
                            sync_artists_to_twitter,
                            title=f"Syncing {source_name} Artists with Twitter",
                            label_format="{status}"
                        )
                    else:
                        # Si todo falla, crear un diálogo de progreso manual básico
                        from PyQt6.QtWidgets import QProgressDialog
                        from PyQt6.QtCore import Qt
                        
                        progress_dialog = QProgressDialog(
                            f"Syncing {source_name} Artists with Twitter",
                            "Cancel",
                            0, 100,
                            self.parent
                        )
                        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                        progress_dialog.setMinimumDuration(0)
                        progress_dialog.setValue(0)
                        progress_dialog.setAutoClose(True)
                        progress_dialog.setAutoReset(False)
                        progress_dialog.show()
                        
                        # Función personalizada para actualizar el progreso
                        def update_progress_dialog(current, total, status="", indeterminate=False):
                            if progress_dialog.wasCanceled():
                                return False
                                
                            if indeterminate:
                                progress_dialog.setRange(0, 0)
                            else:
                                progress_dialog.setRange(0, 100)
                                progress_percent = int((current / total) * 100) if total > 0 else 0
                                progress_dialog.setValue(progress_percent)
                                
                            progress_dialog.setLabelText(status)
                            QApplication.processEvents()
                            return True
                            
                        # Ejecutar la función con nuestro callback personalizado
                        result = sync_artists_to_twitter(update_progress_dialog)
                        
                        # Cerrar el diálogo
                        progress_dialog.close()
                except Exception as e3:
                    # Si todo falla, manejar el error
                    self.logger.error(f"Error accessing show_progress_operation: {e1}, {e2}, {e3}")
                    QMessageBox.warning(
                        self.parent,
                        "Error",
                        "No se pudo acceder a la función de progreso. Intenta actualizar la aplicación."
                    )
                    return
        
        # Process results
        if result and result.get("success"):
            sync_results = result.get("results", {})
            
            # Display results
            self.ui_callback.clear()
            self.ui_callback.append(f"Twitter Synchronization Results for {source_name}")
            self.ui_callback.append("=" * 50)
            self.ui_callback.append(f"Artists processed: {sync_results.get('processed', 0)}/{len(artists_data)}")
            self.ui_callback.append(f"Successfully followed: {sync_results.get('successful_follows', 0)}")
            self.ui_callback.append(f"Already following: {sync_results.get('already_following', 0)}")
            self.ui_callback.append(f"Not found on Twitter: {sync_results.get('not_found', 0)}")
            self.ui_callback.append(f"Failed to follow: {sync_results.get('failed', 0)}")
            
            # Display details for successful follows
            if sync_results.get("successful_follows", 0) > 0:
                self.ui_callback.append("\nSuccessfully followed artists:")
                for detail in sync_results.get("details", []):
                    if detail.get("status") == "followed":
                        artist = detail.get("artist", "Unknown")
                        twitter_name = detail.get("twitter_name", "")
                        twitter_username = detail.get("twitter_username", "")
                        self.ui_callback.append(f"- {artist} → {twitter_name} (@{twitter_username})")
            
            # Show summary in a message box
            QMessageBox.information(
                self.parent, 
                "Twitter Sync Complete",
                f"Successfully followed {sync_results.get('successful_follows', 0)} artists on Twitter.\n" +
                f"Already following: {sync_results.get('already_following', 0)}\n" +
                f"Not found: {sync_results.get('not_found', 0)}\n" +
                f"Failed: {sync_results.get('failed', 0)}"
            )
            
            # Refresh the cache for followed users
            self.cache_manager.cache_manager("followed_users", None, force_refresh=True)
            
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.ui_callback.append(f"Error: {error_msg}")
            QMessageBox.warning(self.parent, "Error", f"Could not sync artists with Twitter: {error_msg}")



    def sync_db_artists_with_twitter(self):
        """
        Sincroniza artistas seleccionados de la base de datos con Twitter
        mostrando primero un diálogo para seleccionar artistas
        """
        # Verificar primero si hay cliente de Twitter directamente
        twitter_client = None
        if hasattr(self, 'twitter_auth'):
            try:
                twitter_client = self.twitter_auth.get_client()
            except Exception as e:
                self.logger.warning(f"Error obteniendo cliente de Twitter: {e}")
        
        # Si no hay cliente, intentar autenticación explícita
        if not twitter_client:
            self.logger.info("No hay cliente de Twitter, iniciando autenticación...")
            if hasattr(self, 'twitter_auth') and self.twitter_auth:
                # Intentar autenticación directa con authenticate
                try:
                    result = self.twitter_auth.authenticate(silent=False)
                    if result:
                        self.logger.info("Autenticación de Twitter exitosa")
                        twitter_client = self.twitter_auth.get_client()
                    else:
                        self.logger.warning("Autenticación de Twitter fallida")
                        QMessageBox.warning(self.parent, "Error", "La autenticación con Twitter falló")
                        return
                except Exception as e:
                    self.logger.error(f"Error en authenticate: {e}")
                    QMessageBox.warning(self.parent, "Error", f"Error durante la autenticación: {str(e)}")
                    return
            else:
                QMessageBox.warning(self.parent, "Error", "Twitter no está configurado correctamente")
                return
        
        # Verificar una vez más si tenemos el cliente
        if not twitter_client:
            QMessageBox.warning(self.parent, "Error", "No se pudo obtener cliente de Twitter después de autenticar")
            return
            
        # Mostrar diálogo de selección de artistas
        self.show_artist_selection_for_twitter()

      
    def show_artist_selection_for_twitter(self):
        """
        Muestra un diálogo para seleccionar artistas para Twitter
        similar a load_artists_from_file pero guardando en artists_selected_twitter.json
        """
        try:
            # Asegurar que tenemos PROJECT_ROOT
            if not hasattr(self, 'project_root'):
                QMessageBox.warning(self.parent, "Error", "PROJECT_ROOT no definido")
                return

            # Asegurar db_path es absoluto
            if not hasattr(self.parent, 'db_path'):
                QMessageBox.warning(self.parent, "Error", "Database path not defined")
                return
                
            full_db_path = self.parent.db_path
            if not os.path.isabs(full_db_path):
                full_db_path = Path(self.project_root, full_db_path)
            
            # Construir ruta al script
            script_path = Path(self.project_root, "db", "tools", "consultar_items_db.py")
            
            # Verificar si el script existe
            if not os.path.exists(script_path):
                QMessageBox.warning(self.parent, "Error", f"Script not found at {script_path}")
                return
                
            # Ejecutar la consulta para artistas en la base de datos
            self.display_manager.show_text_page()
            self.ui_callback.clear()
            self.ui_callback.append("Ejecutando consulta para artistas en la base de datos...")
            QApplication.processEvents()  # Actualizar UI
            
            cmd = f"python {script_path} --db {full_db_path} --buscar artistas"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.ui_callback.append(f"Error ejecutando script: {result.stderr}")
                return
                
            # Cargar resultados como JSON
            try:
                artists_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                self.ui_callback.append(f"Error procesando salida del script: {e}")
                self.ui_callback.append(f"Salida del script: {result.stdout[:500]}...")
                return
            
            # Verificar si hay artistas
            if not artists_data:
                self.ui_callback.append("No se encontraron artistas en la base de datos.")
                return
            
            # Asegurar que existe el directorio de caché
            cache_dir = Path(self.project_root, ".content", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            # Cargar artistas existentes si el archivo ya existe
            json_path = Path(cache_dir, "artists_selected_twitter.json")
            existing_artists = []
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = f.read()
                        if data:  # Solo intentar cargar si no está vacío
                            existing_artists = json.loads(data)
                except Exception as e:
                    self.ui_callback.append(f"Error cargando artistas existentes: {e}")
            
            # Crear una lista de nombres de artistas existentes
            existing_names = set()
            if existing_artists:
                existing_names = {artist.get("nombre", "") for artist in existing_artists if isinstance(artist, dict) and "nombre" in artist}
            
            # Crear el diálogo usando el archivo UI
            dialog = QDialog(self.parent)
            ui_file_path = Path(self.project_root, "ui", "muspy", "muspy_artist_selection_dialog.ui")
            
            if os.path.exists(ui_file_path):
                try:
                    # Cargar el archivo UI
                    uic.loadUi(ui_file_path, dialog)
                    
                    # Conectar explícitamente los botones del diálogo
                    if hasattr(dialog, 'buttonBox'):
                        dialog.buttonBox.accepted.connect(dialog.accept)
                        dialog.buttonBox.rejected.connect(dialog.reject)
                    
                    # Actualizar la etiqueta con el número de artistas
                    dialog.info_label.setText(f"Selecciona los artistas para buscar en Twitter ({len(artists_data)} encontrados)")
                    
                    # Eliminar checkboxes de ejemplo de scroll_layout
                    for i in reversed(range(dialog.scroll_layout.count())):
                        widget = dialog.scroll_layout.itemAt(i).widget()
                        if widget is not None:
                            widget.deleteLater()
                    
                    # Crear checkboxes para cada artista
                    checkboxes = []
                    for artist in artists_data:
                        artist_name = artist.get('nombre', '')
                        artist_mbid = artist.get('mbid', '')
                        
                        checkbox = QCheckBox(f"{artist_name} ({artist_mbid})")
                        checkbox.setChecked(artist_name in existing_names)  # Pre-seleccionar si ya existe
                        checkbox.setProperty("artist_data", artist)  # Almacenar datos del artista en el checkbox
                        checkboxes.append(checkbox)
                        dialog.scroll_layout.addWidget(checkbox)
                    
                    # Encontrar la función filter_artists en parent
                    filter_fn = None
                    if hasattr(self.parent, 'filter_artists'):
                        filter_fn = self.parent.filter_artists
                    elif hasattr(self, 'filter_artists'):
                        filter_fn = self.filter_artists
                    
                    # Definir función de filtrado genérica
                    def generic_filter_artists(search_text, checkboxes):
                        search_text = search_text.lower()
                        for checkbox in checkboxes:
                            artist_data = checkbox.property("artist_data")
                            
                            # Mostrar/ocultar basado en coincidencia del nombre del artista
                            if isinstance(artist_data, dict) and "nombre" in artist_data:
                                artist_name = artist_data["nombre"].lower()
                                visible = search_text in artist_name
                                checkbox.setVisible(visible)
                            else:
                                # Fallback al texto del checkbox si artist_data no está disponible
                                checkbox_text = checkbox.text().lower()
                                visible = search_text in checkbox_text
                                checkbox.setVisible(visible)
                    
                    # Conectar señales
                    dialog.search_input.textChanged.connect(
                        lambda text: filter_fn(text, checkboxes) if filter_fn else generic_filter_artists(text, checkboxes)
                    )
                    dialog.action_select_all.clicked.connect(lambda: [cb.setChecked(True) for cb in checkboxes if not cb.isHidden()])
                    dialog.action_deselect_all.clicked.connect(lambda: [cb.setChecked(False) for cb in checkboxes])
                    
                except Exception as e:
                    self.ui_callback.append(f"Error cargando UI para selección de artistas: {e}")
                    return
            else:
                self.ui_callback.append(f"Archivo UI no encontrado: {ui_file_path}")
                return
                
            # Mostrar el diálogo
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted:
                self.ui_callback.append("Diálogo aceptado, procesando selección...")
            else:
                self.ui_callback.append("Operación cancelada por el usuario.")
                return
            
            # Recolectar artistas seleccionados
            selected_artists = []
            
            # Obtener artistas seleccionados de los checkboxes
            for checkbox in checkboxes:
                if checkbox.isChecked():
                    artist_data = checkbox.property("artist_data")
                    if artist_data:
                        selected_artists.append(artist_data)
            
            self.ui_callback.append(f"Número de artistas seleccionados: {len(selected_artists)}")
            
            # Guardar artistas seleccionados en JSON
            try:
                # Asegurar que existe el directorio
                os.makedirs(cache_dir, exist_ok=True)
                json_path = Path(cache_dir, "artists_selected_twitter.json")
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(selected_artists, f, ensure_ascii=False, indent=2)
                
                self.ui_callback.append(f"Guardados {len(selected_artists)} artistas en {json_path}")
                
                # Continuar con la sincronización de Twitter
                if selected_artists:
                    self._sync_twitter_from_selected_file("artists_selected_twitter.json")
                else:
                    QMessageBox.information(
                        self.parent, 
                        "Selección vacía", 
                        "No se seleccionaron artistas para sincronizar con Twitter."
                    )
            except Exception as e:
                self.ui_callback.append(f"Error guardando artistas: {e}")
        
        except Exception as e:
            self.ui_callback.append(f"Error: {str(e)}")
            self.logger.error(f"Error en show_artist_selection_for_twitter: {e}", exc_info=True)


 
    def _sync_twitter_from_selected_file(self, filename="artists_selected_twitter.json"):
        """
        Sincroniza artistas desde un archivo JSON específico con Twitter
        
        Args:
            filename (str): Nombre del archivo JSON con artistas seleccionados
        """
        # Comprobar cliente de Twitter directamente - sin silent mode para forzar la autenticación interactiva
        if not self.ensure_twitter_auth(silent=False):
            self.logger.error("No se pudo autenticar con Twitter")
            QMessageBox.warning(self.parent, "Error", "La autenticación con Twitter falló. Por favor, verifica tus credenciales y permisos de API.")
            return
            
        # Obtener cliente de Twitter después de la autenticación
        twitter_client = self.twitter_auth.get_client()
        if not twitter_client:
            self.logger.error("No hay cliente de Twitter disponible para sincronización aunque la autenticación fue exitosa")
            QMessageBox.warning(self.parent, "Error", "No se pudo obtener un cliente de Twitter válido. Por favor, inténtalo de nuevo.")
            return
                
        # Cargar artistas seleccionados
        json_path = Path(self.project_root, ".content", "cache", filename)
        
        if not os.path.exists(json_path):
            QMessageBox.warning(self.parent, "Error", f"Archivo {filename} no encontrado.")
            return
                
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                artists_data = json.load(f)
                    
            if not artists_data:
                QMessageBox.warning(self.parent, "Error", "No hay artistas en el archivo de selección.")
                return
        except Exception as e:
            QMessageBox.warning(self.parent, "Error", f"Error cargando artistas: {str(e)}")
            return
        
        # Proceder con la sincronización - usando el cliente de Twitter ya verificado
        self._sync_artists_list_with_twitter(artists_data, "base de datos", twitter_client)
  
  
    def _sync_artists_list_with_twitter(self, artists_data, source_name="", twitter_client=None):
        """
        Sincroniza una lista de artistas con Twitter
        
        Args:
            artists_data (list): Lista de diccionarios con datos de artistas
            source_name (str): Nombre de la fuente de datos (ej: "Spotify", "base de datos")
            twitter_client (TwitterClient, optional): Cliente de Twitter ya existente
        """
        # Usar cliente proporcionado o intentar obtener uno
        if not twitter_client and hasattr(self, 'twitter_auth'):
            try:
                twitter_client = self.twitter_auth.get_client()
            except Exception as e:
                self.logger.warning(f"Error obteniendo cliente de Twitter: {e}")
        
        if not twitter_client:
            self.logger.error("No hay cliente de Twitter disponible para sincronización")
            QMessageBox.warning(self.parent, "Error", "No se pudo conectar con Twitter. Por favor, inténtalo de nuevo.")
            return
        
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Preparando para sincronizar {len(artists_data)} artistas de {source_name} con Twitter...")
        QApplication.processEvents()
        
        # SOLUCIÓN: Usar una única función de progreso con un solo parámetro (valor)
        # que sea compatible con ProgressWorker
        def operation_function(progress_callback, status_callback=None):
            """
            Función para procesar artistas con Twitter
            
            Args:
                progress_callback: Función para reportar progreso (valor de 0 a 100)
                status_callback: Función para reportar estado textual
            """
            try:
                # Prepare counters for results
                results = {
                    "successful_follows": 0,
                    "already_following": 0,
                    "not_found": 0,
                    "failed": 0,
                    "processed": 0,
                    "details": []
                }
                
                # Informar estado inicial
                if status_callback:
                    status_callback(f"Preparando sincronización de {len(artists_data)} artistas...")
                    
                # Process each artist
                for i, artist_data in enumerate(artists_data):
                    # Update progress (0-100%)
                    progress_percent = int((i / len(artists_data)) * 100)
                    progress_callback(progress_percent)
                    
                    # Get artist name based on the data structure
                    if isinstance(artist_data, dict):
                        if "nombre" in artist_data:
                            artist_name = artist_data.get("nombre", "")
                        elif "name" in artist_data:
                            artist_name = artist_data.get("name", "")
                        else:
                            # Try to find any key that might contain the name
                            name_keys = ["artist_name", "artist", "nombre_artista"]
                            artist_name = ""
                            for key in name_keys:
                                if key in artist_data:
                                    artist_name = artist_data.get(key, "")
                                    break
                    elif isinstance(artist_data, str):
                        artist_name = artist_data
                    else:
                        # Skip this item if we can't determine the artist name
                        results["failed"] += 1
                        continue
                    
                    if not artist_name:
                        results["failed"] += 1
                        continue
                    
                    # Update status text
                    if status_callback:
                        status_callback(f"Procesando {artist_name} ({i+1}/{len(artists_data)})...")
                    
                    # Search for the artist on Twitter
                    search_result = twitter_client.search_users(artist_name, max_results=3)
                    
                    if not search_result or "data" not in search_result:
                        # Artist not found
                        results["not_found"] += 1
                        results["details"].append({
                            "artist": artist_name,
                            "status": "not_found",
                            "message": "No results found on Twitter"
                        })
                        continue
                    
                    users = search_result["data"]
                    
                    # Find best match
                    best_match = None
                    
                    for user in users:
                        user_name = user.get("name", "").lower()
                        username = user.get("username", "").lower()
                        
                        # Check for exact or close match
                        artist_lower = artist_name.lower()
                        if (artist_lower == user_name or
                            artist_lower in user_name or
                            artist_lower == username or
                            artist_lower in username):
                            best_match = user
                            break
                    
                    if not best_match:
                        # No good match found
                        results["not_found"] += 1
                        results["details"].append({
                            "artist": artist_name,
                            "status": "no_match",
                            "message": "No suitable match found on Twitter"
                        })
                        continue
                    
                    # Get user ID
                    user_id = best_match.get("id")
                    if not user_id:
                        results["failed"] += 1
                        continue
                    
                    # Try to follow the artist
                    try:
                        follow_result = twitter_client.follow_user(user_id)
                        
                        if follow_result and "data" in follow_result:
                            if follow_result["data"].get("following"):
                                # Successfully followed
                                results["successful_follows"] += 1
                                results["details"].append({
                                    "artist": artist_name,
                                    "status": "followed",
                                    "twitter_name": best_match.get("name", ""),
                                    "twitter_username": best_match.get("username", "")
                                })
                            else:
                                # Already following or other status
                                results["already_following"] += 1
                                results["details"].append({
                                    "artist": artist_name,
                                    "status": "already_following",
                                    "twitter_name": best_match.get("name", ""),
                                    "twitter_username": best_match.get("username", "")
                                })
                        else:
                            # Failed to follow
                            results["failed"] += 1
                            results["details"].append({
                                "artist": artist_name,
                                "status": "failed",
                                "message": "API request failed"
                            })
                    except Exception as e:
                        # Exception during follow request
                        results["failed"] += 1
                        results["details"].append({
                            "artist": artist_name,
                            "status": "error",
                            "message": str(e)
                        })
                    
                    # Update processed count
                    results["processed"] += 1
                    
                # Completion
                progress_callback(100)
                if status_callback:
                    status_callback("Sincronización completada")
                
                return {
                    "success": True,
                    "results": results
                }
                
            except Exception as e:
                self.logger.error(f"Error syncing artists with Twitter: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Ejecutar con el diálogo de progreso compatible con ProgressWorker
        try:
            # Importar módulo de progreso
            from modules.submodules.muspy.progress_utils import show_progress_operation
            
            # Llamar a show_progress_operation con la función compatible
            result = show_progress_operation(
                self.parent,
                operation_function,
                title=f"Syncing {source_name} Artists with Twitter",
                label_format="Artista {current}/{total} - {status}"
            )
        except Exception as e:
            self.logger.error(f"Error executing progress operation: {e}", exc_info=True)
            QMessageBox.warning(
                self.parent,
                "Error",
                f"Error during processing: {str(e)}"
            )
            return
        
        # Process results
        if result and result.get("success"):
            sync_results = result.get("results", {})
            
            # Display results
            self.ui_callback.clear()
            self.ui_callback.append(f"Twitter Synchronization Results for {source_name}")
            self.ui_callback.append("=" * 50)
            self.ui_callback.append(f"Artists processed: {sync_results.get('processed', 0)}/{len(artists_data)}")
            self.ui_callback.append(f"Successfully followed: {sync_results.get('successful_follows', 0)}")
            self.ui_callback.append(f"Already following: {sync_results.get('already_following', 0)}")
            self.ui_callback.append(f"Not found on Twitter: {sync_results.get('not_found', 0)}")
            self.ui_callback.append(f"Failed to follow: {sync_results.get('failed', 0)}")
            
            # Display details for successful follows
            if sync_results.get("successful_follows", 0) > 0:
                self.ui_callback.append("\nSuccessfully followed artists:")
                for detail in sync_results.get("details", []):
                    if detail.get("status") == "followed":
                        artist = detail.get("artist", "Unknown")
                        twitter_name = detail.get("twitter_name", "")
                        twitter_username = detail.get("twitter_username", "")
                        self.ui_callback.append(f"- {artist} → {twitter_name} (@{twitter_username})")
            
            # Show summary in a message box
            QMessageBox.information(
                self.parent, 
                "Twitter Sync Complete",
                f"Successfully followed {sync_results.get('successful_follows', 0)} artists on Twitter.\n" +
                f"Already following: {sync_results.get('already_following', 0)}\n" +
                f"Not found: {sync_results.get('not_found', 0)}\n" +
                f"Failed: {sync_results.get('failed', 0)}"
            )
            
            # Refresh the cache for followed users
            self.cache_manager.cache_manager("followed_users", None, force_refresh=True)
            
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation failed"
            self.ui_callback.append(f"Error: {error_msg}")
            QMessageBox.warning(self.parent, "Error", f"Could not sync artists with Twitter: {error_msg}")
  
    def sync_spotify_artists_with_twitter(self):
        """
        Sincroniza artistas seguidos en Spotify con Twitter
        """
        # Comprobar que Spotify está habilitado
        if not self.spotify_manager.ensure_spotify_auth():
            QMessageBox.warning(self.parent, "Error", "Spotify no está configurado o la autenticación falló")
            return
        
        # Mostrar diálogo de confirmación
        reply = QMessageBox.question(
            self.parent,
            "Sincronizar Spotify con Twitter",
            "Esto buscará tus artistas seguidos en Spotify y los seguirá en Twitter si se encuentran. ¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Mostrar página de texto durante la carga
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append("Obteniendo artistas seguidos en Spotify...")
        QApplication.processEvents()
        
        # Función para mostrar progreso
        def sync_spotify_with_twitter(update_progress):
            try:
                # Obtener cliente de Spotify
                spotify_client = self.spotify_manager.spotify_auth.get_client()
                if not spotify_client:
                    return {
                        "success": False,
                        "error": "No se pudo obtener cliente de Spotify. Verifica la autenticación."
                    }
                
                # Obtener cliente de Twitter
                twitter_client = self.twitter_auth.get_client()
                if not twitter_client:
                    return {
                        "success": False,
                        "error": "No se pudo obtener cliente de Twitter. Verifica la autenticación."
                    }
                
                # Obtener artistas seguidos de Spotify
                update_progress(5, 100, "Obteniendo artistas seguidos en Spotify...")
                
                all_artists = []
                offset = 0
                limit = 50  # Máximo de Spotify
                total = 1  # Se actualizará después de la primera petición
                
                # Paginar a través de todos los artistas seguidos
                while offset < total:
                    # Obtener página actual de artistas
                    results = spotify_client.current_user_followed_artists(limit=limit, after=None if offset == 0 else all_artists[-1]['id'])
                    
                    if 'artists' in results and 'items' in results['artists']:
                        # Obtener artistas de esta página
                        artists_page = results['artists']['items']
                        all_artists.extend(artists_page)
                        
                        # Actualizar conteo total
                        total = results['artists']['total']
                        
                        # Si obtuvimos menos de lo solicitado, terminamos
                        if len(artists_page) < limit:
                            break
                            
                        # Actualizar offset
                        offset += len(artists_page)
                    else:
                        # No hay más resultados o error
                        break
                
                # Mostrar progreso
                update_progress(20, 100, f"Se encontraron {len(all_artists)} artistas en Spotify. Buscando en Twitter...")
                
                # Contadores para resultados
                results = {
                    "found": 0,
                    "not_found": 0,
                    "followed": 0,
                    "already_following": 0,
                    "failed": 0,
                    "details": []
                }
                
                # Buscar cada artista en Twitter
                for i, artist in enumerate(all_artists):
                    artist_name = artist.get('name', '')
                    
                    # Actualizar progreso (escalar de 20-90%)
                    progress_value = 20 + int((i / len(all_artists)) * 70)
                    update_progress(progress_value, 100, f"Buscando {artist_name} en Twitter ({i+1}/{len(all_artists)})...")
                    
                    # Buscar artista en Twitter
                    search_result = twitter_client.search_users(artist_name, max_results=3)
                    
                    if not search_result or "data" not in search_result:
                        results["not_found"] += 1
                        results["details"].append({
                            "name": artist_name,
                            "status": "not_found"
                        })
                        continue
                    
                    users = search_result["data"]
                    
                    # Encontrar la mejor coincidencia
                    best_match = None
                    
                    for user in users:
                        user_name = user.get("name", "").lower()
                        username = user.get("username", "").lower()
                        
                        # Verificar coincidencia exacta o cercana
                        artist_lower = artist_name.lower()
                        if (artist_lower == user_name or
                            artist_lower in user_name or
                            artist_lower == username or
                            artist_lower in username):
                            best_match = user
                            break
                    
                    if not best_match:
                        results["not_found"] += 1
                        results["details"].append({
                            "name": artist_name,
                            "status": "no_match"
                        })
                        continue
                    
                    # Incrementar conteo de encontrados
                    results["found"] += 1
                    
                    # Obtener ID de usuario de Twitter
                    twitter_id = best_match.get("id")
                    if not twitter_id:
                        results["failed"] += 1
                        continue
                    
                    # Seguir al artista
                    try:
                        follow_result = twitter_client.follow_user(twitter_id)
                        
                        if follow_result and "data" in follow_result:
                            if follow_result["data"].get("following"):
                                results["followed"] += 1
                                results["details"].append({
                                    "name": artist_name,
                                    "status": "followed",
                                    "twitter_name": best_match.get("name", ""),
                                    "twitter_username": best_match.get("username", "")
                                })
                            else:
                                results["already_following"] += 1
                                results["details"].append({
                                    "name": artist_name,
                                    "status": "already_following",
                                    "twitter_name": best_match.get("name", ""),
                                    "twitter_username": best_match.get("username", "")
                                })
                        else:
                            results["failed"] += 1
                    except Exception as e:
                        results["failed"] += 1
                
                # Finalizar
                update_progress(100, 100, "Sincronización completada")
                
                return {
                    "success": True,
                    "results": results
                }
                
            except Exception as e:
                self.logger.error(f"Error sincronizando artistas de Spotify con Twitter: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Intentar diferentes opciones para acceder a la función show_progress_operation
        try:
            # Opción 1: Usar desde el módulo progress_utils directamente
            from modules.submodules.muspy.progress_utils import show_progress_operation
            result = show_progress_operation(
                self.parent,
                sync_spotify_with_twitter,
                title="Sincronizando Spotify con Twitter",
                label_format="{status}"
            )
        except Exception as e1:
            try:
                # Opción 2: Intentar usar el método en parent
                result = self.parent.show_progress_operation(
                    sync_spotify_with_twitter,
                    title="Sincronizando Spotify con Twitter",
                    label_format="{status}"
                )
            except Exception as e2:
                try:
                    # Opción 3: Si hay progress_utils disponible en self
                    if hasattr(self, 'progress_utils') and self.progress_utils is not None:
                        result = self.progress_utils.show_progress_operation(
                            sync_spotify_with_twitter,
                            title="Sincronizando Spotify con Twitter",
                            label_format="{status}"
                        )
                    else:
                        # Si todo falla, crear un diálogo de progreso manual básico
                        from PyQt6.QtWidgets import QProgressDialog
                        from PyQt6.QtCore import Qt
                        
                        progress_dialog = QProgressDialog(
                            "Sincronizando Spotify con Twitter",
                            "Cancelar",
                            0, 100,
                            self.parent
                        )
                        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                        progress_dialog.setMinimumDuration(0)
                        progress_dialog.setValue(0)
                        progress_dialog.setAutoClose(True)
                        progress_dialog.setAutoReset(False)
                        progress_dialog.show()
                        
                        # Función personalizada para actualizar el progreso
                        def update_progress_dialog(current, total, status="", indeterminate=False):
                            if progress_dialog.wasCanceled():
                                return False
                                
                            if indeterminate:
                                progress_dialog.setRange(0, 0)
                            else:
                                progress_dialog.setRange(0, 100)
                                progress_percent = int((current / total) * 100) if total > 0 else 0
                                progress_dialog.setValue(progress_percent)
                                
                            progress_dialog.setLabelText(status)
                            QApplication.processEvents()
                            return True
                            
                        # Ejecutar la función con nuestro callback personalizado
                        result = sync_spotify_with_twitter(update_progress_dialog)
                        
                        # Cerrar el diálogo
                        progress_dialog.close()
                except Exception as e3:
                    # Si todo falla, manejar el error
                    self.logger.error(f"Error accessing show_progress_operation: {e1}, {e2}, {e3}")
                    QMessageBox.warning(
                        self.parent,
                        "Error",
                        "No se pudo acceder a la función de progreso. Intenta actualizar la aplicación."
                    )
                    return
        
        # Procesar resultados
        if result and result.get("success"):
            sync_results = result.get("results", {})
            
            # Mostrar resultados
            self.ui_callback.clear()
            self.ui_callback.append("Resultados de sincronización Spotify con Twitter")
            self.ui_callback.append("=" * 50)
            self.ui_callback.append(f"Artistas encontrados en Twitter: {sync_results.get('found', 0)}/{sync_results.get('found', 0) + sync_results.get('not_found', 0)}")
            self.ui_callback.append(f"Artistas seguidos nuevos: {sync_results.get('followed', 0)}")
            self.ui_callback.append(f"Artistas ya seguidos: {sync_results.get('already_following', 0)}")
            self.ui_callback.append(f"Fallos al seguir: {sync_results.get('failed', 0)}")
            
            # Mostrar detalles de artistas seguidos
            if sync_results.get("followed", 0) > 0:
                self.ui_callback.append("\nArtistas seguidos:")
                for detail in sync_results.get("details", []):
                    if detail.get("status") == "followed":
                        artist_name = detail.get("name", "Unknown")
                        twitter_name = detail.get("twitter_name", "")
                        twitter_username = detail.get("twitter_username", "")
                        self.ui_callback.append(f"- {artist_name} → {twitter_name} (@{twitter_username})")
            
            # Mostrar resumen en un cuadro de mensaje
            QMessageBox.information(
                self.parent,
                "Sincronización Completada",
                f"Sincronización de Spotify con Twitter completada:\n\n" +
                f"Artistas encontrados: {sync_results.get('found', 0)}/{sync_results.get('found', 0) + sync_results.get('not_found', 0)}\n" +
                f"Artistas seguidos nuevos: {sync_results.get('followed', 0)}\n" +
                f"Artistas ya seguidos: {sync_results.get('already_following', 0)}\n" +
                f"Fallos al seguir: {sync_results.get('failed', 0)}"
            )
        else:
            error_msg = result.get("error", "Error desconocido") if result else "Operación cancelada"
            self.ui_callback.append(f"Error: {error_msg}")
            QMessageBox.warning(self.parent, "Error", f"No se pudieron sincronizar los artistas: {error_msg}")

    def _execute_lastfm_twitter_search(self, period, count, auto_follow=False, use_cache=True):
        """
        Ejecuta la búsqueda de artistas de LastFM en Twitter
        
        Args:
            period (str): Período para artistas top de LastFM
            count (int): Número de artistas a buscar
            auto_follow (bool): Si es True, sigue automáticamente los artistas encontrados
            use_cache (bool): Si es True, usa datos en caché cuando estén disponibles
        """
        if not self.lastfm_manager.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "LastFM no está configurado")
            return
        
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Obteniendo top {count} artistas de LastFM para el período {period}...")
        QApplication.processEvents()
        
        # Try to get top artists from cache
        cache_key = f"lastfm_top_artists_{period}_{count}"
        top_artists = None
        
        if use_cache:
            cached_data = self.cache_manager.cache_manager(cache_key)
            if cached_data:
                top_artists = cached_data
                self.ui_callback.append("Usando datos de LastFM en caché...")
        
        # If no cache, fetch fresh data
        if not top_artists:
            # Get top artists from LastFM
            top_artists = self.lastfm_manager.get_lastfm_top_artists_direct(count, period)
            
            # Cache results if successful
            if top_artists:
                self.cache_manager.cache_manager(cache_key, top_artists)
        
        if not top_artists:
            self.ui_callback.append("No se pudieron obtener artistas de LastFM.")
            return

        # Variables para recolectar resultados
        found_artists = []
        not_found_artists = []
        already_following = []
        newly_followed = []
        failed_follows = []
        
        # Crear la función worker para el diálogo de progreso
        def worker_function(self, update_progress):
            try:
                # Get Twitter client
                twitter_client = self.twitter_auth.get_client()
                if not twitter_client:
                    return {
                        "success": False,
                        "error": "No se pudo obtener cliente de Twitter. Verifica la autenticación."
                    }
                
                update_progress(10, 100, f"Buscando {len(top_artists)} artistas en Twitter...")
                
                # Procesar cada artista
                for i, artist in enumerate(top_artists):
                    artist_name = artist.get('name', '')
                    
                    # Update progress (scale from 10-90%)
                    progress_value = 10 + int((i / len(top_artists)) * 80)
                    update_progress(progress_value, 100, f"Buscando {artist_name} ({i+1}/{len(top_artists)})...")
                    
                    # Search for artist on Twitter
                    search_result = twitter_client.search_users(artist_name, max_results=3)
                    
                    if not search_result or "data" not in search_result:
                        not_found_artists.append(artist_name)
                        continue
                    
                    users = search_result["data"]
                    
                    # Find best match
                    best_match = None
                    
                    for user in users:
                        user_name = user.get("name", "").lower()
                        username = user.get("username", "").lower()
                        
                        # Check for exact or close match
                        artist_lower = artist_name.lower()
                        if (artist_lower == user_name or
                            artist_lower in user_name or
                            artist_lower == username or
                            artist_lower in username):
                            best_match = user
                            break
                    
                    if not best_match:
                        not_found_artists.append(artist_name)
                        continue
                    
                    # Get user data
                    twitter_name = best_match.get("name", "")
                    twitter_username = best_match.get("username", "")
                    twitter_id = best_match.get("id", "")
                    
                    if not twitter_id:
                        not_found_artists.append(artist_name)
                        continue
                    
                    # Add to found artists
                    found_artists.append({
                        'lastfm_name': artist_name,
                        'lastfm_playcount': artist.get('playcount', 0),
                        'twitter_id': twitter_id,
                        'twitter_name': twitter_name,
                        'twitter_username': twitter_username,
                        'profile_image_url': best_match.get('profile_image_url', ''),
                        'description': best_match.get('description', ''),
                        'public_metrics': best_match.get('public_metrics', {})
                    })
                    
                    # Auto-follow if requested
                    if auto_follow:
                        try:
                            follow_result = twitter_client.follow_user(twitter_id)
                            
                            if follow_result and "data" in follow_result:
                                if follow_result["data"].get("following"):
                                    newly_followed.append(artist_name)
                                else:
                                    already_following.append(artist_name)
                            else:
                                failed_follows.append(artist_name)
                        except Exception as e:
                            failed_follows.append(artist_name)
                
                update_progress(95, 100, "Procesando resultados...")
                
                # Store results in cache
                results_cache_key = f"lastfm_twitter_results_{period}_{count}"
                results_data = {
                    "found_artists": found_artists,
                    "not_found_artists": not_found_artists,
                    "already_following": already_following,
                    "newly_followed": newly_followed,
                    "failed_follows": failed_follows,
                    "timestamp": time.time()
                }
                
                self.cache_manager.cache_manager(results_cache_key, results_data)
                
                update_progress(100, 100, "Búsqueda completada")
                
                return {
                    "success": True,
                    "results": results_data
                }
                
            except Exception as e:
                self.logger.error(f"Error searching LastFM artists on Twitter: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": f"Error: {str(e)}"
                }
        
        # Ejecutar el worker con diálogo de progreso
        result = self.progress_utils.show_progress_operation(
            worker_function,
            title="Buscando Artistas de LastFM en Twitter",
            label_format="{status}"
        )
        
        # Procesar resultados
        if result and result.get("success"):
            results_data = result.get("results", {})
            
            # Display results summary
            self.ui_callback.clear()
            self.ui_callback.append(f"Resultados de búsqueda de artistas LastFM en Twitter")
            self.ui_callback.append("=" * 50)
            self.ui_callback.append(f"Artistas buscados: {len(top_artists)}")
            self.ui_callback.append(f"Artistas encontrados: {len(found_artists)}")
            self.ui_callback.append(f"Artistas no encontrados: {len(not_found_artists)}")
            
            if auto_follow:
                self.ui_callback.append("\nResultados de seguimiento automático:")
                self.ui_callback.append(f"Artistas seguidos nuevos: {len(newly_followed)}")
                self.ui_callback.append(f"Artistas ya seguidos: {len(already_following)}")
                self.ui_callback.append(f"Fallos al seguir: {len(failed_follows)}")
            
            # Display found artists
            if found_artists:
                self.ui_callback.append("\nArtistas encontrados:")
                for artist in found_artists:
                    self.ui_callback.append(f"- {artist['lastfm_name']} → {artist['twitter_name']} (@{artist['twitter_username']})")
                    
                    # Add follow link if not auto-followed
                    if not auto_follow:
                        self.ui_callback.append(f"  [<a href=\"follow:{artist['twitter_id']}:{artist['twitter_name']}:{artist['twitter_username']}\">Seguir en Twitter</a>] [<a href=\"view:{artist['twitter_username']}\">Ver perfil</a>]")
            
            # Display not found artists if any
            if not_found_artists:
                self.ui_callback.append("\nArtistas no encontrados:")
                for name in not_found_artists[:10]:  # Show only first 10
                    self.ui_callback.append(f"- {name}")
                
                if len(not_found_artists) > 10:
                    self.ui_callback.append(f"  ...y {len(not_found_artists) - 10} más")
            
            # Connect link handler if needed
            if not auto_follow and found_artists:
                # Desconectar primero para evitar conexiones múltiples
                try:
                    self.ui_callback.anchorClicked.disconnect(self._handle_artist_link)
                except:
                    pass
                # Conectar el manejador
                self.ui_callback.anchorClicked.connect(self._handle_artist_link)
            
            # Show results in a message box
            QMessageBox.information(
                self.parent,
                "Búsqueda Completada",
                f"Se encontraron {len(found_artists)} de {len(top_artists)} artistas en Twitter.\n" +
                (f"Se siguieron automáticamente {len(newly_followed)} artistas nuevos." if auto_follow else "")
            )
        else:
            error_msg = result.get("error", "Error desconocido") if result else "Operación cancelada"
            self.ui_callback.append(f"Error: {error_msg}")
            QMessageBox.warning(self.parent, "Error", error_msg)



    def show_lastfm_twitter_dialog(self):
        """
        Muestra un diálogo para seleccionar período y número de artistas de LastFM para buscar en Twitter
        """
        if not self.lastfm_manager.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "LastFM no está configurado")
            return
        
        # Crear diálogo
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Buscar Top Artistas de LastFM en Twitter")
        dialog.setMinimumWidth(350)
        
        # Crear layout
        layout = QVBoxLayout(dialog)
        
        # Período de tiempo
        period_layout = QHBoxLayout()
        period_label = QLabel("Período de tiempo:")
        period_combo = QComboBox()
        period_combo.addItem("7 días", "7day")
        period_combo.addItem("1 mes", "1month")
        period_combo.addItem("3 meses", "3month")
        period_combo.addItem("6 meses", "6month")
        period_combo.addItem("12 meses", "12month")
        period_combo.addItem("Todo el tiempo", "overall")
        period_combo.setCurrentIndex(5)  # Default a "Todo el tiempo"
        period_layout.addWidget(period_label)
        period_layout.addWidget(period_combo)
        layout.addLayout(period_layout)
        
        # Número de artistas
        count_layout = QHBoxLayout()
        count_label = QLabel("Número de artistas:")
        count_spin = QSpinBox()
        count_spin.setRange(5, 200)
        count_spin.setValue(50)
        count_spin.setSingleStep(5)
        count_layout.addWidget(count_label)
        count_layout.addWidget(count_spin)
        layout.addLayout(count_layout)
        
        # Opciones adicionales
        options_layout = QVBoxLayout()
        follow_checkbox = QCheckBox("Seguir artistas automáticamente si se encuentran")
        follow_checkbox.setChecked(False)
        options_layout.addWidget(follow_checkbox)
        
        cache_checkbox = QCheckBox("Usar datos en caché si están disponibles")
        cache_checkbox.setChecked(True)
        options_layout.addWidget(cache_checkbox)
        layout.addLayout(options_layout)
        
        # Botones
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Mostrar diálogo
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Obtener valores seleccionados
            period = period_combo.currentData()
            count = count_spin.value()
            auto_follow = follow_checkbox.isChecked()
            use_cache = cache_checkbox.isChecked()
            
            # Fix: Use the right method with proper arguments
            self.search_lastfm_artists_on_twitter(period, count, auto_follow, use_cache)

    def search_lastfm_artists_on_twitter(self, period, count, auto_follow=False, use_cache=True):
        """
        Busca artistas top de LastFM en Twitter
        
        Args:
            period (str): Período para artistas top de LastFM
            count (int): Número de artistas a buscar
            auto_follow (bool): Si es True, sigue automáticamente los artistas encontrados
            use_cache (bool): Si es True, usa datos en caché cuando estén disponibles
        """
        if not self.lastfm_manager.lastfm_enabled:
            QMessageBox.warning(self.parent, "Error", "LastFM no está configurado")
            return
        
        # Make sure we're showing the text page during loading
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Obteniendo top {count} artistas de LastFM para el período {period}...")
        QApplication.processEvents()
        
        # Try to get top artists from cache
        cache_key = f"lastfm_top_artists_{period}_{count}"
        top_artists = None
        
        if use_cache:
            cached_data = self.cache_manager.cache_manager(cache_key)
            if cached_data:
                top_artists = cached_data
                self.ui_callback.append("Usando datos de LastFM en caché...")
        
        # If no cache, fetch fresh data
        if not top_artists:
            # Get top artists from LastFM
            top_artists = self.lastfm_manager.get_lastfm_top_artists_direct(count, period)
            
            # Cache results if successful
            if top_artists:
                self.cache_manager.cache_manager(cache_key, top_artists)
        
        if not top_artists:
            self.ui_callback.append("No se pudieron obtener artistas de LastFM.")
            return
        
        # Store data for worker function to access
        self._temp_data = {
            "top_artists": top_artists,
            "auto_follow": auto_follow,
            "period": period,
            "count": count
        }
        
        # Define worker wrapper function
        def worker_function(update_progress):
            return self._search_lastfm_artists_on_twitter_worker(update_progress)
        
        # Execute with progress dialog
        progress_function = self._get_progress_function()
        result = progress_function(
            worker_function,
            title="Buscando Artistas de LastFM en Twitter",
            label_format="{status}"
        )
        
        # Clean up temp data
        del self._temp_data
        
        # Process results
        if result and result.get("success"):
            self._display_lastfm_twitter_results(result)
        else:
            error_msg = result.get("error", "Error desconocido") if result else "Operación cancelada"
            self.ui_callback.append(f"Error: {error_msg}")
            QMessageBox.warning(self.parent, "Error", error_msg)

    def _search_lastfm_artists_on_twitter_worker(self, update_progress):
        """
        Método trabajador para buscar artistas de LastFM en Twitter con progreso
        
        Args:
            update_progress: Función para actualizar el progreso
                
        Returns:
            dict: Resultados de la búsqueda
        """
        try:
            # Accedemos a los datos temporales almacenados
            temp_data = self._temp_data
            top_artists = temp_data["top_artists"]
            auto_follow = temp_data["auto_follow"]
            period = temp_data["period"]
            count = temp_data["count"]
            
            # Get Twitter client
            twitter_client = self.twitter_auth.get_client()
            if not twitter_client:
                return {
                    "success": False,
                    "error": "No se pudo obtener cliente de Twitter. Verifica la autenticación."
                }
            
            # Now search for each artist on Twitter
            found_artists = []
            not_found_artists = []
            already_following = []
            newly_followed = []
            failed_follows = []
            
            total_artists = len(top_artists)
            
            update_progress(10, 100, f"Buscando {total_artists} artistas en Twitter...")
            
            for i, artist in enumerate(top_artists):
                artist_name = artist.get('name', '')
                
                # Update progress (scale from 10-90%)
                progress_value = 10 + int((i / total_artists) * 80)
                update_progress(progress_value, 100, f"Buscando {artist_name} ({i+1}/{total_artists})...")
                
                # Search for artist on Twitter
                search_result = twitter_client.search_users(artist_name, max_results=3)
                
                if not search_result or "data" not in search_result:
                    not_found_artists.append(artist_name)
                    continue
                
                users = search_result["data"]
                
                # Find best match
                best_match = None
                
                for user in users:
                    user_name = user.get("name", "").lower()
                    username = user.get("username", "").lower()
                    
                    # Check for exact or close match
                    artist_lower = artist_name.lower()
                    if (artist_lower == user_name or
                        artist_lower in user_name or
                        artist_lower == username or
                        artist_lower in username):
                        best_match = user
                        break
                
                if not best_match:
                    not_found_artists.append(artist_name)
                    continue
                
                # Get user data
                twitter_name = best_match.get("name", "")
                twitter_username = best_match.get("username", "")
                twitter_id = best_match.get("id", "")
                
                if not twitter_id:
                    not_found_artists.append(artist_name)
                    continue
                
                # Add to found artists
                found_artists.append({
                    'lastfm_name': artist_name,
                    'lastfm_playcount': artist.get('playcount', 0),
                    'twitter_id': twitter_id,
                    'twitter_name': twitter_name,
                    'twitter_username': twitter_username,
                    'profile_image_url': best_match.get('profile_image_url', ''),
                    'description': best_match.get('description', ''),
                    'public_metrics': best_match.get('public_metrics', {})
                })
                
                # Auto-follow if requested
                if auto_follow:
                    try:
                        follow_result = twitter_client.follow_user(twitter_id)
                        
                        if follow_result and "data" in follow_result:
                            if follow_result["data"].get("following"):
                                newly_followed.append(artist_name)
                            else:
                                already_following.append(artist_name)
                        else:
                            failed_follows.append(artist_name)
                    except Exception as e:
                        failed_follows.append(artist_name)
            
            update_progress(95, 100, "Procesando resultados...")
            
            # Store results in cache
            results_cache_key = f"lastfm_twitter_results_{period}_{count}"
            results_data = {
                "found_artists": found_artists,
                "not_found_artists": not_found_artists,
                "already_following": already_following,
                "newly_followed": newly_followed,
                "failed_follows": failed_follows,
                "timestamp": time.time()
            }
            
            self.cache_manager.cache_manager(results_cache_key, results_data)
            
            update_progress(100, 100, "Búsqueda completada")
            
            return {
                "success": True,
                "results": results_data
            }
            
        except Exception as e:
            self.logger.error(f"Error buscando artistas de LastFM en Twitter: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }

    # Método para mostrar resultados (separado para mayor claridad)
    def _display_lastfm_twitter_results(self, result):
        """
        Muestra los resultados de la búsqueda de artistas LastFM en Twitter
        
        Args:
            result (dict): Resultado de la búsqueda
        """
        results_data = result.get("results", {})
        found_artists = results_data.get("found_artists", [])
        not_found_artists = results_data.get("not_found_artists", [])
        already_following = results_data.get("already_following", [])
        newly_followed = results_data.get("newly_followed", [])
        failed_follows = results_data.get("failed_follows", [])
        
        # Accedemos a los datos temporales
        temp_data = getattr(self, '_temp_data', {})
        top_artists = temp_data.get("top_artists", [])
        auto_follow = temp_data.get("auto_follow", False)
        
        # Display results summary
        self.ui_callback.clear()
        self.ui_callback.append(f"Resultados de búsqueda de artistas LastFM en Twitter")
        self.ui_callback.append("=" * 50)
        self.ui_callback.append(f"Artistas buscados: {len(top_artists)}")
        self.ui_callback.append(f"Artistas encontrados: {len(found_artists)}")
        self.ui_callback.append(f"Artistas no encontrados: {len(not_found_artists)}")
        
        if auto_follow:
            self.ui_callback.append("\nResultados de seguimiento automático:")
            self.ui_callback.append(f"Artistas seguidos nuevos: {len(newly_followed)}")
            self.ui_callback.append(f"Artistas ya seguidos: {len(already_following)}")
            self.ui_callback.append(f"Fallos al seguir: {len(failed_follows)}")
        
        # Display found artists
        if found_artists:
            self.ui_callback.append("\nArtistas encontrados:")
            for artist in found_artists:
                self.ui_callback.append(f"- {artist['lastfm_name']} → {artist['twitter_name']} (@{artist['twitter_username']})")
                
                # Add follow link if not auto-followed
                if not auto_follow:
                    self.ui_callback.append(f"  [<a href=\"follow:{artist['twitter_id']}:{artist['twitter_name']}:{artist['twitter_username']}\">Seguir en Twitter</a>] [<a href=\"view:{artist['twitter_username']}\">Ver perfil</a>]")
        
        # Display not found artists if any
        if not_found_artists:
            self.ui_callback.append("\nArtistas no encontrados:")
            for name in not_found_artists[:10]:  # Show only first 10
                self.ui_callback.append(f"- {name}")
            
            if len(not_found_artists) > 10:
                self.ui_callback.append(f"  ...y {len(not_found_artists) - 10} más")
        
        # Connect link handler if needed
        if not auto_follow and found_artists:
            # Desconectar primero para evitar conexiones múltiples
            try:
                self.ui_callback.anchorClicked.disconnect(self._handle_artist_link)
            except:
                pass
            # Conectar el manejador
            self.ui_callback.anchorClicked.connect(self._handle_artist_link)
        
        # Show results in a message box
        QMessageBox.information(
            self.parent,
            "Búsqueda Completada",
            f"Se encontraron {len(found_artists)} de {len(top_artists)} artistas en Twitter.\n" +
            (f"Se siguieron automáticamente {len(newly_followed)} artistas nuevos." if auto_follow else "")
        )

    def sync_mb_artists_with_twitter(self):
        """
        Sincroniza artistas de colección de MusicBrainz con Twitter
        """
        # Verificar autenticación de Twitter y MusicBrainz
        if not self.ensure_twitter_auth():
            QMessageBox.warning(self.parent, "Error", "Twitter authentication required")
            return
            
        if not self.musicbrainz_manager.musicbrainz_auth.is_authenticated():
            QMessageBox.warning(self.parent, "Error", "MusicBrainz authentication required")
            return
        
        # Obtener las colecciones del usuario
        if not hasattr(self, '_mb_collections') or not self._mb_collections:
            self._mb_collections = self.musicbrainz_manager.fetch_all_musicbrainz_collections()
        
        if not self._mb_collections:
            QMessageBox.warning(self.parent, "Error", "No MusicBrainz collections found")
            return
        
        # Crear diálogo para seleccionar colección
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Select MusicBrainz Collection")
        dialog.setMinimumWidth(400)
        
        # Crear layout
        layout = QVBoxLayout(dialog)
        
        # Etiqueta
        layout.addWidget(QLabel("Select a collection to sync with Twitter:"))
        
        # ComboBox para colecciones
        combo = QComboBox()
        for collection in self._mb_collections:
            collection_name = collection.get('name', 'Unnamed Collection')
            collection_count = collection.get('entity_count', 0)
            combo.addItem(f"{collection_name} ({collection_count} items)", collection)
        
        layout.addWidget(combo)
        
        # Botones
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Mostrar diálogo
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        # Obtener colección seleccionada
        selected_index = combo.currentIndex()
        if selected_index < 0:
            return
            
        selected_collection = combo.itemData(selected_index)
        collection_id = selected_collection.get('id')
        collection_name = selected_collection.get('name', 'Unnamed Collection')
        
        if not collection_id:
            QMessageBox.warning(self.parent, "Error", "No collection ID found")
            return
        
        # Obtener artistas de la colección
        self.display_manager.show_text_page()
        self.ui_callback.clear()
        self.ui_callback.append(f"Cargando artistas de la colección '{collection_name}'...")
        QApplication.processEvents()
        
        def fetch_collection_artists(update_progress):
            try:
                update_progress(0, 100, "Loading collection items...", indeterminate=True)
                
                # Obtener artistas de la colección
                collection_items = self.musicbrainz_manager.musicbrainz_auth.get_collection_items(collection_id)
                
                if not collection_items:
                    return {
                        "success": False,
                        "error": "No items found in collection"
                    }
                
                # Extraer artistas únicos de los lanzamientos
                artists_data = []
                artist_ids = set()  # Para evitar duplicados
                
                update_progress(50, 100, "Processing artists from collection...", indeterminate=True)
                
                for item in collection_items:
                    artist_credit = item.get('artist-credit', [])
                    
                    for artist in artist_credit:
                        if isinstance(artist, dict) and 'artist' in artist:
                            artist_info = artist['artist']
                            artist_id = artist_info.get('id')
                            
                            if artist_id and artist_id not in artist_ids:
                                artist_ids.add(artist_id)
                                artists_data.append({
                                    "nombre": artist_info.get('name', 'Unknown'),
                                    "mbid": artist_id
                                })
                
                update_progress(100, 100, "Completed")
                
                return {
                    "success": True,
                    "artists": artists_data
                }
            except Exception as e:
                self.logger.error(f"Error fetching collection artists: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Ejecutar con diálogo de progreso
        result = self.progress_utils.show_progress_operation(
            fetch_collection_artists,
            title="Loading MusicBrainz Collection",
            label_format="{status}"
        )
        
        # Procesar resultados
        if result and result.get("success"):
            artists_data = result.get("artists", [])
            
            if not artists_data:
                QMessageBox.warning(self.parent, "No Artists", "No artists found in the selected collection")
                return
            
            # Confirmar sincronización
            reply = QMessageBox.question(
                self.parent,
                "Confirm Sync",
                f"Found {len(artists_data)} unique artists in '{collection_name}'.\nDo you want to follow them on Twitter?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Proceder con la sincronización
                self._sync_artists_list_with_twitter(artists_data, f"MusicBrainz collection '{collection_name}'")
        else:
            error_msg = result.get("error", "Unknown error") if result else "Operation canceled"
            QMessageBox.warning(self.parent, "Error", f"Failed to load collection: {error_msg}")


    def _handle_artist_link(self, url):
        """
        Maneja clics en enlaces de artistas
        
        Args:
            url (QUrl): URL del enlace
        """
        url_str = url.toString()
        
        if url_str.startswith("follow:"):
            # Follow artist action
            _, twitter_id, twitter_name, twitter_username = url_str.split(":", 3)
            self.follow_twitter_user(twitter_id, twitter_name, twitter_username)
        elif url_str.startswith("view:"):
            # View profile action
            _, username = url_str.split(":", 1)
            self.utils.open_url(f"https://twitter.com/{username}")


    def _get_progress_function(self):
        """
        Obtiene la función de progreso disponible, con fallbacks
        
        Returns:
            function: Función para mostrar progreso
        """
        # Opción 1: Usar progress_utils si está disponible
        if hasattr(self, 'progress_utils') and self.progress_utils is not None:
            return self.progress_utils.show_progress_operation
        
        # Opción 2: Usar el método del parent si está disponible
        if hasattr(self.parent, 'show_progress_operation'):
            return self.parent.show_progress_operation
        
        # Opción 3: Importar directamente desde el módulo
        try:
            from modules.submodules.muspy.progress_utils import show_progress_operation
            return lambda *args, **kwargs: show_progress_operation(self.parent, *args, **kwargs)
        except ImportError:
            pass
        
        # Opción 4: Fallback manual
        return self._manual_progress_dialog

    def _manual_progress_dialog(self, operation_function, **kwargs):
        """
        Fallback manual para diálogo de progreso
        
        Args:
            operation_function: Función a ejecutar
            **kwargs: Argumentos adicionales
            
        Returns:
            Resultado de la operación
        """
        from PyQt6.QtWidgets import QProgressDialog
        from PyQt6.QtCore import Qt
        
        title = kwargs.get('title', 'Processing...')
        
        progress_dialog = QProgressDialog(
            title,
            "Cancel",
            0, 100,
            self.parent
        )
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        progress_dialog.setAutoClose(True)
        progress_dialog.setAutoReset(False)
        progress_dialog.show()
        
        # Función para actualizar progreso
        def update_progress(current, total=100, status="", indeterminate=False):
            if progress_dialog.wasCanceled():
                return False
                
            if indeterminate:
                progress_dialog.setRange(0, 0)
            else:
                progress_dialog.setRange(0, 100)
                progress_percent = int((current / total) * 100) if total > 0 else current
                progress_dialog.setValue(progress_percent)
                
            if status:
                progress_dialog.setLabelText(status)
            QApplication.processEvents()
            return True
            
        try:
            # Ejecutar la operación
            result = operation_function(update_progress)
            progress_dialog.close()
            return result
        except Exception as e:
            progress_dialog.close()
            raise e