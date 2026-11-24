#!/usr/bin/env python3
"""
Singles de cada álbum de la colección, desde MusicBrainz.

Por cada artista con MBID pide una vez su lista de release groups (todos los
tipos, de 100 en 100) y cruza los singles con las pistas de sus álbumes
locales. Cada single se asigna al primer álbum local (por fecha del release
group) que contiene la canción, y se guarda en una de dos tablas:

  album_singles        los singles del álbum: título sin remix/edit/directo,
                       sin tipo secundario (Remix, Live, Compilation...) y
                       publicados entre 2 años antes y 2 años después del álbum
  album_singles_otros  el resto de singles de esas canciones, con `tipo`:
                       remix, directo, reedicion (fuera de esas fechas) u otro

Columnas: album_id, song_id (la pista local), single_mbid (release group),
titulo, fecha, dias (días desde el álbum; negativo = antes del álbum) y,
en _otros, tipo.

Se marca artists.singles_checked y no se repite hasta pasados
`reintentar_dias`; al repetir se rehacen las filas de sus álbumes.

Config (config_database_creator.json, sección "musicbrainz/mb_singles"):
  limite           artistas por ejecución (300 por defecto, ~15 min; 0 = todos)
  reintentar_dias  días antes de volver a mirar un artista (90)
"""
import logging
import os
import re
import signal
import sqlite3
import sys
import threading
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import date, datetime, timedelta

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base.db_connection import apply_pragmas  # noqa: E402
from base.discos import normalizar  # noqa: E402

USER_AGENT = "music-fuzzy/1.0 (+https://github.com/volteret4/mfuz; mb_singles)"
API = "https://musicbrainz.org/ws/2/"
LIMITE = 60         # segundos como mucho por petición
PAUSA = 1.1          # MusicBrainz: 1 petición por segundo
EPOCA = 2 * 365      # días antes/después del álbum para ser «su» single
ERROR = object()
MAX_GRUPOS = 2000    # más release groups que esto no es un artista, es un cajón (no se pagina)
# Artistas especiales de MusicBrainz: millones de release groups y ningún single propio
ESPECIALES = (
    "89ad4ac3-39f7-470e-963a-56509c546377",  # Various Artists
    "125ec42a-7229-4250-afc5-e057484327fe",  # [unknown]
    "f731ccc4-e22a-43af-a747-64213329e088",  # [anonymous]
    "33cf029c-63b0-41a0-9855-be2a3665fb3b",  # [data]
    "eec63d3c-3b81-4ad4-b1e4-7c147d4d2b61",  # [no artist]
    "9be7f096-97ec-4615-8957-8d40b5dcbc41",  # [traditional]
    "314e1c25-dde7-4e4d-b2f4-0a7b9f7c56dc",  # [dialogue]
)

REMIX = re.compile(r"\b(remix(es|ed)?|rmx|mix|edit|rework|bootleg|dub|version|instrumental|"
                   r"acapella|a cappella|vip|flip|redux|reprise)\b", re.I)
DIRECTO = re.compile(r"\b(live|en directo|en vivo|acoustic|acustico|session)\b", re.I)

logger = logging.getLogger("mb_singles")


def _fecha(texto):
    """'1995-11-27' / '1995-11' / '1995' → date (día 1 / julio si falta)."""
    m = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", texto or "")
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2) or 7), int(m.group(3) or 1))
    except ValueError:
        return None


