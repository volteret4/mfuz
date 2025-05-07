def create_optimized_indices(conn, username=None):
    """
    Creates optimized database indices based on common queries and data patterns
    
    Args:
        conn: Database connection
        username: Optional Last.fm username to create user-specific indices
        
    Returns:
        Number of indices created
    """
    cursor = conn.cursor()
    indices_created = 0
    
    # Define all the indices we want to create
    indices = [
        # Artists table indices
        "CREATE INDEX IF NOT EXISTS idx_artists_name ON artists(name)",
        "CREATE INDEX IF NOT EXISTS idx_artists_name_lower ON artists(lower(name))",  # Case-insensitive lookups
        "CREATE INDEX IF NOT EXISTS idx_artists_mbid ON artists(mbid)",
        "CREATE INDEX IF NOT EXISTS idx_artists_tags ON artists(tags)",  # For genre/tag-based queries
        "CREATE INDEX IF NOT EXISTS idx_artists_origen ON artists(origen)",
        
        # Albums table indices
        "CREATE INDEX IF NOT EXISTS idx_albums_name ON albums(name)",
        "CREATE INDEX IF NOT EXISTS idx_albums_name_lower ON albums(lower(name))",  # Case-insensitive lookups
        "CREATE INDEX IF NOT EXISTS idx_albums_artist_id ON albums(artist_id)",
        "CREATE INDEX IF NOT EXISTS idx_albums_mbid ON albums(mbid)", 
        "CREATE INDEX IF NOT EXISTS idx_albums_year ON albums(year)",  # For year-based searches
        "CREATE INDEX IF NOT EXISTS idx_albums_origen ON albums(origen)",
        "CREATE INDEX IF NOT EXISTS idx_albums_artist_year ON albums(artist_id, year)",  # For chronological artist discographies
        
        # Songs table indices
        "CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title)",
        "CREATE INDEX IF NOT EXISTS idx_songs_title_lower ON songs(lower(title))",  # Case-insensitive lookups
        "CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist)",
        "CREATE INDEX IF NOT EXISTS idx_songs_artist_lower ON songs(lower(artist))",  # Case-insensitive artist lookups
        "CREATE INDEX IF NOT EXISTS idx_songs_album ON songs(album)",
        "CREATE INDEX IF NOT EXISTS idx_songs_mbid ON songs(mbid)",
        "CREATE INDEX IF NOT EXISTS idx_songs_added_year ON songs(added_year)",  # For songs by year added
        "CREATE INDEX IF NOT EXISTS idx_songs_added_month ON songs(added_month)",  # For songs by month added
        "CREATE INDEX IF NOT EXISTS idx_songs_origen ON songs(origen)",
        "CREATE INDEX IF NOT EXISTS idx_songs_genre ON songs(genre)",  # For genre-based queries
        "CREATE INDEX IF NOT EXISTS idx_songs_artist_title ON songs(lower(artist), lower(title))",  # Common lookup pattern
        
        # Song links table indices
        "CREATE INDEX IF NOT EXISTS idx_song_links_song_id ON song_links(song_id)",
        "CREATE INDEX IF NOT EXISTS idx_song_links_lastfm_url ON song_links(lastfm_url)",
        
        # Lyrics table indices
        "CREATE INDEX IF NOT EXISTS idx_lyrics_track_id ON lyrics(track_id)"
    ]
    
    # Add user-specific scrobble indices if a username is provided
    if username:
        scrobbles_table = f"scrobbles_{username}"
        
        # Check if the table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{scrobbles_table}'")
        if cursor.fetchone():
            user_indices = [
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist_name ON {scrobbles_table}(artist_name)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist_name_lower ON {scrobbles_table}(lower(artist_name))",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_album_name ON {scrobbles_table}(album_name)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_track_name ON {scrobbles_table}(track_name)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_timestamp ON {scrobbles_table}(timestamp)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_scrobble_date ON {scrobbles_table}(scrobble_date)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_song_id ON {scrobbles_table}(song_id)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist_id ON {scrobbles_table}(artist_id)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_album_id ON {scrobbles_table}(album_id)",
                # Compound indices for common queries
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist_album ON {scrobbles_table}(artist_name, album_name)",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_artist_track ON {scrobbles_table}(artist_name, track_name)",
                # Date-based indices for statistics
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_date_year ON {scrobbles_table}(strftime('%Y', scrobble_date))",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_date_month ON {scrobbles_table}(strftime('%Y-%m', scrobble_date))",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_date_day ON {scrobbles_table}(strftime('%Y-%m-%d', scrobble_date))",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_date_hour ON {scrobbles_table}(strftime('%H', scrobble_date))",
                f"CREATE INDEX IF NOT EXISTS idx_{scrobbles_table}_date_weekday ON {scrobbles_table}(strftime('%w', scrobble_date))"
            ]
            indices.extend(user_indices)
    
    # Create all the defined indices
    for index_query in indices:
        try:
            cursor.execute(index_query)
            indices_created += 1
            
            # Commit after each index to avoid locking the database for too long
            conn.commit()
        except Exception as e:
            print(f"Error creating index: {e}")
            print(f"Query was: {index_query}")
    
    print(f"Created or verified {indices_created} indices")
    return indices_created

def analyze_database_performance(conn):
    """
    Analyzes the database and suggests optimizations
    
    Args:
        conn: Database connection
        
    Returns:
        Dictionary with analysis results
    """
    cursor = conn.cursor()
    results = {
        'table_sizes': {},
        'missing_indices': [],
        'suggestions': []
    }
    
    # Get table sizes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        results['table_sizes'][table_name] = count
    
    # Check for missing indices on common query patterns
    common_query_patterns = [
        {'table': 'artists', 'columns': ['name']},
        {'table': 'artists', 'columns': ['mbid']},
        {'table': 'albums', 'columns': ['name', 'artist_id']},
        {'table': 'albums', 'columns': ['mbid']},
        {'table': 'songs', 'columns': ['title', 'artist']},
        {'table': 'songs', 'columns': ['mbid']},
        {'table': 'songs', 'columns': ['genre']}
    ]
    
    # Check for existing indices
    cursor.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index'")
    existing_indices = cursor.fetchall()
    existing_index_names = [idx[0] for idx in existing_indices]
    
    for pattern in common_query_patterns:
        table = pattern['table']
        columns = pattern['columns']
        
        # Check if index exists
        col_str = '_'.join(columns)
        index_name = f"idx_{table}_{col_str}"
        
        if index_name not in existing_index_names:
            results['missing_indices'].append({
                'table': table,
                'columns': columns,
                'suggested_name': index_name
            })
    
    # Make suggestions based on table sizes
    for table, size in results['table_sizes'].items():
        if size > 10000:
            results['suggestions'].append(f"Table '{table}' is large ({size} rows). Consider adding indices for frequent query patterns.")
        
        if table.startswith('songs_fts') or table.startswith('song_fts'):
            results['suggestions'].append(f"Consider using FTS tables '{table}' for text searches instead of LIKE queries.")
    
    # Check for vacuum and analyze
    results['suggestions'].append("Consider running VACUUM and ANALYZE on the database to optimize storage and statistics.")
    
    return results