
Estructura de la tabla: songs
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'file_path', 'TEXT', 0, None, 0)
(2, 'title', 'TEXT', 0, None, 0)
(3, 'track_number', 'INTEGER', 0, None, 0)
(4, 'artist', 'TEXT', 0, None, 0)
(5, 'album_artist', 'TEXT', 0, None, 0)
(6, 'album', 'TEXT', 0, None, 0)
(7, 'date', 'TEXT', 0, None, 0)
(8, 'genre', 'TEXT', 0, None, 0)
(9, 'label', 'TEXT', 0, None, 0)
(10, 'mbid', 'TEXT', 0, None, 0)
(11, 'bitrate', 'INTEGER', 0, None, 0)
(12, 'bit_depth', 'INTEGER', 0, None, 0)
(13, 'sample_rate', 'INTEGER', 0, None, 0)
(14, 'last_modified', 'TIMESTAMP', 0, None, 0)
(15, 'added_timestamp', 'TIMESTAMP', 0, None, 0)
(16, 'added_week', 'INTEGER', 0, None, 0)
(17, 'added_month', 'INTEGER', 0, None, 0)
(18, 'added_year', 'INTEGER', 0, None, 0)
(19, 'duration', 'REAL', 0, None, 0)
(20, 'lyrics_id', 'INTEGER', 0, None, 0)
(21, 'replay_gain_track_gain', 'REAL', 0, None, 0)
(22, 'replay_gain_track_peak', 'REAL', 0, None, 0)
(23, 'replay_gain_album_gain', 'REAL', 0, None, 0)
(24, 'replay_gain_album_peak', 'REAL', 0, None, 0)
(25, 'album_art_path_denorm', 'TEXT', 0, None, 0)
(26, 'has_lyrics', 'INTEGER', 0, '0', 0)

Estructura de la tabla: artists
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'name', 'TEXT', 0, None, 0)
(2, 'bio', 'TEXT', 0, None, 0)
(3, 'tags', 'TEXT', 0, None, 0)
(4, 'similar_artists', 'TEXT', 0, None, 0)
(5, 'last_updated', 'TIMESTAMP', 0, None, 0)
(6, 'origin', 'TEXT', 0, None, 0)
(7, 'formed_year', 'INTEGER', 0, None, 0)
(8, 'total_albums', 'INTEGER', 0, None, 0)
(9, 'spotify_url', 'TEXT', 0, None, 0)
(10, 'youtube_url', 'TEXT', 0, None, 0)
(11, 'musicbrainz_url', 'TEXT', 0, None, 0)
(12, 'discogs_url', 'TEXT', 0, None, 0)
(13, 'rateyourmusic_url', 'TEXT', 0, None, 0)
(14, 'links_updated', 'TIMESTAMP', 0, None, 0)
(15, 'wikipedia_url', 'TEXT', 0, None, 0)
(16, 'wikipedia_content', 'TEXT', 0, None, 0)
(17, 'wikipedia_updated', 'TIMESTAMP', 0, None, 0)
(18, 'mbid', 'TEXT', 0, None, 0)
(19, 'bandcamp_url', 'TEXT', 0, None, 0)
(20, 'member_of', 'TEXT', 0, None, 0)
(21, 'aliases', 'TEXT', 0, None, 0)
(22, 'lastfm_url', 'TEXT', 0, None, 0)

Estructura de la tabla: albums
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'artist_id', 'INTEGER', 0, None, 0)
(2, 'name', 'TEXT', 0, None, 0)
(3, 'year', 'TEXT', 0, None, 0)
(4, 'label', 'TEXT', 0, None, 0)
(5, 'genre', 'TEXT', 0, None, 0)
(6, 'total_tracks', 'INTEGER', 0, None, 0)
(7, 'album_art_path', 'TEXT', 0, None, 0)
(8, 'last_updated', 'TIMESTAMP', 0, None, 0)
(9, 'spotify_url', 'TEXT', 0, None, 0)
(10, 'spotify_id', 'TEXT', 0, None, 0)
(11, 'youtube_url', 'TEXT', 0, None, 0)
(12, 'musicbrainz_url', 'TEXT', 0, None, 0)
(13, 'discogs_url', 'TEXT', 0, None, 0)
(14, 'rateyourmusic_url', 'TEXT', 0, None, 0)
(15, 'links_updated', 'TIMESTAMP', 0, None, 0)
(16, 'wikipedia_url', 'TEXT', 0, None, 0)
(17, 'wikipedia_content', 'TEXT', 0, None, 0)
(18, 'wikipedia_updated', 'TIMESTAMP', 0, None, 0)
(19, 'mbid', 'TEXT', 0, None, 0)
(20, 'folder_path', 'TEXT', 0, None, 0)
(21, 'bitrate_range', 'TEXT', 0, None, 0)
(22, 'bandcamp_url', 'TEXT', 0, None, 0)
(23, 'producers', 'TEXT', 0, None, 0)
(24, 'engineers', 'TEXT', 0, None, 0)
(25, 'mastering_engineers', 'TEXT', 0, None, 0)
(26, 'credits', 'TEXT', 0, None, 0)
(27, 'lastfm_url', 'TEXT', 0, None, 0)

