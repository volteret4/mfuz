#!/usr/bin/env python3
"""
Script para crear una copia de seguridad parcial de la base de datos musical.
Extrae solo los registros con origen específico y toda la información relacionada.
"""

import sqlite3
import os
import sys
import argparse
from datetime import datetime
import json

class MusicDatabaseBackup:
    def __init__(self, source_db_path, backup_db_path, origen='local'):
        self.source_db_path = source_db_path
        self.backup_db_path = backup_db_path
        self.origen = origen
        self.source_conn = None
        self.backup_conn = None
        
        # Conjuntos para almacenar IDs válidos
        self.valid_artist_ids = set()
        self.valid_album_ids = set()
        self.valid_song_ids = set()
        self.valid_label_ids = set()
        
        # Tablas inmutables que se copian completas
        self.immutable_tables = set()
        
    def connect_databases(self):
        """Conectar a las bases de datos origen y destino"""
        try:
            self.source_conn = sqlite3.connect(self.source_db_path)
            self.backup_conn = sqlite3.connect(self.backup_db_path)
            print(f"✓ Conectado a {self.source_db_path}")
            print(f"✓ Creando backup en {self.backup_db_path}")
            print(f"✓ Filtrando por origen: '{self.origen}'")
        except sqlite3.Error as e:
            print(f"✗ Error conectando a las bases de datos: {e}")
            sys.exit(1)
    
    def close_connections(self):
        """Cerrar conexiones a las bases de datos"""
        if self.source_conn:
            self.source_conn.close()
        if self.backup_conn:
            self.backup_conn.close()
    
    def get_all_tables(self):
        """Obtener lista de todas las tablas en la base de datos"""
        cursor = self.source_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall()]
    
    def identify_immutable_tables(self):
        """Identificar tablas que deben copiarse completas (inmutables)"""
        all_tables = self.get_all_tables()
        
        for table in all_tables:
            # Patrones para tablas inmutables
            if (table.startswith('uk_') or 
                table.startswith('spain_') or 
                table.startswith('billboard_') or
                table == 'nme_charts' or
                'listenbrainz' in table.lower() or
                'lastfm' in table.lower() or
                'scrobbles' in table.lower()):
                self.immutable_tables.add(table)
        
        print(f"  ✓ Identificadas {len(self.immutable_tables)} tablas inmutables:")
        for table in sorted(self.immutable_tables):
            print(f"    - {table}")
    
    def get_table_schema(self, table_name):
        """Obtener el esquema de una tabla"""
        cursor = self.source_conn.cursor()
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        result = cursor.fetchone()
        return result[0] if result else None
    
    def copy_table_schema(self, table_name):
        """Copiar el esquema de una tabla"""
        schema = self.get_table_schema(table_name)
        if schema:
            self.backup_conn.execute(schema)
            print(f"  ✓ Esquema copiado: {table_name}")
        return schema is not None
    
    def get_local_entities(self):
        """Identificar entidades con el origen especificado"""
        cursor = self.source_conn.cursor()
        
        # Obtener artistas con el origen especificado
        cursor.execute("SELECT id FROM artists WHERE origen = ?", (self.origen,))
        self.valid_artist_ids = {row[0] for row in cursor.fetchall()}
        print(f"  ✓ Encontrados {len(self.valid_artist_ids)} artistas con origen '{self.origen}'")
        
        # Obtener albums con el origen especificado
        cursor.execute("SELECT id FROM albums WHERE origen = ?", (self.origen,))
        self.valid_album_ids = {row[0] for row in cursor.fetchall()}
        print(f"  ✓ Encontrados {len(self.valid_album_ids)} albums con origen '{self.origen}'")
        
        # Obtener songs con el origen especificado
        cursor.execute("SELECT id FROM songs WHERE origen = ?", (self.origen,))
        self.valid_song_ids = {row[0] for row in cursor.fetchall()}
        print(f"  ✓ Encontradas {len(self.valid_song_ids)} canciones con origen '{self.origen}'")
        
        # Obtener labels relacionados con albums del origen especificado
        if self.valid_album_ids:
            placeholders = ','.join(['?' for _ in self.valid_album_ids])
            cursor.execute(f"""
                SELECT DISTINCT l.id 
                FROM labels l 
                JOIN albums a ON l.name = a.label 
                WHERE a.id IN ({placeholders})
            """, list(self.valid_album_ids))
            self.valid_label_ids = {row[0] for row in cursor.fetchall()}
        
        print(f"  ✓ Encontrados {len(self.valid_label_ids)} labels relacionados")
    
    def copy_main_tables(self):
        """Copiar las tablas principales (artists, albums, songs)"""
        print("\n📋 Copiando tablas principales...")
        
        # Copiar artistas
        if self.copy_table_schema('artists') and self.valid_artist_ids:
            placeholders = ','.join(['?' for _ in self.valid_artist_ids])
            cursor = self.source_conn.cursor()
            cursor.execute(f"SELECT * FROM artists WHERE id IN ({placeholders})", 
                         list(self.valid_artist_ids))
            
            columns = [description[0] for description in cursor.description]
            placeholders_insert = ','.join(['?' for _ in columns])
            
            rows = cursor.fetchall()
            self.backup_conn.executemany(
                f"INSERT INTO artists VALUES ({placeholders_insert})", rows)
            print(f"  ✓ Copiados {len(rows)} artistas")
        
        # Copiar albums
        if self.copy_table_schema('albums') and self.valid_album_ids:
            placeholders = ','.join(['?' for _ in self.valid_album_ids])
            cursor = self.source_conn.cursor()
            cursor.execute(f"SELECT * FROM albums WHERE id IN ({placeholders})", 
                         list(self.valid_album_ids))
            
            columns = [description[0] for description in cursor.description]
            placeholders_insert = ','.join(['?' for _ in columns])
            
            rows = cursor.fetchall()
            self.backup_conn.executemany(
                f"INSERT INTO albums VALUES ({placeholders_insert})", rows)
            print(f"  ✓ Copiados {len(rows)} albums")
        
        # Copiar songs
        if self.copy_table_schema('songs') and self.valid_song_ids:
            placeholders = ','.join(['?' for _ in self.valid_song_ids])
            cursor = self.source_conn.cursor()
            cursor.execute(f"SELECT * FROM songs WHERE id IN ({placeholders})", 
                         list(self.valid_song_ids))
            
            columns = [description[0] for description in cursor.description]
            placeholders_insert = ','.join(['?' for _ in columns])
            
            rows = cursor.fetchall()
            self.backup_conn.executemany(
                f"INSERT INTO songs VALUES ({placeholders_insert})", rows)
            print(f"  ✓ Copiadas {len(rows)} canciones")
    
    def copy_immutable_tables(self):
        """Copiar tablas inmutables completas"""
        print("\n🔒 Copiando tablas inmutables (completas)...")
        
        for table_name in sorted(self.immutable_tables):
            try:
                if self.copy_table_schema(table_name):
                    cursor = self.source_conn.cursor()
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()
                    
                    if rows:
                        columns = [description[0] for description in cursor.description]
                        placeholders = ','.join(['?' for _ in columns])
                        
                        self.backup_conn.executemany(
                            f"INSERT INTO {table_name} VALUES ({placeholders})", rows)
                        print(f"  ✓ Copiados {len(rows)} registros de {table_name}")
                    else:
                        print(f"  - {table_name} está vacía")
            except sqlite3.Error as e:
                print(f"  ✗ Error copiando {table_name}: {e}")
    
    def copy_related_tables(self):
        """Copiar tablas relacionadas basadas en las IDs válidas (excluyendo inmutables)"""
        print("\n🔗 Copiando tablas relacionadas...")
        
        # Mapeo de tablas relacionadas y sus campos de referencia
        related_tables = {
            'lyrics': [('track_id', self.valid_song_ids)],
            'song_links': [('song_id', self.valid_song_ids)],
            'listens': [('song_id', self.valid_song_ids), ('album_id', self.valid_album_ids), ('artist_id', self.valid_artist_ids)],
            'listens_guevifrito': [('song_id', self.valid_song_ids), ('album_id', self.valid_album_ids), ('artist_id', self.valid_artist_ids)],
            'artists_networks': [('artist_id', self.valid_artist_ids)],
            'artists_setlistfm': [('artist_id', self.valid_artist_ids)],
            'artists_discogs_info': [('artist_id', self.valid_artist_ids)],
            'discogs_discography': [('artist_id', self.valid_artist_ids), ('album_id', self.valid_album_ids)],
            'mb_data_songs': [('song_id', self.valid_song_ids)],
            'mb_release_group': [('artist_id', self.valid_artist_ids), ('album_id', self.valid_album_ids)],
            'mb_wikidata': [('artist_id', self.valid_artist_ids), ('album_id', self.valid_album_ids), ('label_id', self.valid_label_ids)],
            'feeds': [('entity_id', self.valid_artist_ids.union(self.valid_album_ids))],
            'menciones': [('artist_id', self.valid_artist_ids)],
            'normalized_songs': [('song_id', self.valid_song_ids)],
        }
        
        # Copiar labels si hay IDs válidos
        if self.valid_label_ids:
            related_tables['labels'] = [('id', self.valid_label_ids)]
            related_tables['label_relationships'] = [
                ('source_label_id', self.valid_label_ids),
                ('target_label_id', self.valid_label_ids)
            ]
            related_tables['label_release_relationships'] = [
                ('label_id', self.valid_label_ids),
                ('album_id', self.valid_album_ids)
            ]
            related_tables['label_artist_relationships'] = [
                ('label_id', self.valid_label_ids),
                ('artist_id', self.valid_artist_ids)
            ]
            related_tables['label_external_catalog'] = [('label_id', self.valid_label_ids)]
        
        for table_name, field_mappings in related_tables.items():
            # Saltar si es una tabla inmutable (ya se copió completa)
            if table_name in self.immutable_tables:
                continue
                
            if not self.copy_table_schema(table_name):
                continue
                
            # Construir la condición WHERE
            conditions = []
            params = []
            
            for field_name, valid_ids in field_mappings:
                if valid_ids:
                    placeholders = ','.join(['?' for _ in valid_ids])
                    conditions.append(f"{field_name} IN ({placeholders})")
                    params.extend(list(valid_ids))
            
            if not conditions:
                continue
                
            where_clause = ' OR '.join(conditions)
            
            try:
                cursor = self.source_conn.cursor()
                cursor.execute(f"SELECT * FROM {table_name} WHERE {where_clause}", params)
                rows = cursor.fetchall()
                
                if rows:
                    columns = [description[0] for description in cursor.description]
                    placeholders_insert = ','.join(['?' for _ in columns])
                    
                    self.backup_conn.executemany(
                        f"INSERT INTO {table_name} VALUES ({placeholders_insert})", rows)
                    print(f"  ✓ Copiados {len(rows)} registros de {table_name}")
                else:
                    print(f"  - Sin registros para {table_name}")
                    
            except sqlite3.Error as e:
                print(f"  ✗ Error copiando {table_name}: {e}")
    
    def copy_fts_tables(self):
        """Copiar tablas FTS (Full Text Search) relacionadas"""
        print("\n🔍 Copiando tablas FTS...")
        
        fts_tables = [
            'songs_fts', 'songs_fts_data', 'songs_fts_idx', 'songs_fts_docsize', 'songs_fts_config',
            'song_fts', 'song_fts_data', 'song_fts_idx', 'song_fts_content', 'song_fts_docsize', 'song_fts_config',
            'artist_fts', 'artist_fts_data', 'artist_fts_idx', 'artist_fts_content', 'artist_fts_docsize', 'artist_fts_config',
            'album_fts', 'album_fts_data', 'album_fts_idx', 'album_fts_content', 'album_fts_docsize', 'album_fts_config',
            'lyrics_fts', 'lyrics_fts_data', 'lyrics_fts_idx', 'lyrics_fts_docsize', 'lyrics_fts_config'
        ]
        
        for table_name in fts_tables:
            try:
                if self.copy_table_schema(table_name):
                    cursor = self.source_conn.cursor()
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()
                    
                    if rows:
                        columns = [description[0] for description in cursor.description]
                        placeholders = ','.join(['?' for _ in columns])
                        
                        self.backup_conn.executemany(
                            f"INSERT INTO {table_name} VALUES ({placeholders})", rows)
                        print(f"  ✓ Copiados {len(rows)} registros de {table_name}")
            except sqlite3.Error as e:
                print(f"  - {table_name} no copiado (puede ser virtual): {e}")
    
    def copy_config_tables(self):
        """Copiar tablas de configuración (excluyendo inmutables)"""
        print("\n⚙️ Copiando tablas de configuración...")
        
        config_tables = [
            'genres', 'sqlite_sequence'
        ]
        
        for table_name in config_tables:
            # Saltar si es una tabla inmutable
            if table_name in self.immutable_tables:
                continue
                
            try:
                if self.copy_table_schema(table_name):
                    cursor = self.source_conn.cursor()
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()
                    
                    if rows:
                        columns = [description[0] for description in cursor.description]
                        placeholders = ','.join(['?' for _ in columns])
                        
                        self.backup_conn.executemany(
                            f"INSERT INTO {table_name} VALUES ({placeholders})", rows)
                        print(f"  ✓ Copiados {len(rows)} registros de {table_name}")
            except sqlite3.Error as e:
                print(f"  ✗ Error copiando {table_name}: {e}")
    
    def create_backup_info(self):
        """Crear tabla con información del backup"""
        print("\n📝 Creando información del backup...")
        
        self.backup_conn.execute("""
            CREATE TABLE IF NOT EXISTS backup_info (
                id INTEGER PRIMARY KEY,
                backup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_db_path TEXT,
                backup_type TEXT,
                origen_filter TEXT,
                total_artists INTEGER,
                total_albums INTEGER,
                total_songs INTEGER,
                total_labels INTEGER,
                immutable_tables_count INTEGER,
                notes TEXT
            )
        """)
        
        self.backup_conn.execute("""
            INSERT INTO backup_info 
            (source_db_path, backup_type, origen_filter, total_artists, total_albums, total_songs, total_labels, immutable_tables_count, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.source_db_path,
            f'Parcial - Solo origen {self.origen}',
            self.origen,
            len(self.valid_artist_ids),
            len(self.valid_album_ids),
            len(self.valid_song_ids),
            len(self.valid_label_ids),
            len(self.immutable_tables),
            f'Backup parcial incluyendo solo entidades con origen = "{self.origen}" y toda su información relacionada. Tablas inmutables copiadas completas.'
        ))
        
        print("  ✓ Información del backup guardada")
    
    def create_backup(self):
        """Crear el backup completo"""
        print("🎵 Iniciando backup parcial de la base de datos musical...")
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Origen: {self.origen}")
        print("=" * 60)
        
        try:
            self.connect_databases()
            
            print("\n🔒 Identificando tablas inmutables...")
            self.identify_immutable_tables()
            
            print(f"\n🔍 Identificando entidades con origen '{self.origen}'...")
            self.get_local_entities()
            
            if not (self.valid_artist_ids or self.valid_album_ids or self.valid_song_ids):
                print(f"⚠️ No se encontraron entidades con origen '{self.origen}'")
                return False
            
            self.copy_main_tables()
            self.copy_immutable_tables()
            self.copy_related_tables()
            self.copy_fts_tables()
            self.copy_config_tables()
            self.create_backup_info()
            
            self.backup_conn.commit()
            
            print("\n" + "=" * 60)
            print("✅ Backup completado exitosamente!")
            print(f"📁 Archivo: {self.backup_db_path}")
            print(f"📊 Estadísticas del backup:")
            print(f"   • Origen filtrado: {self.origen}")
            print(f"   • Artistas: {len(self.valid_artist_ids)}")
            print(f"   • Albums: {len(self.valid_album_ids)}")
            print(f"   • Canciones: {len(self.valid_song_ids)}")
            print(f"   • Labels: {len(self.valid_label_ids)}")
            print(f"   • Tablas inmutables: {len(self.immutable_tables)}")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error durante el backup: {e}")
            return False
        finally:
            self.close_connections()

def main():
    parser = argparse.ArgumentParser(description='Crear backup parcial de base de datos musical')
    parser.add_argument('source_db', help='Ruta de la base de datos origen')
    parser.add_argument('backup_db', nargs='?', help='Ruta de la base de datos destino (opcional)')
    parser.add_argument('--origen', default='local', help='Filtro de origen (default: local)')
    
    args = parser.parse_args()
    
    source_db = args.source_db
    origen = args.origen
    
    if args.backup_db:
        backup_db = args.backup_db
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_db = f"music_{origen}_backup_{timestamp}.db"
    
    if not os.path.exists(source_db):
        print(f"✗ Error: No se encuentra la base de datos origen: {source_db}")
        sys.exit(1)
    
    if os.path.exists(backup_db):
        response = input(f"⚠️ El archivo {backup_db} ya existe. ¿Sobrescribir? (s/N): ")
        if response.lower() != 's':
            print("Operación cancelada.")
            sys.exit(0)
    
    backup_manager = MusicDatabaseBackup(source_db, backup_db, origen)
    success = backup_manager.create_backup()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()