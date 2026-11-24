#!/usr/bin/env python3
"""
Detalle de los sellos de la colección: catálogo, créditos habituales y relaciones.

Por cada sello de los álbumes locales (los que más discos tienen primero):

  Discogs      catálogo del sello (hasta `max_paginas` × 100 lanzamientos, uno por
               artista + título) → label_catalog, y los créditos de una muestra de
               `muestra` discos repartidos por años → label_credits:
                 tipo = estudio | masterizacion | grabacion | mezcla | produccion
  MusicBrainz  relaciones del sello (fundadores, dueños, sello matriz, subsellos,
               imprints, cambios de nombre) → labels.mb_relaciones (JSON)

Se marca labels.detalle_checked (y labels.discogs_id) y no se repite hasta pasados
`reintentar_dias`. Si en el buzón (db/sqlite/buzon_sellos/*.json) hay sellos que
ya bajó la pestaña «Sello» de Infobar NG en el PC, se importan primero sin gastar
peticiones a Discogs.

Lo lee ~/Scripts/Musica/deadbeef/sello.py (pestaña «Sello» de DeaDBeeF).

Config (config_database_creator.json, sección "discogs/sellos_detalle"):
  limite           sellos por ejecución (15 por defecto, ~1 min cada uno; 0 = todos)
  muestra          discos de los que se leen créditos (40)
  max_paginas      páginas de 100 del catálogo (3)
  reintentar_dias  días antes de volver a mirar un sello (180)
"""
import json
import logging
import re
import sqlite3
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parents[1]))
from base.db_connection import apply_pragmas  # noqa: E402

USER_AGENT = "music-fuzzy/1.0 (+https://github.com/volteret4/mfuz; sellos_detalle)"
PAUSA_DISCOGS = 1.1
PAUSA_MB = 1.1
GENERICOS = {"[no label]", "not on label", "self-released", "none", "", "no label", "unknown"}
BUZON = Path(__file__).resolve().parents[1] / "sqlite/buzon_sellos"

# papel de Discogs → tipo (el primero que encaje)
TIPOS = [
    ("masterizacion", re.compile(r"master|lacquer", re.I)),
    ("mezcla", re.compile(r"(?<!re)mix", re.I)),
    ("grabacion", re.compile(r"engineer|recorded|recording", re.I)),
    ("produccion", re.compile(r"produc", re.I)),
]
ESTUDIO = re.compile(r"(recorded|mixed|mastered|engineered|produced|remastered|lacquer cut) at", re.I)
# claves de la pestaña Sello (sello.py) → tipo
GRUPOS_PC = {"Masterización": "masterizacion", "Ingeniería": "grabacion", "Mezcla": "mezcla",
             "Producción": "produccion"}

logger = logging.getLogger("sellos_detalle")


def dname(n):
    return re.sub(r"\s*\(\d+\)$", "", n or "")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[4:] if s.startswith("the ") else s


def label_norm(s):
    s = dname(s or "").lower()
    s = re.sub(r"\b(records?|recordings?|music|label|ltd\.?|inc\.?|llc|gmbh|s\.?l\.?|co\.?)\b", " ", s)
    return norm(s)


def add_credits(people, studios, extraartists, companies):
    for c in extraartists or []:
        role, name = c.get("role", ""), dname(c.get("name", ""))
        for tipo, rx in TIPOS:
            if name and rx.search(role):
                people[tipo][name] += 1
                break
    for c in companies or []:
        role = c.get("entity_type_name", "")
        if ESTUDIO.search(role) and "glass" not in role.lower():
            studios[dname(c.get("name", ""))] += 1


def mb_relations(mb):
    out = defaultdict(list)
    for r in mb.get("relations", []):
        t, d = r.get("type", ""), r.get("direction")
        b, e = (r.get("begin") or "")[:4], (r.get("end") or "")[:4]
        when = f" ({b}–{e})" if b and e else (f" ({b})" if b else "")
        tt = r.get("target-type")
        if tt == "artist":
            a = r["artist"]["name"]
            if "founder" in t:
                out["fundadores"].append(a + when)
            elif "owner" in t:
                out["dueños"].append(a + when)
            elif "personal label" in t:
                out["sello personal de"].append(a)
        elif tt == "label":
            lab = r["label"]["name"]
            if t == "label rename":
                out["antes" if d == "backward" else "después"].append(lab + when)
            elif t in ("label ownership", "imprint", "label reissue", "label distribution", "business association"):
                if d == "backward":
                    out["pertenece a" if t == "label ownership" else f"{t} de"].append(lab + when)
                else:
                    out["subsellos" if t in ("label ownership", "imprint") else t].append(lab + when)
        elif tt == "url":
            out["url_" + t].append(r["url"]["resource"])
    return dict(out)