Estructura de la tabla: genres
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'name', 'TEXT', 0, None, 0)
(2, 'description', 'TEXT', 0, None, 0)
(3, 'related_genres', 'TEXT', 0, None, 0)
(4, 'origin_year', 'INTEGER', 0, None, 0)

Estructura de la tabla: lyrics
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'track_id', 'INTEGER', 0, None, 0)
(2, 'lyrics', 'TEXT', 0, None, 0)
(3, 'source', 'TEXT', 0, "'Genius'", 0)
(4, 'last_updated', 'TIMESTAMP', 0, None, 0)

Estructura de la tabla: song_links
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'song_id', 'INTEGER', 0, None, 0)
(2, 'spotify_url', 'TEXT', 0, None, 0)
(3, 'spotify_id', 'TEXT', 0, None, 0)
(4, 'lastfm_url', 'TEXT', 0, None, 0)
(5, 'links_updated', 'TIMESTAMP', 0, None, 0)
(6, 'youtube_url', 'TEXT', 0, None, 0)
(7, 'musicbrainz_url', 'TEXT', 0, None, 0)
(8, 'musicbrainz_recording_id', 'TEXT', 0, None, 0)
(9, 'bandcamp_url', 'TEXT', 0, None, 0)
(10, 'soundcloud_url', 'TEXT', 0, None, 0)
(11, 'boomkat_url', 'TEXT', 0, None, 0)

Estructura de la tabla: songs_fts
(0, 'title', '', 0, None, 0)
(1, 'artist', '', 0, None, 0)
(2, 'album', '', 0, None, 0)
(3, 'genre', '', 0, None, 0)

Estructura de la tabla: songs_fts_data
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'block', 'BLOB', 0, None, 0)

Estructura de la tabla: songs_fts_idx
(0, 'segid', '', 1, None, 1)
(1, 'term', '', 1, None, 2)
(2, 'pgno', '', 0, None, 0)

Estructura de la tabla: songs_fts_docsize
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'sz', 'BLOB', 0, None, 0)

Estructura de la tabla: songs_fts_config
(0, 'k', '', 1, None, 1)
(1, 'v', '', 0, None, 0)

Estructura de la tabla: song_fts
(0, 'id', '', 0, None, 0)
(1, 'title', '', 0, None, 0)
(2, 'artist', '', 0, None, 0)
(3, 'album', '', 0, None, 0)
(4, 'genre', '', 0, None, 0)

Estructura de la tabla: song_fts_data
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'block', 'BLOB', 0, None, 0)

Estructura de la tabla: song_fts_idx
(0, 'segid', '', 1, None, 1)
(1, 'term', '', 1, None, 2)
(2, 'pgno', '', 0, None, 0)

Estructura de la tabla: song_fts_content
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'c0', '', 0, None, 0)
(2, 'c1', '', 0, None, 0)
(3, 'c2', '', 0, None, 0)
(4, 'c3', '', 0, None, 0)
(5, 'c4', '', 0, None, 0)

Estructura de la tabla: song_fts_docsize
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'sz', 'BLOB', 0, None, 0)

Estructura de la tabla: song_fts_config
(0, 'k', '', 1, None, 1)
(1, 'v', '', 0, None, 0)

Estructura de la tabla: artist_fts
(0, 'id', '', 0, None, 0)
(1, 'name', '', 0, None, 0)
(2, 'bio', '', 0, None, 0)
(3, 'tags', '', 0, None, 0)

Estructura de la tabla: artist_fts_data
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'block', 'BLOB', 0, None, 0)

Estructura de la tabla: artist_fts_idx
(0, 'segid', '', 1, None, 1)
(1, 'term', '', 1, None, 2)
(2, 'pgno', '', 0, None, 0)

Estructura de la tabla: artist_fts_content
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'c0', '', 0, None, 0)
(2, 'c1', '', 0, None, 0)
(3, 'c2', '', 0, None, 0)
(4, 'c3', '', 0, None, 0)

Estructura de la tabla: artist_fts_docsize
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'sz', 'BLOB', 0, None, 0)

Estructura de la tabla: artist_fts_config
(0, 'k', '', 1, None, 1)
(1, 'v', '', 0, None, 0)

Estructura de la tabla: album_fts
(0, 'id', '', 0, None, 0)
(1, 'name', '', 0, None, 0)
(2, 'genre', '', 0, None, 0)

