"""
¿Es este enlace de verdad el disco? Comprobaciones compartidas por
enlaces/enlaces_artista_album y enlaces/reparar_enlaces.

Discogs: una release solo vale si su artista y su título son los del álbum
(antes se aceptaba el primer resultado de la búsqueda y se asignaban discos
homónimos de otros artistas). Los créditos usan el formato de
generos/generos_creditos: credits = JSON {rol en minúsculas: [nombres]}.

Bandcamp: el mismo estándar que el blog vvmm (scripts/bandcamp_*.py) y
bandcamp_imap de repeat-one, que lo usan para los reproductores:
  - solo URLs de álbum https://<sub>.bandcamp.com/album/<slug>, sin ?from=…
  - el id numérico del álbum (item_id) es el del EmbeddedPlayer:
    https://bandcamp.com/EmbeddedPlayer/album=<id>/…
  - se da por bueno solo si artista y título coinciden y hay pistas que se
    pueden escuchar (o es la página de un sello: «Artista Título»).
"""
import html
import json
import re
import unicodedata

# ── Normalización ────────────────────────────────────────────────────────────

# Palabras de edición que no cambian el disco: 'OK Computer - Remastered 2009'
_EDICION = re.compile(
    r"\b(remaster(ed)?|remasterizado|deluxe|edition|expanded|anniversary|reissue|"
    r"bonus( tracks?)?|special|super|version|mono|stereo|\d{4}|\d+(st|nd|rd|th))\b")
# Separadores de artistas en colaboraciones: 'Ric Wilson, Chromeo'
_SEP_ARTISTAS = re.compile(
    r"\s*(?:,|&|/|\+|;| and | y | con | with | feat\.? | ft\.? | vs\.? | x )\s*", re.I)
_VARIOS = {"various", "various artists", "va", "varios", "varios artistas"}


