#!/bin/bash
# Estado de las actualizaciones largas de la db (se ejecuta en pepecono).
#   ssh pepecono 'cd ~/gits/pollo/music-fuzzy && db/tools/estado_actualizaciones.sh'
cd "$(dirname "$0")/../.." || exit 1
DB=db/sqlite/musica_local.sqlite
LOGS=db/sqlite/logs
q() { sqlite3 -readonly "$DB" "$1" 2>/dev/null || echo "  (aún no existe)"; }
tabla() { [ -n "$(sqlite3 -readonly "$DB" "SELECT 1 FROM sqlite_master WHERE name='$1'")" ]; }
col() { [ -n "$(sqlite3 -readonly "$DB" "SELECT 1 FROM pragma_table_info('$1') WHERE name='$2'")" ]; }

echo "== $(date '+%F %T')"
echo "== En marcha"
pgrep -af "[d]b_creator.py" | sed -E 's/.*--scripts ([^ ]+).*/  db_creator: \1/'
pgrep -af "[c]aratulas_moode.py" | sed 's/^/  /' | cut -c1-120
pgrep -f "[d]b_creator.py|[c]aratulas_moode.py" >/dev/null || echo "  nada"

echo "== Último cron diario"
ultimo=$(ls -t $LOGS/*_0400.log 2>/dev/null | head -1)
if [ -n "$ultimo" ]; then
    echo "  $ultimo ($(stat -c '%y' "$ultimo" | cut -c1-16))"
    grep -aE "^=== Ejecutando|Bandcamp: [0-9]+/[0-9]+ encontrados|^.{23} - INFO - Hecho:" "$ultimo" | grep -v module.name | sed 's/^/  /' | cut -c1-160
    echo "  Discogs sin release que coincida: $(grep -a 'ninguna release coincide' "$ultimo" | grep -vc module.name)"
fi

echo "== Carátulas de moode (~/caratulas_moode)"
if [ -f ~/caratulas_moode/log.txt ]; then
    awk '{print $1}' ~/caratulas_moode/log.txt | sort | uniq -c | sed 's/^/  /'
    echo "  última: $(tail -1 ~/caratulas_moode/log.txt | cut -c1-110)"
fi

echo "== Singles (musicbrainz/mb_singles)"
[ -f $LOGS/mb_singles_lanzador.out ] && grep -aE "^inicio|^fin|pendientes|/[0-9]+ en|Hecho|Ya hay|Traceback" $LOGS/mb_singles_lanzador.out | tail -3 | sed 's/^/  /' | cut -c1-160
if col artists singles_checked; then
    q "SELECT '  artistas mirados ' || count(singles_checked) || ' de ' || sum(coalesce(mbid,'') != '') FROM artists"
fi
if tabla album_singles; then
    q "SELECT '  album_singles ' || count(*) || ' en ' || count(DISTINCT album_id) || ' álbumes' FROM album_singles"
    q "SELECT '  album_singles_otros ' || group_concat(tipo || ' ' || n, ', ') FROM (SELECT tipo, count(*) n FROM album_singles_otros GROUP BY 1)"
fi

echo "== Recopilatorios y remezclas"
tabla song_appearances && q "SELECT '  song_appearances ' || count(*) FROM song_appearances" || echo "  sin empezar"

echo "== Enlaces (enlaces/enlaces_artista_album)"
q "SELECT '  Discogs: con enlace ' || count(discogs_url) || ', sin buscar ' || sum(discogs_url IS NULL AND links_updated IS NULL) || ', buscados sin release ' || sum(discogs_url IS NULL AND links_updated IS NOT NULL) || ' de ' || count(*) FROM albums"
q "SELECT '  Bandcamp: con enlace ' || count(bandcamp_url) || ' (id ' || count(bandcamp_album_id) || '), sin buscar ' || sum(bandcamp_url IS NULL AND bandcamp_checked IS NULL) || ', buscados sin enlace ' || sum(bandcamp_url IS NULL AND bandcamp_checked IS NOT NULL) FROM albums"

echo "== Géneros y créditos (generos/generos_creditos)"
q "SELECT '  consultados: Discogs ' || count(discogs_checked) || ', MusicBrainz ' || count(mb_checked) || ', Last.fm ' || count(lastfm_checked) || ' · sin ninguno ' || sum(discogs_checked IS NULL AND mb_checked IS NULL AND lastfm_checked IS NULL) || ' de ' || count(*) FROM albums"
q "SELECT '  con datos: Discogs ' || count(discogs_genres) || ', MusicBrainz ' || count(mb_genres) || ', Last.fm ' || count(lastfm_tags) || ', créditos ' || count(credits) FROM albums"

echo "== Sellos (musicbrainz/mb_sellos)"
q "SELECT '  labels ' || count(*) || ' (MusicBrainz ' || count(mb_last_updated) || ', Discogs ' || count(nullif(discogs_url, '')) || ', perfil ' || count(nullif(profile, '')) || '), última ' || coalesce(max(mb_last_updated), '-') FROM labels"
q "SELECT '  sellos de albums sin ficha: ' || count(DISTINCT a.label) FROM albums a WHERE coalesce(a.label, '') != '' AND NOT EXISTS (SELECT 1 FROM labels l WHERE lower(l.name) = lower(a.label))"
