
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
(16, 'added_day', 'INTEGER', 0, None, 0)
(17, 'added_week', 'INTEGER', 0, None, 0)
(18, 'added_month', 'INTEGER', 0, None, 0)
(19, 'added_year', 'INTEGER', 0, None, 0)
(20, 'duration', 'REAL', 0, None, 0)
(21, 'lyrics_id', 'INTEGER', 0, None, 0)
(22, 'replay_gain_track_gain', 'REAL', 0, None, 0)
(23, 'replay_gain_track_peak', 'REAL', 0, None, 0)
(24, 'replay_gain_album_gain', 'REAL', 0, None, 0)
(25, 'replay_gain_album_peak', 'REAL', 0, None, 0)
(26, 'album_art_path_denorm', 'TEXT', 0, None, 0)
(27, 'has_lyrics', 'INTEGER', 0, '0', 0)
(28, 'origen', 'TEXT', 0, "'local'", 0)
(29, 'musicbrainz_artistid', 'TEXT', 0, None, 0)
(30, 'musicbrainz_recordingid', 'TEXT', 0, None, 0)
(31, 'musicbrainz_albumartistid', 'TEXT', 0, None, 0)
(32, 'musicbrainz_releasegroupid', 'TEXT', 0, None, 0)

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
(19, 'added_timestamp', 'TIMESTAMP', 0, None, 0)
(20, 'added_day', 'INTEGER', 0, None, 0)
(21, 'added_week', 'INTEGER', 0, None, 0)
(22, 'added_month', 'INTEGER', 0, None, 0)
(23, 'added_year', 'INTEGER', 0, None, 0)
(24, 'origen', 'TEXT', 0, "'local'", 0)
(25, 'aliases', 'TEXT', 0, None, 0)
(26, 'member_of', 'TEXT', 0, None, 0)
(27, 'lastfm_url', 'TEXT', 0, None, 0)
(28, 'ended_year', 'INTEGER', 0, None, 0)

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
(22, 'added_timestamp', 'TIMESTAMP', 0, None, 0)
(23, 'added_day', 'INTEGER', 0, None, 0)
(24, 'added_week', 'INTEGER', 0, None, 0)
(25, 'added_month', 'INTEGER', 0, None, 0)
(26, 'added_year', 'INTEGER', 0, None, 0)
(27, 'origen', 'TEXT', 0, "'local'", 0)
(28, 'producers', 'TEXT', 0, None, 0)
(29, 'engineers', 'TEXT', 0, None, 0)
(30, 'mastering_engineers', 'TEXT', 0, None, 0)
(31, 'credits', 'JSON', 0, None, 0)
(32, 'musicbrainz_albumid', 'TEXT', 0, None, 0)
(33, 'musicbrainz_albumartistid', 'TEXT', 0, None, 0)
(34, 'musicbrainz_releasegroupid', 'TEXT', 0, None, 0)
(35, 'catalognumber', 'TEXT', 0, None, 0)
(36, 'media', 'TEXT', 0, None, 0)
(37, 'discnumber', 'TEXT', 0, None, 0)
(38, 'releasecountry', 'TEXT', 0, None, 0)
(39, 'originalyear', 'INTEGER', 0, None, 0)
(40, 'catalog_number', 'TEXT', 0, None, 0)

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

Estructura de la tabla: scrobbles_huanitochico
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'artist_name', 'TEXT', 1, None, 0)
(2, 'artist_mbid', 'TEXT', 0, None, 0)
(3, 'name', 'TEXT', 1, None, 0)
(4, 'album_name', 'TEXT', 0, None, 0)
(5, 'album_mbid', 'TEXT', 0, None, 0)
(6, 'timestamp', 'INTEGER', 1, None, 0)
(7, 'fecha_scrobble', 'TIMESTAMP', 1, None, 0)
(8, 'lastfm_url', 'TEXT', 0, None, 0)
(9, 'fecha_adicion', 'TIMESTAMP', 0, 'CURRENT_TIMESTAMP', 0)
(10, 'reproducciones', 'INTEGER', 0, '1', 0)
(11, 'fecha_reproducciones', 'TEXT', 0, None, 0)

Estructura de la tabla: lastfm_config
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'lastfm_username', 'TEXT', 0, None, 0)
(2, 'last_timestamp', 'INTEGER', 0, None, 0)
(3, 'last_updated', 'TIMESTAMP', 0, None, 0)

