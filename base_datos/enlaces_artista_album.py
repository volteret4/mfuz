#!/usr/bin/env python
#
# Script Name: db_musica_links.py
# Description: Complementa db_musica.py añadiendo enlaces a servicios externos (Spotify, YouTube, MusicBrainz, Discogs, RateYourMusic, Bandcamp)
#              para artistas y álbumes en la base de datos musical.
# Author: basado en el trabajo de volteret4
# Dependencies: - python3, sqlite3, dotenv, spotipy, musicbrainzngs, discogs_client, google-api-python-client
# TODO: - arreglar spotify url e id de album
#       - copiar artist
#       - anadir bandcamp
#       - anadir rateyourmusic 

import os
import json
import logging
import sqlite3
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import argparse
import requests
import urllib.parse
import traceback
import lxml

# APIs específicas
import pylast
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import musicbrainzngs
import discogs_client
from googleapiclient.discovery import build


# Adaptador personalizado para datetime
def adapt_datetime(dt):
    return dt.isoformat()

# Registrar el adaptador
sqlite3.register_adapter(datetime, adapt_datetime)

class MusicLinksManager:
    def __init__(self, config):
        # Asegurar que db_path sea un string o Path
        db_path = config.get('db_path')
        if not db_path:
            raise ValueError("No se proporcionó una ruta de base de datos válida")
        
        # Convertir a Path y resolver
        self.db_path = Path(str(db_path)).resolve()
        
        # Servicios deshabilitados
        self.disabled_services = config.get('disable_services', [])
        
        # Límite de tasa
        self.rate_limit = config.get('rate_limit', 0.5)
        
        # Configuración de APIs
        self.lastfm_api_key = config.get('lastfm_api_key')
        self.lastfm_user = config.get('lastfm_user')
        self.youtube_api_key = config.get('youtube_api_key')
        self.spotify_client_id = config.get('spotify_client_id')
        self.spotify_client_secret = config.get('spotify_client_secret')
        self.discogs_token = config.get('discogs_token')
        
        # Configuración de logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Depuración de configuración
        print("Configuración recibida:")
        for key, value in config.items():
            print(f"{key}: {value}")
        
        # Inicialización de APIs
        self._init_apis()
        
        # Inicialización de base de datos
        self._update_database_schema()
    
    def _init_apis(self):
        """Inicializa las conexiones a las APIs externas"""
        # [Código existente para otras APIs...]
        
        # Spotify
        if 'spotify' not in self.disabled_services:
            try:
                spotify_client_id = self.spotify_client_id
                spotify_client_secret = self.spotify_client_secret
                
                if spotify_client_id and spotify_client_secret:
                    client_credentials_manager = SpotifyClientCredentials(
                        client_id=spotify_client_id, 
                        client_secret=spotify_client_secret
                    )
                    self.spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
                    self.logger.info("Spotify API initialized successfully")
                else:
                    self.spotify = None
                    self.logger.warning("Spotify API credentials not found")
            except Exception as e:
                self.spotify = None
                self.logger.error(f"Failed to initialize Spotify API: {str(e)}")
        else:
            self.spotify = None
            self.logger.info("Spotify service disabled")
        
        # MusicBrainz
        if 'musicbrainz' not in self.disabled_services:
            try:
                # Configurar el agente de usuario para MusicBrainz
                musicbrainzngs.set_useragent(
                    "Python Music Library Links Manager",
                    "0.1",
                    "https://github.com/volteret4/"
                )
                # Configurar el logger de MusicBrainz para suprimir mensajes informativos
                mb_logger = logging.getLogger("musicbrainzngs")
                mb_logger.setLevel(logging.ERROR)  # Solo mostrar errores, no advertencias o info
                # Crear un manejador que no haga nada con los mensajes
                null_handler = logging.NullHandler()
                mb_logger.addHandler(null_handler)
                # Quitar todos los demás manejadores que pudieran existir
                for handler in mb_logger.handlers[:]:
                    if not isinstance(handler, logging.NullHandler):
                        mb_logger.removeHandler(handler)
                self.logger.info("MusicBrainz API initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize MusicBrainz API: {str(e)}")
        else:
            self.logger.info("MusicBrainz service disabled")
        
        # Discogs
        if 'discogs' not in self.disabled_services:
            try:
                discogs_token = self.discogs_token
                if discogs_token:
                    self.discogs = discogs_client.Client('MusicLibraryLinksManager/0.1', user_token=discogs_token)
                    self.logger.info("Discogs API initialized successfully")
                else:
                    self.discogs = None
                    self.logger.warning("Discogs API token not found")
            except Exception as e:
                self.discogs = None
                self.logger.error(f"Failed to initialize Discogs API: {str(e)}")
        else:
            self.discogs = None
            self.logger.info("Discogs service disabled")
        
        # YouTube
        if 'youtube' not in self.disabled_services:
            try:
                youtube_api_key = self.youtube_api_key
                if youtube_api_key:
                    print(f"construyendo api para youtube con apikey: {youtube_api_key}")
                    self.youtube = build('youtube', 'v3', developerKey=youtube_api_key)
                    self.logger.info("YouTube API initialized successfully")
                else:
                    self.youtube = None
                    self.logger.warning("YouTube API key not found")
            except Exception as e:
                self.youtube = None
                self.logger.error(f"Failed to initialize YouTube API: {str(e)}")
        else:
            self.youtube = None
            self.logger.info("YouTube service disabled")
        
        # Bandcamp (nuevo)
        if 'bandcamp' in self.disabled_services:
            self.bandcamp_enabled = False
            self.logger.info("Bandcamp service disabled")
        else:
            self.bandcamp_enabled = True
            self.logger.info("Bandcamp service enabled (URL generation only)")
        
        # RateYourMusic no necesita API, pero registramos si está deshabilitado
        if 'rateyourmusic' in self.disabled_services:
            self.rateyourmusic_enabled = False
            self.logger.info("RateYourMusic service disabled")
        else:
            self.rateyourmusic_enabled = True

        # Last.fm
        if 'lastfm' not in self.disabled_services:
            try:
                lastfm_api_key = getattr(self, 'lastfm_api_key', None)
                if lastfm_api_key:
                    self.lastfm_network = pylast.LastFMNetwork(
                        api_key=lastfm_api_key,
                        username=getattr(self, 'lastfm_user', None)
                    )
                    self.lastfm_enabled =True
                    self.logger.info("Last.fm API initialized successfully")
                else:
                    self.lastfm_enabled = False
                    self.lastfm_network = None
                    self.logger.warning("Last.fm API key not found")
            except Exception as e:
                self.lastfm_network = None
                self.logger.error(f"Failed to initialize Last.fm API: {str(e)}")
        else:
            self.lastfm_network = None
            self.logger.info("Last.fm service disabled")

    
    def _update_database_schema(self):
        """Actualiza el esquema de la base de datos para incluir columnas de enlaces"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Añadir columna MBID a artistas si no existe
        c.execute("PRAGMA table_info(artists)")
        artist_columns = {col[1] for col in c.fetchall()}
        
        if 'mbid' not in artist_columns:
            c.execute("ALTER TABLE artists ADD COLUMN mbid TEXT")
        
        # Añadir columna bandcamp_url a artistas si no existe
        if 'bandcamp_url' not in artist_columns:
            c.execute("ALTER TABLE artists ADD COLUMN bandcamp_url TEXT")
        
        # Añadir columna bandcamp_url a artistas si no existe
        if 'member_of' not in artist_columns:
            c.execute("ALTER TABLE artists ADD COLUMN member_of TEXT")

        # Añadir columna aliases a artistas si no existe
        if 'aliases' not in artist_columns:
            c.execute("ALTER TABLE artists ADD COLUMN aliases TEXT")

        # Añadir columna lastfm a artistas si no existe
        if 'lastfm_url' not in artist_columns:
            c.execute("ALTER TABLE artists ADD COLUMN lastfm_url TEXT")


        # Añadir columna MBID a álbumes si no existe
        c.execute("PRAGMA table_info(albums)")
        album_columns = {col[1] for col in c.fetchall()}
        
        if 'mbid' not in album_columns:
            c.execute("ALTER TABLE albums ADD COLUMN mbid TEXT")
        
        # Añadir columna bandcamp_url a álbumes si no existe
        if 'bandcamp_url' not in album_columns:
            c.execute("ALTER TABLE albums ADD COLUMN bandcamp_url TEXT")
        
        # Añadir columna lastfm a artistas si no existe
        if 'lastfm_url' not in album_columns:
            c.execute("ALTER TABLE albums ADD COLUMN lastfm_url TEXT")

        conn.commit()
        conn.close()
        self.logger.info("Database schema updated with new link columns")




    def _get_bandcamp_artist_url(self, artist_name: str) -> Optional[str]:
        """Obtiene la URL más precisa del artista en Bandcamp usando scraping"""
        if 'bandcamp' in self.disabled_services:
            return None
            
        try:
            import requests
            from bs4 import BeautifulSoup
            import urllib.parse
            
            # Preparar consulta de búsqueda
            artist_query = urllib.parse.quote(artist_name)
            search_url = f"https://bandcamp.com/search?q={artist_query}&item_type=b"
            
            # Hacemos una solicitud a la página de búsqueda
            headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Selector más específico para resultados
                results = soup.select('ul.result-items li.searchresult.data-search div.result-info')
                
                if not results:
                    self.logger.warning(f"No search results found for artist: {artist_name}")
                    return None
                
                for result in results:
                    # Buscar el enlace dentro del resultado
                    artist_link = result.select_one('div:nth-child(2) a')
                    
                    if not artist_link:
                        continue
                    
                    result_name = artist_link.text.strip()
                    artist_url = artist_link.get('href', '')
                    
                    # Verificar si el nombre coincide
                    name_match = (
                        artist_name.lower() in result_name.lower() or 
                        result_name.lower() in artist_name.lower() or 
                        self._similar_names(artist_name, result_name)
                    )
                    
                    if name_match:
                        # Limpiar la URL, eliminando parámetros de búsqueda
                        if '?from=search' in artist_url:
                            artist_url = artist_url.split('?from=search')[0]
                        
                        # Validar que sea una URL de Bandcamp
                        if artist_url.startswith('http') and 'bandcamp.com' in artist_url:
                            return artist_url
                
                # Si no hay coincidencia exacta, intentar con el primer resultado
                first_link = results[0].select_one('div:nth-child(2) a')
                if first_link:
                    first_url = first_link.get('href', '')
                    if first_url.startswith('http') and 'bandcamp.com' in first_url:
                        # Limpiar la URL de parámetros de búsqueda
                        if '?from=search' in first_url:
                            first_url = first_url.split('?from=search')[0]
                        return first_url
            
            return None
        
        except Exception as e:
            self.logger.error(f"Bandcamp artist URL generation error for {artist_name}: {str(e)}")
            return None


    def _get_bandcamp_album_url(self, artist_name: str, album_name: str) -> Optional[str]:
        """
        Obtiene la URL del álbum en Bandcamp usando búsqueda simple con expresiones regulares.
        
        Args:
            artist_name (str): Nombre del artista
            album_name (str): Nombre del álbum
        
        Returns:
            Optional[str]: URL del álbum o None si no se encuentra
        """
        if 'bandcamp' in self.disabled_services:
            return None

        try:
            import requests
            import re
            import urllib.parse

            # Preparar consulta de búsqueda
            encoded_album = urllib.parse.quote(album_name)
            search_url = f"https://bandcamp.com/search?q={encoded_album}&item_type=a"

            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            # Realizar solicitud de búsqueda
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                self.logger.warning(f"Error de solicitud HTTP: {response.status_code}")
                return None

            # Buscar URLs de álbumes usando regex
            album_pattern = rf'href="(https://[^.]+\.bandcamp\.com/album/{re.escape(album_name.lower().replace(" ", "-"))}[^"]*)"'
            matches = re.findall(album_pattern, response.text, re.IGNORECASE)

            # Filtrar por artista si es posible
            artist_matches = [
                url for url in matches 
                if artist_name.lower().replace(" ", "-") in url.lower()
            ]

            # Devolver la primera coincidencia
            if artist_matches:
                return artist_matches[0].split('?')[0]
            elif matches:
                return matches[0].split('?')[0]

            self.logger.info(f"No se encontró URL de álbum para {album_name} by {artist_name}")
            return None

        except Exception as e:
            self.logger.error(f"Error en búsqueda de álbum Bandcamp: {e}")
            return None





    def _check_tables_exist(self):
        """Verifica qué tablas existen en la base de datos"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in c.fetchall()}
        conn.close()
        return tables
    
    def get_table_counts(self):
        """Obtiene el número de registros en cada tabla relevante"""
        counts = {}
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        tables = self._check_tables_exist()
        
        if 'artists' in tables:
            c.execute("SELECT COUNT(*) FROM artists")
            counts['artists'] = c.fetchone()[0]
        
        if 'albums' in tables:
            c.execute("SELECT COUNT(*) FROM albums")
            counts['albums'] = c.fetchone()[0]
        
        if 'tracks' in tables:
            c.execute("SELECT COUNT(*) FROM tracks")
            counts['tracks'] = c.fetchone()[0]
            
        conn.close()
        return counts
  
    def update_links(self, days_threshold=30, force_update=False, recent_only=True, missing_only=False):
        """
        Actualiza los enlaces externos para artistas, álbumes y canciones.
        Prioriza la búsqueda de MBID antes que otros enlaces.
        """
        # Primero actualizar los MBID
        self.update_missing_mbids()
        
        # Resto de la lógica de actualización de enlaces
        conn = sqlite3.connect(self.db_path)
        try:
            #self.update_artist_links(days_threshold, force_update, recent_only, missing_only)
            self.update_album_and_track_links(days_threshold, force_update, recent_only, missing_only)
        finally:
            conn.close()

 
    def update_artist_links(self, days_threshold=30, force_update=False, recent_only=True, missing_only=False):
        """
        Actualiza los enlaces externos y metadatos para artistas
        
        Args:
            days_threshold: Umbral de días para filtrar registros
            force_update: Forzar actualización de todos los registros
            recent_only: Si es True, actualiza solo registros recientes; si es False, actualiza los antiguos
            missing_only: Si es True, actualiza solo registros con enlaces o datos faltantes
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        if force_update:
            c.execute("SELECT id, name FROM artists")
        elif missing_only:
            # Construir consulta para encontrar artistas con enlaces o datos faltantes
            missing_conditions = []
            if self.spotify:
                missing_conditions.append("spotify_url IS NULL")
            if self.youtube:
                missing_conditions.append("youtube_url IS NULL")
            if 'musicbrainz' not in self.disabled_services:
                missing_conditions.append("musicbrainz_url IS NULL")
                # Añadir condiciones para los nuevos campos
                missing_conditions.append("origin IS NULL")
                missing_conditions.append("formed_year IS NULL")
                missing_conditions.append("total_albums IS NULL")
            if self.discogs:
                missing_conditions.append("discogs_url IS NULL")
                # Añadir nuevas condiciones para campos de Discogs
                missing_conditions.append("aliases IS NULL")
                missing_conditions.append("member_of IS NULL")
            if self.rateyourmusic_enabled:
                missing_conditions.append("rateyourmusic_url IS NULL")
            if self.bandcamp_enabled:
                missing_conditions.append("bandcamp_url IS NULL")
            # Añadir condición para biografía de Last.fm
            if self.lastfm_api_key:
                missing_conditions.append("bio IS NULL")
            
            if missing_conditions:
                query = f"SELECT id, name FROM artists WHERE {' OR '.join(missing_conditions)}"
                c.execute(query)
            else:
                # Si todos los servicios están deshabilitados, no hay nada que actualizar
                c.execute("SELECT id, name FROM artists WHERE 0=1")  # Consulta vacía
        else:
            if recent_only:
                # Filtrar registros recientes (creados/modificados en los últimos X días)
                c.execute("""
                    SELECT id, name FROM artists 
                    WHERE datetime(last_updated) > datetime('now', ?)
                    OR last_updated IS NULL
                """, (f'-{days_threshold} days',))
            else:
                # Filtrar por fecha de actualización de enlaces (antiguos)
                c.execute("""
                    SELECT id, name FROM artists 
                    WHERE links_updated IS NULL 
                    OR datetime(links_updated) < datetime('now', ?)
                """, (f'-{days_threshold} days',))
        
        artists = c.fetchall()
        total_artists = len(artists)
        self.logger.info(f"Found {total_artists} artists to update links and metadata")
        
        for idx, (artist_id, artist_name) in enumerate(artists, 1):
            self.logger.info(f"Processing artist {idx}/{total_artists}: {artist_name}")
            
            # Obtener los enlaces y datos actuales para no solicitar API si ya existen
            if missing_only:
                c.execute("""
                    SELECT spotify_url, youtube_url, musicbrainz_url, 
                        discogs_url, rateyourmusic_url, bandcamp_url,
                        origin, formed_year, total_albums, bio, aliases, member_of,
                        similar_artists, tags
                    FROM artists WHERE id = ?
                """, (artist_id,))
                result = c.fetchone()
                current_data = dict(zip(
                    ['spotify_url', 'youtube_url', 'musicbrainz_url', 'discogs_url', 
                    'rateyourmusic_url', 'bandcamp_url', 'origin', 'formed_year', 
                    'total_albums', 'bio', 'similar_artists', 'tags', 'aliases', 'member_of', 
                    'lastfm_url'], 
                    result
                ))
            else:
                current_data = {
                    'spotify_url': None, 
                    'youtube_url': None, 
                    'musicbrainz_url': None, 
                    'discogs_url': None, 
                    'rateyourmusic_url': None,
                    'bandcamp_url': None,
                    'origin': None,
                    'formed_year': None,
                    'total_albums': None,
                    'bio': None,
                    'similar_artists': None,
                    'tags': None,
                    'aliases': None,
                    'member_of': None,
                    'lastfm_url': None
                }
        
            
            # Datos de enlaces
            discogs_url, aliases, member_of = None, None, None
            if self.discogs and (current_data['discogs_url'] is None or 
                            current_data['aliases'] is None or 
                            current_data['member_of'] is None):
                discogs_url, aliases, member_of = self._get_discogs_artist_url(artist_name)
            else:
                discogs_url = current_data['discogs_url']
                aliases = current_data['aliases']
                member_of = current_data['member_of']
            
            links = {
                'spotify_url': (self._get_spotify_artist_url(artist_name) if self.spotify and current_data['spotify_url'] is None else current_data['spotify_url']), 
                'youtube_url': (self._get_youtube_artist_url(artist_name) if self.youtube and current_data['youtube_url'] is None else current_data['youtube_url']),
                'musicbrainz_url': (self._get_musicbrainz_artist_url(artist_name) if 'musicbrainz' not in self.disabled_services and current_data['musicbrainz_url'] is None else current_data['musicbrainz_url']),
                'discogs_url': discogs_url,
                'rateyourmusic_url': (self._get_rateyourmusic_artist_url(artist_name) if self.rateyourmusic_enabled and current_data['rateyourmusic_url'] is None else current_data['rateyourmusic_url']),
                'bandcamp_url': (self._get_bandcamp_artist_url(artist_name) if self.bandcamp_enabled and current_data['bandcamp_url'] is None else current_data['bandcamp_url']),
                'links_updated': datetime.now()
            }
            
            # Obtener información de MusicBrainz si es necesario
            # Modificar la sección de obtención de información de MusicBrainz
            mb_info = {'origin': current_data['origin'], 'formed_year': current_data['formed_year'], 'total_albums': current_data['total_albums']}
            if 'musicbrainz' not in self.disabled_services and (current_data['origin'] is None or current_data['formed_year'] is None or current_data['total_albums'] is None):
                try:
                    musicbrainz_result = self._get_musicbrainz_artist_info(artist_name)
                    
                    # Verificar si el resultado es válido antes de usarlo
                    if musicbrainz_result:
                        mb_info['origin'] = musicbrainz_result.get('origin', current_data['origin'])
                        mb_info['formed_year'] = musicbrainz_result.get('formed_year', current_data['formed_year'])
                        mb_info['total_albums'] = musicbrainz_result.get('total_albums', current_data['total_albums'])
                    
                    # Log para depuración
                    if not musicbrainz_result:
                        self.logger.warning(f"No se obtuvo información de MusicBrainz para {artist_name}")
                except Exception as e:
                    # Capturar cualquier otra excepción inesperada
                    self.logger.error(f"Error obteniendo información de MusicBrainz para {artist_name}: {str(e)}")
                    # Mantener los datos actuales
                    mb_info = {
                        'origin': current_data['origin'], 
                        'formed_year': current_data['formed_year'], 
                        'total_albums': current_data['total_albums']
                    }
            
            # Obtener biografía de Last.fm si es necesario
            lastfm_result = None
            artist_lastfm_url = None  # Initialize this variable
            if self.lastfm_api_key and (
                current_data['bio'] is None or 
                current_data['similar_artists'] is None or 
                current_data['tags'] is None or 
                force_update
            ):
                try:
                    lastfm_result = self._get_lastfm_artist_bio(artist_name)
                except Exception as e:
                    self.logger.error(f"Error getting Last.fm info for {artist_name}: {str(e)}")

            # Prepare Last.fm data
            if lastfm_result:
                artist_lastfm_url, bio, similar_artists, tags, _ = lastfm_result
                
                # Use existing data if no new data found
                bio_param = bio if bio else current_data['bio']
                similar_artists_param = similar_artists if similar_artists else current_data['similar_artists']
                tags_param = tags if tags else current_data['tags']
            else:
                # Keep existing data if no new Last.fm data
                bio_param = current_data['bio']
                similar_artists_param = current_data['similar_artists']
                tags_param = current_data['tags']
                artist_lastfm_url = current_data.get('lastfm_url')  # Try to get existing URL

            
            # Update query to include similar artists and tags
            update_query = """
                UPDATE artists SET 
                spotify_url = ?, youtube_url = ?, musicbrainz_url = ?, 
                discogs_url = ?, rateyourmusic_url = ?, bandcamp_url = ?,
                origin = ?, formed_year = ?, total_albums = ?, bio = ?,
                similar_artists = ?, tags = ?,
                aliases = ?, member_of = ?,
                links_updated = ?, last_updated = ?, lastfm_url = ?
                WHERE id = ?
            """
            c.execute(update_query, (
                links['spotify_url'], links['youtube_url'], links['musicbrainz_url'],
                links['discogs_url'], links['rateyourmusic_url'], links['bandcamp_url'],
                mb_info['origin'], mb_info['formed_year'], mb_info['total_albums'], bio_param,
                similar_artists_param, tags_param,
                aliases, member_of,
                links['links_updated'], links['links_updated'], artist_lastfm_url, artist_id
                
            ))
            
            conn.commit()
            

            
            # Pausa usando el rate limiter
            self._rate_limit_pause()
        
        conn.close()
        self.logger.info(f"Updated links and metadata for {total_artists} artists")
        
    def update_album_and_track_links(self, days_threshold=30, force_update=False, recent_only=True, missing_only=False):
        """
        Actualiza los enlaces externos y metadatos para álbumes y sus pistas
        
        Args:
            days_threshold: Umbral de días para filtrar registros
            force_update: Forzar actualización de todos los registros
            recent_only: Si es True, actualiza solo registros recientes; si es False, actualiza los antiguos
            missing_only: Si es True, prioriza álbumes con información faltante
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Definir columnas adicionales a verificar y crear
        additional_columns = [
            ('spotify_url', 'TEXT'),
            ('spotify_id', 'TEXT'),
            ('youtube_url', 'TEXT'),
            ('musicbrainz_url', 'TEXT'),
            ('discogs_url', 'TEXT'),
            ('rateyourmusic_url', 'TEXT'),
            ('producers', 'TEXT'),
            ('engineers', 'TEXT'),
            ('mastering_engineers', 'TEXT'),
            ('credits', 'TEXT'),
            ('links_updated', 'DATETIME'),
            ('lastfm_url', 'TEXT')
        ]
        
        # Verificar y crear columnas faltantes
        c.execute("PRAGMA table_info(albums)")
        existing_columns = [column[1] for column in c.fetchall()]
        
        for column_name, column_type in additional_columns:
            if column_name not in existing_columns:
                try:
                    c.execute(f"ALTER TABLE albums ADD COLUMN {column_name} {column_type}")
                    self.logger.info(f"Created column {column_name} in albums table")
                except sqlite3.OperationalError as e:
                    self.logger.warning(f"Could not add column {column_name}: {e}")
        
        conn.commit()
        
        tables = self._check_tables_exist()
        has_tracks_table = 'tracks' in tables
        
        # Construir consulta base para seleccionar álbumes
        base_query = """
            SELECT albums.id, albums.name, artists.name 
            FROM albums JOIN artists ON albums.artist_id = artists.id
        """
        
        # Modificar la consulta según los parámetros
        if force_update:
            # Todos los álbumes si force_update es True
            c.execute(base_query)
        else:
            # Construir condiciones adicionales
            conditions = []
            
            if missing_only:
                # Añadir condiciones para información faltante
                missing_links_conditions = []
                if self.spotify:
                    missing_links_conditions.append("albums.spotify_url IS NULL")
                if self.youtube:
                    missing_links_conditions.append("albums.youtube_url IS NULL")
                if 'musicbrainz' not in self.disabled_services:
                    missing_links_conditions.append("albums.musicbrainz_url IS NULL")
                if self.discogs:
                    missing_links_conditions.append("albums.discogs_url IS NULL")
                    missing_links_conditions.append("(albums.producers IS NULL OR albums.engineers IS NULL OR albums.mastering_engineers IS NULL)")
                if self.rateyourmusic_enabled:
                    missing_links_conditions.append("albums.rateyourmusic_url IS NULL")
                
                # Si hay condiciones de información faltante, incluirlas
                if missing_links_conditions:
                    conditions.append(f"({' OR '.join(missing_links_conditions)})")
            
            if recent_only:
                # Añadir condición de registros recientes
                conditions.append(f"(datetime(albums.last_updated) > datetime('now', '-{days_threshold} days') OR albums.last_updated IS NULL)")
            else:
                # Añadir condición de registros antiguos
                conditions.append(f"(albums.links_updated IS NULL OR datetime(albums.links_updated) < datetime('now', '-{days_threshold} days'))")
            
            # Combinar condiciones
            if conditions:
                query = base_query + " WHERE " + " AND ".join(conditions)
                c.execute(query)
            else:
                # Si no hay condiciones, ejecutar consulta base
                c.execute(base_query)
        
        # Obtener los resultados de la consulta
        albums = c.fetchall()
        total_albums = len(albums)
        self.logger.info(f"Found {total_albums} albums to update links and metadata")
        
    
        try:
            for idx, (album_id, album_name, artist_name) in enumerate(albums, 1):
                self.logger.info(f"Processing album {idx}/{total_albums}: {album_name} by {artist_name}")
                
                # Inicializar variables con valores predeterminados
                discogs_url = None
                producers = None
                engineers = None
                mastering_engineers = None
                credits = None
                credits_dict = {}
                results_list = []
                bandcamp_url = None
                lastfm_url = None

                try:
                    # Obtener los enlaces y datos actuales para no solicitar API si ya existen
                    if missing_only:
                        c.execute("""
                            SELECT spotify_url, spotify_id, youtube_url, musicbrainz_url, 
                                discogs_url, rateyourmusic_url, bandcamp_url, producers, 
                                engineers, mastering_engineers, credits, lastfm_url
                            FROM albums WHERE id = ?
                        """, (album_id,))
                        current_data = dict(zip(
                            ['spotify_url', 'spotify_id', 'youtube_url', 'musicbrainz_url', 
                            'discogs_url', 'rateyourmusic_url', 'bandcamp_url', 'producers', 
                            'engineers', 'mastering_engineers', 'credits', 'lastfm_url'], 
                            c.fetchone()
                        ))
                    else:
                        current_data = {
                            'spotify_url': None, 
                            'spotify_id': None,
                            'youtube_url': None, 
                            'musicbrainz_url': None, 
                            'discogs_url': None, 
                            'rateyourmusic_url': None,
                            'bandcamp_url': None,
                            'producers': None,
                            'engineers': None,
                            'mastering_engineers': None,
                            'credits': None,
                            'lastfm_url': None
                        }

                    # Obtener enlace de Bandcamp
                    if self.bandcamp_enabled and current_data['bandcamp_url'] is None:
                        try:
                            bandcamp_url = self._get_bandcamp_album_url(artist_name, album_name)
                            # Si se encuentra un enlace de Bandcamp, usarlo
                            if bandcamp_url:
                                current_data['bandcamp_url'] = bandcamp_url
                        except Exception as bandcamp_error:
                            self.logger.warning(f"Bandcamp album search error for {album_name} by {artist_name}: {bandcamp_error}")
                    
                    # Obtener enlace de LastFM (nuevo)
                    if self.lastfm_enabled and current_data['lastfm_url'] is None:
                        try:
                            lastfm_url = self._get_lastfm_album_url(artist_name, album_name)
                            if lastfm_url:
                                current_data['lastfm_url'] = lastfm_url
                        except Exception as lastfm_error:
                            self.logger.warning(f"LastFM album search error for {album_name} by {artist_name}: {lastfm_error}")




                    # Obtener los enlaces y datos adicionales del álbum
                    if self.discogs and (current_data['discogs_url'] is None or 
                                    current_data['producers'] is None or 
                                    current_data['engineers'] is None or 
                                    current_data['mastering_engineers'] is None):
                        try:
                            discogs_url, producers, engineers, mastering_engineers, credits = self._get_discogs_album_url(artist_name, album_name)
                        except Exception as discogs_error:
                            self.logger.warning(f"Discogs album search error for {album_name} by {artist_name}: {discogs_error}")
                            discogs_url = current_data['discogs_url']
                            producers = current_data['producers']
                            engineers = current_data['engineers']
                            mastering_engineers = current_data['mastering_engineers']
                            credits = current_data['credits']
                    else:
                        discogs_url = current_data['discogs_url']
                        producers = current_data['producers']
                        engineers = current_data['engineers']
                        mastering_engineers = current_data['mastering_engineers']
                        credits = current_data['credits']
                    
                    # Manejar conversión de créditos a JSON de manera segura
                    try:
                        if credits and isinstance(credits, str):
                            credits_dict = json.loads(credits) if credits.strip() else {}
                    except (json.JSONDecodeError, TypeError) as json_error:
                        self.logger.warning(f"Error al convertir créditos a JSON para {album_name}: {json_error}")
                        credits_dict = {}
                    
                
                    album_links = {
                        'spotify_url': current_data['spotify_url'],
                        'spotify_id': current_data['spotify_id'],
                        'youtube_url': (self._get_youtube_album_url(artist_name, album_name) if self.youtube and current_data['youtube_url'] is None else current_data['youtube_url']),
                        'musicbrainz_url': (self._get_musicbrainz_album_url(artist_name, album_name) if 'musicbrainz' not in self.disabled_services and current_data['musicbrainz_url'] is None else current_data['musicbrainz_url']),
                        'discogs_url': discogs_url,
                        'bandcamp_url': current_data['bandcamp_url'],  # Usar el enlace de Bandcamp ya sea nuevo o existente
                        'rateyourmusic_url': (self._get_rateyourmusic_album_url(artist_name, album_name) if self.rateyourmusic_enabled and current_data['rateyourmusic_url'] is None else current_data['rateyourmusic_url']),
                        'lastfm_url': current_data['lastfm_url'],
                        'links_updated': datetime.now()
                    }
                    
                    # Actualizar enlace de Bandcamp en la base de datos
                
                    update_query = """
                        UPDATE albums SET 
                        spotify_url = ?, spotify_id = ?, youtube_url = ?, musicbrainz_url = ?, 
                        discogs_url = ?, rateyourmusic_url = ?, bandcamp_url = ?, producers = ?, 
                        engineers = ?, mastering_engineers = ?, credits = ?, lastfm_url = ?, 
                        links_updated = ?
                        
                        WHERE id = ?
                    """
                    c.execute(update_query, (
                        album_links['spotify_url'], album_links['spotify_id'], album_links['youtube_url'], 
                        album_links['musicbrainz_url'], album_links['discogs_url'], 
                        album_links['rateyourmusic_url'], album_links['bandcamp_url'], producers, engineers,
                        mastering_engineers, credits, album_links['lastfm_url'], album_links['links_updated'],  
                        album_id
                    ))
                    conn.commit()
                    
                    
                except Exception as album_error:
                    self.logger.error(f"Error processing album {album_name} by {artist_name}: {album_error}")
                    # Continuar con el siguiente álbum en caso de error
                    continue
            
            self.logger.info(f"Updated links and metadata for {total_albums} albums")
        
        except Exception as e:
            self.logger.error(f"Error updating album links: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
            
    def _rate_limit_pause(self):
        """Realiza una pausa según la configuración del rate limiter"""
        time.sleep(self.rate_limit)

    def _get_lastfm_album_url(self, artist_name, album_name):
        """
        Obtiene la URL de Last.fm para un álbum específico

        Args:
        artist_name: Nombre del artista
        album_name: Nombre del álbum

        Returns:
        URL del álbum en Last.fm o None si no se encuentra
        """
        if not self.lastfm_api_key:
            self.logger.warning(f"Last.fm API key no configurada. No se puede obtener URL del álbum.")
            return None

        try:
            self.logger.info(f"Buscando URL de álbum en Last.fm para: {artist_name} - {album_name}")
            
            params = {
                'method': 'album.getinfo',
                'artist': artist_name,
                'album': album_name,
                'api_key': self.lastfm_api_key,
                'format': 'json'
            }
            
            response = requests.get('https://ws.audioscrobbler.com/2.0/', params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verificar que la respuesta contiene los datos necesarios
                if 'album' in data and 'url' in data['album']:
                    album_url = data['album']['url']
                    
                    self.logger.info(f"URL de álbum encontrada: {album_url}")
                    return album_url
                
                self.logger.warning(f"No se encontró URL para el álbum {album_name} de {artist_name}")
                return None
            
            else:
                self.logger.warning(f"Error en la respuesta de Last.fm: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Error obteniendo URL de álbum de Last.fm: {str(e)}")
            return None

        finally:
            # Pequeño delay para respetar límites de API
            time.sleep(0.5)


    # def _update_track_links(self, conn, album_id, spotify_tracks, missing_only=False):
    #     """
    #     Actualiza los enlaces de pistas para un álbum específico
        
    #     Args:
    #         conn: Conexión a la base de datos
    #         album_id: ID del álbum
    #         spotify_tracks: Lista de pistas de Spotify
    #         missing_only: Si es True, actualiza solo pistas con enlaces faltantes
    #     """
    #     c = conn.cursor()
        
    #     # Obtener todas las pistas del álbum
    #     if missing_only:
    #         c.execute("SELECT id, name, number, spotify_url, spotify_id FROM tracks WHERE album_id = ? ORDER BY number", (album_id,))
    #         db_tracks = c.fetchall()
    #     else:
    #         c.execute("SELECT id, name, number FROM tracks WHERE album_id = ? ORDER BY number", (album_id,))
    #         db_tracks = c.fetchall()
        
    #     if not db_tracks:
    #         return
        
    #     # Mapear nombres de pistas de Spotify con la base de datos
    #     for db_track in db_tracks:
    #         if missing_only:
    #             track_id, track_name, track_number, current_spotify_url, current_spotify_id = db_track
    #             # Si ya tiene enlaces y estamos en modo missing_only, saltamos
    #             if current_spotify_url is not None and current_spotify_id is not None:
    #                 continue
    #         else:
    #             track_id, track_name, track_number = db_track
            
    #         # Intentar encontrar la pista correspondiente en Spotify
    #         spotify_track = None
            
    #         # Primero intentar por número de pista
    #         if 1 <= track_number <= len(spotify_tracks):
    #             spotify_track = spotify_tracks[track_number - 1]
    #         else:
    #             # Si no coincide por número, intentar por nombre
    #             for sp_track in spotify_tracks:
    #                 # Comparación simple de nombres
    #                 if self._similar_names(track_name, sp_track['name']):
    #                     spotify_track = sp_track
    #                     break
            
    #         if spotify_track:
    #             c.execute("""
    #                 UPDATE tracks 
    #                 SET spotify_url = ?, spotify_id = ?
    #                 WHERE id = ?
    #             """, (spotify_track['url'], spotify_track['id'], track_id))
    
    def _similar_names(self, name1, name2):
        """Compara si dos nombres son similares (ignorando caso, espacios, etc.)"""
        # Normalizar nombres: convertir a minúsculas, eliminar espacios extras
        n1 = re.sub(r'\s+', ' ', name1.lower().strip())
        n2 = re.sub(r'\s+', ' ', name2.lower().strip())
        
        # Comprobar exactitud
        if n1 == n2:
            return True
        
        # Eliminar caracteres especiales y comparar
        n1_clean = re.sub(r'[^\w\s]', '', n1)
        n2_clean = re.sub(r'[^\w\s]', '', n2)
        
        return n1_clean == n2_clean
    

    def count_missing_mbids(self):
        """
        Cuenta los registros sin MBID en artistas, álbumes y canciones.
        
        Returns:
            Dict con el número de registros sin MBID en cada tabla
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        missing_mbids = {
            'artists': 0,
            'albums': 0,
            'songs': 0
        }
        
        # Contar artistas sin MBID
        c.execute("SELECT COUNT(*) FROM artists WHERE mbid IS NULL")
        missing_mbids['artists'] = c.fetchone()[0]
        
        # Contar álbumes sin MBID
        c.execute("SELECT COUNT(*) FROM albums WHERE mbid IS NULL")
        missing_mbids['albums'] = c.fetchone()[0]
        
        # Contar canciones sin MBID (si la tabla existe)
        tables = self._check_tables_exist()
        if 'songs' in tables:
            c.execute("SELECT COUNT(*) FROM songs WHERE mbid IS NULL")
            missing_mbids['songs'] = c.fetchone()[0]
        
        conn.close()
        return missing_mbids



    def update_missing_mbids(self):
        """
        Actualiza los MBID faltantes en artistas, álbumes y canciones.
        Prioriza obtener MBID antes que otros tipos de enlaces.
        """
        before_mbids = self.count_missing_mbids()
        self.logger.info("Missing MBIDs before update:")
        for table, count in before_mbids.items():
            self.logger.info(f"{table.capitalize()}: {count}")
        
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()


        # Actualizar MBID de artistas
        c.execute("SELECT id, name FROM artists WHERE mbid IS NULL")
        artists_without_mbid = c.fetchall()
        
        for artist_id, artist_name in artists_without_mbid:
            try:
                mbid = self._get_musicbrainz_artist_mbid(artist_name)
                if mbid:
                    c.execute("UPDATE artists SET mbid = ? WHERE id = ?", (mbid, artist_id))
                    conn.commit()
                    self.logger.info(f"Found MBID for artist: {artist_name}")
                    self._rate_limit_pause()
            except Exception as e:
                self.logger.error(f"Error finding MBID for artist {artist_name}: {e}")

        # Actualizar MBID de álbumes
        c.execute("""
            SELECT albums.id, albums.name, artists.name 
            FROM albums 
            JOIN artists ON albums.artist_id = artists.id 
            WHERE albums.mbid IS NULL
        """)
        albums_without_mbid = c.fetchall()
        
        for album_id, album_name, artist_name in albums_without_mbid:
            try:
                mbid = self._get_musicbrainz_album_mbid(artist_name, album_name)
                if mbid:
                    c.execute("UPDATE albums SET mbid = ? WHERE id = ?", (mbid, album_id))
                    conn.commit()
                    self.logger.info(f"Found MBID for album: {album_name}")
                    self._rate_limit_pause()
            except Exception as e:
                self.logger.error(f"Error finding MBID for album {album_name}: {e}")

        # Actualizar MBID de canciones (opcional, dependiendo de tu estructura)
        c.execute("""
            SELECT id, title, artist, album 
            FROM songs 
            WHERE mbid IS NULL
        """)
        songs_without_mbid = c.fetchall()
        
        for song_id, title, artist, album in songs_without_mbid:
            try:
                mbid = self._get_musicbrainz_recording_mbid(artist, title, album)
                if mbid:
                    c.execute("UPDATE songs SET mbid = ? WHERE id = ?", (mbid, song_id))
                    conn.commit()
                    self.logger.info(f"Found MBID for song: {title}")
                    self._rate_limit_pause()
            except Exception as e:
                self.logger.error(f"Error finding MBID for song {title}: {e}")

        conn.close()
        # Contar registros sin MBID después de la actualización
        after_mbids = self.count_missing_mbids()
        self.logger.info("Missing MBIDs after update:")
        for table, count in after_mbids.items():
            self.logger.info(f"{table.capitalize()}: {count}")
            
        # Calcular y registrar cuántos MBID se encontraron
        mbids_found = {
            table: before_count - after_count 
            for table, (before_count, after_count) in zip(
                before_mbids.keys(), 
                zip(before_mbids.values(), after_mbids.values())
            )
        }
        
        self.logger.info("MBIDs found during update:")
        for table, count in mbids_found.items():
            self.logger.info(f"{table.capitalize()}: {count}")

    def _get_musicbrainz_artist_mbid(self, artist_name: str) -> Optional[str]:
        """Obtiene el MBID de un artista desde MusicBrainz"""
        if 'musicbrainz' in self.disabled_services:
            return None
        
        try:
            result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
            
            if result['artist-list'] and len(result['artist-list']) > 0:
                return result['artist-list'][0]['id']
        except Exception as e:
            self.logger.error(f"MusicBrainz artist MBID search error for {artist_name}: {str(e)}")
        
        return None



    def _get_musicbrainz_album_mbid(self, artist_name: str, album_name: str) -> Optional[str]:
        """Obtiene el MBID de un álbum desde MusicBrainz"""
        if 'musicbrainz' in self.disabled_services:
            return None
        
        try:
            result = musicbrainzngs.search_releases(artist=artist_name, release=album_name, limit=1)
            
            if result['release-list'] and len(result['release-list']) > 0:
                return result['release-list'][0]['id']
        except Exception as e:
            self.logger.error(f"MusicBrainz album MBID search error for {album_name}: {str(e)}")
        
        return None



    def _get_musicbrainz_recording_mbid(self, artist: str, title: str, album: str) -> Optional[str]:
        """Obtiene el MBID de una grabación desde MusicBrainz"""
        if 'musicbrainz' in self.disabled_services:
            return None
        
        try:
            result = musicbrainzngs.search_recordings(
                artist=artist, 
                recording=title, 
                release=album, 
                limit=1
            )
            
            if result['recording-list'] and len(result['recording-list']) > 0:
                return result['recording-list'][0]['id']
        except Exception as e:
            self.logger.error(f"MusicBrainz recording MBID search error for {title}: {str(e)}")
        
        return None


    def _get_musicbrainz_artist_info(self, artist_name):
        """
        Obtiene información detallada de un artista desde MusicBrainz: origen, año de formación y total de discos.
        
        Args:
            artist_name: Nombre del artista
            
        Returns:
            Dictionary con origin, formed_year y total_albums, o valores None si no se encuentra
        """
        if 'musicbrainz' in self.disabled_services:
            return {'origin': None, 'formed_year': None, 'total_albums': None}
        
        try:
            # Intentar primero obtener por MBID si existe
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT mbid FROM artists WHERE name = ?", (artist_name,))
            result = c.fetchone()
            mbid = result[0] if result and result[0] else None
            
            # Preparar URL y headers
            headers = {
                'User-Agent': 'YourAppName/1.0 (your@email.com)', 
                'Accept': 'application/json'
            }
            
            if mbid:
                # Buscar por MBID
                self.logger.info(f"Buscando información en MusicBrainz usando MBID para: {artist_name}")
                url = f"https://musicbrainz.org/ws/2/artist/{mbid}?inc=release-groups&fmt=json"
            else:
                # Buscar por nombre
                self.logger.info(f"Buscando información en MusicBrainz para: {artist_name}")
                query = urllib.parse.quote_plus(artist_name)
                url = f"https://musicbrainz.org/ws/2/artist/?query={query}&fmt=json"
            
            # Realizar solicitud
            #self.logger.info(f"URL de consulta: {url}")
            response = requests.get(url, headers=headers)
            
            # Depuración detallada
            self.logger.info(f"Código de estado: {response.status_code}")
            #self.logger.info(f"Contenido de la respuesta: {response.text}")
            
            # Verificar si la respuesta es exitosa
            if response.status_code == 200:
                try:
                    data = response.json()
                except json.JSONDecodeError as je:
                    self.logger.error(f"Error decodificando JSON: {je}")
                    return {'origin': None, 'formed_year': None, 'total_albums': None}
                
                # Depuración del contenido JSON
                self.logger.info(f"Tipo de datos recibidos: {type(data)}")
                #self.logger.info(f"Claves en los datos: {data.keys() if isinstance(data, dict) else 'No es un diccionario'}") # Activar si es necesario comprobar los dict
                
                # Lógica para procesar datos por MBID o por búsqueda
                if mbid:
                    # Procesar datos de artista por MBID
                    if not data or not isinstance(data, dict):
                        self.logger.error(f"Datos inválidos para MBID {mbid}")
                        return {'origin': None, 'formed_year': None, 'total_albums': None}
                    
                    # Obtener origen
                    origin = (data.get('area', {}) or {}).get('name') if 'area' in data else None
                    
                    # Obtener año de formación
                    life_span = data.get('life-span', {}) or {}
                    formed_year = None
                    if 'begin' in life_span and life_span['begin']:
                        year_match = re.match(r'(\d{4})', life_span['begin'])
                        if year_match:
                            formed_year = int(year_match.group(1))
                    
                    # Contar álbumes
                    total_albums = 0
                    if 'release-groups' in data:
                        albums = [rg for rg in data.get('release-groups', []) if rg.get('primary-type') == 'Album']
                        total_albums = len(albums)
                    
                    return {'origin': origin, 'formed_year': formed_year, 'total_albums': total_albums}
                
                else:
                    # Procesar resultados de búsqueda por nombre
                    if 'artists' in data and data['artists']:
                        artist = data['artists'][0]
                        artist_mbid = artist.get('id')
                        
                        if artist_mbid:
                            # Actualizar MBID en la base de datos
                            c.execute("UPDATE artists SET mbid = ? WHERE name = ?", (artist_mbid, artist_name))
                            conn.commit()
                            
                            # Llamada recursiva con MBID
                            return self._get_musicbrainz_artist_info(artist_name)
            
            # Si no se encontró información
            self.logger.warning(f"No se encontró información para {artist_name}")
            return {'origin': None, 'formed_year': None, 'total_albums': None}
        
        except Exception as e:
            # Loguear el error completo
            self.logger.error(f"Error inesperado para {artist_name}: {traceback.format_exc()}")
            return {'origin': None, 'formed_year': None, 'total_albums': None}
        finally:
            # Cerrar conexión de base de datos
            if 'conn' in locals():
                conn.close()
            
            # Respetar rate limit
            time.sleep(1.1)

    def _get_lastfm_artist_bio(self, artist_name, lang='es'):
        """
        Obtiene información detallada de un artista desde Last.fm
        Args:
        artist_name: Nombre del artista
        lang: Idioma a intentar (por defecto español)
        Returns:
        Tuple con información del artista o None si no se encuentra
        """
        if not self.lastfm_api_key:
            self.logger.warning(f"Last.fm API key no configurada. No se puede obtener información para {artist_name}.")
            return None
        
        try:
            self.logger.info(f"Buscando información en Last.fm para: {artist_name} (idioma: {lang})")
            params = {
                'method': 'artist.getinfo',
                'artist': artist_name,
                'api_key': self.lastfm_api_key,
                'format': 'json',
                'lang': lang
            }
            
            response = requests.get('https://ws.audioscrobbler.com/2.0/', params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verificar que la respuesta contiene los datos necesarios
                if 'artist' in data:
                    # URL del artista 
                    artist_lastfm_url = data['artist'].get('url')

                    # Biografía
                    bio_content = data['artist'].get('bio', {}).get('content')
                    bio_summary = data['artist'].get('bio', {}).get('summary')
                    bio_text = bio_content if bio_content and len(bio_content) > 10 else bio_summary
                    
                    if bio_text:
                        # Eliminar enlaces de Last.fm que suelen aparecer al final
                        bio_text = re.sub(r'<a href="https://www.last.fm/music/.*?">Read more.*?</a>', '', bio_text)
                        bio_text = bio_text.strip()
                    
                    # Si no hay biografía y estamos en español, intentar en inglés
                    if not bio_text and lang == 'es':
                        return self._get_lastfm_artist_bio(artist_name, lang='en')
                    
                    # Artistas similares
                    similar_artists = [
                        artist.get('name') for artist in data['artist'].get('similar', {}).get('artist', [])
                    ]
                    
                    # Géneros/Tags
                    tags = [
                        tag.get('name') for tag in data['artist'].get('tags', {}).get('tag', [])
                    ]
                    
                    # Log de la información recuperada
                    self.logger.info(
                        f"Información recuperada para {artist_name}: "
                        f"Bio: {bool(bio_text)}, "
                        f"Artistas similares: {len(similar_artists)}, "
                        f"Tags: {len(tags)}"
                    )

                    # Convertir a cadenas para almacenar en base de datos
                    similar_artists_str = ','.join(similar_artists) if similar_artists else None
                    tags_str = ','.join(tags) if tags else None
                    
                    return (
                        artist_lastfm_url,
                        bio_text,
                        similar_artists_str,
                        tags_str,
                        None  # Placeholder for album URLs
                    )
                
                self.logger.warning(f"No se encontró información para {artist_name} en Last.fm")
                return None
            
            else:
                self.logger.warning(f"Error en la respuesta de Last.fm para {artist_name}: {response.status_code}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error obteniendo información de Last.fm para {artist_name}: {str(e)}")
            return None
        
        finally:
            # Añadir un pequeño delay para respetar límites de API
            time.sleep(0.5)


    def _get_spotify_artist_url(self, artist_name: str) -> Optional[str]:
        """Obtiene la URL del artista en Spotify"""
        if not self.spotify:
            return None
        
        try:
            results = self.spotify.search(q=f'artist:{artist_name}', type='artist', limit=1)
            
            if results and results['artists']['items']:
                return results['artists']['items'][0]['external_urls']['spotify']
        except Exception as e:
            self.logger.error(f"Spotify artist search error for {artist_name}: {str(e)}")
        
        return None
    
    def _get_spotify_album_data(self, artist_name: str, album_name: str) -> Optional[Dict]:
        """Obtiene datos completos del álbum en Spotify, incluyendo pistas"""
        if not self.spotify:
            self.logger.debug("Spotify client not initialized")
            return None
        
        try:
            self.logger.debug(f"Buscando en Spotify álbum: '{album_name}' por '{artist_name}'")
            
            # Intentar con búsqueda de formato exacto primero
            query = f'artist:"{artist_name}" album:"{album_name}"'
            self.logger.debug(f"Consulta inicial: {query}")
            
            results = self.spotify.search(q=query, type='album', limit=5)
            self.logger.debug(f"Resultados iniciales: {len(results['albums']['items']) if results and 'albums' in results else 0} álbumes encontrados")
            
            # Si no hay resultados, intentar una búsqueda más flexible
            if not (results and results['albums']['items']):
                self.logger.debug("No se encontraron resultados exactos, intentando búsqueda flexible")
                clean_query = f'{artist_name} {album_name}'
                self.logger.debug(f"Consulta flexible: {clean_query}")
                results = self.spotify.search(q=clean_query, type='album', limit=10)
                self.logger.debug(f"Resultados flexibles: {len(results['albums']['items']) if results and 'albums' in results else 0} álbumes encontrados")
            
            if not (results and results['albums']['items']):
                self.logger.debug(f"No se encontraron álbumes para '{album_name}' por '{artist_name}'")
                return None
            
            # Intenta encontrar la coincidencia más probable
            album = None
            for item in results['albums']['items']:
                # Verifica coincidencia de artista
                album_artists = [artist['name'].lower() for artist in item['artists']]
                artist_match = False
                
                for a in album_artists:
                    if (artist_name.lower() in a or a in artist_name.lower()):
                        artist_match = True
                        break
                
                if artist_match:
                    # Verifica coincidencia de nombre de álbum
                    if (album_name.lower() == item['name'].lower() or 
                        album_name.lower() in item['name'].lower() or 
                        item['name'].lower() in album_name.lower()):
                        album = item
                        self.logger.debug(f"Coincidencia encontrada: {item['name']} por {item['artists'][0]['name']}")
                        break
            
            # Si no se encuentra una buena coincidencia, tomar el primer resultado como respaldo
            if not album and results['albums']['items']:
                album = results['albums']['items'][0]
                self.logger.debug(f"Usando primer resultado como alternativa: {album['name']} por {album['artists'][0]['name']}")
            
            if not album:
                self.logger.debug(f"No se encontró coincidencia adecuada")
                return None
                
            album_id = album['id']
            album_url = album['external_urls']['spotify']
            
            # Obtener pistas del álbum
            self.logger.debug(f"Obteniendo pistas para el álbum ID: {album_id}")
            tracks_result = self.spotify.album_tracks(album_id)
            tracks = []
            
            if not tracks_result or 'items' not in tracks_result:
                self.logger.debug(f"No se pudieron obtener pistas para el álbum")
                # Devolver al menos la información del álbum aunque no tengamos pistas
                return {
                    'album_id': album_id,
                    'album_url': album_url,
                    'tracks': []
                }
            
            for track in tracks_result['items']:
                tracks.append({
                    'name': track['name'],
                    'id': track['id'],
                    'url': track['external_urls']['spotify'],
                    'number': track['track_number']
                })
            
            self.logger.debug(f"Se obtuvieron con éxito {len(tracks)} pistas del álbum")
            
            return {
                'album_id': album_id,
                'album_url': album_url,
                'tracks': tracks
            }
            
        except Exception as e:
            self.logger.error(f"Error al obtener datos de Spotify para {album_name} por {artist_name}: {str(e)}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
        
        return None
    
    def _get_youtube_artist_url(self, artist_name: str) -> Optional[str]:
        """Obtiene la URL del canal/tópico del artista en YouTube"""
        if not self.youtube:
            return None
        
        try:
            search_response = self.youtube.search().list(
                q=f"{artist_name} topic",
                part="snippet",
                maxResults=1,
                type="channel"
            ).execute()
            
            if search_response['items']:
                channel_id = search_response['items'][0]['id']['channelId']
                return f"https://www.youtube.com/channel/{channel_id}"
        except Exception as e:
            self.logger.error(f"YouTube artist search error for {artist_name}: {str(e)}")
        
        return None
    
 




    def _get_youtube_album_url(self, artist_name: str, album_name: str) -> Optional[str]:
        """Obtiene la URL de resultados de búsqueda del álbum en YouTube"""
        if not self.youtube:
            return None
        
        try:
            query = f"{artist_name} {album_name} album"
            search_response = self.youtube.search().list(
                q=query,
                part="snippet",
                maxResults=1,
                type="playlist"
            ).execute()
            
            if search_response['items']:
                playlist_id = search_response['items'][0]['id']['playlistId']
                return f"https://www.youtube.com/playlist?list={playlist_id}"
            else:
                # Si no hay playlist, devolver un enlace de búsqueda
                query_encoded = query.replace(' ', '+')
                return f"https://www.youtube.com/results?search_query={query_encoded}"
        except Exception as e:
            self.logger.error(f"YouTube album search error for {album_name} by {artist_name}: {str(e)}")
        
        return None



    
    def _get_musicbrainz_artist_url(self, artist_name: str) -> Optional[str]:
        """Obtiene la URL del artista en MusicBrainz"""
        if 'musicbrainz' in self.disabled_services:
            return None
            
        try:
            result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
            
            if result['artist-list'] and len(result['artist-list']) > 0:
                artist_id = result['artist-list'][0]['id']
                return f"https://musicbrainz.org/artist/{artist_id}"
        except Exception as e:
            self.logger.error(f"MusicBrainz artist search error for {artist_name}: {str(e)}")
        
        return None
    
    def _get_musicbrainz_album_url(self, artist_name: str, album_name: str) -> Optional[str]:
        """Obtiene la URL del álbum en MusicBrainz"""
        if 'musicbrainz' in self.disabled_services:
            return None
            
        try:
            result = musicbrainzngs.search_releases(artist=artist_name, release=album_name, limit=1)
            
            if result['release-list'] and len(result['release-list']) > 0:
                release_id = result['release-list'][0]['id']
                return f"https://musicbrainz.org/release/{release_id}"
        except Exception as e:
            self.logger.error(f"MusicBrainz album search error for {album_name} by {artist_name}: {str(e)}")
        
        return None
    
   
    def _get_musicbrainz_recording_url(self, artist: str, title: str, album: str) -> Optional[str]:
        """Obtiene URL de grabación en MusicBrainz"""
        if 'musicbrainz' in self.disabled_services:
            return None
        
        try:
            result = musicbrainzngs.search_recordings(
                artist=artist, 
                recording=title, 
                release=album, 
                limit=1
            )
            
            if result['recording-list'] and len(result['recording-list']) > 0:
                recording_id = result['recording-list'][0]['id']
                return f"https://musicbrainz.org/recording/{recording_id}"
        except Exception as e:
            self.logger.error(f"MusicBrainz recording search error for {title}: {str(e)}")
        
        return None

    def _get_discogs_artist_url(self, artist_name: str) -> tuple:
        """Obtiene la URL del artista en Discogs y datos adicionales con enfoque robusto ante errores de tipo"""
        if not self.discogs:
            return None, None, None
        
        try:
            # Realizar búsqueda simple
            results = self.discogs.search(artist_name, type='artist')
            
            if not results:
                return None, None, None
                
            # Convertir results a lista si es necesario para evitar problemas con slices
            try:
                results_list = list(results)[:5]  # Convertir a lista y tomar los primeros 5
            except Exception as e:
                self.logger.warning(f"Error al convertir resultados para {artist_name}: {str(e)}")
                # Intento alternativo: acceder directamente al primer resultado
                if len(results) > 0:
                    try:
                        return f"https://www.discogs.com/artist/{results[0].id}", None, None
                    except Exception:
                        return None, None, None
                return None, None, None
                
            # Variables para almacenar datos adicionales
            artist_url = None
            aliases = None
            member_of = None
            best_artist = None
                
            # Enfoque simplificado sin usar operaciones problemáticas
            for result in results_list:
                try:
                    # Obtener detalles del artista
                    artist = self.discogs.artist(result.id)
                    artist_name_norm = artist_name.lower().strip()
                    result_name_norm = artist.name.lower().strip()
                    
                    # Verificar coincidencia exacta primero
                    if artist_name_norm == result_name_norm:
                        artist_url = f"https://www.discogs.com/artist/{artist.id}"
                        best_artist = artist
                        break
                        
                    # Verificar si un nombre contiene al otro
                    if artist_name_norm in result_name_norm or result_name_norm in artist_name_norm:
                        artist_url = f"https://www.discogs.com/artist/{artist.id}"
                        best_artist = artist
                        break
                        
                    # Método alternativo de comparación sin usar división
                    # Simplemente verificar si hay palabras en común
                    try:
                        words_query = set(artist_name_norm.split())
                        words_result = set(result_name_norm.split())
                        common_words = words_query.intersection(words_result)
                        
                        # Si hay al menos una palabra en común (sin usar división)
                        if common_words and len(common_words) > 0:
                            if len(words_query) <= 2:  # Para nombres cortos, requerir más coincidencia
                                if len(common_words) == len(words_query):
                                    artist_url = f"https://www.discogs.com/artist/{artist.id}"
                                    best_artist = artist
                                    break
                            else:  # Para nombres más largos, ser más flexible
                                if len(common_words) >= 1:
                                    artist_url = f"https://www.discogs.com/artist/{artist.id}"
                                    best_artist = artist
                                    break
                    except Exception as e:
                        self.logger.warning(f"Error en comparación de palabras para {artist_name}: {str(e)}")
                    
                    # Pausa entre resultados
                    self._rate_limit_pause()
                    
                except Exception as e:
                    self.logger.warning(f"Error procesando resultado de Discogs para {artist_name}: {str(e)}")
                    continue
            
            # Si no hay coincidencias buenas, usar el primer resultado
            if not best_artist and results_list:
                try:
                    best_artist = self.discogs.artist(results_list[0].id)
                    artist_url = f"https://www.discogs.com/artist/{best_artist.id}"
                except Exception as e:
                    self.logger.warning(f"Error obteniendo artista de Discogs para {artist_name}: {str(e)}")
            
            # Obtener los datos adicionales del mejor artista encontrado
            if best_artist:
                try:
                    # Obtener aliases
                    if hasattr(best_artist, 'aliases') and best_artist.aliases:
                        try:
                            aliases_list = [alias.name for alias in best_artist.aliases]
                            aliases = ", ".join(aliases_list)
                        except Exception as e:
                            self.logger.warning(f"Error procesando aliases para {artist_name}: {str(e)}")
                    
                    # Obtener grupos
                    if hasattr(best_artist, 'groups') and best_artist.groups:
                        try:
                            groups_list = [group.name for group in best_artist.groups]
                            member_of = ", ".join(groups_list)
                        except Exception as e:
                            self.logger.warning(f"Error procesando grupos para {artist_name}: {str(e)}")
                except Exception as e:
                    self.logger.warning(f"Error obteniendo datos adicionales de Discogs para {artist_name}: {str(e)}")
            
            return artist_url, aliases, member_of
                
        except Exception as e:
            self.logger.error(f"Discogs artist search error for {artist_name}: {str(e)}")
        
        return None, None, None


    def _get_discogs_album_url(self, artist_name: str, album_name: str) -> tuple:
        """Obtiene la URL del álbum en Discogs y datos de producción con enfoque robusto ante errores de tipo"""
        if not self.discogs:
            return None, None, None, None, None
        
        try:
            # Intentar diferentes estrategias de búsqueda
            search_strategies = [
                f'"{artist_name}" - "{album_name}"',  # Búsqueda exacta con comillas
                f'{artist_name} - {album_name}',      # Formato estándar artista - álbum
                f'{artist_name} {album_name}'         # Simple combinación
            ]
            
            best_result = None
            highest_score = 0
            
            for strategy in search_strategies:
                try:
                    results = self.discogs.search(strategy, type='release')
                    
                    if not results:
                        continue
                        
                    # Convertir a lista para evitar problemas con slices
                    try:
                        results_list = list(results)[:3]  # Convertir a lista y tomar los primeros 3
                    except Exception as e:
                        self.logger.warning(f"Error al convertir resultados para {strategy}: {str(e)}")
                        results_list = []
                        # Intento alternativo: acceder al primer resultado
                        if len(results) > 0:
                            try:
                                results_list = [results[0]]
                            except Exception:
                                continue
                    
                    for result in results_list:
                        try:
                            # Obtener detalles completos del lanzamiento
                            release = self.discogs.release(result.id)
                            
                            # Normalizar nombres para comparación
                            album_name_norm = album_name.lower().strip()
                            result_title_norm = release.title.lower().strip()
                            
                            # Determinar artista del resultado
                            result_artist = None
                            if hasattr(release, 'artists') and release.artists:
                                result_artist = release.artists[0].name.lower().strip()
                            
                            # Calcular puntuación sin usar división
                            title_score = 0
                            artist_score = 0
                            
                            # Puntuar título
                            if album_name_norm == result_title_norm:
                                title_score = 100  # Coincidencia exacta
                            elif album_name_norm in result_title_norm:
                                title_score = 80  # Contiene el nombre completo
                            elif result_title_norm in album_name_norm:
                                title_score = 70  # Está contenido en el nombre
                            else:
                                # Comparación por palabras sin usar división
                                try:
                                    words_query = set(album_name_norm.split())
                                    words_result = set(result_title_norm.split())
                                    common_words = words_query.intersection(words_result)
                                    
                                    # Puntuar basado en palabras comunes sin división
                                    if len(common_words) == len(words_query):
                                        title_score = 90  # Todas las palabras de la consulta están en el resultado
                                    elif len(common_words) > 0:
                                        # Puntajes relativos sin usar división
                                        if len(words_query) <= 2 and len(common_words) == 1:
                                            title_score = 60  # Una palabra en común para consultas cortas
                                        elif len(common_words) > 1:
                                            title_score = 70  # Múltiples palabras en común
                                except Exception as e:
                                    self.logger.warning(f"Error en comparación de palabras para título: {str(e)}")
                            
                            # Puntuar artista
                            if result_artist:
                                artist_name_norm = artist_name.lower().strip()
                                if artist_name_norm == result_artist:
                                    artist_score = 100  # Coincidencia exacta
                                elif artist_name_norm in result_artist:
                                    artist_score = 80  # Contiene el nombre completo
                                elif result_artist in artist_name_norm:
                                    artist_score = 70  # Está contenido en el nombre
                                else:
                                    # Comparación por palabras sin usar división
                                    try:
                                        words_artist_query = set(artist_name_norm.split())
                                        words_artist_result = set(result_artist.split())
                                        common_artist_words = words_artist_query.intersection(words_artist_result)
                                        
                                        # Puntuar basado en palabras comunes sin división
                                        if len(common_artist_words) == len(words_artist_query):
                                            artist_score = 90  # Todas las palabras de la consulta están en el resultado
                                        elif len(common_artist_words) > 0:
                                            # Puntajes relativos sin usar división
                                            if len(words_artist_query) <= 2 and len(common_artist_words) == 1:
                                                artist_score = 60  # Una palabra en común para consultas cortas
                                            elif len(common_artist_words) > 1:
                                                artist_score = 70  # Múltiples palabras en común
                                    except Exception as e:
                                        self.logger.warning(f"Error en comparación de palabras para artista: {str(e)}")
                            
                            # Calcular puntuación combinada sin usar división
                            # 60% título (0.6) y 40% artista (0.4)
                            # Simplificado a: (6*título + 4*artista) / 10
                            score = (6 * title_score + 4 * artist_score) // 10
                            
                            if score > highest_score:
                                highest_score = score
                                best_result = release
                                
                            # Si encontramos una coincidencia muy buena, terminar
                            if score >= 90:
                                break
                                
                            # Pausar para evitar rate limiting
                            self._rate_limit_pause()
                        except Exception as e:
                            self.logger.warning(f"Error procesando resultado de Discogs para {album_name}: {str(e)}")
                            continue
                
                except Exception as e:
                    self.logger.warning(f"Error en estrategia de búsqueda '{strategy}': {str(e)}")
                    continue
                    
                # Si ya encontramos una coincidencia buena, no probar más estrategias
                if highest_score >= 85:
                    break
                    
                # Pausa entre estrategias
                self._rate_limit_pause()
            
            # Extraer datos de producción del mejor resultado
            album_url = None
            producers = None
            engineers = None
            mastering_engineers = None
            credits_json = None
            
            if best_result and highest_score > 60:  # Umbral para considerar una coincidencia aceptable
                album_url = f"https://www.discogs.com/release/{best_result.id}"
                
                # Extraer información de créditos
                try:
                    if hasattr(best_result, 'credits') and best_result.credits:
                        # Diccionario para agrupar por roles
                        credits_dict = {}
                        producers_list = []
                        engineers_list = []
                        mastering_list = []
                        
                        for credit in best_result.credits:
                            if hasattr(credit, 'name') and hasattr(credit, 'role'):
                                name = credit.name
                                role = credit.role.lower()
                                
                                # Agregar al diccionario de créditos
                                if role not in credits_dict:
                                    credits_dict[role] = []
                                if name not in credits_dict[role]:
                                    credits_dict[role].append(name)
                                
                                # Agrupar por categorías específicas
                                if 'produc' in role:
                                    if name not in producers_list:
                                        producers_list.append(name)
                                elif 'engineer' in role and 'master' not in role:
                                    if name not in engineers_list:
                                        engineers_list.append(name)
                                elif 'master' in role:
                                    if name not in mastering_list:
                                        mastering_list.append(name)
                        
                        # Convertir a texto separado por comas
                        if producers_list:
                            producers = ", ".join(producers_list)
                        if engineers_list:
                            engineers = ", ".join(engineers_list)
                        if mastering_list:
                            mastering_engineers = ", ".join(mastering_list)
                        
                        # Guardar diccionario completo como JSON
                        # Guardar diccionario completo como JSON
                    try:
                        import json
                        credits_json = json.dumps(credits_dict)
                    except Exception as e:
                        self.logger.warning(f"Error al convertir créditos a JSON para {album_name}: {str(e)}")
                
                except Exception as e:
                    self.logger.warning(f"Error procesando créditos de Discogs para {album_name}: {str(e)}")
            
                return album_url, producers, engineers, mastering_engineers, credits_json
            elif results_list:
                # Si no hay buena coincidencia pero hay resultados, usar el primero
                try:
                    first_release = self.discogs.release(results_list[0].id)
                    album_url = f"https://www.discogs.com/release/{first_release.id}"
                    # Intentar extraer créditos también del primer resultado
                    try:
                        if hasattr(first_release, 'credits') and first_release.credits:
                            credits_dict = {}
                            producers_list = []
                            engineers_list = []
                            mastering_list = []
                            
                            for credit in first_release.credits:
                                if hasattr(credit, 'name') and hasattr(credit, 'role'):
                                    name = credit.name
                                    role = credit.role.lower()
                                    
                                    # Agregar al diccionario de créditos
                                    if role not in credits_dict:
                                        credits_dict[role] = []
                                    if name not in credits_dict[role]:
                                        credits_dict[role].append(name)
                                    
                                    # Agrupar por categorías específicas
                                    if 'produc' in role:
                                        if name not in producers_list:
                                            producers_list.append(name)
                                    elif 'engineer' in role and 'master' not in role:
                                        if name not in engineers_list:
                                            engineers_list.append(name)
                                    elif 'master' in role:
                                        if name not in mastering_list:
                                            mastering_list.append(name)
                            
                            # Convertir a texto separado por comas
                            if producers_list:
                                producers = ", ".join(producers_list)
                            if engineers_list:
                                engineers = ", ".join(engineers_list)
                            if mastering_list:
                                mastering_engineers = ", ".join(mastering_list)
                            
                            # Guardar diccionario completo como JSON
                            try:
                                import json
                                credits_json = json.dumps(credits_dict)
                            except Exception as e:
                                self.logger.warning(f"Error al convertir créditos a JSON para {album_name}: {str(e)}")
                        
                    except Exception as e:
                        self.logger.warning(f"Error procesando créditos de primer resultado para {album_name}: {str(e)}")
                    
                    return album_url, producers, engineers, mastering_engineers, credits_json
                except Exception as e:
                    self.logger.warning(f"Error procesando primer resultado para {album_name}: {str(e)}")
                    return f"https://www.discogs.com/release/{results_list[0].id}", None, None, None, None
        except Exception as e:
            self.logger.error(f"Discogs album search error for {album_name} by {artist_name}: {str(e)}")
        
        return None, None, None, None, None



    def _get_rateyourmusic_artist_url(self, artist_name: str) -> Optional[str]:
        """Genera la URL del artista en RateYourMusic"""
        if not self.rateyourmusic_enabled:
            return None
            
        # RateYourMusic no tiene API, así que generamos la URL directamente
        artist_slug = artist_name.lower().replace(' ', '-')
        # Eliminar caracteres especiales
        artist_slug = re.sub(r'[^a-z0-9-]', '', artist_slug)
        return f"https://rateyourmusic.com/artist/{artist_slug}"
    
    def _get_rateyourmusic_album_url(self, artist_name: str, album_name: str) -> Optional[str]:
        """Genera la URL del álbum en RateYourMusic"""
        if not self.rateyourmusic_enabled:
            return None
            
        # RateYourMusic no tiene API, así que generamos la URL directamente
        artist_slug = artist_name.lower().replace(' ', '-')
        album_slug = album_name.lower().replace(' ', '-')
        # Eliminar caracteres especiales
        artist_slug = re.sub(r'[^a-z0-9-]', '', artist_slug)
        album_slug = re.sub(r'[^a-z0-9-]', '', album_slug)
        return f"https://rateyourmusic.com/release/album/{artist_slug}/{album_slug}/"





def main(config=None):
    if config is None:
        parser = argparse.ArgumentParser(description='enlaces_artista_album')
        parser.add_argument('--config', required=True, help='Archivo de configuración')
        args = parser.parse_args()

        # Cargar configuración
        with open(args.config, 'r') as f:
            config_data = json.load(f)

        # Combinar configuraciones
        config = {}
        config.update(config_data.get("common", {}))
        config.update(config_data.get("enlaces_artista_album", {}))
    
    # Imprimir configuración para depuración
    print("Configuración final:")
    print(json.dumps(config, indent=2))

    # Crear instancia de MusicLinksManager
    manager = MusicLinksManager(config)

    # Resto del código original...
    if config.get('artist'):
        mbid = manager._get_musicbrainz_artist_mbid(config['artist'])
        if mbid:
            print(mbid)
        else:
            print("None")

    if config.get('summary_only'):
        counts = manager.get_table_counts()
        missing_mbids = manager.count_missing_mbids()

        print("Table Record Counts:")
        for table, count in counts.items():
            print(f"{table.capitalize()}: {count}")

        print("\nMissing MBIDs:")
        for table, count in missing_mbids.items():
            print(f"{table.capitalize()}: {count}")
    else:
        manager.update_links(
            days_threshold=config.get('days', 30),
            force_update=config.get('force_update', False),
            recent_only=not config.get('older_only', False),
            missing_only=config.get('missing_only', False),
        )

if __name__ == "__main__":
    main()