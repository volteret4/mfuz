def get_last_timestamp(conn, lastfm_username):
    """
    Gets the timestamp of the last processed scrobble from the config table
    
    Args:
        conn: Database connection
        lastfm_username: Last.fm username
    """
    cursor = conn.cursor()
    cursor.execute("SELECT last_timestamp FROM lastfm_config WHERE id = 1 AND lastfm_username = ?", (lastfm_username,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    return 0

def save_last_timestamp(conn, timestamp, lastfm_username):
    """
    Saves the timestamp of the last processed scrobble to the config table
    
    Args:
        conn: Database connection
        timestamp: Timestamp to save
        lastfm_username: Last.fm username
    """
    cursor = conn.cursor()
    
    # Try to update first
    cursor.execute("""
        UPDATE lastfm_config 
        SET last_timestamp = ?, lastfm_username = ?, last_updated = datetime('now')
        WHERE id = 1 AND lastfm_username = ?
    """, (timestamp, lastfm_username, lastfm_username))
    
    # If no rows were updated, try to update without filtering by username
    if cursor.rowcount == 0:
        cursor.execute("""
            UPDATE lastfm_config 
            SET last_timestamp = ?, lastfm_username = ?, last_updated = datetime('now')
            WHERE id = 1
        """, (timestamp, lastfm_username))
    
    # If still no rows were updated, insert
    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO lastfm_config (id, lastfm_username, last_timestamp, last_updated)
            VALUES (1, ?, ?, datetime('now'))
        """, (lastfm_username, timestamp))
    
    conn.commit()

def find_best_match(name, candidates, threshold=0.8):
    """
    Finds the best match for 'name' among the candidates.
    Enhanced to detect music collaboration cases.
    
    Args:
        name: Name to search for
        candidates: List of candidate names or dictionary where keys are names
        threshold: Minimum match threshold (0-1)
    
    Returns:
        Tuple (best_match, score) or (None, 0) if no matches
    """
    import difflib
    import re
    
    if not candidates or not name:
        return None, 0
    
    # Normalize name for comparison
    def normalize_name(text):
        if not text:
            return ""
        # Convert to lowercase
        text = text.lower().strip()
        # Remove special characters and accents
        text = re.sub(r'[^\w\s]', ' ', text)
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    # Extract the main artist (before feat, con, y, &, etc.)
    def extract_main_artist(text):
        if not text:
            return ""
        
        # Common patterns for collaborations
        patterns = [
            r'^(.*?)\s+feat[\.\s]+.*$',
            r'^(.*?)\s+featuring\s+.*$',
            r'^(.*?)\s+ft[\.\s]+.*$',
            r'^(.*?)\s+con\s+.*$',
            r'^(.*?)\s+y\s+.*$',
            r'^(.*?)\s+and\s+.*$',
            r'^(.*?)\s+&\s+.*$',
            r'^(.*?)\s+vs[\.\s]+.*$',
            r'^(.*?)\s+versus\s+.*$',
            r'^(.*?)\s+presents\s+.*$',
            r'^(.*?)\s+presenta\s+.*$',
        ]
        
        normalized = normalize_name(text)
        
        for pattern in patterns:
            match = re.match(pattern, normalized)
            if match:
                return match.group(1).strip()
        
        return normalized
    
    # Prepare normalized name and main artist
    name_norm = normalize_name(name)
    main_artist_name = extract_main_artist(name)
    
    # If candidates is a dictionary, extract the keys (names)
    if isinstance(candidates, dict):
        candidate_items = list(candidates.items())
        candidate_names = [k for k, v in candidate_items]
    else:
        candidate_names = candidates
        candidate_items = [(c, c) for c in candidates]
    
    # First look for exact matches (Case insensitive)
    for i, cname in enumerate(candidate_names):
        if normalize_name(cname) == name_norm:
            return candidate_items[i][1], 1.0  # Perfect match
    
    # Look for exact matches with the main artist
    if main_artist_name != name_norm:  # If the main artist differs from the full name
        for i, cname in enumerate(candidate_names):
            if normalize_name(cname) == main_artist_name:
                return candidate_items[i][1], 0.95  # Very high match (main artist)
            
            # Also check if the candidate is the main artist of the searched name
            candidate_main = extract_main_artist(cname)
            if candidate_main and candidate_main == main_artist_name:
                return candidate_items[i][1], 0.9  # High match (same main artist)
    
    # If no exact match, calculate scores with main artist
    best_score = 0
    best_match = None
    
    for i, cname in enumerate(candidate_names):
        cname_norm = normalize_name(cname)
        
        # Compare full names
        full_ratio = difflib.SequenceMatcher(None, name_norm, cname_norm).ratio()
        
        # Compare main artists
        candidate_main = extract_main_artist(cname)
        main_ratio = 0
        
        if main_artist_name and candidate_main:
            main_ratio = difflib.SequenceMatcher(None, main_artist_name, candidate_main).ratio()
        
        # Check if one contains the other (useful for abbreviated versions)
        contains_ratio = 0
        if name_norm in cname_norm or cname_norm in name_norm:
            min_len = min(len(name_norm), len(cname_norm))
            max_len = max(len(name_norm), len(cname_norm))
            contains_ratio = min_len / max_len
        
        # Use the best score among the three measures
        score = max(full_ratio, main_ratio, contains_ratio)
        
        if score > best_score:
            best_score = score
            best_match = candidate_items[i][1]
    
    # Return only if above threshold
    if best_score >= threshold:
        return best_match, best_score
    
    return None, 0

def calculate_match_quality(artist_match, album_match, song_match, match_score=None):
    """
    Calculates a match quality value based on which elements match
    
    Args:
        artist_match: True if the artist matches
        album_match: True if the album matches
        song_match: True if the song matches
        match_score: Artist's match score (0-1) if available
    
    Returns:
        Value between 0 and 1 representing the match quality
    """
    # If everything matches, it's perfect
    if artist_match and album_match and song_match:
        return 1.0
    
    # If artist and song match, it's a very good match
    if artist_match and song_match:
        if match_score and match_score < 0.95:
            # If it's a partial artist match (e.g.: SFDK vs SFDK featuring...)
            return 0.8  # Lower score for review
        return 0.9
    
    # If artist and album match, it's a good match
    if artist_match and album_match:
        if match_score and match_score < 0.95:
            return 0.75  # Lower score for review
        return 0.85
    
    # Only artist is a moderate match
    if artist_match:
        if match_score and match_score < 0.95:
            return 0.65  # Partial artist match
        return 0.7
    
    # Only album or song is a weak match
    if album_match or song_match:
        return 0.5
    
    # Nothing matches
    return 0.0

def lookup_artist_in_database(conn, artist_name, mbid=None, threshold=0.85):
    """
    Enhanced lookup artist using database information with better fuzzy matching
    Returns (artist_id, artist_info) or (None, None) if not found
    """
    cursor = conn.cursor()
    
    # Try exact name match first (case-insensitive)
    cursor.execute("SELECT id, mbid, name, origen FROM artists WHERE LOWER(name) = LOWER(?)", (artist_name,))
    result = cursor.fetchone()
    
    # If no match by name but we have MBID, try by MBID
    if not result and mbid:
        cursor.execute("SELECT id, mbid, name, origen FROM artists WHERE mbid = ?", (mbid,))
        result = cursor.fetchone()
        
        # If found by MBID but names differ significantly, log the discrepancy
        if result and result[2].lower() != artist_name.lower():
            print(f"Note: Artist '{artist_name}' matched by MBID to existing '{result[2]}'")
    
    # If still no match and threshold < 1.0, try fuzzy matching
    if not result and threshold < 1.0:
        # Get all artists for fuzzy matching
        cursor.execute("SELECT id, mbid, name, origen FROM artists")
        all_artists = cursor.fetchall()
        
        # Build dictionary of names to full records
        artist_dict = {row[2]: row for row in all_artists}
        
        # Find best match
        best_match, score = find_best_match(artist_name, artist_dict.keys(), threshold)
        
        if best_match:
            print(f"Found artist by approximate match: '{best_match}' (score: {score:.2f})")
            result = artist_dict[best_match]
    
    if result:
        return result[0], {
            'id': result[0],
            'mbid': result[1],
            'name': result[2],
            'origen': result[3]
        }
    
    return None, None

def lookup_album_in_database(conn, album_name, artist_id=None, artist_name=None, mbid=None, threshold=0.85):
    """
    Enhanced lookup album using database information with better fuzzy matching
    Prioritizes search by artist_id if available
    Returns (album_id, album_info) or (None, None) if not found
    """
    cursor = conn.cursor()
    
    # Initial query construction for exact match (case-insensitive)
    query = "SELECT a.id, a.mbid, a.name, a.artist_id, ar.name, a.origen FROM albums a JOIN artists ar ON a.artist_id = ar.id WHERE "
    conditions = []
    params = []
    
    # Base condition on album name
    conditions.append("LOWER(a.name) = LOWER(?)")
    params.append(album_name)
    
    # If we have artist_id, prioritize it
    if artist_id:
        conditions.append("a.artist_id = ?")
        params.append(artist_id)
    # Otherwise use artist name if available
    elif artist_name:
        conditions.append("LOWER(ar.name) = LOWER(?)")
        params.append(artist_name)
    
    # Execute with available conditions
    cursor.execute(query + " AND ".join(conditions), params)
    result = cursor.fetchone()
    
    # If no match by name/artist but we have MBID, try by MBID
    if not result and mbid:
        cursor.execute("SELECT a.id, a.mbid, a.name, a.artist_id, ar.name, a.origen FROM albums a JOIN artists ar ON a.artist_id = ar.id WHERE a.mbid = ?", (mbid,))
        result = cursor.fetchone()
        
        # If found by MBID but names differ significantly, log the discrepancy
        if result and result[2].lower() != album_name.lower():
            print(f"Note: Album '{album_name}' matched by MBID to existing '{result[2]}'")
    
    # If still no match and threshold < 1.0, try fuzzy matching
    if not result and threshold < 1.0:
        # Try multiple approaches for fuzzy matching
        
        # 1. First try with artist_id if available (most reliable)
        if artist_id:
            cursor.execute("SELECT a.id, a.mbid, a.name, a.artist_id, ar.name, a.origen FROM albums a JOIN artists ar ON a.artist_id = ar.id WHERE a.artist_id = ?", (artist_id,))
            artist_albums = cursor.fetchall()
            
            # Build dictionary of album names to full records
            album_dict = {row[2]: row for row in artist_albums}
            
            # Find best match among this artist's albums
            best_match, score = find_best_match(album_name, album_dict.keys(), threshold)
            
            if best_match:
                print(f"Found album by approximate match: '{best_match}' (score: {score:.2f})")
                result = album_dict[best_match]
        
        # 2. If we still don't have a match but have artist_name, try all albums
        if not result and artist_name:
            # Get all albums
            cursor.execute("SELECT a.id, a.mbid, a.name, a.artist_id, ar.name, a.origen FROM albums a JOIN artists ar ON a.artist_id = ar.id")
            all_albums = cursor.fetchall()
            
            # Try two approaches:
            
            # 2.1 First with artist name filter
            artist_albums = [album for album in all_albums if album[4].lower() == artist_name.lower()]
            album_dict = {album[2]: album for album in artist_albums}
            best_match, score = find_best_match(album_name, album_dict.keys(), threshold)
            
            if best_match:
                print(f"Found album by approximate match with artist filter: '{best_match}' (score: {score:.2f})")
                result = album_dict[best_match]
            
            # 2.2 If still no match, try with composite keys (artist - album)
            if not result:
                # Create composite keys with artist and album name
                album_dict = {f"{row[4]} - {row[2]}": row for row in all_albums}
                
                # Find best match with combined artist-album key
                best_match, score = find_best_match(f"{artist_name} - {album_name}", album_dict.keys(), threshold)
                
                if best_match:
                    print(f"Found album by composite match: '{best_match}' (score: {score:.2f})")
                    result = album_dict[best_match]
    
    if result:
        return result[0], {
            'id': result[0],
            'mbid': result[1],
            'name': result[2],
            'artist_id': result[3],
            'artist_name': result[4],
            'origen': result[5]
        }
    
    return None, None

def lookup_song_in_database(conn, track_name, artist_id=None, artist_name=None, album_id=None, album_name=None, mbid=None, lastfm_url=None, threshold=0.85):
    """
    Enhanced lookup song using database information with better fuzzy matching
    Prioritizes search by existing IDs when available
    Returns (song_id, song_info) or (None, None) if not found
    """
    # If we have a Last.fm URL, try to find by that first
    if lastfm_url:
        song_id, song_info = lookup_song_by_lastfm_url(conn, lastfm_url)
        if song_id:
            return song_id, song_info
    
    cursor = conn.cursor()
    
    # If we have MBID, try first by MBID (most reliable)
    if mbid:
        cursor.execute("SELECT id, mbid, title, artist, album, origen FROM songs WHERE mbid = ?", (mbid,))
        result = cursor.fetchone()
        if result:
            return result[0], {
                'id': result[0],
                'mbid': result[1],
                'title': result[2],
                'artist': result[3],
                'album': result[4],
                'origen': result[5]
            }
    
    # Try exact match with all available info
    query = "SELECT id, mbid, title, artist, album, origen FROM songs WHERE "
    conditions = ["LOWER(title) = LOWER(?)"]
    params = [track_name]
    
    # Add artist condition if available
    if artist_name:
        conditions.append("LOWER(artist) = LOWER(?)")
        params.append(artist_name)
    
    # Add album condition if available
    if album_name:
        conditions.append("LOWER(album) = LOWER(?)")
        params.append(album_name)
    
    # Execute query
    cursor.execute(query + " AND ".join(conditions), params)
    result = cursor.fetchone()
    
    # If no result, try with artist only (common case: same song different albums)
    if not result and artist_name:
        cursor.execute("""
            SELECT id, mbid, title, artist, album, origen 
            FROM songs 
            WHERE LOWER(title) = LOWER(?) AND LOWER(artist) = LOWER(?)
        """, (track_name, artist_name))
        result = cursor.fetchone()
    
    # If still no result, try fuzzy matching
    if not result and threshold < 1.0:
        # Get candidate songs
        query_cond = ""
        query_params = []
        
        if artist_name:
            query_cond = " WHERE LOWER(artist) = LOWER(?)"
            query_params = [artist_name]
        
        cursor.execute(f"SELECT id, mbid, title, artist, album, origen FROM songs{query_cond}", query_params)
        candidates = cursor.fetchall()
        
        # First try exact title match but case-insensitive
        for song in candidates:
            if song[2].lower() == track_name.lower():
                result = song
                print(f"Found song by case-insensitive match: '{song[2]}' by '{song[3]}'")
                break
        
        # If still no match, try fuzzy matching on title
        if not result:
            # Create dictionary of songs by title
            song_dict = {song[2]: song for song in candidates}
            best_match, score = find_best_match(track_name, song_dict.keys(), threshold)
            
            if best_match:
                print(f"Found song by fuzzy title match: '{best_match}' (score: {score:.2f})")
                result = song_dict[best_match]
    
    if result:
        return result[0], {
            'id': result[0],
            'mbid': result[1],
            'title': result[2],
            'artist': result[3],
            'album': result[4],
            'origen': result[5]
        }
    
    return None, None

def lookup_song_by_lastfm_url(conn, lastfm_url):
    """
    Looks up a song in the database by its Last.fm URL
    
    Args:
        conn: Database connection
        lastfm_url: Last.fm URL for the song
    
    Returns:
        (song_id, song_info) or (None, None) if not found
    """
    if not lastfm_url:
        return None, None
    
    cursor = conn.cursor()
    
    # First check in song_links
    cursor.execute("""
    SELECT sl.song_id, s.title, s.artist, s.album, s.mbid, s.origen
    FROM song_links sl
    JOIN songs s ON sl.song_id = s.id
    WHERE sl.lastfm_url = ? 
    """, (lastfm_url,))
    
    result = cursor.fetchone()
    if result:
        return result[0], {
            'id': result[0],
            'title': result[1],
            'artist': result[2],
            'album': result[3],
            'mbid': result[4],
            'origen': result[5]
        }
    
    return None, None

def process_scrobbled_song(conn, track_name, artist_name, album_name, timestamp, lastfm_url, mbid=None):
    """
    Adds or updates an entry in the scrobbled_songs table for listened songs
    that don't exist in the main songs table.
    
    Args:
        conn: Database connection
        track_name: Song name
        artist_name: Artist name
        album_name: Album name (can be None)
        timestamp: UNIX timestamp of the scrobble
        lastfm_url: Last.fm URL for the song
        mbid: Optional MusicBrainz ID
        
    Returns:
        ID of the entry in scrobbled_songs
    """
    cursor = conn.cursor()
    
    # First try to find if an entry already exists for this song/artist
    cursor.execute("""
        SELECT id, scrobble_timestamps, artist_id, album_id, song_id
        FROM scrobbled_songs
        WHERE LOWER(title) = LOWER(?) AND LOWER(artist_name) = LOWER(?)
    """, (track_name, artist_name))
    
    existing = cursor.fetchone()
    
    # Look up related IDs (artist_id, album_id, song_id)
    artist_id = None
    album_id = None
    song_id = None
    
    # Look up artist
    cursor.execute("SELECT id FROM artists WHERE LOWER(name) = LOWER(?)", (artist_name,))
    artist_result = cursor.fetchone()
    if artist_result:
        artist_id = artist_result[0]
    
    # Look up album if we have artist_id
    if artist_id and album_name:
        cursor.execute("""
            SELECT id FROM albums 
            WHERE LOWER(name) = LOWER(?) AND artist_id = ?
        """, (album_name, artist_id))
        album_result = cursor.fetchone()
        if album_result:
            album_id = album_result[0]
    
    # Look up song
    cursor.execute("""
        SELECT id FROM songs
        WHERE LOWER(title) = LOWER(?) AND LOWER(artist) = LOWER(?)
    """, (track_name, artist_name))
    song_result = cursor.fetchone()
    if song_result:
        song_id = song_result[0]
    
    # Format the timestamp for storing in the list
    formatted_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    if existing:
        # Update existing entry adding the new timestamp
        scrobbled_id, timestamp_json, existing_artist_id, existing_album_id, existing_song_id = existing
        
        try:
            # Load existing timestamp list
            timestamps = json.loads(timestamp_json) if timestamp_json else []
        except json.JSONDecodeError:
            timestamps = []
        
        # Add the new timestamp if not already present
        if formatted_time not in timestamps:
            timestamps.append(formatted_time)
            # Sort chronologically
            timestamps.sort()
        
        # Also update the IDs if not already present
        updates = [
            "scrobble_timestamps = ?",
            "lastfm_url = COALESCE(lastfm_url, ?)"
        ]
        params = [json.dumps(timestamps), lastfm_url]
        
        if mbid and mbid.strip():
            updates.append("mbid = COALESCE(mbid, ?)")
            params.append(mbid)
        
        if artist_id and not existing_artist_id:
            updates.append("artist_id = ?")
            params.append(artist_id)
        
        if album_id and not existing_album_id:
            updates.append("album_id = ?")
            params.append(album_id)
        
        if song_id and not existing_song_id:
            updates.append("song_id = ?")
            params.append(song_id)
        
        # Execute update
        cursor.execute(f"""
            UPDATE scrobbled_songs
            SET {', '.join(updates)}
            WHERE id = ?
        """, params + [scrobbled_id])
        
        conn.commit()
        return scrobbled_id
    else:
        # Create new entry
        cursor.execute("""
            INSERT INTO scrobbled_songs
            (title, artist_name, artist_id, album_name, album_id, song_id, lastfm_url, scrobble_timestamps, mbid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            track_name,
            artist_name,
            artist_id,
            album_name,
            album_id,
            song_id,
            lastfm_url,
            json.dumps([formatted_time]),
            mbid
        ))
        
        conn.commit()
        return cursor.lastrowid