class Sellos:
    def __init__(self, config):
        self.db_path = config["db_path"]
        self.token = config.get("discogs_token")
        self.limite = int(config.get("limite", 15))
        self.muestra = int(config.get("muestra", 40))
        self.max_paginas = int(config.get("max_paginas", 3))
        self.reintentar = timedelta(days=int(config.get("reintentar_dias", 180)))
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.ultima = {"dg": 0.0, "mb": 0.0}
        self.conn = sqlite3.connect(self.db_path, timeout=60)
        self.conn.row_factory = sqlite3.Row
        apply_pragmas(self.conn)
        self._tablas()

    def _tablas(self):
        c = self.conn
        cols = {r[1] for r in c.execute("PRAGMA table_info(labels)")}
        for col, tipo in (("discogs_id", "INTEGER"), ("detalle_checked", "TIMESTAMP"), ("detalle_muestra", "INTEGER"),
                          ("mb_relaciones", "TEXT"), ("discogs_parent", "TEXT"), ("discogs_sublabels", "TEXT")):
            if col not in cols:
                c.execute(f"ALTER TABLE labels ADD COLUMN {col} {tipo}")
        c.execute("""CREATE TABLE IF NOT EXISTS label_credits (
                       label_id INTEGER NOT NULL, tipo TEXT NOT NULL, nombre TEXT NOT NULL, veces INTEGER,
                       PRIMARY KEY (label_id, tipo, nombre))""")
        c.execute("""CREATE TABLE IF NOT EXISTS label_catalog (
                       label_id INTEGER NOT NULL, discogs_id INTEGER NOT NULL, artista TEXT, titulo TEXT,
                       anio INTEGER, formato TEXT, PRIMARY KEY (label_id, discogs_id))""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_label_catalog_artista ON label_catalog(artista)")
        c.commit()

    # ── HTTP ─────────────────────────────────────────────────────────────────

    def _get(self, cual, url, **params):
        pausa = PAUSA_DISCOGS if cual == "dg" else PAUSA_MB
        headers = {"Authorization": f"Discogs token={self.token}"} if cual == "dg" and self.token else {}
        if cual == "mb":
            params["fmt"] = "json"
        for intento in range(4):
            espera = pausa - (time.monotonic() - self.ultima[cual])
            if espera > 0:
                time.sleep(espera)
            self.ultima[cual] = time.monotonic()
            try:
                r = self.s.get(url, params=params or None, headers=headers, timeout=(10, 30))
            except requests.RequestException as e:
                logger.debug(f"{url}: {e}")
                time.sleep(5 * (intento + 1))
                continue
            if r.status_code in (429, 503):
                time.sleep(10 * (intento + 1))
                continue
            return r.json() if r.ok else {}
        return {}

    def dg(self, path, **params):
        return self._get("dg", f"https://api.discogs.com/{path}", **params)

    def mb(self, path, **params):
        return self._get("mb", f"https://musicbrainz.org/ws/2/{path}", **params)

    # ── qué sellos ───────────────────────────────────────────────────────────

    def sellos_de_la_coleccion(self):
        """[(label_id, nombre, discos)] de los álbumes locales; crea en labels los que falten."""
        cuenta, nombre = Counter(), {}
        for (lab,) in self.conn.execute("SELECT label FROM albums WHERE label IS NOT NULL AND label <> ''"):
            for parte in re.split(r"\s*;\s*|\s*/\s*(?=[A-Z])", lab):
                if parte.lower().strip() in GENERICOS:
                    continue
                k = label_norm(parte)
                if k:
                    cuenta[k] += 1
                    nombre.setdefault(k, dname(parte.strip()))
        ids = {}
        for row in self.conn.execute("SELECT id, name FROM labels"):
            ids.setdefault(label_norm(row["name"]), row["id"])
        nuevos = [k for k in cuenta if k not in ids]
        for k in nuevos:
            cur = self.conn.execute("INSERT INTO labels (name, last_updated) VALUES (?, ?)",
                                    (nombre[k], datetime.now().isoformat(sep=" ", timespec="seconds")))
            ids[k] = cur.lastrowid
        if nuevos:
            self.conn.commit()
            logger.info(f"{len(nuevos)} sellos nuevos en labels")
        return [(ids[k], nombre[k], n) for k, n in cuenta.most_common()]

    def pendientes(self):
        limite = (datetime.now() - self.reintentar).isoformat(sep=" ", timespec="seconds")
        hechos = {r[0] for r in self.conn.execute(
            "SELECT id FROM labels WHERE detalle_checked IS NOT NULL AND detalle_checked > ?", (limite,))}
        lista = [s for s in self.sellos_de_la_coleccion() if s[0] not in hechos]
        return lista[:self.limite] if self.limite else lista

    # ── guardar ──────────────────────────────────────────────────────────────

    def guardar(self, label_id, discogs_id, discos, studios, people, muestra, parent=None, sublabels=None):
        c = self.conn
        c.execute("DELETE FROM label_catalog WHERE label_id = ?", (label_id,))
        c.executemany("INSERT OR REPLACE INTO label_catalog VALUES (?, ?, ?, ?, ?, ?)",
                      [(label_id, d["id"], d["artist"], d["title"], d.get("year") or None, d.get("format") or None)
                       for d in discos if d.get("id")])
        c.execute("DELETE FROM label_credits WHERE label_id = ?", (label_id,))
        filas = [(label_id, "estudio", n, v) for n, v in studios.items() if n]
        for tipo, cnt in people.items():
            filas += [(label_id, tipo, n, v) for n, v in cnt.items() if n]
        c.executemany("INSERT OR REPLACE INTO label_credits VALUES (?, ?, ?, ?)", filas)
        sets = ["detalle_checked = ?", "detalle_muestra = ?"]
        vals = [datetime.now().isoformat(sep=" ", timespec="seconds"), muestra]
        if discogs_id:
            sets.append("discogs_id = ?")
            vals.append(discogs_id)
        if parent is not None:
            sets.append("discogs_parent = ?")
            vals.append(parent)
        if sublabels is not None:
            sets.append("discogs_sublabels = ?")
            vals.append(json.dumps(sublabels, ensure_ascii=False))
        c.execute(f"UPDATE labels SET {', '.join(sets)} WHERE id = ?", (*vals, label_id))
        c.commit()

    # ── buzón del PC ─────────────────────────────────────────────────────────

    def importar_buzon(self):
        if not BUZON.is_dir():
            return 0
        n = 0
        for f in sorted(BUZON.glob("*.json")):
            try:
                d = json.loads(f.read_text())
                if not d.get("terminado"):
                    continue
                m = re.match(r"dgrel_(\d+)\.json$", f.name)
                lid = d.get("discogs_id") or (int(m.group(1)) if m else None)
                row = self.conn.execute("SELECT id FROM labels WHERE discogs_id = ?", (lid,)).fetchone() if lid else None
                if not row and lid:
                    row = self.conn.execute("SELECT id FROM labels WHERE discogs_url LIKE ?",
                                            (f"%/label/{lid}",)).fetchone()
                if not row and lid and not d.get("label"):
                    d["label"] = dname(self.dg(f"labels/{lid}").get("name"))
                if not row and d.get("label"):
                    k = label_norm(d["label"])
                    row = next((r for r in self.conn.execute("SELECT id, name FROM labels")
                                if label_norm(r["name"]) == k), None)
                if not row and d.get("label"):     # sello de un disco tuyo que labels aún no tenía
                    cur = self.conn.execute("INSERT INTO labels (name, discogs_id, last_updated) VALUES (?, ?, ?)",
                                            (d["label"], lid, datetime.now().isoformat(sep=" ", timespec="seconds")))
                    row = {"id": cur.lastrowid}
                if not row:
                    continue
                people = {GRUPOS_PC.get(g, g): Counter(c) for g, c in (d.get("people") or {}).items()}
                self.guardar(row["id"], lid, d.get("discos") or [], Counter(d.get("studios") or {}), people,
                             d.get("muestra") or 0)
                f.unlink()
                n += 1
            except Exception as e:
                logger.warning(f"buzón {f.name}: {type(e).__name__}: {e}")
        if n:
            logger.info(f"{n} sellos importados del buzón del PC")
        return n

    # ── un sello ─────────────────────────────────────────────────────────────

    def discogs_id(self, label_id, nombre):
        row = self.conn.execute("SELECT discogs_id, discogs_url FROM labels WHERE id = ?", (label_id,)).fetchone()
        if row["discogs_id"]:
            return row["discogs_id"]
        m = re.search(r"/label/(\d+)", row["discogs_url"] or "")
        if m:
            return int(m.group(1))
        res = self.dg("database/search", q=nombre, type="label", per_page=5).get("results", [])
        k = label_norm(nombre)
        hit = next((r for r in res if label_norm(r.get("title")) == k), None)
        return hit["id"] if hit else None

    def relaciones_mb(self, label_id, nombre):
        row = self.conn.execute("SELECT mbid FROM labels WHERE id = ?", (label_id,)).fetchone()
        mbid = row["mbid"]
        if not mbid:
            res = self.mb("label", query=f'label:"{nombre}"', limit=5).get("labels", [])
            k = label_norm(nombre)
            hit = next((x for x in res if label_norm(x.get("name")) == k), None)
            mbid = hit["id"] if hit else None
        if not mbid:
            return
        d = self.mb(f"label/{mbid}", inc="label-rels+artist-rels+url-rels")
        if not d:
            return
        rel = mb_relations(d)
        ls = d.get("life-span") or {}
        self.conn.execute(
            "UPDATE labels SET mb_relaciones = ?, mbid = coalesce(mbid, ?), country = coalesce(country, ?), "
            "founded_year = coalesce(founded_year, ?), mb_type = coalesce(mb_type, ?) WHERE id = ?",
            (json.dumps(rel, ensure_ascii=False), mbid, d.get("country"),
             int(ls["begin"][:4]) if (ls.get("begin") or "")[:4].isdigit() else None, d.get("type"), label_id))
        self.conn.commit()

    def procesar(self, label_id, nombre):
        lid = self.discogs_id(label_id, nombre)
        discos, studios, people, muestra, parent, subs = [], Counter(), defaultdict(Counter), 0, None, None
        if lid:
            info = self.dg(f"labels/{lid}")
            if info.get("parent_label"):
                parent = dname(info["parent_label"].get("name"))
            subs = [dname(s.get("name")) for s in info.get("sublabels", [])]
            rels = []
            for page in range(1, self.max_paginas + 1):
                d = self.dg(f"labels/{lid}/releases", page=page, per_page=100)
                rels += d.get("releases", [])
                if page >= (d.get("pagination") or {}).get("pages", 1):
                    break
            uniq = {}
            for r in rels:
                k = (norm(dname(r.get("artist", ""))), norm(re.sub(r"[\(\[][^\)\]]*[\)\]]", "", r.get("title", ""))))
                if k not in uniq or (r.get("year") or 9999) < (uniq[k].get("year") or 9999):
                    uniq[k] = r
            discos = [{"artist": dname(r.get("artist", "")), "title": r.get("title", ""), "year": r.get("year") or 0,
                       "format": r.get("format", ""), "id": r.get("id")} for r in uniq.values()]
            sample = sorted(discos, key=lambda x: x["year"] or 0)
            if len(sample) > self.muestra:
                paso = len(sample) / self.muestra
                sample = [sample[int(i * paso)] for i in range(self.muestra)]
            for dsc in sample:
                rel = self.dg(f"releases/{dsc['id']}")
                if not rel:
                    continue
                extra = list(rel.get("extraartists", []))
                for t in rel.get("tracklist", []):
                    extra += t.get("extraartists", [])
                add_credits(people, studios, extra, rel.get("companies", []))
                muestra += 1
        self.guardar(label_id, lid, discos, studios, people, muestra, parent, subs)
        self.relaciones_mb(label_id, nombre)
        return len(discos), muestra

    def run(self):
        self.importar_buzon()
        if not self.token:
            logger.warning("Sin discogs_token: solo relaciones de MusicBrainz")
        lista = self.pendientes()
        logger.info(f"{len(lista)} sellos pendientes (límite {self.limite or 'ninguno'})")
        inicio = time.monotonic()
        for n, (label_id, nombre, discos) in enumerate(lista, 1):
            try:
                cat, mu = self.procesar(label_id, nombre)
                logger.info(f"{n}/{len(lista)} {nombre} ({discos} tuyos): catálogo {cat}, créditos de {mu}")
            except Exception as e:  # un sello raro no debe parar el resto
                logger.warning(f"{nombre}: {type(e).__name__}: {e}")
        logger.info(f"Hecho: {len(lista)} sellos en {(time.monotonic() - inicio) / 60:.1f} min")
        self.conn.close()


def main(config=None):
    if config is None:
        import argparse
        ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        ap.add_argument("--db-path", required=True)
        ap.add_argument("--discogs-token")
        ap.add_argument("--limite", type=int, default=15)
        ap.add_argument("--muestra", type=int, default=40)
        ap.add_argument("--max-paginas", type=int, default=3)
        ap.add_argument("--reintentar-dias", type=int, default=180)
        a = ap.parse_args()
        config = {k: v for k, v in vars(a).items()}
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    Sellos(config).run()


if __name__ == "__main__":
    main()