Estructura de la tabla: album_links
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'album_id', 'INTEGER', 0, None, 0)
(2, 'album_name', 'TEXT', 0, None, 0)
(3, 'artist_name', 'TEXT', 0, None, 0)
(4, 'lastfm_url', 'TEXT', 0, None, 0)
(5, 'spotify_url', 'TEXT', 0, None, 0)
(6, 'spotify_id', 'TEXT', 0, None, 0)
(7, 'youtube_url', 'TEXT', 0, None, 0)
(8, 'musicbrainz_url', 'TEXT', 0, None, 0)
(9, 'discogs_url', 'TEXT', 0, None, 0)
(10, 'bandcamp_url', 'TEXT', 0, None, 0)
(11, 'apple_music_url', 'TEXT', 0, None, 0)
(12, 'rateyourmusic_url', 'TEXT', 0, None, 0)
(13, 'links_updated', 'TIMESTAMP', 0, 'CURRENT_TIMESTAMP', 0)

Estructura de la tabla: sqlite_stat1
(0, 'tbl', '', 0, None, 0)
(1, 'idx', '', 0, None, 0)
(2, 'stat', '', 0, None, 0)

Estructura de la tabla: sqlite_stat4
(0, 'tbl', '', 0, None, 0)
(1, 'idx', '', 0, None, 0)
(2, 'neq', '', 0, None, 0)
(3, 'nlt', '', 0, None, 0)
(4, 'ndlt', '', 0, None, 0)
(5, 'sample', '', 0, None, 0)

Estructura de la tabla: artists_networks
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'artist_id', 'INTEGER', 0, None, 0)
(2, 'artist_name', 'TEXT', 0, None, 0)
(3, 'allmusic', 'TEXT', 0, None, 0)
(4, 'bandcamp', 'TEXT', 0, None, 0)
(5, 'boomkat', 'TEXT', 0, None, 0)
(6, 'facebook', 'TEXT', 0, None, 0)
(7, 'twitter', 'TEXT', 0, None, 0)
(8, 'mastodon', 'TEXT', 0, None, 0)
(9, 'bluesky', 'TEXT', 0, None, 0)
(10, 'instagram', 'TEXT', 0, None, 0)
(11, 'spotify', 'TEXT', 0, None, 0)
(12, 'lastfm', 'TEXT', 0, None, 0)
(13, 'wikipedia', 'TEXT', 0, None, 0)
(14, 'juno', 'TEXT', 0, None, 0)
(15, 'soundcloud', 'TEXT', 0, None, 0)
(16, 'youtube', 'TEXT', 0, None, 0)
(17, 'imdb', 'TEXT', 0, None, 0)
(18, 'progarchives', 'TEXT', 0, None, 0)
(19, 'setlist_fm', 'TEXT', 0, None, 0)
(20, 'who_sampled', 'TEXT', 0, None, 0)
(21, 'vimeo', 'TEXT', 0, None, 0)
(22, 'genius', 'TEXT', 0, None, 0)
(23, 'myspace', 'TEXT', 0, None, 0)
(24, 'tumblr', 'TEXT', 0, None, 0)
(25, 'resident_advisor', 'TEXT', 0, None, 0)
(26, 'rateyourmusic', 'TEXT', 0, None, 0)
(27, 'enlaces', 'TEXT', 0, None, 0)
(28, 'last_updated', 'TIMESTAMP', 0, 'CURRENT_TIMESTAMP', 0)
(29, 'musicbrainz', 'TEXT', 0, None, 0)
(30, 'discogs', 'TEXT', 0, None, 0)
(31, 'discogs_http', 'TEXT', 0, None, 0)

Estructura de la tabla: discogs_discography
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'artist_id', 'INTEGER', 1, None, 0)
(2, 'album_id', 'INTEGER', 0, None, 0)
(3, 'album_name', 'TEXT', 1, None, 0)
(4, 'type', 'TEXT', 0, None, 0)
(5, 'main_release', 'INTEGER', 0, None, 0)
(6, 'role', 'TEXT', 0, None, 0)
(7, 'resource_url', 'TEXT', 0, None, 0)
(8, 'year', 'INTEGER', 0, None, 0)
(9, 'thumb', 'TEXT', 0, None, 0)
(10, 'stats_comm_wantlist', 'INTEGER', 0, None, 0)
(11, 'stats_comm_coll', 'INTEGER', 0, None, 0)
(12, 'user_wantlist', 'INTEGER', 0, '0', 0)
(13, 'user_coll', 'INTEGER', 0, '0', 0)
(14, 'format', 'TEXT', 0, None, 0)
(15, 'label', 'TEXT', 0, None, 0)
(16, 'status', 'TEXT', 0, None, 0)
(17, 'discogs_id', 'INTEGER', 0, None, 0)
(18, 'last_updated', 'TIMESTAMP', 0, 'CURRENT_TIMESTAMP', 0)
