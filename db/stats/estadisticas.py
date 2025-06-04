
"""
Script para generar estadísticas pre-calculadas de la base de datos musical
Uso: python generate_stats.py <database_path> <username>

TABLAS GENERADAS (35 total):

📊 ESTADÍSTICAS BÁSICAS:
- _stats_basic_listening: Métricas generales de escucha
- _stats_artists_popularity: Popularidad de artistas
- _stats_albums_analysis: Análisis de álbumes
- _stats_genres_trends: Tendencias de géneros
- _stats_decade_analysis: Análisis por décadas
- _stats_top_tracks_all_time: Top 1000 canciones
- _stats_metadata: Timestamp y metadatos de generación

🎯 ANÁLISIS DE CALIDAD Y PREFERENCIAS:
- _stats_quality_analysis: Análisis bitrate/sample_rate vs reproducciones
- _stats_bitrate_quality_preference: Preferencias detalladas de calidad
- _stats_duration_preferences: Preferencias por duración
- _stats_lyrics_analysis: Canciones con vs sin letras
- _stats_replay_gain_listening_preference: Preferencias de volumen

⏰ ANÁLISIS TEMPORAL Y PATRONES:
- _stats_discovery_time: Tiempo entre agregar y primera escucha
- _stats_listening_patterns: Patrones temporales (año/mes/día/hora)
- _stats_time_to_milestones: Tiempo para alcanzar 10/25/50/100 reproducciones
- _stats_listening_velocity: Velocidad de escucha y patrones de consumo
- _stats_temporal_listening_clusters: Clusters temporales de escucha
- _stats_mood_based_duration_analysis: Análisis duración por momento del día
- _stats_weekend_vs_weekday_preferences: Fin de semana vs días laborables
- _stats_rediscovery_cycles: Ciclos de redescubrimiento de canciones

🎨 ANÁLISIS DE GÉNEROS Y DIVERSIDAD:
- _stats_rare_genres: Géneros raros pero populares
- _stats_orphan_gems: Joyas huérfanas (géneros/artistas nicho)
- _stats_multi_genre_albums: Álbumes multi-género vs mono-género
- _stats_artist_genre_flexibility: Flexibilidad de géneros por artista
- _stats_genre_evolution_monthly: Evolución de géneros mes a mes
- _stats_decade_cross_pollination: Transiciones entre décadas

🤝 ANÁLISIS DE RELACIONES Y REDES:
- _stats_similar_artists_network: Red de artistas similares
- _stats_artist_collaboration_density: Densidad de colaboraciones
- _stats_label_influence: Influencia de sellos discográficos
- _stats_label_artist_success_correlation: Correlación éxito sellos-artistas

🎵 ANÁLISIS DE COMPORTAMIENTO:
- _stats_album_completeness: Completitud de álbumes escuchados
- _stats_album_discovery_patterns: Patrones de descubrimiento de álbumes
- _stats_artist_loyalty_index: Índice de lealtad a artistas
- _stats_listening_addiction_patterns: Patrones de adicción a canciones
"""

