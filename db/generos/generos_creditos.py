#!/usr/bin/env python3
"""
Géneros y créditos de los álbumes de la colección, para consultarlos sin red.

Por cada álbum local guarda en `albums`:
  - discogs_genres, discogs_styles  ← la release de `discogs_url` (api.discogs.com)
  - mb_genres                        ← el release group del `mbid` (MusicBrainz)
  - lastfm_tags                      ← album.getTopTags (Last.fm)
  - producers, engineers, mastering_engineers, credits ← extraartists de la
    release de Discogs, solo si están vacíos (mismo formato que enlaces_artista_album)
El género de las etiquetas ya lo guarda db_musica_path en `albums.genre`.

Cada fuente marca cuándo se consultó (*_checked): un álbum no se vuelve a
consultar hasta pasados `reintentar_dias` días si la fuente no tenía nada.
Los álbumes más recientes van primero, para que los recién descargados
tengan sus datos enseguida (lo lanza también la cola de qBittorrent).

Config (config_database_creator.json, sección "generos/generos_creditos"):
  limite           álbumes por ejecución (por defecto 600, ~30 min)
  reintentar_dias  días antes de reintentar una fuente que no tenía datos (30)
  fuentes          lista de fuentes a consultar: discogs, musicbrainz, lastfm
"""
import json
import logging
import os
import re
import sqlite3
import sys
import time
import unicodedata
from datetime import datetime, timedelta

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base.db_connection import apply_pragmas  # noqa: E402

USER_AGENT = "music-fuzzy/1.0 (generos_creditos)"
# Fallo de red o del servicio: la fuente queda pendiente, no se marca como consultada
ERROR = object()
TIMEOUT = 20
FUENTES = ("discogs", "musicbrainz", "lastfm")
# Pausa entre peticiones a cada servicio (Discogs: 60/min con token; MusicBrainz: 1/s)
PAUSA = {"discogs": 1.1, "musicbrainz": 1.1, "lastfm": 0.25}
# Etiquetas de Last.fm que no son géneros
LASTFM_RUIDO = re.compile(r"^(albums? i own|favou?rites?|seen live|my |\d{2,4}s?$|best of|awesome|amazing|"
                          r"love|beautiful|cool|great|vinyl|cd$|owned|to listen|check out|boring|overrated|meh|shit|crap|emo$|\w+ records$)", re.I)

COLUMNAS = {
    "discogs_genres": "TEXT", "discogs_styles": "TEXT", "discogs_checked": "TIMESTAMP",
    "mb_genres": "TEXT", "mb_checked": "TIMESTAMP",
    "lastfm_tags": "TEXT", "lastfm_checked": "TIMESTAMP",
}

logger = logging.getLogger("generos_creditos")


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    texto = re.sub(r"\s*\(\d+\)\s*$", "", texto)          # 'Grimes (4)' de Discogs
    texto = re.sub(r"[(\[{].*?[)\]}]", " ", texto)          # '(Deluxe)', '[Remastered]'
    texto = texto.replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", texto).split())


def parecidos(a, b):
    a, b = normalizar(a), normalizar(b)
    return bool(a) and bool(b) and (a == b or a in b or b in a)


