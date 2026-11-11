#!/bin/bash
# Discos recién descargados → db de music-fuzzy (solo en pepecono).
#
# El script de fin de descarga de qBittorrent (contenedor qbittorrent_musica,
# scripts/descarga_completa_gpt.sh) deja un .txt por disco copiado en la cola.
# Un timer de systemd lanza esto cada 5 min: si hay algo en cola, ejecuta el
# preset «nuevo» (escanea la carpeta de música y busca géneros y créditos de
# los álbumes más recientes) y exporta la instantánea sin reiniciar repeat-one;
# Syncthing la lleva al PC y mover_mix_playerctl.py la lee de ahí.
set -u
COLA=/home/pepe/contenedores/musica/qbittorrent/scripts/cola_mfuzz
REPO=$(cd "$(dirname "$0")" && pwd)
CANDADO="$REPO/db/sqlite/.actualizar_db.lock"

shopt -s nullglob
pendientes=("$COLA"/*.txt)
[ ${#pendientes[@]} -eq 0 ] && exit 0

# Si el cron (u otra ejecución) está escribiendo la db, se deja para la próxima vuelta
if ! flock -n "$CANDADO" true; then
    echo "$(date '+%F %T') db ocupada; ${#pendientes[@]} en cola, se reintenta luego"
    exit 0
fi

echo "$(date '+%F %T') ${#pendientes[@]} disco(s) nuevo(s): $(cat "${pendientes[@]}" | paste -sd '|')"
cd "$REPO" || exit 1
# Se procesan los que había al empezar; lo que llegue mientras, en la siguiente vuelta.
# Se borran pase lo que pase: si algo falla, el cron diario lo recoge igualmente.
./actualizar_db.py run nuevo --sin-subir --param limite=40
codigo=$?
rm -f "${pendientes[@]}"
exit $codigo