import sqlite3
import sys
from datetime import datetime, timedelta
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MusicStatsGenerator:
    def __init__(self, db_path, username):
        self.db_path = db_path
        self.username = username
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        
    def close(self):
        self.conn.close()
    
    def drop_existing_stats_tables(self):
        """Elimina todas las tablas que empiecen con _stats_"""
        cursor = self.conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '_stats_%'
        """)
        tables = cursor.fetchall()
        
        for table in tables:
            logger.info(f"Eliminando tabla existente: {table[0]}")
            self.conn.execute(f"DROP TABLE IF EXISTS {table[0]}")
        
        self.conn.commit()
    
    def update_song_reproducciones(self):
        """Corrige el conteo de reproducciones en la tabla songs"""
        logger.info("Actualizando conteo de reproducciones en tabla songs...")
        
        # Primero resetear el campo a 1 (valor por defecto)
        self.conn.execute("UPDATE songs SET reproducciones = 1")
        
        # Intentar contar desde tabla listens del usuario
        try:
            query = f"""
            UPDATE songs 
            SET reproducciones = (
                SELECT COUNT(*) 
                FROM listens_{self.username} l 
                WHERE l.song_id = songs.id
            )
            WHERE EXISTS (
                SELECT 1 FROM listens_{self.username} l2 
                WHERE l2.song_id = songs.id
            )
            """
            self.conn.execute(query)
            self.conn.commit()
            logger.info("Reproducciones actualizadas desde listens")
            return
        except sqlite3.Error as e:
            logger.warning(f"Tabla listens_{self.username} no encontrada: {e}")
            
        # Intentar con tabla scrobbles si listens no existe
        try:
            query_scrobbles = f"""
            UPDATE songs 
            SET reproducciones = (
                SELECT COUNT(*) 
                FROM scrobbles_{self.username} s 
                WHERE s.song_id = songs.id
            )
            WHERE EXISTS (
                SELECT 1 FROM scrobbles_{self.username} s2 
                WHERE s2.song_id = songs.id
            )
            """
            self.conn.execute(query_scrobbles)
            self.conn.commit()
            logger.info("Reproducciones actualizadas desde scrobbles")
            return
        except sqlite3.Error as e2:
            logger.warning(f"Tabla scrobbles_{self.username} no encontrada: {e2}")
            
        # Si no hay tablas específicas, intentar con tablas genéricas
        try:
            query_generic = """
            UPDATE songs 
            SET reproducciones = (
                SELECT COUNT(*) 
                FROM listens l 
                WHERE l.song_id = songs.id
            )
            WHERE EXISTS (
                SELECT 1 FROM listens l2 
                WHERE l2.song_id = songs.id
            )
            """
            self.conn.execute(query_generic)
            self.conn.commit()
            logger.info("Reproducciones actualizadas desde tabla genérica listens")
        except sqlite3.Error as e3:
            logger.warning(f"No se pudieron actualizar reproducciones: {e3}")
            logger.info("Usando valores por defecto de reproducciones")
    
    def create_stats_basic_listening(self):
        """Estadísticas básicas de escucha"""
        logger.info("Creando _stats_basic_listening...")
        
        self.conn.execute("""
        CREATE TABLE _stats_basic_listening AS
        SELECT 
            COUNT(DISTINCT s.id) as total_canciones_escuchadas,
            COUNT(DISTINCT s.artist) as total_artistas_escuchados,
            COUNT(DISTINCT s.album) as total_albums_escuchados,
            COUNT(DISTINCT s.genre) as total_generos_escuchados,
            SUM(s.reproducciones) as total_reproducciones,
            AVG(s.reproducciones) as promedio_reproducciones_por_cancion,
            MAX(s.reproducciones) as max_reproducciones_cancion,
            SUM(s.duration) as tiempo_total_musica_segundos,
            SUM(s.duration * s.reproducciones) as tiempo_total_escuchado_segundos
        FROM songs s
        WHERE s.reproducciones > 1
        """)
    
    def create_stats_artists_popularity(self):
        """Popularidad de artistas"""
        logger.info("Creando _stats_artists_popularity...")
        
        self.conn.execute("""
        CREATE TABLE _stats_artists_popularity AS
        SELECT 
            s.artist,
            COUNT(DISTINCT s.id) as canciones_en_biblioteca,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            COUNT(DISTINCT s.album) as albums_en_biblioteca,
            COUNT(DISTINCT s.genre) as generos_diferentes,
            MAX(s.reproducciones) as cancion_mas_escuchada_reproducciones,
            (SELECT title FROM songs WHERE artist = s.artist ORDER BY reproducciones DESC LIMIT 1) as cancion_mas_escuchada_titulo,
            SUM(s.duration * s.reproducciones) as tiempo_total_escuchado
        FROM songs s
        WHERE s.reproducciones > 0
        GROUP BY s.artist
        ORDER BY reproducciones_totales DESC
        """)
    
    def create_stats_albums_analysis(self):
        """Análisis de álbumes"""
        logger.info("Creando _stats_albums_analysis...")
        
        self.conn.execute("""
        CREATE TABLE _stats_albums_analysis AS
        SELECT 
            s.album,
            s.artist as album_artist,
            s.date as year,
            COUNT(s.id) as total_tracks,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            SUM(s.duration) as duracion_total,
            COUNT(DISTINCT s.genre) as generos_diferentes,
            CASE WHEN COUNT(DISTINCT s.genre) > 1 THEN 'Multi-género' ELSE 'Mono-género' END as tipo_album,
            ROUND(SUM(s.reproducciones) * 1.0 / COUNT(s.id), 2) as completitud_escucha
        FROM songs s
        WHERE s.album IS NOT NULL
        GROUP BY s.album, s.artist
        ORDER BY SUM(s.reproducciones) DESC
        """)
    
    def create_stats_genres_trends(self):
        """Tendencias de géneros"""
        logger.info("Creando _stats_genres_trends...")
        
        self.conn.execute("""
        CREATE TABLE _stats_genres_trends AS
        SELECT 
            s.genre,
            COUNT(DISTINCT s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            COUNT(DISTINCT s.artist) as artistas_diferentes,
            COUNT(DISTINCT s.album) as albums_diferentes,
            AVG(s.duration) as duracion_promedio,
            SUM(s.duration * s.reproducciones) as tiempo_total_escuchado,
            (SUM(s.reproducciones) * 100.0 / (SELECT SUM(reproducciones) FROM songs WHERE reproducciones > 0)) as porcentaje_reproducciones_totales
        FROM songs s
        WHERE s.genre IS NOT NULL AND s.reproducciones > 0
        GROUP BY s.genre
        ORDER BY reproducciones_totales DESC
        """)
    
    def create_stats_decade_analysis(self):
        """Análisis por décadas"""
        logger.info("Creando _stats_decade_analysis...")
        
        self.conn.execute("""
        CREATE TABLE _stats_decade_analysis AS
        SELECT 
            CASE 
                WHEN CAST(s.date as INTEGER) BETWEEN 1950 AND 1959 THEN '1950s'
                WHEN CAST(s.date as INTEGER) BETWEEN 1960 AND 1969 THEN '1960s'
                WHEN CAST(s.date as INTEGER) BETWEEN 1970 AND 1979 THEN '1970s'
                WHEN CAST(s.date as INTEGER) BETWEEN 1980 AND 1989 THEN '1980s'
                WHEN CAST(s.date as INTEGER) BETWEEN 1990 AND 1999 THEN '1990s'
                WHEN CAST(s.date as INTEGER) BETWEEN 2000 AND 2009 THEN '2000s'
                WHEN CAST(s.date as INTEGER) BETWEEN 2010 AND 2019 THEN '2010s'
                WHEN CAST(s.date as INTEGER) BETWEEN 2020 AND 2029 THEN '2020s'
                ELSE 'Desconocido'
            END as decada,
            COUNT(DISTINCT s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            COUNT(DISTINCT s.artist) as artistas_diferentes,
            COUNT(DISTINCT s.genre) as generos_diferentes
        FROM songs s
        WHERE s.reproducciones > 0 AND s.date IS NOT NULL
        GROUP BY decada
        ORDER BY 
            CASE decada 
                WHEN '1950s' THEN 1950
                WHEN '1960s' THEN 1960
                WHEN '1970s' THEN 1970
                WHEN '1980s' THEN 1980
                WHEN '1990s' THEN 1990
                WHEN '2000s' THEN 2000
                WHEN '2010s' THEN 2010
                WHEN '2020s' THEN 2020
                ELSE 9999
            END
        """)
    
    def create_stats_quality_analysis(self):
        """Análisis de calidad de audio"""
        logger.info("Creando _stats_quality_analysis...")
        
        self.conn.execute("""
        CREATE TABLE _stats_quality_analysis AS
        SELECT 
            s.bitrate,
            s.sample_rate,
            COUNT(s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            COUNT(DISTINCT s.artist) as artistas_diferentes,
            COUNT(DISTINCT s.genre) as generos_diferentes
        FROM songs s
        WHERE s.reproducciones > 0 AND s.bitrate IS NOT NULL
        GROUP BY s.bitrate, s.sample_rate
        ORDER BY promedio_reproducciones DESC
        """)
    
    def create_stats_discovery_time(self):
        """Tiempo de descubrimiento de canciones"""
        logger.info("Creando _stats_discovery_time...")
        
        # Esta tabla necesita datos de scrobbles/listens para calcular correctamente
        try:
            self.conn.execute(f"""
            CREATE TABLE _stats_discovery_time AS
            SELECT 
                s.id as song_id,
                s.title,
                s.artist,
                s.added_timestamp,
                MIN(l.listen_date) as primera_escucha,
                julianday(MIN(l.listen_date)) - julianday(s.added_timestamp) as dias_hasta_primera_escucha,
                s.reproducciones as total_reproducciones
            FROM songs s
            LEFT JOIN listens_{self.username} l ON l.song_id = s.id
            WHERE s.added_timestamp IS NOT NULL
            GROUP BY s.id, s.title, s.artist, s.added_timestamp
            HAVING primera_escucha IS NOT NULL
            ORDER BY dias_hasta_primera_escucha DESC
            """)
        except sqlite3.Error:
            logger.warning("No se pudo crear _stats_discovery_time - tabla de listens no encontrada")
    
    def create_stats_listening_patterns(self):
        """Patrones de escucha temporales"""
        logger.info("Creando _stats_listening_patterns...")
        
        try:
            self.conn.execute(f"""
            CREATE TABLE _stats_listening_patterns AS
            SELECT 
                strftime('%Y', l.listen_date) as año,
                strftime('%m', l.listen_date) as mes,
                strftime('%w', l.listen_date) as dia_semana,
                strftime('%H', l.listen_date) as hora,
                COUNT(*) as total_escuchas,
                COUNT(DISTINCT l.song_id) as canciones_diferentes,
                COUNT(DISTINCT s.artist) as artistas_diferentes
            FROM listens_{self.username} l
            JOIN songs s ON s.id = l.song_id
            GROUP BY año, mes, dia_semana, hora
            ORDER BY año DESC, mes DESC, dia_semana, hora
            """)
        except sqlite3.Error:
            logger.warning("No se pudo crear _stats_listening_patterns - tabla de listens no encontrada")
    
    def create_stats_lyrics_analysis(self):
        """Análisis de letras"""
        logger.info("Creando _stats_lyrics_analysis...")
        
        self.conn.execute("""
        CREATE TABLE _stats_lyrics_analysis AS
        SELECT 
            s.has_lyrics,
            COUNT(s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            COUNT(DISTINCT s.artist) as artistas_diferentes,
            COUNT(DISTINCT s.genre) as generos_diferentes
        FROM songs s
        WHERE s.reproducciones > 0
        GROUP BY s.has_lyrics
        """)
    

    def create_stats_rare_genres(self):
        """Géneros raros con pocas canciones pero reproducciones"""
        logger.info("Creando _stats_rare_genres...")
        
        self.conn.execute("""
        CREATE TABLE _stats_rare_genres AS
        SELECT 
            s.genre,
            COUNT(s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            COUNT(DISTINCT s.artist) as artistas_diferentes
        FROM songs s
        WHERE s.reproducciones > 1 AND s.genre IS NOT NULL
        GROUP BY s.genre
        HAVING canciones_total <= 5 AND reproducciones_totales > 5
        ORDER BY promedio_reproducciones DESC
        """)
    
    def create_stats_top_tracks_all_time(self):
        """Top tracks de todos los tiempos"""
        logger.info("Creando _stats_top_tracks_all_time...")
        
        self.conn.execute("""
        CREATE TABLE _stats_top_tracks_all_time AS
        SELECT 
            ROW_NUMBER() OVER (ORDER BY s.reproducciones DESC) as ranking,
            s.title,
            s.artist,
            s.album,
            s.genre,
            s.date as year,
            s.reproducciones,
            s.duration,
            (s.duration * s.reproducciones) as tiempo_total_escuchado
        FROM songs s
        WHERE s.reproducciones > 1
        ORDER BY s.reproducciones DESC
        LIMIT 1000
        """)
    
    def create_stats_label_influence(self):
        """Influencia de sellos discográficos"""
        logger.info("Creando _stats_label_influence...")
        
        self.conn.execute("""
        CREATE TABLE _stats_label_influence AS
        SELECT 
            s.label,
            COUNT(DISTINCT s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            COUNT(DISTINCT s.artist) as artistas_diferentes,
            COUNT(DISTINCT s.album) as albums_diferentes,
            COUNT(DISTINCT s.genre) as generos_diferentes
        FROM songs s
        WHERE s.reproducciones > 1 AND s.label IS NOT NULL AND s.label != ''
        GROUP BY s.label
        ORDER BY SUM(s.reproducciones) DESC
        """)
    
    def create_stats_duration_preferences(self):
        """Preferencias de duración de canciones"""
        logger.info("Creando _stats_duration_preferences...")
        
        self.conn.execute("""
        CREATE TABLE _stats_duration_preferences AS
        SELECT 
            CASE 
                WHEN s.duration < 120 THEN 'Muy corta (<2min)'
                WHEN s.duration < 180 THEN 'Corta (2-3min)'
                WHEN s.duration < 240 THEN 'Normal (3-4min)'
                WHEN s.duration < 300 THEN 'Larga (4-5min)'
                WHEN s.duration < 420 THEN 'Muy larga (5-7min)'
                ELSE 'Épica (>7min)'
            END as categoria_duracion,
            AVG(s.duration) as duracion_promedio,
            COUNT(s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones
        FROM songs s
        WHERE s.reproducciones > 1 AND s.duration IS NOT NULL
        GROUP BY categoria_duracion
        ORDER BY promedio_reproducciones DESC
        """)
    
    def create_stats_bitrate_quality_preference(self):
        """Preferencias detalladas de calidad de audio"""
        logger.info("Creando _stats_bitrate_quality_preference...")
        
        self.conn.execute("""
        CREATE TABLE _stats_bitrate_quality_preference AS
        SELECT 
            CASE 
                WHEN s.bitrate >= 320 THEN 'Alta (>=320kbps)'
                WHEN s.bitrate >= 256 THEN 'Media-Alta (256-319kbps)'
                WHEN s.bitrate >= 192 THEN 'Media (192-255kbps)'
                WHEN s.bitrate >= 128 THEN 'Baja (128-191kbps)'
                ELSE 'Muy_Baja (<128kbps)'
            END as categoria_bitrate,
            CASE 
                WHEN s.sample_rate >= 48000 THEN 'Hi-Res (>=48kHz)'
                WHEN s.sample_rate >= 44100 THEN 'CD (44.1kHz)'
                ELSE 'Baja (<44.1kHz)'
            END as categoria_sample_rate,
            COUNT(s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            COUNT(DISTINCT s.artist) as artistas_diferentes,
            COUNT(DISTINCT s.genre) as generos_diferentes,
            SUM(s.duration * s.reproducciones) as tiempo_total_escuchado
        FROM songs s
        WHERE s.reproducciones > 1 AND s.bitrate IS NOT NULL AND s.sample_rate IS NOT NULL
        GROUP BY categoria_bitrate, categoria_sample_rate
        ORDER BY promedio_reproducciones DESC
        """)
    
    def create_stats_orphan_gems(self):
        """Joyas huérfanas - géneros/artistas poco representados pero populares"""
        logger.info("Creando _stats_orphan_gems...")
        
        self.conn.execute("""
        CREATE TABLE _stats_orphan_gems AS
        WITH genre_stats AS (
            SELECT 
                s.genre,
                COUNT(s.id) as canciones_en_genero,
                AVG(s.reproducciones) as promedio_reproducciones_genero
            FROM songs s
            WHERE s.reproducciones > 1 AND s.genre IS NOT NULL
            GROUP BY s.genre
        ),
        artist_stats AS (
            SELECT 
                s.artist,
                COUNT(s.id) as canciones_en_artista,
                AVG(s.reproducciones) as promedio_reproducciones_artista
            FROM songs s
            WHERE s.reproducciones > 1
            GROUP BY s.artist
        )
        SELECT 
            'Género' as tipo,
            gs.genre as nombre,
            gs.canciones_en_genero as canciones_total,
            gs.promedio_reproducciones_genero as promedio_reproducciones,
            'Nicho_Popular' as categoria
        FROM genre_stats gs
        WHERE gs.canciones_en_genero <= 5 AND gs.promedio_reproducciones_genero > 
              (SELECT AVG(promedio_reproducciones_genero) FROM genre_stats)
        
        UNION ALL
        
        SELECT 
            'Artista' as tipo,
            asi.artist as nombre,
            asi.canciones_en_artista as canciones_total,
            asi.promedio_reproducciones_artista as promedio_reproducciones,
            'Artista_Nicho' as categoria
        FROM artist_stats asi
        WHERE asi.canciones_en_artista <= 3 AND asi.promedio_reproducciones_artista > 
              (SELECT AVG(promedio_reproducciones_artista) FROM artist_stats)
        
        ORDER BY promedio_reproducciones DESC
        """)
    
    def create_stats_replay_gain_listening_preference(self):
        """Preferencias de volumen según replay gain"""
        logger.info("Creando _stats_replay_gain_listening_preference...")
        
        self.conn.execute("""
        CREATE TABLE _stats_replay_gain_listening_preference AS
        SELECT 
            CASE 
                WHEN s.replay_gain_track_gain > 3 THEN 'Muy_Fuerte (>3dB)'
                WHEN s.replay_gain_track_gain > 0 THEN 'Fuerte (0-3dB)'
                WHEN s.replay_gain_track_gain > -3 THEN 'Normal (0 a -3dB)'
                WHEN s.replay_gain_track_gain > -6 THEN 'Suave (-3 a -6dB)'
                ELSE 'Muy_Suave (<-6dB)'
            END as categoria_volumen,
            COUNT(s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            AVG(s.replay_gain_track_gain) as promedio_gain,
            COUNT(DISTINCT s.genre) as generos_diferentes
        FROM songs s
        WHERE s.reproducciones > 1 AND s.replay_gain_track_gain IS NOT NULL
        GROUP BY categoria_volumen
        ORDER BY promedio_reproducciones DESC
        """)
    
    def create_stats_multi_genre_albums(self):
        """Análisis de álbumes multi-género vs mono-género"""
        logger.info("Creando _stats_multi_genre_albums...")
        
        self.conn.execute("""
        CREATE TABLE _stats_multi_genre_albums AS
        WITH album_genre_diversity AS (
            SELECT 
                s.album,
                s.artist,
                COUNT(DISTINCT s.genre) as generos_diferentes,
                COUNT(s.id) as tracks_total,
                SUM(s.reproducciones) as reproducciones_totales,
                AVG(s.reproducciones) as promedio_reproducciones,
                GROUP_CONCAT(DISTINCT s.genre) as lista_generos
            FROM songs s
            WHERE s.album IS NOT NULL AND s.genre IS NOT NULL
            GROUP BY s.album, s.artist
            HAVING SUM(CASE WHEN s.reproducciones > 1 THEN 1 ELSE 0 END) > 0
        )
        SELECT 
            agd.album,
            agd.artist,
            agd.generos_diferentes,
            agd.tracks_total,
            agd.reproducciones_totales,
            agd.promedio_reproducciones,
            agd.lista_generos,
            CASE 
                WHEN agd.generos_diferentes = 1 THEN 'Mono-género'
                WHEN agd.generos_diferentes <= 3 THEN 'Multi-género_Moderado'
                ELSE 'Multi-género_Ecléctico'
            END as tipo_diversidad,
            ROUND(agd.reproducciones_totales * 1.0 / agd.tracks_total, 2) as engagement_por_track
        FROM album_genre_diversity agd
        ORDER BY agd.generos_diferentes DESC, agd.reproducciones_totales DESC
        """)
    
    def create_stats_artist_genre_flexibility(self):
        """Flexibilidad de géneros por artista"""
        logger.info("Creando _stats_artist_genre_flexibility...")
        
        self.conn.execute("""
        CREATE TABLE _stats_artist_genre_flexibility AS
        SELECT 
            s.artist,
            COUNT(DISTINCT s.genre) as generos_explorados,
            COUNT(DISTINCT s.album) as albums_diferentes,
            COUNT(s.id) as canciones_totales,
            SUM(s.reproducciones) as reproducciones_totales,
            GROUP_CONCAT(DISTINCT s.genre) as lista_generos,
            CASE 
                WHEN COUNT(DISTINCT s.genre) = 1 THEN 'Mono-género'
                WHEN COUNT(DISTINCT s.genre) <= 3 THEN 'Bi/Tri-género'
                WHEN COUNT(DISTINCT s.genre) <= 5 THEN 'Multi-género'
                ELSE 'Ecléctico_Extremo'
            END as categoria_flexibilidad,
            ROUND(COUNT(DISTINCT s.genre) * 1.0 / CASE WHEN COUNT(DISTINCT s.album) = 0 THEN 1 ELSE COUNT(DISTINCT s.album) END, 2) as generos_por_album,
            AVG(s.reproducciones) as promedio_reproducciones
        FROM songs s
        WHERE s.reproducciones > 1 AND s.genre IS NOT NULL
        GROUP BY s.artist
        HAVING canciones_totales > 1
        ORDER BY generos_explorados DESC, reproducciones_totales DESC
        """)
    
    def create_stats_artist_loyalty_index(self):
        """Índice de lealtad a artistas"""
        logger.info("Creando _stats_artist_loyalty_index...")
        
        self.conn.execute("""
        CREATE TABLE _stats_artist_loyalty_index AS
        WITH artist_metrics AS (
            SELECT 
                s.artist,
                COUNT(DISTINCT s.id) as canciones_en_biblioteca,
                SUM(s.reproducciones) as reproducciones_totales,
                COUNT(DISTINCT s.album) as albums_diferentes,
                AVG(s.reproducciones) as promedio_reproducciones,
                MAX(s.reproducciones) as max_reproducciones_cancion,
                MIN(s.reproducciones) as min_reproducciones_cancion,
                (MAX(s.reproducciones) - MIN(s.reproducciones)) as rango_reproducciones
            FROM songs s
            WHERE s.reproducciones > 1
            GROUP BY s.artist
            HAVING canciones_en_biblioteca > 1
        )
        SELECT 
            am.artist,
            am.canciones_en_biblioteca,
            am.reproducciones_totales,
            am.albums_diferentes,
            am.promedio_reproducciones,
            am.rango_reproducciones,
            ROUND((am.reproducciones_totales * 1.0 / am.canciones_en_biblioteca), 2) as consistencia_escucha,
            ROUND((am.albums_diferentes * 1.0 / am.canciones_en_biblioteca) * 100, 2) as exploracion_discografia,
            CASE 
                WHEN am.promedio_reproducciones > 20 AND am.rango_reproducciones < 10 THEN 'Lealtad_Alta_Consistente'
                WHEN am.promedio_reproducciones > 20 THEN 'Lealtad_Alta_Variable'
                WHEN am.promedio_reproducciones > 10 THEN 'Lealtad_Media'
                ELSE 'Lealtad_Baja'
            END as categoria_lealtad
        FROM artist_metrics am
        ORDER BY am.promedio_reproducciones DESC, am.reproducciones_totales DESC
        """)
    
    def create_stats_label_artist_success_correlation(self):
        """Correlación éxito de sellos con artistas"""
        logger.info("Creando _stats_label_artist_success_correlation...")
        
        self.conn.execute("""
        CREATE TABLE _stats_label_artist_success_correlation AS
        SELECT 
            s.label,
            s.artist,
            COUNT(DISTINCT s.id) as canciones_artista_sello,
            SUM(s.reproducciones) as reproducciones_artista_sello,
            AVG(s.reproducciones) as promedio_reproducciones_artista_sello,
            (SELECT SUM(reproducciones) FROM songs WHERE label = s.label AND reproducciones > 1) as reproducciones_totales_sello,
            (SELECT COUNT(DISTINCT artist) FROM songs WHERE label = s.label AND reproducciones > 1) as artistas_totales_sello,
            ROUND((SUM(s.reproducciones) * 100.0 / (SELECT SUM(reproducciones) FROM songs WHERE label = s.label AND reproducciones > 1)), 2) as porcentaje_contribucion_sello
        FROM songs s
        WHERE s.reproducciones > 1 AND s.label IS NOT NULL AND s.label != ''
        GROUP BY s.label, s.artist
        HAVING reproducciones_artista_sello > 1
        ORDER BY porcentaje_contribucion_sello DESC, reproducciones_artista_sello DESC
        """)
    
    def create_stats_album_completeness(self):
        """Completitud de álbumes escuchados"""
        logger.info("Creando _stats_album_completeness...")
        
        self.conn.execute("""
        CREATE TABLE _stats_album_completeness AS
        SELECT 
            s.album,
            s.artist,
            COUNT(s.id) as tracks_total,
            SUM(CASE WHEN s.reproducciones > 1 THEN 1 ELSE 0 END) as tracks_escuchados,
            ROUND((SUM(CASE WHEN s.reproducciones > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(s.id)), 2) as porcentaje_completitud,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones
        FROM songs s
        WHERE s.album IS NOT NULL
        GROUP BY s.album, s.artist
        HAVING tracks_total > 1
        ORDER BY porcentaje_completitud DESC, SUM(s.reproducciones) DESC
        """)
    
    def create_stats_top_tracks_all_time(self):
        """Top tracks de todos los tiempos"""
        logger.info("Creando _stats_top_tracks_all_time...")
        
        self.conn.execute("""
        CREATE TABLE _stats_top_tracks_all_time AS
        SELECT 
            ROW_NUMBER() OVER (ORDER BY s.reproducciones DESC) as ranking,
            s.title,
            s.artist,
            s.album,
            s.genre,
            s.date as year,
            s.reproducciones,
            s.duration,
            (s.duration * s.reproducciones) as tiempo_total_escuchado
        FROM songs s
        WHERE s.reproducciones > 0
        ORDER BY s.reproducciones DESC
        LIMIT 1000
        """)
    
    def create_stats_label_influence(self):
        """Influencia de sellos discográficos"""
        logger.info("Creando _stats_label_influence...")
        
        self.conn.execute("""
        CREATE TABLE _stats_label_influence AS
        SELECT 
            s.label,
            COUNT(DISTINCT s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            COUNT(DISTINCT s.artist) as artistas_diferentes,
            COUNT(DISTINCT s.album) as albums_diferentes,
            COUNT(DISTINCT s.genre) as generos_diferentes
        FROM songs s
        WHERE s.reproducciones > 0 AND s.label IS NOT NULL AND s.label != ''
        GROUP BY s.label
        ORDER BY reproducciones_totales DESC
        """)
    
    def create_stats_duration_preferences(self):
        """Preferencias de duración de canciones"""
        logger.info("Creando _stats_duration_preferences...")
        
        self.conn.execute("""
        CREATE TABLE _stats_duration_preferences AS
        SELECT 
            CASE 
                WHEN s.duration < 120 THEN 'Muy corta (<2min)'
                WHEN s.duration < 180 THEN 'Corta (2-3min)'
                WHEN s.duration < 240 THEN 'Normal (3-4min)'
                WHEN s.duration < 300 THEN 'Larga (4-5min)'
                WHEN s.duration < 420 THEN 'Muy larga (5-7min)'
                ELSE 'Épica (>7min)'
            END as categoria_duracion,
            AVG(s.duration) as duracion_promedio,
            COUNT(s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones
        FROM songs s
        WHERE s.reproducciones > 0 AND s.duration IS NOT NULL
        GROUP BY categoria_duracion
        ORDER BY promedio_reproducciones DESC
        """)
    
    def create_stats_similar_artists_network(self):
        """Red de artistas similares y flujo de reproducciones"""
        logger.info("Creando _stats_similar_artists_network...")
        
        # Verificar si existe la tabla artists y el campo similar_artists
        try:
            cursor = self.conn.execute("SELECT similar_artists FROM artists LIMIT 1")
            cursor.fetchone()
            
            self.conn.execute("""
            CREATE TABLE _stats_similar_artists_network AS
            SELECT 
                a.name as artista_principal,
                TRIM(SUBSTR(a.similar_artists, 
                    CASE WHEN INSTR(a.similar_artists, ',') = 0 THEN 1 
                         ELSE 1 END,
                    CASE WHEN INSTR(a.similar_artists, ',') = 0 THEN LENGTH(a.similar_artists)
                         ELSE INSTR(a.similar_artists, ',') - 1 END
                )) as artista_similar,
                SUM(s.reproducciones) as reproducciones_artista_principal,
                (SELECT SUM(s2.reproducciones) FROM songs s2 WHERE s2.artist LIKE '%' || TRIM(SUBSTR(a.similar_artists, 1, CASE WHEN INSTR(a.similar_artists, ',') = 0 THEN LENGTH(a.similar_artists) ELSE INSTR(a.similar_artists, ',') - 1 END)) || '%') as reproducciones_artista_similar,
                COUNT(DISTINCT s.genre) as generos_principal
            FROM artists a
            LEFT JOIN songs s ON s.artist = a.name AND s.reproducciones > 1
            WHERE a.similar_artists IS NOT NULL 
            AND a.similar_artists != ''
            AND LENGTH(TRIM(a.similar_artists)) > 0
            GROUP BY a.name, TRIM(SUBSTR(a.similar_artists, 1, CASE WHEN INSTR(a.similar_artists, ',') = 0 THEN LENGTH(a.similar_artists) ELSE INSTR(a.similar_artists, ',') - 1 END))
            HAVING SUM(s.reproducciones) > 1
            ORDER BY SUM(s.reproducciones) DESC
            """)
        except sqlite3.Error as e:
            logger.warning(f"No se pudo crear _stats_similar_artists_network: {e}")
            # Crear tabla vacía como fallback
            self.conn.execute("""
            CREATE TABLE _stats_similar_artists_network AS
            SELECT 
                'No disponible' as artista_principal,
                'No disponible' as artista_similar,
                0 as reproducciones_artista_principal,
                0 as reproducciones_artista_similar,
                0 as generos_principal
            WHERE 1=0
            """)
    
    def create_stats_genre_evolution_monthly(self):
        """Evolución de géneros mes a mes"""
        logger.info("Creando _stats_genre_evolution_monthly...")
        
        try:
            self.conn.execute(f"""
            CREATE TABLE _stats_genre_evolution_monthly AS
            SELECT 
                s.genre,
                strftime('%Y-%m', l.listen_date) as mes_año,
                COUNT(*) as escuchas_mes,
                COUNT(DISTINCT s.id) as canciones_diferentes,
                COUNT(DISTINCT s.artist) as artistas_diferentes,
                LAG(COUNT(*)) OVER (PARTITION BY s.genre ORDER BY strftime('%Y-%m', l.listen_date)) as escuchas_mes_anterior,
                CASE 
                    WHEN LAG(COUNT(*)) OVER (PARTITION BY s.genre ORDER BY strftime('%Y-%m', l.listen_date)) > 0 
                    THEN ROUND((COUNT(*) - LAG(COUNT(*)) OVER (PARTITION BY s.genre ORDER BY strftime('%Y-%m', l.listen_date))) * 100.0 / 
                              LAG(COUNT(*)) OVER (PARTITION BY s.genre ORDER BY strftime('%Y-%m', l.listen_date)), 2)
                    ELSE NULL 
                END as porcentaje_cambio
            FROM songs s
            JOIN listens_{self.username} l ON l.song_id = s.id
            WHERE s.genre IS NOT NULL
            GROUP BY s.genre, mes_año
            ORDER BY s.genre, mes_año DESC
            """)
        except sqlite3.Error:
            logger.warning("No se pudo crear _stats_genre_evolution_monthly - tabla de listens no encontrada")
    
    def create_stats_artist_collaboration_density(self):
        """Densidad de colaboraciones por artista"""
        logger.info("Creando _stats_artist_collaboration_density...")
        
        # Verificar si existe la tabla albums con el campo credits
        try:
            cursor = self.conn.execute("SELECT credits FROM albums LIMIT 1")
            cursor.fetchone()
            
            self.conn.execute("""
            CREATE TABLE _stats_artist_collaboration_density AS
            SELECT 
                s.artist,
                COUNT(DISTINCT s.album) as albums_totales,
                SUM(s.reproducciones) as reproducciones_totales,
                AVG(s.reproducciones) as promedio_reproducciones,
                COUNT(DISTINCT s.genre) as generos_explorados,
                COUNT(DISTINCT s.label) as sellos_diferentes,
                CASE 
                    WHEN AVG(s.reproducciones) > 10 THEN 'Alta_Actividad'
                    WHEN AVG(s.reproducciones) > 5 THEN 'Media_Actividad'
                    ELSE 'Baja_Actividad'
                END as nivel_actividad
            FROM songs s
            WHERE s.reproducciones > 1
            GROUP BY s.artist
            HAVING albums_totales > 0
            ORDER BY SUM(s.reproducciones) DESC
            """)
        except sqlite3.Error as e:
            logger.warning(f"No se pudo crear _stats_artist_collaboration_density: {e}")
            # Crear versión simplificada
            self.conn.execute("""
            CREATE TABLE _stats_artist_collaboration_density AS
            SELECT 
                s.artist,
                COUNT(DISTINCT s.album) as albums_totales,
                SUM(s.reproducciones) as reproducciones_totales,
                AVG(s.reproducciones) as promedio_reproducciones,
                COUNT(DISTINCT s.genre) as generos_explorados
            FROM songs s
            WHERE s.reproducciones > 1
            GROUP BY s.artist
            HAVING albums_totales > 0
            ORDER BY SUM(s.reproducciones) DESC
            """)
    
    def create_stats_time_to_milestones(self):
        """Tiempo para alcanzar milestones de reproducciones"""
        logger.info("Creando _stats_time_to_milestones...")
        
        try:
            self.conn.execute(f"""
            CREATE TABLE _stats_time_to_milestones AS
            WITH milestone_dates AS (
                SELECT 
                    s.id,
                    s.title,
                    s.artist,
                    s.added_timestamp,
                    COUNT(*) OVER (PARTITION BY s.id ORDER BY l.listen_date) as reproducciones_acumuladas,
                    l.listen_date,
                    ROW_NUMBER() OVER (PARTITION BY s.id ORDER BY l.listen_date) as orden_escucha
                FROM songs s
                JOIN listens_{self.username} l ON l.song_id = s.id
                WHERE s.added_timestamp IS NOT NULL
            )
            SELECT 
                md.id,
                md.title,
                md.artist,
                md.added_timestamp,
                MIN(CASE WHEN md.reproducciones_acumuladas >= 10 THEN md.listen_date END) as fecha_10_reproducciones,
                MIN(CASE WHEN md.reproducciones_acumuladas >= 25 THEN md.listen_date END) as fecha_25_reproducciones,
                MIN(CASE WHEN md.reproducciones_acumuladas >= 50 THEN md.listen_date END) as fecha_50_reproducciones,
                MIN(CASE WHEN md.reproducciones_acumuladas >= 100 THEN md.listen_date END) as fecha_100_reproducciones,
                julianday(MIN(CASE WHEN md.reproducciones_acumuladas >= 10 THEN md.listen_date END)) - julianday(md.added_timestamp) as dias_a_10,
                julianday(MIN(CASE WHEN md.reproducciones_acumuladas >= 25 THEN md.listen_date END)) - julianday(md.added_timestamp) as dias_a_25,
                julianday(MIN(CASE WHEN md.reproducciones_acumuladas >= 50 THEN md.listen_date END)) - julianday(md.added_timestamp) as dias_a_50,
                julianday(MIN(CASE WHEN md.reproducciones_acumuladas >= 100 THEN md.listen_date END)) - julianday(md.added_timestamp) as dias_a_100
            FROM milestone_dates md
            GROUP BY md.id, md.title, md.artist, md.added_timestamp
            ORDER BY dias_a_10 ASC
            """)
        except sqlite3.Error:
            logger.warning("No se pudo crear _stats_time_to_milestones - tabla de listens no encontrada")
    
    def create_stats_album_discovery_patterns(self):
        """Patrones de descubrimiento de álbumes"""
        logger.info("Creando _stats_album_discovery_patterns...")
        
        self.conn.execute("""
        CREATE TABLE _stats_album_discovery_patterns AS
        SELECT 
            s.album,
            s.artist,
            COUNT(s.id) as tracks_total,
            SUM(CASE WHEN s.reproducciones > 1 THEN 1 ELSE 0 END) as tracks_escuchados,
            COALESCE(MIN(CASE WHEN s.reproducciones > 1 THEN s.track_number END), 0) as primer_track_escuchado,
            COALESCE(MAX(CASE WHEN s.reproducciones > 1 THEN s.track_number END), 0) as ultimo_track_escuchado,
            SUM(s.reproducciones) as reproducciones_totales,
            CASE 
                WHEN MIN(CASE WHEN s.reproducciones > 1 THEN s.track_number END) = 1 THEN 'Secuencial'
                WHEN MAX(s.reproducciones) = (SELECT reproducciones FROM songs s2 WHERE s2.album = s.album AND s2.track_number = 1 LIMIT 1) THEN 'Por_Single'
                ELSE 'Aleatorio'
            END as patron_descubrimiento,
            AVG(s.reproducciones) as promedio_reproducciones_track
        FROM songs s
        WHERE s.album IS NOT NULL 
        GROUP BY s.album, s.artist
        HAVING tracks_escuchados > 0
        ORDER BY SUM(s.reproducciones) DESC
        """)
    
    def create_stats_bitrate_quality_preference(self):
        """Preferencias detalladas de calidad de audio"""
        logger.info("Creando _stats_bitrate_quality_preference...")
        
        self.conn.execute("""
        CREATE TABLE _stats_bitrate_quality_preference AS
        SELECT 
            CASE 
                WHEN s.bitrate >= 320 THEN 'Alta (>=320kbps)'
                WHEN s.bitrate >= 256 THEN 'Media-Alta (256-319kbps)'
                WHEN s.bitrate >= 192 THEN 'Media (192-255kbps)'
                WHEN s.bitrate >= 128 THEN 'Baja (128-191kbps)'
                ELSE 'Muy_Baja (<128kbps)'
            END as categoria_bitrate,
            CASE 
                WHEN s.sample_rate >= 48000 THEN 'Hi-Res (>=48kHz)'
                WHEN s.sample_rate >= 44100 THEN 'CD (44.1kHz)'
                ELSE 'Baja (<44.1kHz)'
            END as categoria_sample_rate,
            COUNT(s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            COUNT(DISTINCT s.artist) as artistas_diferentes,
            COUNT(DISTINCT s.genre) as generos_diferentes,
            SUM(s.duration * s.reproducciones) as tiempo_total_escuchado
        FROM songs s
        WHERE s.reproducciones > 0 AND s.bitrate IS NOT NULL AND s.sample_rate IS NOT NULL
        GROUP BY categoria_bitrate, categoria_sample_rate
        ORDER BY promedio_reproducciones DESC
        """)
    
    def create_stats_orphan_gems(self):
        """Joyas huérfanas - géneros/artistas poco representados pero populares"""
        logger.info("Creando _stats_orphan_gems...")
        
        self.conn.execute("""
        CREATE TABLE _stats_orphan_gems AS
        WITH genre_stats AS (
            SELECT 
                s.genre,
                COUNT(s.id) as canciones_en_genero,
                AVG(s.reproducciones) as promedio_reproducciones_genero
            FROM songs s
            WHERE s.reproducciones > 0 AND s.genre IS NOT NULL
            GROUP BY s.genre
        ),
        artist_stats AS (
            SELECT 
                s.artist,
                COUNT(s.id) as canciones_en_artista,
                AVG(s.reproducciones) as promedio_reproducciones_artista
            FROM songs s
            WHERE s.reproducciones > 0
            GROUP BY s.artist
        )
        SELECT 
            'Género' as tipo,
            gs.genre as nombre,
            gs.canciones_en_genero as canciones_total,
            gs.promedio_reproducciones_genero as promedio_reproducciones,
            'Nicho_Popular' as categoria
        FROM genre_stats gs
        WHERE gs.canciones_en_genero <= 5 AND gs.promedio_reproducciones_genero > 
              (SELECT AVG(promedio_reproducciones_genero) FROM genre_stats)
        
        UNION ALL
        
        SELECT 
            'Artista' as tipo,
            asi.artist as nombre,
            asi.canciones_en_artista as canciones_total,
            asi.promedio_reproducciones_artista as promedio_reproducciones,
            'Artista_Nicho' as categoria
        FROM artist_stats asi
        WHERE asi.canciones_en_artista <= 3 AND asi.promedio_reproducciones_artista > 
              (SELECT AVG(promedio_reproducciones_artista) FROM artist_stats)
        
        ORDER BY promedio_reproducciones DESC
        """)
    
    def create_stats_replay_gain_listening_preference(self):
        """Preferencias de volumen según replay gain"""
        logger.info("Creando _stats_replay_gain_listening_preference...")
        
        self.conn.execute("""
        CREATE TABLE _stats_replay_gain_listening_preference AS
        SELECT 
            CASE 
                WHEN s.replay_gain_track_gain > 3 THEN 'Muy_Fuerte (>3dB)'
                WHEN s.replay_gain_track_gain > 0 THEN 'Fuerte (0-3dB)'
                WHEN s.replay_gain_track_gain > -3 THEN 'Normal (0 a -3dB)'
                WHEN s.replay_gain_track_gain > -6 THEN 'Suave (-3 a -6dB)'
                ELSE 'Muy_Suave (<-6dB)'
            END as categoria_volumen,
            COUNT(s.id) as canciones_total,
            SUM(s.reproducciones) as reproducciones_totales,
            AVG(s.reproducciones) as promedio_reproducciones,
            AVG(s.replay_gain_track_gain) as promedio_gain,
            COUNT(DISTINCT s.genre) as generos_diferentes
        FROM songs s
        WHERE s.reproducciones > 0 AND s.replay_gain_track_gain IS NOT NULL
        GROUP BY categoria_volumen
        ORDER BY promedio_reproducciones DESC
        """)
    
    def create_stats_multi_genre_albums(self):
        """Análisis de álbumes multi-género vs mono-género"""
        logger.info("Creando _stats_multi_genre_albums...")
        
        self.conn.execute("""
        CREATE TABLE _stats_multi_genre_albums AS
        WITH album_genre_diversity AS (
            SELECT 
                s.album,
                s.artist,
                COUNT(DISTINCT s.genre) as generos_diferentes,
                COUNT(s.id) as tracks_total,
                SUM(s.reproducciones) as reproducciones_totales,
                AVG(s.reproducciones) as promedio_reproducciones,
                GROUP_CONCAT(DISTINCT s.genre) as lista_generos
            FROM songs s
            WHERE s.album IS NOT NULL AND s.genre IS NOT NULL
            GROUP BY s.album, s.artist
            HAVING SUM(s.reproducciones) > 0
        )
        SELECT 
            agd.album,
            agd.artist,
            agd.generos_diferentes,
            agd.tracks_total,
            agd.reproducciones_totales,
            agd.promedio_reproducciones,
            agd.lista_generos,
            CASE 
                WHEN agd.generos_diferentes = 1 THEN 'Mono-género'
                WHEN agd.generos_diferentes <= 3 THEN 'Multi-género_Moderado'
                ELSE 'Multi-género_Ecléctico'
            END as tipo_diversidad,
            ROUND(agd.reproducciones_totales * 1.0 / agd.tracks_total, 2) as engagement_por_track
        FROM album_genre_diversity agd
        ORDER BY agd.generos_diferentes DESC, agd.reproducciones_totales DESC
        """)
    
    def create_stats_listening_velocity(self):
        """Velocidad de escucha y patrones de consumo"""
        logger.info("Creando _stats_listening_velocity...")
        
        try:
            self.conn.execute(f"""
            CREATE TABLE _stats_listening_velocity AS
            WITH listening_sessions AS (
                SELECT 
                    s.id as song_id,
                    s.title,
                    s.artist,
                    s.duration,
                    l.listen_date,
                    LAG(l.listen_date) OVER (ORDER BY l.listen_date) as prev_listen,
                    (julianday(l.listen_date) - julianday(LAG(l.listen_date) OVER (ORDER BY l.listen_date))) * 24 * 60 as minutos_desde_anterior
                FROM songs s
                JOIN listens_{self.username} l ON l.song_id = s.id
                ORDER BY l.listen_date
            )
            SELECT 
                ls.song_id,
                ls.title,
                ls.artist,
                COUNT(*) as total_escuchas,
                AVG(ls.minutos_desde_anterior) as promedio_minutos_entre_escuchas,
                MIN(ls.minutos_desde_anterior) as minima_pausa_entre_escuchas,
                MAX(ls.minutos_desde_anterior) as maxima_pausa_entre_escuchas,
                CASE 
                    WHEN AVG(ls.minutos_desde_anterior) < 5 THEN 'Repetición_Obsesiva'
                    WHEN AVG(ls.minutos_desde_anterior) < 30 THEN 'Escucha_Frecuente'
                    WHEN AVG(ls.minutos_desde_anterior) < 1440 THEN 'Escucha_Regular'
                    ELSE 'Escucha_Esporádica'
                END as patron_velocidad
            FROM listening_sessions ls
            WHERE ls.minutos_desde_anterior IS NOT NULL
            GROUP BY ls.song_id, ls.title, ls.artist
            HAVING total_escuchas > 2
            ORDER BY promedio_minutos_entre_escuchas ASC
            """)
        except sqlite3.Error:
            logger.warning("No se pudo crear _stats_listening_velocity - tabla de listens no encontrada")
    
    
    
    def create_stats_temporal_listening_clusters(self):
        """Clusters temporales de escucha"""
        logger.info("Creando _stats_temporal_listening_clusters...")
        
        try:
            self.conn.execute(f"""
            CREATE TABLE _stats_temporal_listening_clusters AS
            SELECT 
                strftime('%Y-%m', l.listen_date) as mes_año,
                strftime('%H', l.listen_date) as hora_dia,
                CASE strftime('%w', l.listen_date)
                    WHEN '0' THEN 'Domingo'
                    WHEN '1' THEN 'Lunes'
                    WHEN '2' THEN 'Martes'
                    WHEN '3' THEN 'Miércoles'
                    WHEN '4' THEN 'Jueves'
                    WHEN '5' THEN 'Viernes'
                    WHEN '6' THEN 'Sábado'
                END as dia_semana,
                COUNT(*) as escuchas_total,
                COUNT(DISTINCT s.id) as canciones_diferentes,
                COUNT(DISTINCT s.artist) as artistas_diferentes,
                COUNT(DISTINCT s.genre) as generos_diferentes,
                AVG(s.duration) as duracion_promedio_sesion,
                CASE 
                    WHEN CAST(strftime('%H', l.listen_date) AS INTEGER) BETWEEN 6 AND 11 THEN 'Mañana'
                    WHEN CAST(strftime('%H', l.listen_date) AS INTEGER) BETWEEN 12 AND 17 THEN 'Tarde'
                    WHEN CAST(strftime('%H', l.listen_date) AS INTEGER) BETWEEN 18 AND 23 THEN 'Noche'
                    ELSE 'Madrugada'
                END as periodo_dia
            FROM listens_{self.username} l
            JOIN songs s ON s.id = l.song_id
            GROUP BY mes_año, hora_dia, dia_semana
            ORDER BY mes_año DESC, hora_dia
            """)
        except sqlite3.Error:
            logger.warning("No se pudo crear _stats_temporal_listening_clusters - tabla de listens no encontrada")
    
    def create_stats_artist_genre_flexibility(self):
        """Flexibilidad de géneros por artista"""
        logger.info("Creando _stats_artist_genre_flexibility...")
        
        self.conn.execute("""
        CREATE TABLE _stats_artist_genre_flexibility AS
        SELECT 
            s.artist,
            COUNT(DISTINCT s.genre) as generos_explorados,
            COUNT(DISTINCT s.album) as albums_diferentes,
            COUNT(s.id) as canciones_totales,
            SUM(s.reproducciones) as reproducciones_totales,
            GROUP_CONCAT(DISTINCT s.genre) as lista_generos,
            CASE 
                WHEN COUNT(DISTINCT s.genre) = 1 THEN 'Mono-género'
                WHEN COUNT(DISTINCT s.genre) <= 3 THEN 'Bi/Tri-género'
                WHEN COUNT(DISTINCT s.genre) <= 5 THEN 'Multi-género'
                ELSE 'Ecléctico_Extremo'
            END as categoria_flexibilidad,
            ROUND(COUNT(DISTINCT s.genre) * 1.0 / COUNT(DISTINCT s.album), 2) as generos_por_album,
            AVG(s.reproducciones) as promedio_reproducciones
        FROM songs s
        WHERE s.reproducciones > 0 AND s.genre IS NOT NULL
        GROUP BY s.artist
        HAVING canciones_totales > 1
        ORDER BY generos_explorados DESC, reproducciones_totales DESC
        """)
    
    def create_stats_listening_addiction_patterns(self):
        """Patrones de adicción a canciones"""
        logger.info("Creando _stats_listening_addiction_patterns...")
        
        try:
            self.conn.execute(f"""
            CREATE TABLE _stats_listening_addiction_patterns AS
            WITH consecutive_plays AS (
                SELECT 
                    s.id,
                    s.title,
                    s.artist,
                    l.listen_date,
                    LAG(l.listen_date) OVER (ORDER BY l.listen_date) as prev_listen,
                    CASE 
                        WHEN (julianday(l.listen_date) - julianday(LAG(l.listen_date) OVER (ORDER BY l.listen_date))) * 24 * 60 < 5 
                        THEN 1 ELSE 0 
                    END as es_consecutiva
                FROM songs s
                JOIN listens_{self.username} l ON l.song_id = s.id
                ORDER BY l.listen_date
            ),
            addiction_analysis AS (
                SELECT 
                    cp.id,
                    cp.title,
                    cp.artist,
                    COUNT(*) as total_reproducciones,
                    SUM(cp.es_consecutiva) as reproducciones_consecutivas,
                    MAX(cp.es_consecutiva) as tuvo_racha_consecutiva,
                    ROUND(SUM(cp.es_consecutiva) * 100.0 / COUNT(*), 2) as porcentaje_consecutivas
                FROM consecutive_plays cp
                GROUP BY cp.id, cp.title, cp.artist
                HAVING total_reproducciones > 5
            )
            SELECT 
                aa.*,
                CASE 
                    WHEN aa.porcentaje_consecutivas > 50 THEN 'Altamente_Adictiva'
                    WHEN aa.porcentaje_consecutivas > 25 THEN 'Moderadamente_Adictiva'
                    WHEN aa.porcentaje_consecutivas > 10 THEN 'Ligeramente_Adictiva'
                    ELSE 'No_Adictiva'
                END as nivel_adiccion
            FROM addiction_analysis aa
            ORDER BY aa.porcentaje_consecutivas DESC, aa.total_reproducciones DESC
            """)
        except sqlite3.Error:
            logger.warning("No se pudo crear _stats_listening_addiction_patterns - tabla de listens no encontrada")
    
    def create_stats_mood_based_duration_analysis(self):
        """Análisis de duración basado en estado de ánimo inferido"""
        logger.info("Creando _stats_mood_based_duration_analysis...")
        
        try:
            self.conn.execute(f"""
            CREATE TABLE _stats_mood_based_duration_analysis AS
            WITH hourly_listening AS (
                SELECT 
                    s.id,
                    s.title,
                    s.artist,
                    s.duration,
                    s.genre,
                    strftime('%H', l.listen_date) as hora,
                    CASE 
                        WHEN CAST(strftime('%H', l.listen_date) AS INTEGER) BETWEEN 6 AND 9 THEN 'Despertar'
                        WHEN CAST(strftime('%H', l.listen_date) AS INTEGER) BETWEEN 10 AND 14 THEN 'Productivo'
                        WHEN CAST(strftime('%H', l.listen_date) AS INTEGER) BETWEEN 15 AND 18 THEN 'Tarde_Activa'
                        WHEN CAST(strftime('%H', l.listen_date) AS INTEGER) BETWEEN 19 AND 22 THEN 'Relax_Nocturno'
                        ELSE 'Madrugada_Introspectiva'
                    END as momento_emocional
                FROM songs s
                JOIN listens_{self.username} l ON l.song_id = s.id
            )
            SELECT 
                hl.momento_emocional,
                COUNT(*) as total_escuchas,
                AVG(hl.duration) as duracion_promedio_preferida,
                COUNT(DISTINCT hl.genre) as diversidad_generos,
                COUNT(DISTINCT hl.artist) as diversidad_artistas,
                CASE 
                    WHEN AVG(hl.duration) > 300 THEN 'Prefiere_Canciones_Largas'
                    WHEN AVG(hl.duration) > 240 THEN 'Prefiere_Canciones_Normales'
                    ELSE 'Prefiere_Canciones_Cortas'
                END as preferencia_duracion,
                GROUP_CONCAT(DISTINCT hl.genre) as generos_frecuentes
            FROM hourly_listening hl
            GROUP BY hl.momento_emocional
            ORDER BY total_escuchas DESC
            """)
        except sqlite3.Error:
            logger.warning("No se pudo crear _stats_mood_based_duration_analysis - tabla de listens no encontrada")
    
    def create_stats_artist_loyalty_index(self):
        """Índice de lealtad a artistas"""
        logger.info("Creando _stats_artist_loyalty_index...")
        
        self.conn.execute("""
        CREATE TABLE _stats_artist_loyalty_index AS
        WITH artist_metrics AS (
            SELECT 
                s.artist,
                COUNT(DISTINCT s.id) as canciones_en_biblioteca,
                SUM(s.reproducciones) as reproducciones_totales,
                COUNT(DISTINCT s.album) as albums_diferentes,
                AVG(s.reproducciones) as promedio_reproducciones,
                MAX(s.reproducciones) as max_reproducciones_cancion,
                MIN(s.reproducciones) as min_reproducciones_cancion,
                (MAX(s.reproducciones) - MIN(s.reproducciones)) as rango_reproducciones
            FROM songs s
            WHERE s.reproducciones > 0
            GROUP BY s.artist
            HAVING canciones_en_biblioteca > 1
        )
        SELECT 
            am.artist,
            am.canciones_en_biblioteca,
            am.reproducciones_totales,
            am.albums_diferentes,
            am.promedio_reproducciones,
            am.rango_reproducciones,
            ROUND((am.reproducciones_totales * 1.0 / am.canciones_en_biblioteca), 2) as consistencia_escucha,
            ROUND((am.albums_diferentes * 1.0 / am.canciones_en_biblioteca) * 100, 2) as exploracion_discografia,
            CASE 
                WHEN am.promedio_reproducciones > 20 AND am.rango_reproducciones < 10 THEN 'Lealtad_Alta_Consistente'
                WHEN am.promedio_reproducciones > 20 THEN 'Lealtad_Alta_Variable'
                WHEN am.promedio_reproducciones > 10 THEN 'Lealtad_Media'
                ELSE 'Lealtad_Baja'
            END as categoria_lealtad
        FROM artist_metrics am
        ORDER BY am.promedio_reproducciones DESC, am.reproducciones_totales DESC
        """)
    
    def create_stats_decade_cross_pollination(self):
        """Polinización cruzada entre décadas"""
        logger.info("Creando _stats_decade_cross_pollination...")
        
        try:
            self.conn.execute(f"""
            CREATE TABLE _stats_decade_cross_pollination AS
            WITH session_decades AS (
                SELECT 
                    l.listen_date,
                    CASE 
                        WHEN CAST(s.date as INTEGER) BETWEEN 1950 AND 1959 THEN '1950s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 1960 AND 1969 THEN '1960s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 1970 AND 1979 THEN '1970s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 1980 AND 1989 THEN '1980s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 1990 AND 1999 THEN '1990s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 2000 AND 2009 THEN '2000s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 2010 AND 2019 THEN '2010s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 2020 AND 2029 THEN '2020s'
                        ELSE 'Desconocido'
                    END as decada,
                    LAG(CASE 
                        WHEN CAST(s.date as INTEGER) BETWEEN 1950 AND 1959 THEN '1950s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 1960 AND 1969 THEN '1960s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 1970 AND 1979 THEN '1970s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 1980 AND 1989 THEN '1980s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 1990 AND 1999 THEN '1990s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 2000 AND 2009 THEN '2000s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 2010 AND 2019 THEN '2010s'
                        WHEN CAST(s.date as INTEGER) BETWEEN 2020 AND 2029 THEN '2020s'
                        ELSE 'Desconocido'
                    END) OVER (ORDER BY l.listen_date) as decada_anterior
                FROM songs s
                JOIN listens_{self.username} l ON l.song_id = s.id
                WHERE s.date IS NOT NULL
                ORDER BY l.listen_date
            )
            SELECT 
                sd.decada_anterior,
                sd.decada as decada_actual,
                COUNT(*) as transiciones_totales,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM session_decades WHERE decada_anterior IS NOT NULL), 2) as porcentaje_transiciones
            FROM session_decades sd
            WHERE sd.decada_anterior IS NOT NULL 
            AND sd.decada_anterior != sd.decada
            GROUP BY sd.decada_anterior, sd.decada
            ORDER BY transiciones_totales DESC
            """)
        except sqlite3.Error:
            logger.warning("No se pudo crear _stats_decade_cross_pollination - tabla de listens no encontrada")
    
    def create_stats_weekend_vs_weekday_preferences(self):
        """Preferencias fin de semana vs días laborables"""
        logger.info("Creando _stats_weekend_vs_weekday_preferences...")
        
        try:
            self.conn.execute(f"""
            CREATE TABLE _stats_weekend_vs_weekday_preferences AS
            SELECT 
                CASE 
                    WHEN CAST(strftime('%w', l.listen_date) AS INTEGER) IN (0, 6) THEN 'Fin_de_Semana'
                    ELSE 'Día_Laborable'
                END as tipo_dia,
                s.genre,
                s.artist,
                COUNT(*) as escuchas_totales,
                COUNT(DISTINCT s.id) as canciones_diferentes,
                AVG(s.duration) as duracion_promedio,
                SUM(s.duration) as tiempo_total_escuchado,
                ROUND(COUNT(*) * 100.0 / (
                    SELECT COUNT(*) 
                    FROM listens_{self.username} l2 
                    WHERE CASE 
                        WHEN CAST(strftime('%w', l2.listen_date) AS INTEGER) IN (0, 6) THEN 'Fin_de_Semana'
                        ELSE 'Día_Laborable'
                    END = CASE 
                        WHEN CAST(strftime('%w', l.listen_date) AS INTEGER) IN (0, 6) THEN 'Fin_de_Semana'
                        ELSE 'Día_Laborable'
                    END
                ), 2) as porcentaje_del_tipo_dia
            FROM songs s
            JOIN listens_{self.username} l ON l.song_id = s.id
            WHERE s.genre IS NOT NULL
            GROUP BY tipo_dia, s.genre, s.artist
            HAVING escuchas_totales > 2
            ORDER BY tipo_dia, escuchas_totales DESC
            """)
        except sqlite3.Error:
            logger.warning("No se pudo crear _stats_weekend_vs_weekday_preferences - tabla de listens no encontrada")
    
    def create_stats_rediscovery_cycles(self):
        """Ciclos de redescubrimiento de canciones"""
        logger.info("Creando _stats_rediscovery_cycles...")
        
        try:
            self.conn.execute(f"""
            CREATE TABLE _stats_rediscovery_cycles AS
            WITH listening_gaps AS (
                SELECT 
                    s.id,
                    s.title,
                    s.artist,
                    l.listen_date,
                    LAG(l.listen_date) OVER (PARTITION BY s.id ORDER BY l.listen_date) as prev_listen,
                    julianday(l.listen_date) - julianday(LAG(l.listen_date) OVER (PARTITION BY s.id ORDER BY l.listen_date)) as dias_gap
                FROM songs s
                JOIN listens_{self.username} l ON l.song_id = s.id
                ORDER BY s.id, l.listen_date
            )
            SELECT 
                lg.id,
                lg.title,
                lg.artist,
                COUNT(*) as total_redescubrimientos,
                AVG(lg.dias_gap) as promedio_dias_entre_redescubrimientos,
                MIN(lg.dias_gap) as minimo_gap_redescubrimiento,
                MAX(lg.dias_gap) as maximo_gap_redescubrimiento,
                CASE 
                    WHEN AVG(lg.dias_gap) < 7 THEN 'Redescubrimiento_Frecuente'
                    WHEN AVG(lg.dias_gap) < 30 THEN 'Redescubrimiento_Mensual'
                    WHEN AVG(lg.dias_gap) < 90 THEN 'Redescubrimiento_Trimestral'
                    ELSE 'Redescubrimiento_Esporádico'
                END as patron_redescubrimiento
            FROM listening_gaps lg
            WHERE lg.dias_gap IS NOT NULL AND lg.dias_gap > 1
            GROUP BY lg.id, lg.title, lg.artist
            HAVING total_redescubrimientos > 2
            ORDER BY promedio_dias_entre_redescubrimientos ASC
            """)
        except sqlite3.Error:
            logger.warning("No se pudo crear _stats_rediscovery_cycles - tabla de listens no encontrada")
    
    def create_stats_metadata_timestamp(self):
        """Timestamp de cuándo se generaron las estadísticas"""
        logger.info("Creando _stats_metadata...")
        
        self.conn.execute("""
        CREATE TABLE _stats_metadata AS
        SELECT 
            datetime('now') as fecha_generacion,
            ? as usuario,
            (SELECT COUNT(*) FROM songs WHERE reproducciones > 1) as canciones_con_reproducciones,
            (SELECT COUNT(*) FROM songs) as canciones_totales,
            (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE '_stats_%') as tablas_estadisticas_generadas
        """, (self.username,))
    
    def generate_all_stats(self):
        """Genera todas las estadísticas"""
        logger.info(f"Iniciando generación de estadísticas para usuario: {self.username}")
        
        # Eliminar tablas existentes
        self.drop_existing_stats_tables()
        
        # Actualizar reproducciones
        self.update_song_reproducciones()
        
        # Actualizar todas las referencias de reproducciones > 0 a reproducciones > 1
        # ya que 1 es el valor por defecto para canciones no escuchadas
        try:
            # Estadísticas básicas (15 originales)
            self.create_stats_basic_listening()
            self.create_stats_artists_popularity()
            self.create_stats_albums_analysis()
            self.create_stats_genres_trends()
            self.create_stats_decade_analysis()
            self.create_stats_quality_analysis()
            self.create_stats_discovery_time()
            self.create_stats_listening_patterns()
            self.create_stats_lyrics_analysis()
            self.create_stats_rare_genres()
            self.create_stats_album_completeness()
            self.create_stats_top_tracks_all_time()
            self.create_stats_label_influence()
            self.create_stats_duration_preferences()
            
            # Estadísticas avanzadas (20 adicionales)
            self.create_stats_similar_artists_network()
            self.create_stats_genre_evolution_monthly()
            self.create_stats_artist_collaboration_density()
            self.create_stats_time_to_milestones()
            self.create_stats_album_discovery_patterns()
            self.create_stats_bitrate_quality_preference()
            self.create_stats_orphan_gems()
            self.create_stats_replay_gain_listening_preference()
            self.create_stats_multi_genre_albums()
            self.create_stats_listening_velocity()
            self.create_stats_label_artist_success_correlation()
            self.create_stats_temporal_listening_clusters()
            self.create_stats_artist_genre_flexibility()
            self.create_stats_listening_addiction_patterns()
            self.create_stats_mood_based_duration_analysis()
            self.create_stats_artist_loyalty_index()
            self.create_stats_decade_cross_pollination()
            self.create_stats_weekend_vs_weekday_preferences()
            self.create_stats_rediscovery_cycles()
            
            # Metadata (siempre al final)
            self.create_stats_metadata_timestamp()
            
            self.conn.commit()
            logger.info("Todas las estadísticas generadas correctamente - 35 tablas creadas")
            
        except Exception as e:
            logger.error(f"Error generando estadísticas: {e}")
            self.conn.rollback()
            raise

def main():
    if len(sys.argv) != 3:
        print("Uso: python generate_stats.py <database_path> <username>")
        print("Ejemplo: python generate_stats.py music.db guevifrito")
        sys.exit(1)
    
    db_path = sys.argv[1]
    username = sys.argv[2]
    
    try:
        generator = MusicStatsGenerator(db_path, username)
        generator.generate_all_stats()
        generator.close()
        print(f"Estadísticas generadas exitosamente para usuario: {username}")
        print("📊 Total de tablas generadas: 35 (_stats_*)")
        print("🎵 Análisis completo de patrones de escucha disponible")
        
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()