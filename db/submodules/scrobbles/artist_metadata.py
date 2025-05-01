def update_artist_with_lastfm_info(conn, artist_id, artist_name, artist_mbid, lastfm_api_key, lastfm_cache=None):
    """
    Updates an artist's metadata with information from Last.fm (bio, tags, similar artists)
    
    Args:
        conn: Database connection
        artist_id: ID of the artist to update
        artist_name: Name of the artist
        artist_mbid: MusicBrainz ID of the artist (can be None)
        lastfm_api_key: Last.fm API key
        lastfm_cache: Optional cache for Last.fm requests
        
    Returns:
        True if updated successfully, False otherwise
    """
    # Get artist info from Last.fm
    artist_info = get_artist_info(artist_name, artist_mbid, lastfm_api_key, lastfm_cache)
    if not artist_info:
        print(f"No se pudo obtener información de Last.fm para {artist_name}")
        return False
    
    # Prepare updates
    cursor = conn.cursor()
    updates = []
    params = []
    updated = False
    
    # Bio
    if 'bio' in artist_info and 'content' in artist_info['bio'] and artist_info['bio']['content']:
        bio = artist_info['bio']['content']
        if bio and bio.strip():
            updates.append("bio = ?")
            params.append(bio)
            updated = True
    
    # Tags
    if 'tags' in artist_info and 'tag' in artist_info['tags']:
        tag_list = artist_info['tags']['tag']
        tags = []
        
        if isinstance(tag_list, list):
            tags = [tag['name'] for tag in tag_list]
        elif isinstance(tag_list, dict):
            tags = [tag_list['name']]
            
        tags_str = ','.join(tags)
        if tags_str:
            updates.append("tags = ?")
            params.append(tags_str)
            updated = True
    
    # Similar artists
    if 'similar' in artist_info and 'artist' in artist_info['similar']:
        similar_artists = artist_info['similar']['artist']
        if similar_artists:
            try:
                # Extract relevant information
                similar_data = []
                
                if isinstance(similar_artists, list):
                    for artist in similar_artists:
                        similar_data.append({
                            'name': artist.get('name', ''),
                            'url': artist.get('url', ''),
                            'mbid': artist.get('mbid', '')
                        })
                else:
                    similar_data.append({
                        'name': similar_artists.get('name', ''),
                        'url': similar_artists.get('url', ''),
                        'mbid': similar_artists.get('mbid', '')
                    })
                
                import json
                updates.append("similar_artists = ?")
                params.append(json.dumps(similar_data))
                updated = True
            except Exception as e:
                print(f"Error al procesar artistas similares para {artist_name}: {e}")
    
    # URL de Last.fm
    if 'url' in artist_info:
        updates.append("lastfm_url = COALESCE(lastfm_url, ?)")
        params.append(artist_info['url'])
        updated = True
    
    # Update if we have changes
    if updates and updated:
        query = f"UPDATE artists SET {', '.join(updates)} WHERE id = ?"
        params.append(artist_id)
        
        try:
            cursor.execute(query, params)
            conn.commit()
            print(f"Actualizada información de Last.fm para artista {artist_name} (ID: {artist_id})")
            return True
        except Exception as e:
            print(f"Error al actualizar artista {artist_name}: {e}")
    
    return False

def batch_update_artists_with_lastfm(conn, lastfm_api_key, limit=20, lastfm_cache=None):
    """
    Updates metadata for multiple artists in a batch operation
    
    Args:
        conn: Database connection
        lastfm_api_key: Last.fm API key
        limit: Maximum number of artists to update
        lastfm_cache: Optional cache for Last.fm requests
        
    Returns:
        Number of artists updated
    """
    cursor = conn.cursor()
    
    # Find artists without bio or tags
    cursor.execute("""
        SELECT id, name, mbid
        FROM artists
        WHERE (bio IS NULL OR tags IS NULL OR similar_artists IS NULL OR bio = '' OR tags = '')
        LIMIT ?
    """, (limit,))
    
    artists_to_update = cursor.fetchall()
    artists_updated = 0
    
    for artist_id, artist_name, artist_mbid in artists_to_update:
        if update_artist_with_lastfm_info(conn, artist_id, artist_name, artist_mbid, lastfm_api_key, lastfm_cache):
            artists_updated += 1
    
    return artists_updated