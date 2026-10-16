"""
Shared descriptions for all database-populating scripts.
Used in the wizard (db_creator_ui_module) and as tooltips in the table module
(ui_db_creator_module).
"""
from modules.submodules.db.db_music_path_module import DBMusicPathModule
from modules.submodules.db.lastfm_module import LastFMModule

SCRIPT_DESCRIPTIONS = {
    'path/db_musica_path':               DBMusicPathModule.DESCRIPTION,
    'lastfm_escuchas':                   LastFMModule.DESCRIPTION,
    'path/db_musica_spotify':            'Asocia artistas y álbumes con sus IDs de Spotify para enriquecer la BD con popularidad, géneros e imágenes.',
    'enlaces/enlaces_artista_album':     'Obtiene URLs de artistas y álbumes desde múltiples servicios: Bandcamp, YouTube, Spotify, Discogs, LastFM, MusicBrainz, etc.',
    'enlaces/redes_sociales':            'Busca y almacena enlaces a redes sociales (Instagram, Twitter, Facebook, etc.) de los artistas.',
    'enlaces/yt_song_links':             'Obtiene URLs de YouTube para cada canción de la BD.',
    'enlaces/enlaces_canciones':         'Recopila enlaces a canciones en Last.fm, Spotify, Bandcamp, SoundCloud y YouTube.',
    'enlaces/spotify_preview_urls':      'Descarga URLs de preview de 30 segundos de Spotify para cada canción.',
    'enlaces/enlaces_albumes':           'Obtiene URLs de álbumes en servicios externos.',
    'img/portadas_artistas':             'Descarga imágenes de artistas y portadas de álbumes desde Spotify y MusicBrainz.',
    'letras/letras_genius_ovh':          'Descarga letras de canciones usando las APIs de Genius, Happi y Musixmatch.',
    'wiki/wikilinks_desde_mb':           'Obtiene enlaces de Wikipedia para artistas y álbumes desde MusicBrainz.',
    'listenbrainz/listens_listenbrainz': 'Importa escuchas desde ListenBrainz con reconciliación por MBID y coincidencia difusa.',
    'musicbrainz/mb_sellos':             'Obtiene información de sellos discográficos (MusicBrainz): Wikipedia, Discogs, relaciones.',
    'musicbrainz/mb_data_canciones':     'Enriquece canciones con datos de MusicBrainz: ISRC, duración, relaciones.',
    'musicbrainz/mb_release_group':      'Descarga grupos de lanzamientos (release groups) de MusicBrainz.',
    'musicbrainz/mb_discografia':        'Descarga la discografía completa de artistas desde MusicBrainz.',
    'discogs/discografia_masters':       'Importa masters de Discogs (álbumes canónicos) con formatos aceptados configurables.',
    'discogs/artists_info':              'Obtiene información biográfica y de estilo de artistas desde Discogs.',
    'discogs/discografia_releases_info': 'Descarga información detallada de lanzamientos de Discogs.',
    'setlistfm/setlists':                'Importa setlists de conciertos desde Setlist.fm.',
    'posts/review_scrapper':             'Extrae y almacena reseñas de álbumes desde Metacritic y AOTY para los álbumes de la BD.',
    'posts/posts_fresh_rss':             'Busca menciones de artistas y álbumes en artículos de FreshRSS (blogs, revistas).',
    'posts/menciones':                   'Procesa y almacena menciones de entidades de la BD encontradas en posts.',
    'rateyourmusic/rym_artists_links':   'Obtiene URLs de artistas en RateYourMusic usando SearXNG.',
    'rateyourmusic/rym_artists_info':    'Extrae información de artistas de RateYourMusic vía scraping (requiere navegador).',
    'rateyourmusic/rym_albums_links':    'Obtiene URLs de álbumes en RateYourMusic usando SearXNG.',
    'charts/uk_csv':                     'Importa charts del Reino Unido desde CSVs históricos.',
    'charts/billboard_csv':              'Importa charts de Billboard desde CSVs históricos.',
    'charts/spain_charts':               'Importa charts históricos de España (radio y streaming).',
    'charts/uk_indie_nme':               'Importa charts indie del Reino Unido y listas históricas de NME.',
    'posts/equipboard_artists':          'Busca artistas de la BD en Equipboard (instrumentos usados por músicos).',
    'posts/equipboard_instruments':      'Extrae qué instrumentos usa cada artista según Equipboard.',
    'posts/equipboard_details':          'Obtiene detalles de equipamiento (marca, modelo) desde Equipboard.',
    'libros/epubs':                      'Escanea EPUBs buscando menciones de artistas y álbumes de la BD.',
    'optimiza_db_lastpass':              'Ejecuta VACUUM, ANALYZE y reindexado para optimizar el rendimiento de la BD.',
    'descargas/orpheus':                 'Gestiona descargas de música desde Orpheus (requiere cuenta y token de API).',
    'similares/musicmap':                'Obtiene artistas similares desde MusicMap vía scraping.',
    'descargas/rutracker':               'Busca y gestiona descargas desde RuTracker vía Jackett.',
}
