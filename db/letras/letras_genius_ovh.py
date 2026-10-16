import os
import sys
import logging
import sqlite3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base.db_connection import apply_pragmas
import argparse
import json
import time
import requests
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import lyricsgenius


sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import PROJECT_ROOT

# Adaptador personalizado para datetime
def adapt_datetime(dt):
    return dt.isoformat()

# Registrar el adaptador
sqlite3.register_adapter(datetime, adapt_datetime)


class MultiLyricsManager:
    def __init__(self, db_path, batch_size=1000, config=None):
        self.db_path = db_path
        self.batch_size = batch_size
        self.config = config or {}

        # Logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Configurar sesión HTTP con reintentos y timeouts mejorados
        self.session = self._create_session()

        # Genius API initialization (como backup)
        genius_token = self.config.get("genius_access_token")
        if genius_token:
            self.genius = lyricsgenius.Genius(genius_token, timeout=15, sleep_time=1.5)
            self.genius.verbose = False
        else:
            self.genius = None
            self.logger.warning("genius_access_token no encontrado en configuración. Genius no estará disponible como fuente de respaldo.")

        # Archivo de estado para pausar/continuar
        self.state_file = PROJECT_ROOT / '.content' / 'logs' / 'db' / 'lyrics_update_state.json'

        # Retry y backoff settings mejorados
        self.max_retries = 2
        self.retry_delay = 3  # segundos
        self.request_timeout = 20  # timeout aumentado a 20 segundos

        # Initialize database
        self.init_database()

    def _create_session(self):
        """Crea una sesión HTTP con reintentos automáticos y configuración robusta."""
        session = requests.Session()

        # Configurar reintentos automáticos
        retry_strategy = Retry(
            total=2,
            backoff_factor=2,  # Espera exponencial: 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_status=False  # No lanzar excepción en reintentos
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Headers comunes
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        return session

    def init_database(self):
        """Verifica y prepara la base de datos para almacenar letras."""
        conn = sqlite3.connect(self.db_path)
        apply_pragmas(conn)
        c = conn.cursor()

        # Verificar si la tabla lyrics existe
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lyrics'")
        if not c.fetchone():
            # Crear tabla de letras
            c.execute('''
                CREATE TABLE lyrics (
                    id INTEGER PRIMARY KEY,
                    track_id INTEGER UNIQUE,
                    lyrics TEXT,
                    source TEXT DEFAULT 'Genius',
                    last_updated TIMESTAMP,
                    FOREIGN KEY(track_id) REFERENCES songs(id)
                )
            ''')
            self.logger.info("Tabla 'lyrics' creada exitosamente")

        # Verificar si la columna has_lyrics existe en la tabla songs
        c.execute("PRAGMA table_info(songs)")
        columns = {col[1] for col in c.fetchall()}
        if 'has_lyrics' not in columns:
            c.execute("ALTER TABLE songs ADD COLUMN has_lyrics INTEGER DEFAULT 0")
            self.logger.info("Columna 'has_lyrics' añadida a la tabla 'songs'")

        # Verificar y recrear la tabla FTS para lyrics si es necesario
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lyrics_fts'")
        if c.fetchone():
            # Eliminar tablas FTS existentes que puedan estar mal configuradas
            try:
                c.execute("DROP TABLE IF EXISTS lyrics_fts")
                self.logger.info("Tabla 'lyrics_fts' eliminada para recreación")
            except sqlite3.Error as e:
                self.logger.warning(f"Error al eliminar tabla lyrics_fts: {str(e)}")

        # Crear tabla FTS correctamente
        try:
            c.execute('''
                CREATE VIRTUAL TABLE lyrics_fts USING fts5(
                    lyrics,
                    content='lyrics',
                    content_rowid='id'
                )
            ''')
            self.logger.info("Tabla FTS 'lyrics_fts' creada exitosamente")

            # Poblar la tabla FTS con los datos existentes
            c.execute('''
                INSERT INTO lyrics_fts(rowid, lyrics)
                SELECT id, lyrics FROM lyrics WHERE lyrics IS NOT NULL
            ''')
            self.logger.info("Datos existentes migrados a la tabla FTS")
        except sqlite3.Error as e:
            self.logger.warning(f"Error al crear tabla FTS: {str(e)}")

        conn.commit()
        conn.close()

    def get_lyrics_from_ovh(self, artist, title):
        """Intenta obtener letras de lyrics.ovh API - CORREGIDA."""
        base_url = "https://api.lyrics.ovh/v1"

        try:
            # Limpiar caracteres problemáticos y fechas del título
            clean_title = title
            # Eliminar fechas en formato (YYYY-MM-DD) del título
            import re
            clean_title = re.sub(r'\s*\(\d{4}-\d{2}-\d{2}\)\s*$', '', clean_title).strip()

            clean_artist = artist.replace('/', '').replace('\\', '').strip()
            clean_title = clean_title.replace('/', '').replace('\\', '').strip()

            url = f"{base_url}/{clean_artist}/{clean_title}"

            # Usar la sesión configurada con timeout aumentado
            response = self.session.get(url, timeout=self.request_timeout)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'lyrics' in data and data['lyrics']:
                        self.logger.info(f"✓ Letra encontrada en lyrics.ovh: {artist} - {clean_title}")
                        return data['lyrics'], "lyrics.ovh"
                except:
                    pass
            elif response.status_code == 404:
                self.logger.debug(f"Letra no encontrada en lyrics.ovh: {artist} - {clean_title}")

        except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout en lyrics.ovh: {artist} - {title}")
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"Error de conexión en lyrics.ovh: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error inesperado en lyrics.ovh: {str(e)}")

        return None, None

    def get_lyrics_from_lyricsgenius(self, artist, title):
        """Intenta obtener letras usando Genius API."""
        if not self.genius:
            return None, None

        # Limpiar fechas del título
        import re
        clean_title = re.sub(r'\s*\(\d{4}-\d{2}-\d{2}\)\s*$', '', title).strip()

        try:
            self.logger.debug(f"Buscando en Genius: {artist} - {clean_title}")
            song = self.genius.search_song(clean_title, artist)
            if song:
                self.logger.info(f"✓ Letra encontrada en Genius: {artist} - {clean_title}")
                return song.lyrics, "Genius"
            else:
                self.logger.debug(f"Letra no encontrada en Genius: {artist} - {clean_title}")
        except Exception as e:
            self.logger.error(f"Error al buscar en Genius para {artist} - {title}: {str(e)}")

        return None, None

    def get_lyrics_from_happi(self, artist, title):
        """Intenta obtener letras usando Happi API - DESHABILITADA (requiere plan de pago)."""
        # Happi API ya no es gratuita para letras
        return None, None

    def get_lyrics_from_musixmatch(self, artist, title):
        """Intenta obtener letras usando Musixmatch API - CORREGIDA según documentación."""
        musixmatch_key = self.config.get("musixmatch_api_key")
        if not musixmatch_key:
            return None, None

        # Limpiar fechas del título
        import re
        clean_title = re.sub(r'\s*\(\d{4}-\d{2}-\d{2}\)\s*$', '', title).strip()

        base_url = "https://api.musixmatch.com/ws/1.1"

        try:
            # Usar matcher.lyrics.get según documentación oficial
            search_url = f"{base_url}/matcher.lyrics.get"
            params = {
                "apikey": musixmatch_key,
                "q_track": clean_title,
                "q_artist": artist
            }

            response = self.session.get(search_url, params=params, timeout=self.request_timeout)

            if response.status_code == 200:
                data = response.json()

                # CORRECCIÓN: Verificar la estructura correcta según documentación
                # Estructura: data['message']['body']['lyrics']['lyrics_body']
                if isinstance(data, dict):
                    message = data.get('message', {})
                    if isinstance(message, dict):
                        header = message.get('header', {})
                        status_code = header.get('status_code', 0)

                        if status_code == 200:
                            body = message.get('body', {})
                            if isinstance(body, dict):
                                lyrics_data = body.get('lyrics', {})
                                if isinstance(lyrics_data, dict):
                                    lyrics_text = lyrics_data.get('lyrics_body', '')

                                    if lyrics_text:
                                        # Musixmatch API free incluye disclaimer al final
                                        disclaimer_idx = lyrics_text.find("******* This Lyrics is NOT")
                                        if disclaimer_idx > 0:
                                            lyrics_text = lyrics_text[:disclaimer_idx].strip()

                                        self.logger.info(f"✓ Letra encontrada en Musixmatch: {artist} - {clean_title}")
                                        return lyrics_text, "Musixmatch"
                        else:
                            self.logger.debug(f"Musixmatch status: {status_code} para {artist} - {clean_title}")

        except Exception as e:
            self.logger.error(f"Error accediendo a Musixmatch API para {artist} - {title}: {str(e)}")

        return None, None

    def get_song_lyrics(self, artist, title):
        """Busca la letra de una canción en múltiples fuentes."""
        # Limpiar el título y artista
        artist = artist.strip()
        title = title.strip()

        # Intentar con lyrics.ovh primero (sin API key, gratuito)
        lyrics, source = self.get_lyrics_from_ovh(artist, title)
        if lyrics:
            return lyrics, source

        # Intentar con Musixmatch (necesita API key)
        lyrics, source = self.get_lyrics_from_musixmatch(artist, title)
        if lyrics:
            return lyrics, source

        # Intentar con Genius como último recurso
        lyrics, source = self.get_lyrics_from_lyricsgenius(artist, title)
        if lyrics:
            return lyrics, source

        return None, None

    def save_state(self, song_ids, current_index, processed, success, force_update=False):
        """Guarda el estado actual del proceso para continuar más tarde."""
        state = {
            "song_ids": song_ids,
            "current_index": current_index,
            "processed": processed,
            "success": success,
            "force_update": force_update,
            "timestamp": datetime.now().isoformat()
        }

        # Usar un archivo diferente según el modo
        if force_update:
            state_file = f"{PROJECT_ROOT}/.content/logs/db/letras/lyrics_update_state_force.json"
        else:
            state_file = f"{PROJECT_ROOT}/.content/logs/db/letras/lyrics_update_state_normal.json"

        # Crear directorio si no existe
        os.makedirs(os.path.dirname(state_file), exist_ok=True)

        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Estado guardado: procesadas {processed} canciones, {success} exitosas")

    def load_state(self, force_update=False):
        """Carga el estado anterior si existe."""
        state_file = f"{PROJECT_ROOT}/.content/logs/db/letras/lyrics_update_state_force.json" if force_update else f"{PROJECT_ROOT}/.content/logs/db/letras/lyrics_update_state_normal.json"

        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                self.logger.info(f"Estado cargado: continuando desde canción {state['current_index']} de {len(state['song_ids'])}")
                return state
            except Exception as e:
                self.logger.error(f"Error cargando estado: {str(e)}")
        return None

    def update_lyrics(self, resume=True, force_update=False):
        """Actualiza las letras de las canciones en la base de datos."""
        state = None

        if resume and not force_update:
            state = self.load_state(force_update)

        if state:
            song_ids = state["song_ids"]
            current_index = state["current_index"]
            processed = state["processed"]
            success = state["success"]
            self.logger.info(f"Reanudando desde posición: {current_index}/{len(song_ids)}")
        else:
            # Obtener canciones para procesar
            conn = sqlite3.connect(self.db_path)
            apply_pragmas(conn)
            c = conn.cursor()

            if force_update:
                self.logger.info("MODO FORCE: Procesando TODAS las canciones")
                c.execute("""
                    SELECT s.id, s.artist, s.title
                    FROM songs s
                    LEFT JOIN artists a ON s.artist = a.name
                    WHERE s.artist IS NOT NULL AND s.title IS NOT NULL
                    ORDER BY a.total_albums DESC, s.added_timestamp DESC
                """)
            else:
                self.logger.info("MODO NORMAL: Procesando SOLO canciones SIN letras")
                # CORRECCIÓN: Filtrado más estricto
                c.execute("""
                    SELECT s.id, s.artist, s.title
                    FROM songs s
                    LEFT JOIN lyrics l ON s.id = l.track_id
                    LEFT JOIN artists a ON s.artist = a.name
                    WHERE l.track_id IS NULL
                    AND s.artist IS NOT NULL
                    AND s.title IS NOT NULL
                    ORDER BY a.total_albums DESC, s.added_timestamp DESC
                """)

            songs_to_update = c.fetchall()
            conn.close()

            if not songs_to_update:
                self.logger.info("✓ No hay canciones para procesar.")
                return

            self.logger.info(f"Se encontraron {len(songs_to_update)} canciones para procesar")

            song_ids = [(song_id, artist, title) for song_id, artist, title in songs_to_update]
            current_index = 0
            processed = 0
            success = 0

        total_songs = len(song_ids)
        sources_stats = {}
        not_found_count = 0

        conn = sqlite3.connect(self.db_path)
        apply_pragmas(conn)
        c = conn.cursor()

        error_log_path = PROJECT_ROOT / '.content' /'logs' / 'db' / 'lyrics_update_errors.log'
        os.makedirs(os.path.dirname(error_log_path), exist_ok=True)

        error_logger = logging.getLogger('error_log')
        error_logger.setLevel(logging.ERROR)
        error_handler = logging.FileHandler(error_log_path, encoding='utf-8')
        error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        error_handler.setFormatter(error_formatter)
        error_logger.addHandler(error_handler)

        try:
            batch_start = current_index

            for i in range(current_index, total_songs):
                song_id, artist, title = song_ids[i]

                try:
                    processed += 1

                    # Verificación de artista
                    if not artist:
                        c.execute("SELECT album_artist FROM songs WHERE id = ?", (song_id,))
                        album_artist_result = c.fetchone()
                        if album_artist_result and album_artist_result[0]:
                            artist = album_artist_result[0]

                    if not title or not artist:
                        error_logger.error(f"Falta información para song_id {song_id}")
                        continue

                    # CORRECCIÓN: Verificar si ya existe antes de buscar
                    if not force_update:
                        c.execute("SELECT id FROM lyrics WHERE track_id = ?", (song_id,))
                        if c.fetchone():
                            self.logger.debug(f"Canción {song_id} ya tiene letra, saltando...")
                            continue

                    lyrics, source = self.get_song_lyrics(artist, title)

                    if lyrics:
                        sources_stats[source] = sources_stats.get(source, 0) + 1

                        c.execute("""
                            INSERT OR REPLACE INTO lyrics (track_id, lyrics, source, last_updated)
                            VALUES (?, ?, ?, ?)
                        """, (song_id, lyrics, source, datetime.now()))

                        c.execute("SELECT id FROM lyrics WHERE track_id = ?", (song_id,))
                        lyrics_id_result = c.fetchone()
                        if lyrics_id_result:
                            lyrics_id = lyrics_id_result[0]

                            c.execute("""
                                UPDATE songs SET lyrics_id = ?, has_lyrics = 1
                                WHERE id = ?
                            """, (lyrics_id, song_id))

                        # Actualizar FTS
                        try:
                            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lyrics_fts'")
                            if c.fetchone():
                                c.execute("INSERT OR REPLACE INTO lyrics_fts(rowid, lyrics) VALUES(?, ?)",
                                    (lyrics_id, lyrics))
                        except sqlite3.Error as e:
                            self.logger.warning(f"Error actualizando FTS: {str(e)}")

                        conn.commit()
                        success += 1
                    else:
                        not_found_count += 1
                        error_logger.error(f"No encontrada: {artist} - {title}")

                except Exception as e:
                    error_logger.error(f"Error procesando {artist} - {title}: {str(e)}")
                    conn.rollback()

                # Progreso cada 10 canciones
                if processed % 10 == 0:
                    success_rate = (success / processed * 100) if processed > 0 else 0
                    self.logger.info(f"Progreso: {processed}/{total_songs} | {success} exitosas ({success_rate:.1f}%) | {not_found_count} no encontradas")
                    if sources_stats:
                        sources_log = ", ".join([f"{src}: {count}" for src, count in sources_stats.items()])
                        self.logger.info(f"Fuentes: {sources_log}")

                # Guardar estado después de cada lote
                if (i - batch_start + 1) >= self.batch_size:
                    self.save_state(song_ids, i + 1, processed, success, force_update)
                    self.logger.info(f"Lote completado. Continuará en próxima ejecución.")
                    break

        except KeyboardInterrupt:
            self.logger.info("Proceso interrumpido. Guardando estado...")
            self.save_state(song_ids, i, processed, success, force_update)

        finally:
            # Limpiar estado si terminamos
            if current_index + self.batch_size >= total_songs:
                state_file = f"{PROJECT_ROOT}/.content/logs/db/letras/lyrics_update_state_force.json" if force_update else f"{PROJECT_ROOT}/.content/logs/db/letras/lyrics_update_state_normal.json"
                if os.path.exists(state_file):
                    os.remove(state_file)

                success_rate = (success / processed * 100) if processed > 0 else 0
                self.logger.info(f"✓ PROCESO COMPLETO: {processed} procesadas, {success} exitosas ({success_rate:.1f}%)")
                self.logger.info(f"No encontradas: {not_found_count}")
                if sources_stats:
                    sources_log = ", ".join([f"{src}: {count}" for src, count in sources_stats.items()])
                    self.logger.info(f"Fuentes utilizadas: {sources_log}")

            error_logger.removeHandler(error_handler)
            error_handler.close()
            conn.close()

