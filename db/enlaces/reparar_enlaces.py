#!/usr/bin/env python3
"""
Revisa las discogs_url y bandcamp_url ya guardadas en `albums` y quita las que
no son del disco.

enlaces_artista_album guardaba, cuando no había una buena coincidencia, el
primer resultado de la búsqueda de Discogs o de Bandcamp, a veces de otro
artista (discos homónimos). Para cada álbum con enlace:

  - Discogs: pide la release a la API y comprueba artista y título
    (db/base/discos.py, criterio tolerante: el título puede contener al otro,
    el artista tiene que coincidir). Si no es el disco se borran discogs_url y
    lo que salió de esa release: producers, engineers, mastering_engineers,
    credits, discogs_genres y discogs_styles; así enlaces_artista_album la
    vuelve a buscar (con el criterio estricto) y generos_creditos rellena los
    créditos y géneros de la nueva.
  - Bandcamp: descarga la página y comprueba artista, título y que haya pistas
    que se pueden escuchar, como bandcamp_verificar.py de vvmm. Si es el disco
    se guarda la URL limpia (…bandcamp.com/album/…) y bandcamp_album_id (el
    del EmbeddedPlayer); si no, se borra y se volverá a buscar.

Dos fases: la comprobación solo lee la db y guarda cada veredicto en
db/sqlite/.cache/reparar_enlaces.sqlite (se puede interrumpir y seguir); con
aplicar=true se aplican los veredictos y cada cambio, con los valores
anteriores, queda en db/sqlite/logs/reparar_enlaces_<fecha>.tsv.

Config (sección "enlaces/reparar_enlaces" o --param):
  servicios   discogs, bandcamp (por defecto los dos, en paralelo)
  limite      álbumes por servicio y ejecución (0 = todos)
  aplicar     true para escribir en la db (por defecto solo comprueba)
"""
import csv
import json
import logging
import os
import re
import sqlite3
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base.db_connection import apply_pragmas  # noqa: E402
from base.discos import (discogs_es_el_disco, artistas_discogs, url_bandcamp,  # noqa: E402
                         leer_pagina_bandcamp, bandcamp_es_el_disco, UA_BANDCAMP)

logger = logging.getLogger("reparar_enlaces")
SERVICIOS = ("discogs", "bandcamp")
PAUSA = {"discogs": 1.1, "bandcamp": 3.0}  # Discogs: 60/min con token; Bandcamp: como vvmm
ERROR = object()  # fallo de red o del servicio: sin veredicto, se reintenta otro día

CAMPOS_DISCOGS = ["discogs_url", "producers", "engineers", "mastering_engineers", "credits",
                  "discogs_genres", "discogs_styles", "discogs_checked"]
CAMPOS_BANDCAMP = ["bandcamp_url", "bandcamp_album_id", "bandcamp_checked"]


def _verdadero(valor):
    return str(valor).strip().lower() in ("1", "true", "si", "sí", "yes")


