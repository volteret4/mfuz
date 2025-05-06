#!/usr/bin/python3
# tools/twitter_login.py

import os
import json
import time
import logging
import requests
import webbrowser
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QLineEdit
from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path

"""
Twitter/X Authentication Manager

Este módulo maneja la autenticación con Twitter (ahora X) utilizando OAuth 2.0.
Permite obtener tokens de acceso y gestionar la sesión de Twitter.
"""

class TwitterAuthManager(QObject):
    """Gestor de autenticación para Twitter/X API"""
    
    auth_completed = pyqtSignal(bool)
    
    def __init__(self, 
                client_id=None, 
                client_secret=None, 
                redirect_uri=None,
                parent_widget=None,
                project_root=None,
                scope="tweet.read users.read follows.read follows.write"):
        """
        Inicializa el gestor de autenticación de Twitter
        
        Args:
            client_id (str): ID de cliente de la aplicación Twitter
            client_secret (str): Secret de cliente de la aplicación Twitter
            redirect_uri (str): URI de redirección
            parent_widget: Widget padre para diálogos
            project_root (str): Ruta raíz del proyecto
            scope (str): Permisos solicitados
        """
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri or "http://localhost:8080/callback"
        self.parent_widget = parent_widget
        self.project_root = project_root
        self.scope = scope
        
        self.access_token = None
        self.refresh_token = None
        self.expiry_time = None
        
        self.logger = logging.getLogger(__name__)
        
        # Cargar tokens desde caché si existen
        self._load_cached_tokens()
    
    def _get_cache_file_path(self):
        """Obtiene la ruta al archivo de caché de tokens"""
        if not self.project_root:
            return None
            
        cache_dir = Path(self.project_root, ".content", "cache", "twitter")
        os.makedirs(cache_dir, exist_ok=True)
        return Path(cache_dir, ".twitter_tokens.json")
    
    def _load_cached_tokens(self):
        """Carga tokens desde caché si están disponibles"""
        cache_file = self._get_cache_file_path()
        if not cache_file or not os.path.exists(cache_file):
            return False
            
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                self.expiry_time = data.get('expiry_time')
                
                # Verificar si el token ha expirado
                if self.expiry_time and time.time() > self.expiry_time:
                    # Si hay refresh token, intentar renovar
                    if self.refresh_token:
                        self.refresh_access_token()
                    else:
                        return False
                        
                return bool(self.access_token)
        except Exception as e:
            self.logger.error(f"Error loading cached Twitter tokens: {e}")
            return False
    
    def _save_tokens_to_cache(self):
        """Guarda los tokens en caché"""
        cache_file = self._get_cache_file_path()
        if not cache_file:
            return False
            
        try:
            with open(cache_file, 'w') as f:
                data = {
                    'access_token': self.access_token,
                    'refresh_token': self.refresh_token,
                    'expiry_time': self.expiry_time
                }
                json.dump(data, f)
            return True
        except Exception as e:
            self.logger.error(f"Error saving Twitter tokens to cache: {e}")
            return False
    
    def is_authenticated(self):
        """
        Verifica si la autenticación es válida
        
        Returns:
            bool: True si el usuario está autenticado y el token es válido
        """
        if not self.access_token:
            return False
            
        # Verificar si el token ha expirado
        if self.expiry_time and time.time() > self.expiry_time:
            # Si hay refresh token, intentar renovar
            if self.refresh_token:
                return self.refresh_access_token()
            else:
                return False
                
        # Verificar si el token es válido con una llamada de prueba
        try:
            response = requests.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            # Analizar respuesta específicamente para el error de cliente no inscrito
            if response.status_code == 403:
                try:
                    error_data = response.json()
                    if "reason" in error_data and error_data["reason"] == "client-not-enrolled":
                        self.logger.error("Cliente no inscrito en nivel adecuado de API: " + error_data.get("detail", ""))
                        # Limpiar tokens ya que no son útiles con este nivel de API
                        self.clear_session()
                        return False
                except:
                    pass
                    
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Error verificando autenticación: {e}")
            return False
    