def main(config=None):
    if config is None:
        parser = argparse.ArgumentParser(description='Actualizador de letras para biblioteca musical')
        parser.add_argument('--db_path', help='Ruta a la base de datos SQLite')
        parser.add_argument('--force-update', action='store_true', help='Forzar actualización de todas las letras')
        parser.add_argument('--batch-size', type=int, default=1000, help='Número de canciones por lote')
        parser.add_argument('--no-resume', action='store_true', help='No continuar desde el último punto')
        parser.add_argument('--config', help='Archivo de configuración JSON')

        args = parser.parse_args()

        final_config = {}

        if args.config:
            with open(args.config, 'r') as f:
                json_config = json.load(f)
            final_config.update(json_config.get("common", {}))
            final_config.update(json_config.get("letras/letras_genius_ovh", {}))

        arg_dict = vars(args)
        for arg_name, arg_value in arg_dict.items():
            if arg_value is not None and arg_name != 'config':
                config_key = arg_name.replace('-', '_')
                final_config[config_key] = arg_value
    else:
        final_config = config

    # Verificar parámetros requeridos
    required_params = ['db_path']
    missing_params = [param for param in required_params if param not in final_config]
    if missing_params:
        print(f"Error: Faltan parámetros: {', '.join(missing_params)}")
        sys.exit(1)

    # Conversión de tipos
    if 'batch_size' in final_config and isinstance(final_config['batch_size'], str):
        try:
            final_config['batch_size'] = int(final_config['batch_size'])
        except ValueError:
            final_config['batch_size'] = 1000

    # Valores predeterminados
    final_config.setdefault('batch_size', 1000)
    final_config.setdefault('force_update', False)
    final_config.setdefault('no_resume', False)

    # Iniciar proceso
    try:
        manager = MultiLyricsManager(
            final_config['db_path'],
            batch_size=final_config['batch_size'],
            config=final_config
        )

        print("\n" + "="*60)
        print("ACTUALIZADOR DE LETRAS - MULTI-API")
        print(f"- Force update: {'SÍ' if final_config['force_update'] else 'NO'}")
        print(f"- Resume: {'SÍ' if not final_config['no_resume'] else 'NO'}")
        print("="*60 + "\n")

        manager.update_lyrics(
            resume=not final_config['no_resume'],
            force_update=final_config['force_update']
        )
    except KeyboardInterrupt:
        print("\n✗ Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