class Reparador:
    def __init__(self, config):
        self.db_path = Path(config["db_path"])
        self.discogs_token = config.get("discogs_token", "")
        servicios = config.get("servicios", SERVICIOS)
        if isinstance(servicios, str):
            servicios = [x.strip() for x in servicios.split(",")]
        self.servicios = [x for x in servicios if x in SERVICIOS]
        self.limite = int(config.get("limite") or 0)
        self.aplicar = _verdadero(config.get("aplicar", False))
        cache = self.db_path.parent / ".cache"
        cache.mkdir(parents=True, exist_ok=True)
        self.checkpoint = cache / "reparar_enlaces.sqlite"
        self._lock = threading.Lock()
        with self._ck() as ck:
            ck.execute("""CREATE TABLE IF NOT EXISTS veredicto (
                servicio TEXT, album_id INTEGER, url TEXT, ok INTEGER, dice TEXT,
                bandcamp_id INTEGER, cuando TEXT, PRIMARY KEY (servicio, album_id, url))""")

    def _ck(self):
        return sqlite3.connect(self.checkpoint, timeout=30)

    def _db(self, solo_lectura=True):
        if solo_lectura:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=60)
        else:
            conn = sqlite3.connect(self.db_path, timeout=60)
            apply_pragmas(conn)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Comprobación ─────────────────────────────────────────────────────────

    def pendientes(self, servicio):
        col = f"{servicio}_url"
        with self._db() as conn:
            filas = conn.execute(f"""
                SELECT al.id, al.name AS album, ar.name AS artista, al.{col} AS url
                FROM albums al JOIN artists ar ON ar.id = al.artist_id
                WHERE coalesce(al.{col}, '') != ''
                ORDER BY al.id DESC""").fetchall()
        with self._ck() as ck:
            hechos = set(ck.execute("SELECT album_id, url FROM veredicto WHERE servicio = ?", (servicio,)))
        filas = [f for f in filas if (f["id"], f["url"]) not in hechos]
        return filas[:self.limite] if self.limite else filas

    def _get(self, servicio, session, url, **kw):
        for intento in range(4):
            time.sleep(PAUSA[servicio])
            try:
                r = session.get(url, timeout=30, **kw)
            except requests.RequestException as e:
                logger.warning(f"{servicio}: {type(e).__name__}")
                return ERROR
            if r.status_code in (429, 503):
                time.sleep(30 * (intento + 1))
                continue
            if r.status_code in (404, 410):
                return None
            if r.status_code >= 400:
                logger.warning(f"{servicio}: HTTP {r.status_code} en {url.split('?')[0]}")
                return ERROR
            return r
        return ERROR

    def comprobar_discogs(self, session, fila):
        m = re.search(r"/release/(\d+)", fila["url"])
        if not m:
            return False, "no es una URL de release", None
        r = self._get("discogs", session, f"https://api.discogs.com/releases/{m.group(1)}")
        if r is ERROR:
            return ERROR
        if r is None:
            return False, "la release ya no existe (404)", None
        data = r.json()
        dice = f"{', '.join(artistas_discogs(data))} - {data.get('title', '')}"
        return discogs_es_el_disco(data, fila["artista"], fila["album"], estricto=False), dice, None

    def comprobar_bandcamp(self, session, fila):
        url = url_bandcamp(fila["url"])
        if not url:
            return False, "no es una URL de álbum (…bandcamp.com/album/…)", None
        r = self._get("bandcamp", session, url)
        if r is ERROR:
            return ERROR
        if r is None:
            return False, "la página ya no existe (404)", None
        info = leer_pagina_bandcamp(r.text)
        if not info:
            return False, "la página no es de un álbum", None
        dice = f"{info['artista']} - {info['titulo']} ({info['pistas']} pistas)"
        return bandcamp_es_el_disco(info, fila["artista"], fila["album"]), dice, info["id"]

    def comprobar(self, servicio):
        filas = self.pendientes(servicio)
        logger.info(f"{servicio}: {len(filas)} enlaces por comprobar")
        session = requests.Session()
        if servicio == "discogs":
            session.headers["User-Agent"] = "music-fuzzy/1.0 (reparar_enlaces)"
            if self.discogs_token:
                session.headers["Authorization"] = f"Discogs token={self.discogs_token}"
            comprobar = self.comprobar_discogs
        else:
            session.headers["User-Agent"] = UA_BANDCAMP
            comprobar = self.comprobar_bandcamp
        malos = errores = 0
        for i, fila in enumerate(filas, 1):
            try:
                res = comprobar(session, fila)
            except Exception as e:  # respuesta rara: sin veredicto
                logger.warning(f"{servicio}: error con {fila['url']}: {e}")
                res = ERROR
            if res is ERROR:
                errores += 1
                continue
            ok, dice, bc_id = res
            malos += not ok
            with self._lock, self._ck() as ck:
                ck.execute("INSERT OR REPLACE INTO veredicto VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (servicio, fila["id"], fila["url"], int(ok), dice, bc_id,
                            datetime.now().isoformat(sep=" ", timespec="seconds")))
            if not ok:
                logger.info(f"{servicio} MAL: «{fila['artista']} - {fila['album']}» → {fila['url']} es «{dice}»")
            if i % 200 == 0:
                logger.info(f"{servicio}: {i}/{len(filas)} comprobados, {malos} mal, {errores} errores")
        logger.info(f"{servicio}: terminado, {len(filas)} comprobados, {malos} mal, {errores} sin respuesta")

    # ── Aplicar ──────────────────────────────────────────────────────────────

    def aplicar_veredictos(self):
        with self._ck() as ck:
            veredictos = ck.execute(
                "SELECT servicio, album_id, url, ok, dice, bandcamp_id FROM veredicto").fetchall()
        logs = self.db_path.parent / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        informe = logs / f"reparar_enlaces_{datetime.now():%Y-%m-%d_%H%M}.tsv"
        cambios = {"discogs": 0, "bandcamp": 0, "bandcamp_id": 0}
        ahora = datetime.now().isoformat(sep=" ", timespec="seconds")
        conn = self._db(solo_lectura=False)
        columnas = {r[1] for r in conn.execute("PRAGMA table_info(albums)")}
        for col, tipo in (("bandcamp_album_id", "INTEGER"), ("bandcamp_checked", "TIMESTAMP")):
            if col not in columnas:
                conn.execute(f"ALTER TABLE albums ADD COLUMN {col} {tipo}")
        campos_d = [c for c in CAMPOS_DISCOGS if c in columnas]
        with informe.open("w", newline="") as f:
            tsv = csv.writer(f, delimiter="\t")
            tsv.writerow(["servicio", "album_id", "artista", "album", "url", "accion", "dice", "antes"])
            for servicio, album_id, url, ok, dice, bc_id in veredictos:
                if servicio not in self.servicios:
                    continue
                campos = campos_d if servicio == "discogs" else CAMPOS_BANDCAMP
                fila = conn.execute(f"""SELECT ar.name AS artista, al.name AS album, {', '.join('al.' + c for c in campos)}
                                        FROM albums al JOIN artists ar ON ar.id = al.artist_id
                                        WHERE al.id = ?""", (album_id,)).fetchone()
                if not fila or fila[f"{servicio}_url"] != url:
                    continue  # el enlace cambió desde la comprobación
                antes = json.dumps({c: fila[c] for c in campos}, ensure_ascii=False)
                if not ok:
                    nulos = campos + (["links_updated"] if servicio == "discogs" else [])
                    conn.execute(f"UPDATE albums SET {', '.join(c + ' = NULL' for c in nulos)} WHERE id = ?",
                                 (album_id,))
                    accion = "borrado"
                    cambios[servicio] += 1
                elif servicio == "bandcamp" and (fila["bandcamp_url"] != url_bandcamp(url)
                                                 or fila["bandcamp_album_id"] != bc_id):
                    conn.execute("UPDATE albums SET bandcamp_url = ?, bandcamp_album_id = ?, bandcamp_checked = ? "
                                 "WHERE id = ?", (url_bandcamp(url), bc_id, ahora, album_id))
                    accion = "id"
                    cambios["bandcamp_id"] += 1
                else:
                    continue
                tsv.writerow([servicio, album_id, fila["artista"], fila["album"], url, accion, dice, antes])
        conn.commit()
        conn.close()
        logger.info(f"Aplicado: {cambios['discogs']} discogs_url borradas, {cambios['bandcamp']} bandcamp_url "
                    f"borradas, {cambios['bandcamp_id']} bandcamp con URL limpia e id. Informe: {informe}")

    def run(self):
        hilos = [threading.Thread(target=self.comprobar, args=(s,), name=s) for s in self.servicios]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        with self._ck() as ck:
            for servicio, ok, n in ck.execute("SELECT servicio, ok, count(*) FROM veredicto GROUP BY 1, 2"):
                logger.info(f"Veredictos {servicio}: {n} {'bien' if ok else 'MAL'}")
        if self.aplicar:
            self.aplicar_veredictos()
        else:
            logger.info("Solo comprobación (aplicar=true para escribir en la db)")


def main(config=None):
    if config is None:
        import argparse
        ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        ap.add_argument("--db-path", required=True)
        ap.add_argument("--discogs-token", default=os.getenv("DISCOGS_TOKEN", ""))
        ap.add_argument("--servicios", default="discogs,bandcamp")
        ap.add_argument("--limite", type=int, default=0)
        ap.add_argument("--aplicar", action="store_true")
        a = ap.parse_args()
        config = {"db_path": a.db_path, "discogs_token": a.discogs_token, "servicios": a.servicios,
                  "limite": a.limite, "aplicar": a.aplicar}
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s")
    Reparador(config).run()


if __name__ == "__main__":
    main()