# Modificaciones al método authenticate() en TwitterAuthManager

    def authenticate(self, silent=False):
        """
        Inicia el proceso de autenticación con Twitter
        
        Args:
            silent (bool): Si es True, no mostrará diálogos interactivos
                
        Returns:
            bool: True si la autenticación fue exitosa
        """
        # Verificar primero si tenemos un error de cliente no inscrito registrado previamente
        client_not_enrolled = getattr(self, '_client_not_enrolled', False)
        
        # Si ya tenemos un token válido, no es necesario autenticar de nuevo
        if not client_not_enrolled and self.is_authenticated():
            self.logger.info("Ya autenticado con Twitter, usando token existente")
            return True
                
        # Verificar que tenemos las credenciales necesarias
        if not self.client_id or not self.client_secret:
            self.logger.warning(f"Faltan credenciales para Twitter: client_id={bool(self.client_id)}, client_secret={bool(self.client_secret)}")
            
            if not silent and self.parent_widget:
                QMessageBox.warning(
                    self.parent_widget,
                    "Twitter Authentication",
                    "Missing Twitter API credentials. Please check your configuration."
                )
            return False
        
        # Si tenemos el error de cliente no inscrito, mostrar un mensaje específico
        if client_not_enrolled and not silent and self.parent_widget:
            result = QMessageBox.warning(
                self.parent_widget,
                "Twitter API Access Level",
                "Your Twitter API application does not have the required access level.\n\n"
                "To use this functionality, you need to:\n"
                "1. Go to developer.twitter.com\n"
                "2. Create a Project and add your app to it\n"
                "3. Apply for Elevated access or higher\n\n"
                "Would you like to try authentication anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                return False
                
        # En modo silencioso, solo intentamos renovar el token
        if silent:
            if self.refresh_token:
                self.logger.info("Intentando renovar token de Twitter en modo silencioso")
                if self.refresh_access_token():
                    self.logger.info("Token de Twitter renovado correctamente")
                    return True
                else:
                    self.logger.info("No se pudo renovar el token de Twitter")
            else:
                self.logger.info("No hay refresh_token disponible para autenticación silenciosa")
            return False
        
        # Si llegamos aquí, necesitamos autenticación manual completa
        # Generar un estado aleatorio para seguridad
        import uuid
        state = str(uuid.uuid4())
        
        # Construir URL de autorización
        auth_url = "https://twitter.com/i/oauth2/authorize"
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state,
            "code_challenge": "challenge",
            "code_challenge_method": "plain"
        }
        
        # Convertir los parámetros a cadena de consulta
        from urllib.parse import urlencode
        auth_url = f"{auth_url}?{urlencode(params)}"
        
        # Mostrar diálogo con instrucciones detalladas
        if self.parent_widget:
            QMessageBox.information(
                self.parent_widget,
                "Twitter Authentication",
                "You will now be redirected to Twitter to authenticate.\n\n"
                "1. Log in to Twitter in the browser\n"
                "2. Authorize the application\n"
                "3. You'll be redirected to a page (possibly showing an error)\n"
                "4. Copy the FULL URL from your browser's address bar\n"
                "5. Paste it in the dialog that will appear\n\n"
                "Click OK to continue."
            )
        
        # Abrir navegador con la URL de autorización
        self.logger.info(f"Opening Twitter authorization URL: {auth_url}")
        webbrowser.open(auth_url)
        
        # Solicitar al usuario que ingrese la URL de redirección completa
        callback_url, ok = QInputDialog.getText(
            self.parent_widget,
            "Twitter Authentication",
            "Please paste the FULL URL from your browser after authorization:\n\n"
            "(This should be the complete URL in your browser's address bar)",
            QLineEdit.EchoMode.Normal
        )
        
        if not ok or not callback_url:
            self.logger.warning("Autenticación Twitter cancelada por el usuario")
            return False
            
        # Extraer el código de autorización de la URL de redirección
        from urllib.parse import urlparse, parse_qs
        
        # Manejar URLs incompletas o con formato diferente
        try:
            self.logger.info(f"Procesando URL de callback: {callback_url}")
            
            # Intentar primero con URL completa
            parsed_url = urlparse(callback_url)
            query_params = parse_qs(parsed_url.query)
            
            # Si no hay código en la URL pero hay un texto que parece un código, usarlo directamente
            if 'code' not in query_params:
                # Buscar posible código en el texto introducido
                if callback_url.strip().startswith("code="):
                    # El usuario pegó solo el código
                    code = callback_url.strip().replace("code=", "").split("&")[0]
                    self.logger.info(f"Código extraído de 'code=' prefix: {code[:10]}...")
                elif "code=" in callback_url:
                    # Hay un código en alguna parte del texto
                    parts = callback_url.split("code=")
                    if parts and len(parts) > 1:
                        code = parts[1].split("&")[0].strip()
                        self.logger.info(f"Código extraído de texto que contiene 'code=': {code[:10]}...")
                else:
                    # Probar si el texto es directamente el código
                    # Verificar si es solo texto sin espacios y de longitud razonable
                    cleaned_url = callback_url.strip()
                    if 10 <= len(cleaned_url) <= 500 and ' ' not in cleaned_url:
                        code = cleaned_url
                        self.logger.info(f"Usando texto completo como código: {code[:10]}...")
                    else:
                        if self.parent_widget:
                            QMessageBox.warning(
                                self.parent_widget,
                                "Twitter Authentication",
                                "Invalid callback URL. Authorization code not found.\n\n"
                                "Please make sure you copied the complete URL from your browser."
                            )
                        self.logger.error("Código de autorización no encontrado en URL de callback")
                        return False
            else:
                code = query_params['code'][0]
                self.logger.info(f"Código extraído de parámetros de URL: {code[:10]}...")
                
            # Verificar el estado para prevenir ataques CSRF si está presente
            if 'state' in query_params and query_params['state'][0] != state:
                if self.parent_widget:
                    QMessageBox.warning(
                        self.parent_widget,
                        "Twitter Authentication",
                        "Invalid state parameter. Possible security issue."
                    )
                self.logger.error("Parámetro state inválido en callback, posible ataque CSRF")
                return False
                
            # Intercambiar el código por tokens
            self.logger.info("Iniciando intercambio de código por tokens...")
            return self._exchange_code_for_tokens(code)
            
        except Exception as e:
            self.logger.error(f"Error procesando URL de callback: {e}", exc_info=True)
            
            if self.parent_widget:
                QMessageBox.warning(
                    self.parent_widget,
                    "Twitter Authentication",
                    f"Error processing callback URL: {str(e)}\n\n"
                    "Please make sure you copied the complete URL correctly."
                )
                
            return False
    
    def _exchange_code_for_tokens(self, code):
        """
        Intercambia el código de autorización por tokens de acceso
        
        Args:
            code (str): Código de autorización
            
        Returns:
            bool: True si el intercambio fue exitoso
        """
        try:
            token_url = "https://api.twitter.com/2/oauth2/token"
            
            # Datos para la petición
            data = {
                "code": code,
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "code_verifier": "challenge"
            }
            
            # MODIFICACIÓN: Usar autenticación básica con client_id y client_secret
            # según la documentación oficial de Twitter OAuth 2.0
            from requests.auth import HTTPBasicAuth
            auth = HTTPBasicAuth(self.client_id, self.client_secret) if self.client_secret else None
            
            # Realizar la petición con auth y headers adecuados
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Convertir los datos a formato x-www-form-urlencoded
            import urllib.parse
            body = urllib.parse.urlencode(data)
            
            # MODIFICACIÓN: Log para depuración
            self.logger.info(f"Enviando solicitud de token a {token_url}")
            self.logger.info(f"Headers: {headers}")
            self.logger.info(f"Datos: {data}")
            self.logger.info(f"Auth: {'Usando BasicAuth' if auth else 'Sin autenticación'}")
            
            # Realizar la petición con auth
            response = requests.post(token_url, data=body, headers=headers, auth=auth)
            
            self.logger.info(f"Token exchange status: {response.status_code}")
            
            if response.status_code == 200:
                # Procesar la respuesta
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                
                # Verificar que tenemos al menos el access_token
                if not self.access_token:
                    self.logger.error(f"No access_token en la respuesta: {token_data}")
                    if self.parent_widget:
                        QMessageBox.warning(
                            self.parent_widget,
                            "Twitter Authentication",
                            "No access token received from Twitter"
                        )
                    return False
                
                # Calcular tiempo de expiración
                expires_in = token_data.get("expires_in", 7200)  # Default: 2 horas
                self.expiry_time = time.time() + expires_in
                
                # Debug: Mostrar parte del token
                token_preview = self.access_token[:10] + "..." if self.access_token else "None"
                refresh_preview = self.refresh_token[:10] + "..." if self.refresh_token else "None"
                self.logger.info(f"Token obtenido: {token_preview}, Refresh: {refresh_preview}, Expira en: {expires_in}s")
                
                # Guardar tokens en caché inmediatamente
                cache_result = self._save_tokens_to_cache()
                self.logger.info(f"Tokens guardados en caché: {cache_result}")
                
                # Limpiar la marca de cliente no inscrito si existía
                if hasattr(self, '_client_not_enrolled'):
                    delattr(self, '_client_not_enrolled')
                
                # Emitir señal de autenticación completada
                self.auth_completed.emit(True)
                
                return True
            elif response.status_code == 401:
                # Manejo específico para error 401 unauthorized_client
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    pass
                    
                error_type = error_data.get("error", "")
                error_desc = error_data.get("error_description", "")
                
                self.logger.error(f"Error 401 en intercambio de token: {error_type} - {error_desc}")
                
                # Mensaje específico para el usuario
                error_msg = "Error de autenticación con Twitter"
                if error_type == "unauthorized_client":
                    error_msg = (
                        "Error de autenticación: Cliente no autorizado. \n\n"
                        "Por favor, verifica que:\n"
                        "1. Tu Client ID y Client Secret son correctos\n"
                        "2. Tu app tiene permisos para usar OAuth 2.0 Code Flow\n"
                        "3. Has configurado correctamente el callback URL\n\n"
                        f"Error desde Twitter: {error_desc}"
                    )
                    
                if self.parent_widget:
                    QMessageBox.warning(
                        self.parent_widget,
                        "Twitter Authentication",
                        error_msg
                    )
                
                # Emitir señal de autenticación fallida
                self.auth_completed.emit(False)
                
                return False
            elif response.status_code == 403:
                # Analizar si es un error de cliente no inscrito
                try:
                    error_data = response.json()
                    if "reason" in error_data and error_data["reason"] == "client-not-enrolled":
                        error_msg = error_data.get("detail", "Error de acceso a la API")
                        self.logger.error(f"Error de cliente no inscrito: {error_msg}")
                        
                        # Marcar el cliente como no inscrito para futuras referencias
                        self._client_not_enrolled = True
                        
                        if self.parent_widget:
                            QMessageBox.warning(
                                self.parent_widget,
                                "Twitter API Access Level",
                                f"Your Twitter API application does not have the required access level.\n\n"
                                f"Error details: {error_msg}\n\n"
                                f"To use this functionality, you need to:\n"
                                f"1. Go to developer.twitter.com\n"
                                f"2. Create a Project and add your app to it\n"
                                f"3. Apply for Elevated access or higher"
                            )
                        
                        # Limpiar cualquier token almacenado
                        self.clear_session()
                        
                        # Emitir señal de autenticación fallida
                        self.auth_completed.emit(False)
                        
                        return False
                except Exception as e:
                    self.logger.error(f"Error analizando respuesta de error 403: {e}")
                    
                # Si no se identificó como error de cliente no inscrito, mostrar mensaje genérico
                error_msg = f"Token exchange failed: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                
                if self.parent_widget:
                    QMessageBox.warning(
                        self.parent_widget,
                        "Twitter Authentication",
                        f"Authentication failed: {error_msg}"
                    )
                
                # Emitir señal de autenticación fallida
                self.auth_completed.emit(False)
                
                return False
            else:
                # Registrar la respuesta completa para diagnóstico
                self.logger.error(f"Token exchange failed with code {response.status_code}")
                self.logger.error(f"Response text: {response.text}")
                
                # Intentar analizar el contenido JSON si existe
                try:
                    error_data = response.json()
                    self.logger.error(f"Error details: {error_data}")
                except:
                    pass
                    
                error_msg = f"Token exchange failed: {response.status_code} - {response.text}"
                
                if self.parent_widget:
                    QMessageBox.warning(
                        self.parent_widget,
                        "Twitter Authentication",
                        f"Authentication failed: {error_msg}"
                    )
                
                # Emitir señal de autenticación fallida
                self.auth_completed.emit(False)
                
                return False
        
        except Exception as e:
            self.logger.error(f"Error exchanging code for tokens: {e}", exc_info=True)
            
            if self.parent_widget:
                QMessageBox.warning(
                    self.parent_widget,
                    "Twitter Authentication",
                    f"Authentication error: {str(e)}"
                )
            
            # Emitir señal de autenticación fallida
            self.auth_completed.emit(False)
            
            return False

    def refresh_access_token(self):
        """
        Renueva el token de acceso usando el refresh token
        
        Returns:
            bool: True si la renovación fue exitosa
        """
        if not self.refresh_token:
            self.logger.warning("No hay refresh token disponible para renovar")
            return False
        
        if not self.client_id or not self.client_secret:
            self.logger.warning("Faltan credenciales de cliente para renovar token")
            return False
            
        try:
            token_url = "https://api.twitter.com/2/oauth2/token"
            
            # Datos para la petición
            data = {
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
                "client_id": self.client_id
            }
            
            # MODIFICACIÓN: Usar autenticación básica para la solicitud de token
            from requests.auth import HTTPBasicAuth
            auth = HTTPBasicAuth(self.client_id, self.client_secret)
            
            # Headers correctos para la solicitud
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Convertir a formato form-urlencoded
            import urllib.parse
            body = urllib.parse.urlencode(data)
            
            # Log detallado
            self.logger.info(f"Renovando token. URL: {token_url}")
            self.logger.info(f"Datos: {data}")
            self.logger.info(f"Headers: {headers}")
            
            # Realizar la petición
            response = requests.post(token_url, data=body, headers=headers, auth=auth)
            
            self.logger.info(f"Respuesta de renovación: Status: {response.status_code}")
            
            if response.status_code == 200:
                # Procesar la respuesta
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                
                # Actualizar refresh token si se proporciona uno nuevo
                if "refresh_token" in token_data:
                    self.refresh_token = token_data.get("refresh_token")
                
                # Calcular tiempo de expiración
                expires_in = token_data.get("expires_in", 7200)  # Default: 2 horas
                self.expiry_time = time.time() + expires_in
                
                # Log de éxito
                token_preview = self.access_token[:10] + "..." if self.access_token else "None"
                refresh_preview = self.refresh_token[:10] + "..." if self.refresh_token else "None"
                self.logger.info(f"Token renovado: {token_preview}, Refresh: {refresh_preview}, Expira en: {expires_in}s")
                
                # Guardar tokens en caché
                self._save_tokens_to_cache()
                
                return True
            else:
                # Log detallado del error
                self.logger.error(f"Error renovando token: {response.status_code}")
                self.logger.error(f"Respuesta: {response.text}")
                
                try:
                    error_data = response.json()
                    error_type = error_data.get("error", "unknown")
                    error_desc = error_data.get("error_description", "No description")
                    self.logger.error(f"Error tipo: {error_type}, descripción: {error_desc}")
                    
                    # Si el refresh token no es válido, limpiar la sesión
                    if error_type in ["invalid_grant", "invalid_request"]:
                        self.logger.warning("Refresh token inválido, limpiando sesión")
                        self.clear_session()
                except:
                    pass
                    
                return False
        
        except Exception as e:
            self.logger.error(f"Error refreshing access token: {e}", exc_info=True)
            return False
    
    def get_user_info(self):
        """
        Obtiene información del usuario autenticado
        
        Returns:
            dict: Información del usuario o None si hay error
        """
        if not self.is_authenticated():
            if not self.authenticate(silent=True):
                return None
        
        try:
            # Hacer petición a la API
            url = "https://api.twitter.com/2/users/me"
            params = {
                "user.fields": "id,name,username,profile_image_url,description,public_metrics"
            }
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data")
            else:
                self.logger.error(f"Error getting user info: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error getting user info: {e}")
            return None
    
    def clear_session(self):
        """Limpia los datos de sesión y la caché"""
        self.access_token = None
        self.refresh_token = None
        self.expiry_time = None
        
        # Eliminar archivo de caché
        cache_file = self._get_cache_file_path()
        if cache_file and os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except Exception as e:
                self.logger.error(f"Error removing cache file: {e}")
    
    def get_client(self):
        """
        Proporciona un cliente simple para Twitter API
        
        Returns:
            TwitterClient: Cliente para Twitter API o None si no está autenticado
        """
        # Si ya tenemos un token, verificar si es válido
        if self.access_token:
            # Comprobar si ha expirado
            if self.expiry_time and time.time() > self.expiry_time:
                # Si hay refresh token, intentar renovar
                if self.refresh_token:
                    self.logger.info("Token expirado, intentando renovar")
                    if not self.refresh_access_token():
                        self.logger.warning("Renovación del token fallida")
                        return None
                else:
                    self.logger.warning("Token expirado y no hay refresh_token disponible")
                    return None
            
            # Si hemos llegado hasta aquí es porque tenemos un token que parece válido
            # Retornar un cliente con este token, sin intentar otra autenticación
            return TwitterClient(self.access_token, self, self.logger)
        
        # Si no tenemos token, no intentar autenticación silenciosa
        self.logger.warning("No hay token disponible, get_client devuelve None")
        return None