@contextmanager
def _plazo(segundos):
    """Corta la petición si tarda más de `segundos` en total (el timeout de
    requests solo mide el silencio entre bytes: una conexión que gotea o se
    queda a medias lo esquiva). Solo en el hilo principal, que es como se lanza."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    def _salta(*_):
        raise TimeoutError(f"más de {segundos} s")

    anterior = signal.signal(signal.SIGALRM, _salta)
    signal.alarm(segundos)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, anterior)


def _claves(titulo):
    """Títulos de canción con los que se compara: 'A / B' (doble cara A) da dos."""
    return {normalizar(t) for t in re.split(r"\s+/\s+", titulo or "")} - {""}


class Singles:
    def __init__(self, config):
        self.db_path = config["db_path"]
        self.limite = int(config.get("limite", 300))
        self.reintentar = timedelta(days=int(config.get("reintentar_dias", 90)))
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.ultima = 0.0
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        apply_pragmas(self.conn)
        self._asegurar_tablas()

    def _asegurar_tablas(self):
        c = self.conn
        comunes = """album_id INTEGER NOT NULL, song_id INTEGER, single_mbid TEXT NOT NULL,
                     titulo TEXT, fecha TEXT, dias INTEGER"""
        c.execute(f"CREATE TABLE IF NOT EXISTS album_singles ({comunes}, PRIMARY KEY (album_id, single_mbid))")
        c.execute(f"CREATE TABLE IF NOT EXISTS album_singles_otros ({comunes}, tipo TEXT, "
                  "PRIMARY KEY (album_id, single_mbid))")
        for t in ("album_singles", "album_singles_otros"):
            c.execute(f"CREATE INDEX IF NOT EXISTS idx_{t}_song ON {t}(song_id)")
        if "singles_checked" not in {r[1] for r in c.execute("PRAGMA table_info(artists)")}:
            c.execute("ALTER TABLE artists ADD COLUMN singles_checked TIMESTAMP")
        c.commit()

    # ── MusicBrainz ──────────────────────────────────────────────────────────

    def _get(self, ruta, **params):
        params["fmt"] = "json"
        for intento in range(4):
            espera = PAUSA - (time.monotonic() - self.ultima)
            if espera > 0:
                time.sleep(espera)
            try:
                with _plazo(LIMITE):
                    r = self.session.get(API + ruta, params=params, timeout=30)
            except (requests.RequestException, TimeoutError) as e:
                logger.warning(f"MusicBrainz: {type(e).__name__}")
                self.session.close()  # no reutilizar una conexión colgada
                return ERROR
            finally:
                self.ultima = time.monotonic()
            if r.status_code in (429, 503):
                time.sleep(15 * (intento + 1))
                continue
            if r.status_code == 404:
                return None
            if r.status_code >= 400:
                logger.warning(f"MusicBrainz: HTTP {r.status_code}")
                return ERROR
            return r.json()
        return ERROR

    def release_groups(self, artist_mbid):
        grupos, offset = [], 0
        while True:
            d = self._get("release-group", artist=artist_mbid, limit=100, offset=offset)
            if d is ERROR:
                return ERROR
            if d is None:
                return []
            if offset == 0 and d.get("release-group-count", 0) > MAX_GRUPOS:
                logger.warning(f"{artist_mbid}: {d['release-group-count']} release groups, se salta")
                return []
            grupos += d.get("release-groups", [])
            offset += 100
            if offset >= d.get("release-group-count", 0) or not d.get("release-groups"):
                return grupos

    # ── Colección local ──────────────────────────────────────────────────────

    def artistas_pendientes(self):
        limite_fecha = (datetime.now() - self.reintentar).isoformat(sep=" ")
        filas = self.conn.execute(f"""
            SELECT ar.id, ar.name, ar.mbid FROM artists ar
            WHERE coalesce(ar.mbid, '') != ''
              AND lower(ar.mbid) NOT IN ({",".join("?" * len(ESPECIALES))})
              AND EXISTS (SELECT 1 FROM albums al WHERE al.artist_id = ar.id)
              AND (ar.singles_checked IS NULL OR ar.singles_checked < ?)
            ORDER BY ar.singles_checked IS NOT NULL, ar.singles_checked, ar.id DESC""",
                                  (*ESPECIALES, limite_fecha)).fetchall()
        return filas[:self.limite] if self.limite else filas

    def albumes(self, artist_id, artist_name):
        """Álbumes del artista con sus pistas y su release group (el más común entre sus pistas)."""
        res = []
        for al in self.conn.execute("SELECT id, name, year, folder_path FROM albums WHERE artist_id = ?",
                                    (artist_id,)):
            pistas = self.conn.execute("""
                SELECT id, title, musicbrainz_releasegroupid AS rg FROM songs
                WHERE (folder_path = ? AND ? IS NOT NULL) OR (album = ? AND (album_artist = ? OR artist = ?))""",
                                       (al["folder_path"], al["folder_path"], al["name"], artist_name,
                                        artist_name)).fetchall()
            if not pistas:
                continue
            rgs = Counter(p["rg"] for p in pistas if p["rg"])
            res.append({"id": al["id"], "name": al["name"], "year": al["year"],
                        "rg": rgs.most_common(1)[0][0] if rgs else None,
                        "pistas": [(p["id"], k) for p in pistas for k in _claves(p["title"])]})
        return res

    # ── Cruce ────────────────────────────────────────────────────────────────

    def procesar(self, artista):
        grupos = self.release_groups(artista["mbid"])
        if grupos is ERROR:
            return None
        fecha_rg = {g["id"]: _fecha(g.get("first-release-date")) for g in grupos}
        albumes = self.albumes(artista["id"], artista["name"])
        for a in albumes:
            a["fecha"] = fecha_rg.get(a["rg"]) or _fecha(a["year"])
        # canción → álbumes que la tienen, el más antiguo primero
        por_cancion = defaultdict(list)
        for a in sorted(albumes, key=lambda a: a["fecha"] or date.max):
            for song_id, clave in a["pistas"]:
                if all(x[0]["id"] != a["id"] for x in por_cancion[clave]):
                    por_cancion[clave].append((a, song_id))

        exactos, otros = [], []
        for g in grupos:
            if g.get("primary-type") != "Single":
                continue
            claves = _claves(g.get("title"))
            destino = next((por_cancion[k][0] for k in claves if por_cancion.get(k)), None)
            if not destino:
                continue  # single de una canción que no está en ningún álbum local
            album, song_id = destino
            f = _fecha(g.get("first-release-date"))
            dias = (f - album["fecha"]).days if f and album["fecha"] else None
            secundarios = {s.lower() for s in g.get("secondary-types") or []}
            titulo = g.get("title") or ""
            if "remix" in secundarios or "dj-mix" in secundarios or REMIX.search(titulo):
                tipo = "remix"
            elif "live" in secundarios or DIRECTO.search(titulo):
                tipo = "directo"
            elif secundarios:
                tipo = "otro"
            elif dias is not None and abs(dias) <= EPOCA:
                tipo = None
            else:
                tipo = "reedicion"
            fila = (album["id"], song_id, g["id"], titulo, g.get("first-release-date"), dias)
            (exactos if tipo is None else otros).append(fila if tipo is None else fila + (tipo,))

        ids = [a["id"] for a in albumes]
        marcas = ",".join("?" * len(ids))
        with self.conn:
            if ids:
                self.conn.execute(f"DELETE FROM album_singles WHERE album_id IN ({marcas})", ids)
                self.conn.execute(f"DELETE FROM album_singles_otros WHERE album_id IN ({marcas})", ids)
            self.conn.executemany("INSERT OR REPLACE INTO album_singles VALUES (?, ?, ?, ?, ?, ?)", exactos)
            self.conn.executemany("INSERT OR REPLACE INTO album_singles_otros VALUES (?, ?, ?, ?, ?, ?, ?)", otros)
            self.conn.execute("UPDATE artists SET singles_checked = ? WHERE id = ?",
                              (datetime.now().isoformat(sep=" ", timespec="seconds"), artista["id"]))
        return len(exactos), len(otros)

    def run(self):
        artistas = self.artistas_pendientes()
        logger.info(f"{len(artistas)} artistas pendientes (límite {self.limite or 'ninguno'})")
        inicio = time.monotonic()
        total_e = total_o = errores = 0
        for n, artista in enumerate(artistas, 1):
            try:
                r = self.procesar(artista)
            except Exception as e:  # un artista raro no debe parar el resto
                logger.warning(f"{artista['name']}: {type(e).__name__}: {e}")
                r = None
            if r is None:
                errores += 1
            else:
                total_e += r[0]
                total_o += r[1]
            if n % 50 == 0:
                logger.info(f"{n}/{len(artistas)} en {(time.monotonic() - inicio) / 60:.1f} min · "
                            f"singles {total_e}, otros {total_o}")
        logger.info(f"Hecho: {len(artistas)} artistas en {(time.monotonic() - inicio) / 60:.1f} min · "
                    f"singles {total_e}, otros {total_o}, sin respuesta {errores}")
        self.conn.close()


def main(config=None):
    if config is None:
        import argparse
        ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        ap.add_argument("--db-path", required=True)
        ap.add_argument("--limite", type=int, default=300)
        ap.add_argument("--reintentar-dias", type=int, default=90)
        a = ap.parse_args()
        config = {"db_path": a.db_path, "limite": a.limite, "reintentar_dias": a.reintentar_dias}
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    Singles(config).run()


if __name__ == "__main__":
    main()