Estructura de la tabla: album_fts_data
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'block', 'BLOB', 0, None, 0)

Estructura de la tabla: album_fts_idx
(0, 'segid', '', 1, None, 1)
(1, 'term', '', 1, None, 2)
(2, 'pgno', '', 0, None, 0)

Estructura de la tabla: album_fts_content
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'c0', '', 0, None, 0)
(2, 'c1', '', 0, None, 0)
(3, 'c2', '', 0, None, 0)

Estructura de la tabla: album_fts_docsize
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'sz', 'BLOB', 0, None, 0)

Estructura de la tabla: album_fts_config
(0, 'k', '', 1, None, 1)
(1, 'v', '', 0, None, 0)

Estructura de la tabla: lyrics_fts
(0, 'lyrics', '', 0, None, 0)

Estructura de la tabla: lyrics_fts_data
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'block', 'BLOB', 0, None, 0)

Estructura de la tabla: lyrics_fts_idx
(0, 'segid', '', 1, None, 1)
(1, 'term', '', 1, None, 2)
(2, 'pgno', '', 0, None, 0)

Estructura de la tabla: lyrics_fts_docsize
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'sz', 'BLOB', 0, None, 0)

Estructura de la tabla: lyrics_fts_config
(0, 'k', '', 1, None, 1)
(1, 'v', '', 0, None, 0)

Estructura de la tabla: scrobbles
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'track_name', 'TEXT', 1, None, 0)
(2, 'album_name', 'TEXT', 0, None, 0)
(3, 'artist_name', 'TEXT', 1, None, 0)
(4, 'timestamp', 'INTEGER', 1, None, 0)
(5, 'scrobble_date', 'TIMESTAMP', 1, None, 0)
(6, 'lastfm_url', 'TEXT', 0, None, 0)
(7, 'song_id', 'INTEGER', 0, None, 0)
(8, 'album_id', 'INTEGER', 0, None, 0)
(9, 'artist_id', 'INTEGER', 0, None, 0)

Estructura de la tabla: lastfm_config
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'lastfm_username', 'TEXT', 0, None, 0)
(2, 'last_timestamp', 'INTEGER', 0, None, 0)
(3, 'last_updated', 'TIMESTAMP', 0, None, 0)

Estructura de la tabla: labels
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'name', 'TEXT', 1, None, 0)
(2, 'mbid', 'TEXT', 0, None, 0)
(3, 'founded_year', 'INTEGER', 0, None, 0)
(4, 'country', 'TEXT', 0, None, 0)
(5, 'description', 'TEXT', 0, None, 0)
(6, 'last_updated', 'TIMESTAMP', 0, None, 0)
(7, 'official_website', 'TEXT', 0, None, 0)
(8, 'wikipedia_url', 'TEXT', 0, None, 0)
(9, 'wikipedia_content', 'TEXT', 0, None, 0)
(10, 'wikipedia_updated', 'TIMESTAMP', 0, None, 0)
(11, 'discogs_url', 'TEXT', 0, None, 0)
(12, 'bandcamp_url', 'TEXT', 0, None, 0)
(13, 'mb_type', 'TEXT', 0, None, 0)
(14, 'mb_code', 'TEXT', 0, None, 0)
(15, 'mb_last_updated', 'TIMESTAMP', 0, None, 0)

Estructura de la tabla: label_relationships
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'source_label_id', 'INTEGER', 1, None, 0)
(2, 'target_label_id', 'INTEGER', 1, None, 0)
(3, 'relationship_type', 'TEXT', 1, None, 0)
(4, 'begin_date', 'TEXT', 0, None, 0)
(5, 'end_date', 'TEXT', 0, None, 0)
(6, 'last_updated', 'TIMESTAMP', 0, None, 0)

Estructura de la tabla: label_release_relationships
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'label_id', 'INTEGER', 1, None, 0)
(2, 'album_id', 'INTEGER', 1, None, 0)
(3, 'relationship_type', 'TEXT', 1, None, 0)
(4, 'catalog_number', 'TEXT', 0, None, 0)
(5, 'begin_date', 'TEXT', 0, None, 0)
(6, 'end_date', 'TEXT', 0, None, 0)
(7, 'last_updated', 'TIMESTAMP', 0, None, 0)

Estructura de la tabla: listens
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'track_name', 'TEXT', 1, None, 0)
(2, 'album_name', 'TEXT', 0, None, 0)
(3, 'artist_name', 'TEXT', 1, None, 0)
(4, 'timestamp', 'INTEGER', 1, None, 0)
(5, 'listen_date', 'TIMESTAMP', 1, None, 0)
(6, 'listenbrainz_url', 'TEXT', 0, None, 0)
(7, 'song_id', 'INTEGER', 0, None, 0)
(8, 'album_id', 'INTEGER', 0, None, 0)
(9, 'artist_id', 'INTEGER', 0, None, 0)
(10, 'additional_data', 'TEXT', 0, None, 0)