class TwitterClient:
    """Cliente simple para interactuar con la API de Twitter"""
    
    def __init__(self, access_token, auth_manager, logger=None):
        """
        Inicializa el cliente de Twitter
        
        Args:
            access_token (str): Token de acceso
            auth_manager (TwitterAuthManager): Gestor de autenticación
            logger (Logger, optional): Logger para registrar eventos
        """
        self.access_token = access_token
        self.auth_manager = auth_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Base URL para la API v2
        self.base_url = "https://api.twitter.com/2"
    
    def _get_headers(self):
        """Obtiene headers para las peticiones"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method, endpoint, params=None, data=None, retry=True):
        """
        Realiza una petición a la API
        
        Args:
            method (str): Método HTTP (GET, POST, etc.)
            endpoint (str): Endpoint de la API
            params (dict, optional): Parámetros de la petición
            data (dict, optional): Datos para POST/PUT
            retry (bool): Si es True, reintenta la petición si el token expiró
            
        Returns:
            dict: Respuesta de la API o None si hay error
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            headers = self._get_headers()
            
            # Realizar la petición
            response = requests.request(
                method, 
                url, 
                params=params, 
                json=data, 
                headers=headers
            )
            
            # Manejar respuesta
            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            elif response.status_code == 401 and retry:
                # Token expirado, renovar y reintentar
                if self.auth_manager.refresh_access_token():
                    self.access_token = self.auth_manager.access_token
                    return self._make_request(method, endpoint, params, data, retry=False)
                else:
                    self.logger.error("Failed to refresh token for API request")
                    return None
            else:
                self.logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error making API request: {e}")
            return None
    
    def get_user_info(self):
        """
        Obtiene información del usuario autenticado
        
        Returns:
            dict: Información del usuario o None si hay error
        """
        params = {
            "user.fields": "id,name,username,profile_image_url,description,public_metrics"
        }
        return self._make_request("GET", "users/me", params=params)
    
    def get_followed_users(self, user_id=None, max_results=100, pagination_token=None):
        """
        Obtiene usuarios seguidos por el usuario
        
        Args:
            user_id (str, optional): ID del usuario, si es None usa el usuario autenticado
            max_results (int): Número máximo de resultados
            pagination_token (str, optional): Token para paginación
            
        Returns:
            dict: Lista de usuarios seguidos o None si hay error
        """
        if not user_id:
            # Obtener ID del usuario actual si no se proporciona
            user_info = self.get_user_info()
            if not user_info or "data" not in user_info or "id" not in user_info["data"]:
                return None
            user_id = user_info["data"]["id"]
        
        params = {
            "max_results": max_results,
            "user.fields": "id,name,username,profile_image_url,description,public_metrics"
        }
        
        if pagination_token:
            params["pagination_token"] = pagination_token
        
        return self._make_request("GET", f"users/{user_id}/following", params=params)
    
    def follow_user(self, target_user_id):
        """
        Sigue a un usuario
        
        Args:
            target_user_id (str): ID del usuario a seguir
            
        Returns:
            dict: Respuesta de la API o None si hay error
        """
        # Obtener ID del usuario actual
        user_info = self.get_user_info()
        if not user_info or "data" not in user_info or "id" not in user_info["data"]:
            return None
        user_id = user_info["data"]["id"]
        
        # Datos para la petición
        data = {
            "target_user_id": target_user_id
        }
        
        return self._make_request("POST", f"users/{user_id}/following", data=data)
    
    def unfollow_user(self, target_user_id):
        """
        Deja de seguir a un usuario
        
        Args:
            target_user_id (str): ID del usuario a dejar de seguir
            
        Returns:
            bool: True si la operación fue exitosa
        """
        # Obtener ID del usuario actual
        user_info = self.get_user_info()
        if not user_info or "data" not in user_info or "id" not in user_info["data"]:
            return False
        user_id = user_info["data"]["id"]
        
        url = f"{self.base_url}/users/{user_id}/following/{target_user_id}"
        
        try:
            headers = self._get_headers()
            
            # Realizar la petición DELETE
            response = requests.delete(url, headers=headers)
            
            # En caso de éxito, la API devuelve un código 200
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Error unfollowing user: {e}")
            return False
    
    def search_users(self, query, max_results=10):
        """
        Busca usuarios por nombre o username
        
        Args:
            query (str): Término de búsqueda
            max_results (int): Número máximo de resultados
            
        Returns:
            dict: Resultados de la búsqueda o None si hay error
        """
        params = {
            "query": query,
            "max_results": max_results,
            "user.fields": "id,name,username,profile_image_url,description,public_metrics"
        }
        
        return self._make_request("GET", "users/search", params=params)
    
    def get_user_tweets(self, user_id, max_results=10, exclude_replies=True, exclude_retweets=True):
        """
        Obtiene tweets de un usuario
        
        Args:
            user_id (str): ID del usuario
            max_results (int): Número máximo de tweets
            exclude_replies (bool): Si es True, excluye respuestas
            exclude_retweets (bool): Si es True, excluye retweets
            
        Returns:
            dict: Tweets del usuario o None si hay error
        """
        params = {
            "max_results": max_results,
            "tweet.fields": "created_at,public_metrics,text",
            "expansions": "author_id"
        }
        
        # Construir parámetros de exclusión
        exclude_types = []
        if exclude_replies:
            exclude_types.append("replies")
        if exclude_retweets:
            exclude_types.append("retweets")
        
        if exclude_types:
            params["exclude"] = ",".join(exclude_types)
        
        return self._make_request("GET", f"users/{user_id}/tweets", params=params)