class Generos:
    def __init__(self, config):
        self.db_path = config["db_path"]
        self.discogs_token = config.get("discogs_token", "")
        self.lastfm_key = config.get("lastfm_api_key", "")
        self.limite = int(config.get("limite", 600))
        self.reintentar = timedelta(days=int(config.get("reintentar_dias", 30)))
        self.fuentes = [f for f in config.get("fuentes", FUENTES) if f in FUENTES]
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.ultima = {}

        self.conn = sqlite3.connect(self.db_path)
        apply_pragmas(self.conn)
        self.conn.row_factory = sqlite3.Row
        self._asegurar_columnas()

    def _asegurar_columnas(self):
        existentes = {r[1] for r in self.conn.execute("PRAGMA table_info(albums)")}
        for col, tipo in COLUMNAS.items():
            if col not in existentes:
                self.conn.execute(f"ALTER TABLE albums ADD COLUMN {col} {tipo}")
        self.conn.commit()

    def _get(self, servicio, url, **kw):
        espera = PAUSA[servicio] - (time.monotonic() - self.ultima.get(servicio, 0))
        if espera > 0:
            time.sleep(espera)
        try:
            for intento in range(3):
                r = self.session.get(url, timeout=TIMEOUT, **kw)
                self.ultima[servicio] = time.monotonic()
                if r.status_code in (429, 503):  # límite de peticiones: esperar y reintentar
                    time.sleep(30 * (intento + 1))
                    continue
                if r.status_code == 404:
                    return None
                if r.status_code >= 400:
                    logger.warning(f"{servicio}: HTTP {r.status_code}")
                    return ERROR
                return r.json()
        except (requests.RequestException, ValueError) as e:
            # Sin la URL: lleva el token de Discogs o la clave de Last.fm
            logger.warning(f"{servicio}: {type(e).__name__}")
        return ERROR

    # ── Selección ────────────────────────────────────────────────────────────

    def pendientes(self):
        """Álbumes locales con alguna fuente sin consultar (o a reintentar)."""
        limite_fecha = (datetime.now() - self.reintentar).isoformat(sep=" ")
        condiciones = []
        for fuente, col_datos, col_check in (("discogs", "discogs_genres", "discogs_checked"),
                                             ("musicbrainz", "mb_genres", "mb_checked"),
                                             ("lastfm", "lastfm_tags", "lastfm_checked")):
            if fuente in self.fuentes:
                condiciones.append(f"({col_check} IS NULL OR (coalesce({col_datos}, '') = '' "
                                   f"AND {col_check} < '{limite_fecha}'))")
        if not condiciones:
            return []
        return self.conn.execute(f"""
            SELECT al.id, al.name, ar.name AS artist, al.discogs_url, al.mbid, coalesce(al.label, '') AS label,
                   al.discogs_checked, al.mb_checked, al.lastfm_checked,
                   al.discogs_genres, al.mb_genres, al.lastfm_tags,
                   coalesce(al.credits, '') AS credits
            FROM albums al JOIN artists ar ON ar.id = al.artist_id
            WHERE al.origen = 'local' AND ({' OR '.join(condiciones)})
            ORDER BY coalesce(al.added_timestamp, al.last_updated) DESC
            LIMIT ?
        """, (self.limite,)).fetchall()

    def _toca(self, album, fuente, col_datos, col_check):
        if fuente not in self.fuentes:
            return False
        if album[col_check] is None:
            return True
        return not album[col_datos] and album[col_check] < (datetime.now() - self.reintentar).isoformat(sep=" ")

    # ── Fuentes ──────────────────────────────────────────────────────────────

    def discogs(self, album):
        """(géneros, estilos, créditos) de la release enlazada, si es de este disco."""
        m = re.search(r"/release/(\d+)", album["discogs_url"] or "")
        if not m:
            return None
        headers = {"Authorization": f"Discogs token={self.discogs_token}"} if self.discogs_token else {}
        data = self._get("discogs", f"https://api.discogs.com/releases/{m.group(1)}", headers=headers)
        if data is ERROR or not data:
            return data
        # discogs_url lo pone enlaces_artista_album buscando por nombre: comprobar que es el disco
        artistas = [a.get("name", "") for a in data.get("artists", [])]
        if not (parecidos(data.get("title", ""), album["name"])
                and any(parecidos(a, album["artist"]) for a in artistas)):
            logger.info(f"Discogs {m.group(1)} no es «{album['artist']} - {album['name']}» "
                        f"sino «{', '.join(artistas)} - {data.get('title')}»: se ignora")
            return None

        creditos = {}
        extra = list(data.get("extraartists", []))
        for pista in data.get("tracklist", []):
            extra += pista.get("extraartists", [])
        for e in extra:
            nombre = re.sub(r"\s*\(\d+\)\s*$", "", e.get("anv") or e.get("name") or "").strip()
            for rol in (e.get("role") or "").split(","):
                rol = re.sub(r"\s*\[.*?\]", "", rol).strip().lower()
                if nombre and rol and nombre not in creditos.setdefault(rol, []):
                    creditos[rol].append(nombre)
        return data.get("genres", []), data.get("styles", []), creditos

    def musicbrainz(self, album):
        """Géneros del release group (o, si no tiene, de la release)."""
        if not album["mbid"]:
            # Puede que mb_release_group ya lo tenga enlazado
            fila = self.conn.execute("SELECT genre FROM mb_release_group WHERE album_id = ? AND coalesce(genre, '') <> ''",
                                     (album["id"],)).fetchone()
            return [g.strip() for g in fila[0].split(",") if g.strip()] if fila else None
        data = self._get("musicbrainz", f"https://musicbrainz.org/ws/2/release/{album['mbid']}",
                         params={"inc": "release-groups+genres", "fmt": "json"})
        if data is ERROR or not data:
            return data
        generos = data.get("release-group", {}).get("genres") or data.get("genres") or []
        generos = sorted(generos, key=lambda g: -g.get("count", 0))
        return [g["name"] for g in generos if g.get("name")]

    def lastfm(self, album):
        if not self.lastfm_key:
            return None
        data = self._get("lastfm", "https://ws.audioscrobbler.com/2.0/", params={
            "method": "album.gettoptags", "artist": album["artist"], "album": album["name"],
            "autocorrect": 1, "api_key": self.lastfm_key, "format": "json"})
        if data is ERROR:
            return data
        if not data or "toptags" not in data:
            return None
        tags = data["toptags"].get("tag", [])
        tags = tags if isinstance(tags, list) else [tags]
        # Las etiquetas con pocos votos suelen ser de una sola persona
        sello = normalizar(album["label"])
        return [t["name"] for t in tags if int(t.get("count", 0)) >= 10 and not LASTFM_RUIDO.match(t["name"])
                and normalizar(t["name"]) not in (sello, normalizar(album["artist"]), normalizar(album["name"]))][:8]

    # ── Proceso ──────────────────────────────────────────────────────────────

    def procesar(self, album):
        ahora = datetime.now().isoformat(sep=" ", timespec="seconds")
        cambios = {}
        if self._toca(album, "discogs", "discogs_genres", "discogs_checked"):
            r = self.discogs(album)
            if r is not ERROR:
                cambios["discogs_checked"] = ahora
            if r and r is not ERROR:
                generos, estilos, creditos = r
                cambios["discogs_genres"] = ", ".join(generos)
                cambios["discogs_styles"] = ", ".join(estilos)
                if creditos and album["credits"] in ("", "[]", "{}"):
                    def con(*claves, sin=()):
                        return ", ".join(dict.fromkeys(
                            n for rol, nombres in creditos.items()
                            if any(c in rol for c in claves) and not any(s in rol for s in sin)
                            for n in nombres)) or None
                    cambios["credits"] = json.dumps(creditos, ensure_ascii=False)
                    cambios["producers"] = con("produc")
                    cambios["engineers"] = con("engineer", sin=("master",))
                    cambios["mastering_engineers"] = con("master")
        if self._toca(album, "musicbrainz", "mb_genres", "mb_checked"):
            r = self.musicbrainz(album)
            if r is not ERROR:
                cambios["mb_checked"] = ahora
            if r and r is not ERROR:
                cambios["mb_genres"] = ", ".join(r)
        if self._toca(album, "lastfm", "lastfm_tags", "lastfm_checked"):
            r = self.lastfm(album)
            if r is not ERROR:
                cambios["lastfm_checked"] = ahora
            if r and r is not ERROR:
                cambios["lastfm_tags"] = ", ".join(r)
        if cambios:
            self.conn.execute(f"UPDATE albums SET {', '.join(f'{c} = ?' for c in cambios)} WHERE id = ?",
                              (*cambios.values(), album["id"]))
            self.conn.commit()
        return cambios

    def run(self):
        albumes = self.pendientes()
        logger.info(f"{len(albumes)} álbumes pendientes (límite {self.limite}), fuentes: {', '.join(self.fuentes)}")
        inicio = time.monotonic()
        con_datos = {"discogs_genres": 0, "mb_genres": 0, "lastfm_tags": 0, "credits": 0}
        for n, album in enumerate(albumes, 1):
            try:
                cambios = self.procesar(album)
            except Exception as e:  # un álbum raro no debe parar el resto
                logger.warning(f"{album['artist']} - {album['name']}: {e}")
                continue
            for col in con_datos:
                con_datos[col] += bool(cambios.get(col))
            if n % 50 == 0:
                logger.info(f"{n}/{len(albumes)} en {(time.monotonic() - inicio) / 60:.1f} min")
        logger.info(f"Hecho: {len(albumes)} álbumes en {(time.monotonic() - inicio) / 60:.1f} min · "
                    f"nuevos datos: Discogs {con_datos['discogs_genres']}, MusicBrainz {con_datos['mb_genres']}, "
                    f"Last.fm {con_datos['lastfm_tags']}, créditos {con_datos['credits']}")
        self.conn.close()


def main(config=None):
    if config is None:
        import argparse
        ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        ap.add_argument("--db-path", required=True)
        ap.add_argument("--discogs-token", default=os.getenv("DISCOGS_TOKEN", ""))
        ap.add_argument("--lastfm-api-key", default=os.getenv("LASTFM_API_KEY", ""))
        ap.add_argument("--limite", type=int, default=600)
        args = ap.parse_args()
        config = {"db_path": args.db_path, "discogs_token": args.discogs_token,
                  "lastfm_api_key": args.lastfm_api_key, "limite": args.limite}
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    Generos(config).run()


if __name__ == "__main__":
    main()