Estructura de la tabla: listenbrainz_config
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'username', 'TEXT', 0, None, 0)
(2, 'last_timestamp', 'INTEGER', 0, None, 0)
(3, 'last_updated', 'TIMESTAMP', 0, None, 0)

Estructura de la tabla: normalized_songs
(0, 'song_id', 'INTEGER', 0, None, 1)
(1, 'normalized_title', 'TEXT', 0, None, 0)
(2, 'normalized_artist', 'TEXT', 0, None, 0)
(3, 'normalized_album', 'TEXT', 0, None, 0)

Estructura de la tabla: mb_data_songs
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'song_id', 'INTEGER', 1, None, 0)
(2, 'relationship_type', 'TEXT', 1, None, 0)
(3, 'related_mbid', 'TEXT', 1, None, 0)
(4, 'related_title', 'TEXT', 0, None, 0)
(5, 'related_artist', 'TEXT', 0, None, 0)
(6, 'relationship_direction', 'TEXT', 1, None, 0)
(7, 'last_updated', 'TIMESTAMP', 0, 'CURRENT_TIMESTAMP', 0)

Estructura de la tabla: feeds
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'entity_type', 'TEXT', 1, None, 0)
(2, 'entity_id', 'INTEGER', 1, None, 0)
(3, 'feed_name', 'TEXT', 1, None, 0)
(4, 'post_title', 'TEXT', 1, None, 0)
(5, 'post_url', 'TEXT', 1, None, 0)
(6, 'post_date', 'TIMESTAMP', 0, None, 0)
(7, 'content', 'TEXT', 0, None, 0)
(8, 'added_date', 'TIMESTAMP', 0, 'CURRENT_TIMESTAMP', 0)

Estructura de la tabla: mb_release_group
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'mbid', 'TEXT', 1, None, 0)
(2, 'title', 'TEXT', 0, None, 0)
(3, 'artist_credit', 'TEXT', 0, None, 0)
(4, 'first_release_date', 'TEXT', 0, None, 0)
(5, 'primary_type', 'TEXT', 0, None, 0)
(6, 'secondary_types', 'TEXT', 0, None, 0)
(7, 'album_id', 'INTEGER', 0, None, 0)
(8, 'artist_id', 'INTEGER', 0, None, 0)
(9, 'genre', 'TEXT', 0, None, 0)
(10, 'associated_singles', 'TEXT', 0, None, 0)
(11, 'discogs_url', 'TEXT', 0, None, 0)
(12, 'rateyourmusic_url', 'TEXT', 0, None, 0)
(13, 'allmusic_url', 'TEXT', 0, None, 0)
(14, 'wikidata_id', 'TEXT', 0, None, 0)
(15, 'last_updated', 'TIMESTAMP', 0, None, 0)
(16, 'wikipedia_url', 'TEXT', 0, None, 0)
(17, 'musicbrainz_url', 'TEXT', 0, None, 0)
(18, 'género', 'TEXT', 0, None, 0)
(19, 'apple_url', 'TEXT', 0, None, 0)
(20, 'deezer_url', 'TEXT', 0, None, 0)
(21, 'bandcamp_url', 'TEXT', 0, None, 0)
(22, 'website', 'TEXT', 0, None, 0)
(23, 'amazon_url', 'TEXT', 0, None, 0)
(24, 'metacritic_url', 'TEXT', 0, None, 0)
(25, 'caracterizado_por', 'TEXT', 0, None, 0)
(26, 'youtube_url', 'TEXT', 0, None, 0)
(27, 'spotify_url', 'TEXT', 0, None, 0)
(28, 'producer', 'TEXT', 0, None, 0)
(29, 'offiziellecharts_url', 'TEXT', 0, None, 0)
(30, 'anydecentmusic_url', 'TEXT', 0, None, 0)
(31, 'albumoftheyear_url', 'TEXT', 0, None, 0)

Estructura de la tabla: mb_wikidata
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'wikidata_id', 'TEXT', 1, None, 0)
(2, 'release_group_mbid', 'TEXT', 0, None, 0)
(3, 'album_id', 'INTEGER', 0, None, 0)
(4, 'artist_id', 'INTEGER', 0, None, 0)
(5, 'label_id', 'INTEGER', 0, None, 0)
(6, 'property_id', 'TEXT', 0, None, 0)
(7, 'property_label', 'TEXT', 0, None, 0)
(8, 'property_value', 'TEXT', 0, None, 0)
(9, 'last_updated', 'TIMESTAMP', 0, None, 0)
(10, 'value_type', 'TEXT', 0, None, 0)
(11, 'is_link', 'INTEGER', 0, '0', 0)