def normalizar(texto):
    """Minúsculas, sin acentos, sin '(Deluxe)'/'[2009]', sin el '(2)' de Discogs ni 'the '."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).casefold()
    texto = re.sub(r"\s*\(\d+\)\s*$", "", texto)       # 'Grimes (4)' de Discogs
    texto = re.sub(r"[(\[{].*?[)\]}]", " ", texto)       # '(Deluxe)', '[Remastered]'
    texto = texto.replace("&", " and ")
    texto = " ".join(re.sub(r"[\W_]+", " ", texto).split())
    return re.sub(r"^the ", "", texto)


def titulo_igual(a, b):
    """Estricto: mismo título salvo edición ('Remastered 2009', '(Deluxe)')."""
    a, b = normalizar(a), normalizar(b)
    if not a or not b:
        return False
    if a == b:
        return True
    a2, b2 = (" ".join(_EDICION.sub(" ", x).split()) for x in (a, b))
    return bool(a2) and a2 == b2


def parecido(a, b):
    """Como `same` de vvmm: igual, igual sin espacios o uno contiene al otro por palabras."""
    a, b = normalizar(a), normalizar(b)
    if not (a and b):
        return False
    return (a == b or a.replace(" ", "") == b.replace(" ", "")
            or f" {a} " in f" {b} " or f" {b} " in f" {a} ")


def titulo_parecido(titulo, album, artista):
    """Tolerante (contiene/contenido), salvo en discos homónimos del artista:
    «Rita Lee» no es «Rita Lee - Agora é Moda»."""
    if titulo_igual(titulo, album):
        return True
    if normalizar(album) == normalizar(artista):
        return False
    return parecido(titulo, album)


def artista_coincide(local, nombres, estricto=True):
    """local: artista en la db; nombres: artistas del enlace (release, página...)."""
    nombres = [n for n in nombres if n]
    if not nombres:
        return False
    norm = {normalizar(n) for n in nombres} - {""}
    todos = normalizar(" ".join(nombres))
    nl = normalizar(local)
    if nl in _VARIOS:
        return bool(norm & {"various", "various artists", "varios artistas"})
    if not nl:
        return False
    if nl in norm or nl == todos:
        return True
    if not estricto and any(parecido(local, n) for n in nombres + [" ".join(nombres)]):
        return True
    # Colaboraciones: algún artista del nombre local es uno de los del enlace
    partes = {normalizar(x) for x in _SEP_ARTISTAS.split(local or "")} - {""}
    return len(partes) > 1 and bool(partes & norm)


# ── Discogs ──────────────────────────────────────────────────────────────────

def artistas_discogs(data):
    nombres = []
    for a in data.get("artists", []):
        nombres += [x for x in (a.get("name"), a.get("anv")) if x]
    return nombres


def discogs_es_el_disco(data, artista, album, estricto=True):
    """data: release completa de la API de Discogs.

    estricto=True (al buscar): título igual salvo edición.
    estricto=False (al revisar un enlace ya guardado): basta con que uno
    contenga al otro, como en vvmm; el artista tiene que coincidir siempre.
    """
    titulo = data.get("title", "")
    # Recopilatorio con las pistas etiquetadas por artista: «Rod Stewart - Top Of The Pops '74»
    if (not estricto and titulo_igual(titulo, album)
            and {normalizar(n) for n in artistas_discogs(data)} & {"various", "various artists"}):
        return True
    ok_titulo = titulo_igual(titulo, album) if estricto else titulo_parecido(titulo, album, artista)
    return ok_titulo and artista_coincide(artista, artistas_discogs(data), estricto=estricto)


def creditos_discogs(data):
    """(producers, engineers, mastering_engineers, credits_json) de una release."""
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
    if not creditos:
        return None, None, None, None

    def con(*claves, sin=()):
        return ", ".join(dict.fromkeys(
            n for rol, nombres in creditos.items()
            if any(c in rol for c in claves) and not any(x in rol for x in sin)
            for n in nombres)) or None

    return (con("produc"), con("engineer", sin=("master",)), con("master"),
            json.dumps(creditos, ensure_ascii=False))


# ── Bandcamp ─────────────────────────────────────────────────────────────────

BC_ALBUM = re.compile(r"^https?://[\w.-]+\.bandcamp\.com/album/[\w-]+")
# Las páginas de álbum se sirven igual a un cliente que se identifica
UA_BANDCAMP = "music-fuzzy/1.0 (+https://github.com/volteret4/mfuz)"
_TRALBUM = re.compile(r'data-tralbum="([^"]+)"')
_PAGE_PROPS = re.compile(r'name="bc-page-properties"\s+content="([^"]+)"')


def url_bandcamp(url):
    """'https://x.bandcamp.com/album/y?from=search' → 'https://x.bandcamp.com/album/y'; None si no es de álbum."""
    m = BC_ALBUM.match((url or "").strip())
    return m.group(0).replace("http://", "https://", 1) if m else None


def embed_bandcamp(album_id):
    """URL del reproductor (la que usan vvmm y bandcamp_imap)."""
    return (f"https://bandcamp.com/EmbeddedPlayer/album={album_id}/size=large/bgcol=333333/"
            f"linkcol=9a64ff/tracklist=false/artwork=small/transparent=true/")


def leer_pagina_bandcamp(texto):
    """Datos de la página de un álbum: {id, artista, titulo, tipo, pistas} o None."""
    m = _TRALBUM.search(texto)
    if not m:
        return None
    try:
        d = json.loads(html.unescape(m.group(1)))
    except ValueError:
        return None
    album_id = d.get("id")
    props = _PAGE_PROPS.search(texto)
    if props:
        try:
            p = json.loads(html.unescape(props.group(1)))
            if p.get("item_type") == "a" and p.get("item_id"):
                album_id = p["item_id"]
        except ValueError:
            pass
    return {
        "id": int(album_id) if album_id else None,
        "artista": d.get("artist") or "",
        "titulo": (d.get("current") or {}).get("title") or "",
        "tipo": d.get("item_type"),
        "pistas": sum(1 for t in d.get("trackinfo") or [] if t.get("file")),
    }


def bandcamp_es_el_disco(info, artista, album):
    """Criterio de vvmm (bandcamp_verificar.is_match)."""
    if not info or info.get("tipo") != "album" or not info.get("id") or not info.get("pistas"):
        return False
    if titulo_parecido(info["titulo"], album, artista) and artista_coincide(artista, [info["artista"]], estricto=False):
        return True
    # página de un sello: «Heavenly Recordings – Saint Etienne - International»
    return normalizar(info["titulo"]) == normalizar(f"{artista} {album}")
