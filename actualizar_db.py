#!/usr/bin/env python3
"""
Gestor de actualizaciones de la base de datos de music-fuzzy.

pepecono (encendido 24/7, con la música en disco local) es el único que
escribe la db: envuelve db_creator.py (que ejecuta los scripts de db/ con su
configuración de config/config_database_creator.json), deja una instantánea en
la carpeta de Syncthing "mfuzz-db" (solo se reemplaza si la db pasa
quick_check), la despliega para los contenedores de repeat-one y Syncthing la
lleva al PC. En el PC el mismo script lanza las actualizaciones en pepecono por
ssh y, con la app cerrada, instala la última instantánea («traer», lo hace
boot.sh al arrancar).

Uso (en cualquiera de las dos máquinas):
    actualizar_db.py                      menú interactivo
    actualizar_db.py lista                scripts, grupos y presets
    actualizar_db.py run semanal          preset (al terminar exporta la instantánea)
    actualizar_db.py run discogs          grupo entero (carpeta de db/)
    actualizar_db.py run lastfm/lastfm_escuchas --param force_update=true
    actualizar_db.py run rapido --sin-subir   sin desplegar para los contenedores
    actualizar_db.py diario               rapido (domingos semanal); lo lanza el cron de pepecono
    actualizar_db.py exportar | estado
Solo en el PC:
    actualizar_db.py traer                instala la última instantánea si la app está cerrada
"""
import os
import sys
from pathlib import Path

# El mismo script corre en el PC y en pepecono: usar el venv de cada uno
VENV_PY = Path.home() / "Scripts/python_venv/bin/python"
if VENV_PY.exists() and Path(sys.prefix) != VENV_PY.parent.parent:
    os.execv(VENV_PY, [str(VENV_PY), *sys.argv])

import argparse
import datetime as dt
import fcntl
import re
import shlex
import socket
import sqlite3
import subprocess
import time

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config/config_database_creator.json"
DB = ROOT / "db/sqlite/musica_local.sqlite"
LOGS = ROOT / "db/sqlite/logs"
HISTORIAL = ROOT / "db/sqlite/actualizaciones.tsv"
DESCRIPCIONES = ROOT / "modules/submodules/db/script_descriptions.py"
CANDADO = ROOT / "db/sqlite/.actualizar_db.lock"

SERVIDOR = "pepecono"  # alias ssh
EN_SERVIDOR = socket.gethostname() == "pepe-cono"
REPO_SERVIDOR = "/home/pepe/gits/pollo/music-fuzzy"
REPO_PC = "/home/huan/gits/pollo/music-fuzzy"
# Carpeta Syncthing "mfuzz-db": pepecono la envía, el PC solo la recibe
SNAPSHOT_SERVIDOR = "/home/pepe/contenedores/repeat-one/data/mfuzz-db/musica_local.sqlite"
if EN_SERVIDOR:
    SNAPSHOT = Path(SNAPSHOT_SERVIDOR)
else:
    SNAPSHOT = ROOT / "db/sqlite/sync/musica_local.sqlite"
# Despliega la instantánea en la ruta que montan :ro los contenedores de repeat-one
DEPLOY = Path.home() / "Scripts/mfuzz_db_deploy.sh"
DEPLOY_LOG = Path.home() / "Scripts/.content/logs/mfuzz_db_deploy.log"
# En el PC: mtime de la última instantánea instalada en DB
INSTALADA = ROOT / "db/sqlite/.instantanea_instalada"
SALIDA_REMOTA = "db/sqlite/logs/remoto.out"

# Las imágenes descargadas se guardan con ruta absoluta dentro del repo
CARPETAS_IMG = [".content/artistas_img", ".content/albums_img"]
COLUMNAS_RUTAS = [("artists", "img"), ("artists", "img_urls"), ("artists", "img_paths"),
                  ("albums", "album_art_path"), ("albums", "album_art_urls")]

PRESETS = {
    "rapido": [
        "path/db_musica_path",
        "enlaces/enlaces_artista_album",
        "wiki/wikilinks_desde_mb",
    ],
    "semanal": [
        "path/db_musica_path",
        "enlaces/enlaces_artista_album",
        "enlaces/redes_sociales",
        "wiki/wikilinks_desde_mb",
        "img/portadas_artistas",
        "musicbrainz/mb_discografia",
        "discogs/artists_info",
        "lastfm/lastfm_escuchas",
        "listenbrainz/listens_listenbrainz",
        "posts/posts_fresh_rss",
        "posts/menciones",
    ],
}
# 'completo' = todos los scripts salvo estos grupos (descargas, no enriquecen la db)
EXCLUIDOS_DE_COMPLETO = {"descargas"}
# Carpetas de db/ que no son scripts de actualización
NO_SCRIPTS = {"base", "tools", "__pycache__", ".wip", ".cache", ".logs", "sqlite"}

DESC_EXTRA = {
    "path/db_musica_path": "Escanea la carpeta de música y actualiza artistas, álbumes y canciones de la biblioteca local.",
    "lastfm/lastfm_escuchas": "Importa tus escuchas de Last.fm.",
    "lastfm/lastfm_info": "Información de artistas y álbumes desde Last.fm.",
}


# ── Catálogo de scripts ──────────────────────────────────────────────────────

def descripciones() -> dict[str, str]:
    """Lee SCRIPT_DESCRIPTIONS sin importar el módulo (arrastra PyQt)."""
    texto = DESCRIPCIONES.read_text() if DESCRIPCIONES.exists() else ""
    desc = dict(re.findall(r"'([\w/]+)':\s*'([^']+)'", texto))
    return {**desc, **DESC_EXTRA}


def scripts_disponibles() -> list[str]:
    encontrados = []
    for py in sorted((ROOT / "db").glob("*/*.py")):
        grupo = py.parent.name
        if grupo in NO_SCRIPTS or py.name.startswith(("_", "test")):
            continue
        encontrados.append(f"{grupo}/{py.stem}")
    return encontrados


def grupos(scripts: list[str]) -> dict[str, list[str]]:
    g: dict[str, list[str]] = {}
    for s in scripts:
        g.setdefault(s.split("/")[0], []).append(s)
    return g


def resolver(objetivos: list[str], scripts: list[str]) -> list[str]:
    """Convierte presets, grupos, números o nombres en una lista de scripts."""
    por_grupo = grupos(scripts)
    presets = {**PRESETS, "completo": [s for s in scripts if s.split("/")[0] not in EXCLUIDOS_DE_COMPLETO]}
    salida = []
    for obj in objetivos:
        if obj in presets:
            salida += presets[obj]
        elif obj in por_grupo:
            salida += por_grupo[obj]
        elif obj.isdigit() and 1 <= int(obj) <= len(scripts):
            salida.append(scripts[int(obj) - 1])
        elif obj in scripts:
            salida.append(obj)
        else:
            parecidos = [s for s in scripts if obj in s]
            if len(parecidos) == 1:
                salida.append(parecidos[0])
            else:
                sys.exit(f"No reconozco «{obj}»." + (f" ¿Quizá {', '.join(parecidos)}?" if parecidos else ""))
    return list(dict.fromkeys(salida))


def imprimir_lista(scripts: list[str]):
    desc = descripciones()
    n = 1
    for grupo, lista in grupos(scripts).items():
        print(f"\n\033[1m{grupo}\033[0m")
        for s in lista:
            print(f"  {n:>2}. {s.split('/')[1]:<28} \033[2m{desc.get(s, '')}\033[0m")
            n += 1
    print("\n\033[1mpresets\033[0m")
    for nombre, lista in PRESETS.items():
        print(f"  {nombre:<10} {', '.join(x.split('/')[1] for x in lista)}")
    print(f"  {'completo':<10} todos salvo: {', '.join(sorted(EXCLUIDOS_DE_COMPLETO))}")


# ── Rutas absolutas de imágenes ──────────────────────────────────────────────

def reescribir_rutas(con: sqlite3.Connection, desde: str, hacia: str):
    """Cambia el prefijo del repo en las rutas de imágenes guardadas en la db."""
    tablas = {t for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for tabla, col in COLUMNAS_RUTAS:
        if tabla in tablas:
            con.execute(f"UPDATE {tabla} SET {col} = replace({col}, ?, ?) WHERE instr({col}, ?) > 0",
                        (f"{desde}/", f"{hacia}/", f"{desde}/"))
    con.commit()


# ── Instantánea (copia de seguridad + Syncthing) ─────────────────────────────

def exportar() -> bool:
    """Copia consistente de la db (API de backup de SQLite, segura con WAL) a
    la carpeta de Syncthing "mfuzz-db", que la lleva al PC.
    Es la única copia: solo se reemplaza si la db pasa quick_check, así que
    siempre guarda el último estado bueno."""
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    ok = con.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    if not ok:
        con.close()
        print(f"❌ {DB.name} no pasa quick_check: se conserva la instantánea anterior")
        return False
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    # Fuera de la carpeta de Syncthing: al reescribir rutas se crean -wal/-shm
    tmp = DB.with_name("instantanea.sqlite.tmp")
    copia = sqlite3.connect(tmp)
    # De una vez: por pasos, cualquier escritura abierta entre paso y paso
    # reinicia la copia desde cero (con WAL no bloquea a quien escribe)
    con.backup(copia, pages=-1)
    con.close()
    # La instantánea lleva las rutas del PC, que es quien la usa con la app
    reescribir_rutas(copia, REPO_SERVIDOR, REPO_PC)
    copia.execute("PRAGMA journal_mode=DELETE")  # un solo archivo, sin -wal
    copia.close()
    tmp.chmod(0o644)  # sqlite la crea 600; la leen contenedores con otros usuarios
    tmp.replace(SNAPSHOT)
    print(f"💾 Instantánea → {SNAPSHOT} (Syncthing la lleva al PC)")
    return True


def desplegar() -> bool:
    """Despliega la instantánea para los contenedores de repeat-one (los
    reinicia solo si cambió)."""
    print("🚀 Desplegando para los contenedores de repeat-one…")
    exportada = int(SNAPSHOT.stat().st_mtime)
    DEPLOY_LOG.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(f"{DEPLOY} --esperar {exportada} 2>&1 | tee -a {DEPLOY_LOG}", shell=True)
    if r.returncode != 0:
        print("⚠️  No se pudo desplegar ahora; lo hará el cron de las 03:30")
    return r.returncode == 0


# ── Ejecución (pepecono) ─────────────────────────────────────────────────────

def ejecutar(lista: list[str], params: list[str]) -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / f"{dt.datetime.now():%Y-%m-%d_%H%M}.log"
    cmd = [sys.executable, str(ROOT / "db_creator.py"), "--config", str(CONFIG), "--scripts", *lista]
    if params:
        cmd += ["--params", *params]
    print(f"▶ {len(lista)} scripts · log en {log.relative_to(ROOT)}\n")
    inicio = time.monotonic()
    with log.open("w") as f:
        # Sin buffer: si no, por una tubería el log no se escribe hasta el final
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                                env={**os.environ, "PYTHONUNBUFFERED": "1"})
        for linea in proc.stdout:
            sys.stdout.write(linea)
            f.write(linea)
        codigo = proc.wait()
    minutos = (time.monotonic() - inicio) / 60
    errores = [l for l in log.read_text().splitlines() if l.startswith(("Error al ejecutar", "Error: No se encontró"))]
    with HISTORIAL.open("a") as h:
        h.write(f"{dt.datetime.now():%Y-%m-%d %H:%M}\t{minutos:.1f} min\t{len(errores)} errores\t{' '.join(lista)}\n")
    print(f"\n{'✅' if not errores else '⚠️ '} Terminado en {minutos:.1f} min, {len(errores)} scripts con error")
    for e in errores:
        print(f"   {e}")
    return codigo or (1 if errores else 0)


def actualizar(lista: list[str], params: list[str], exportar_al_final: bool = True, subir: bool = True) -> int:
    # Que el cron y una ejecución a mano no escriban la db a la vez
    candado = CANDADO.open("w")
    try:
        fcntl.flock(candado, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("⏸  Ya hay una actualización en marcha (cron o manual); no se lanza otra")
        return 1
    if not SNAPSHOT.exists():
        exportar()  # que haya un estado al que volver antes de tocar nada
    codigo = ejecutar(lista, params)
    if exportar_al_final and exportar() and subir:
        desplegar()
    return codigo


# ── PC: delegar en pepecono e instalar la instantánea ───────────────────────

def ssh(orden: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", "-o", "ConnectTimeout=10", SERVIDOR, orden], **kw)


def en_servidor(argumentos: list[str]) -> int:
    """Lanza actualizar_db.py en pepecono desacoplado de la sesión ssh (si se
    apaga el PC sigue allí), muestra su salida y al terminar trae la db."""
    orden = (f"cd {REPO_SERVIDOR} && mkdir -p {Path(SALIDA_REMOTA).parent} && PYTHONUNBUFFERED=1 setsid nohup ./actualizar_db.py "
             f"{shlex.join(argumentos)} > {SALIDA_REMOTA} 2>&1 < /dev/null & echo $!")
    r = ssh(orden, capture_output=True, text=True)
    pid = r.stdout.strip()
    if r.returncode != 0 or not pid.isdigit():
        print(f"❌ No se pudo lanzar en {SERVIDOR}: {r.stderr.strip()}")
        return 1
    print(f"🖥  Ejecutando en {SERVIDOR} (Ctrl+C deja de mirar; allí sigue)\n")
    try:
        ssh(f"tail -n +1 -f --pid={pid} {REPO_SERVIDOR}/{SALIDA_REMOTA}")
    except KeyboardInterrupt:
        print(f"\n👋 Sigue en {SERVIDOR}; «actualizar_db.py traer» cuando termine")
        return 0
    if "--sin-exportar" in argumentos:
        return 0
    return 0 if esperar_instantanea() and traer() else 1


def esperar_instantanea(minutos: int = 30) -> bool:
    """Espera a que Syncthing traiga la instantánea que acaba de exportar
    pepecono (Syncthing conserva la fecha de modificación y solo la renombra
    a su sitio cuando está completa)."""
    r = ssh(f"stat -c %Y {SNAPSHOT_SERVIDOR}",
            capture_output=True, text=True)
    if r.returncode != 0:
        print(f"⚠️  No pude leer la instantánea de {SERVIDOR}")
        return False
    remota = int(r.stdout.strip())
    print("⏳ Esperando a que Syncthing traiga la db…")
    for _ in range(minutos * 6):
        if SNAPSHOT.exists() and int(SNAPSHOT.stat().st_mtime) >= remota:
            return True
        time.sleep(10)
    print(f"⚠️  No llegó en {minutos} min")
    return False


def db_abierta() -> list[str]:
    """Procesos que tienen abierta la db local (la app, un script…)."""
    procesos = []
    for fd_dir in Path("/proc").glob("[0-9]*/fd"):
        try:
            if any(os.readlink(fd).startswith(str(DB)) for fd in fd_dir.iterdir()):
                procesos.append((fd_dir.parent / "comm").read_text().strip())
        except OSError:
            continue
    return procesos


def traer() -> bool:
    """Instala en el PC la última instantánea de pepecono, si es nueva y nadie
    tiene abierta la db, y trae las imágenes que se hayan descargado allí."""
    if not SNAPSHOT.exists():
        print("💤 Aún no ha llegado ninguna instantánea")
        return False
    mtime = str(int(SNAPSHOT.stat().st_mtime))
    if INSTALADA.exists() and INSTALADA.read_text().strip() == mtime:
        print("✔ La db ya es la última de pepecono")
        return True
    if abiertos := db_abierta():
        print(f"⏸  La db está abierta ({', '.join(sorted(set(abiertos)))}); se instalará al arrancar la app")
        return False
    con = sqlite3.connect(f"file:{SNAPSHOT}?mode=ro&immutable=1", uri=True)
    if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        con.close()
        print("❌ La instantánea no pasa quick_check: se mantiene la db actual")
        return False
    tmp = DB.with_suffix(".sqlite.tmp")
    copia = sqlite3.connect(tmp)
    con.backup(copia, pages=-1)
    con.close()
    reescribir_rutas(copia, REPO_SERVIDOR, str(ROOT))  # por si llega alguna con rutas de pepecono
    copia.close()
    for resto in (DB.with_name(DB.name + "-wal"), DB.with_name(DB.name + "-shm")):
        resto.unlink(missing_ok=True)
    tmp.replace(DB)
    INSTALADA.write_text(mtime)
    print(f"📥 Instalada la db de {SERVIDOR} del {dt.datetime.fromtimestamp(int(mtime)):%Y-%m-%d %H:%M}")
    for carpeta in CARPETAS_IMG:
        (ROOT / carpeta).mkdir(parents=True, exist_ok=True)
        subprocess.run(["rsync", "-a", "-e", "ssh -o ConnectTimeout=10", f"{SERVIDOR}:{REPO_SERVIDOR}/{carpeta}/", str(ROOT / carpeta) + "/"])
    return True


# ── Estado ───────────────────────────────────────────────────────────────────

def estado():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    q = lambda sql: con.execute(sql).fetchone()[0]
    print(f"📀 {DB.relative_to(ROOT)}  {DB.stat().st_size / 1e9:.2f} GB  "
          f"(modificada {dt.datetime.fromtimestamp(DB.stat().st_mtime):%Y-%m-%d %H:%M})")
    print(f"   {q('SELECT count(*) FROM artists')} artistas · {q('SELECT count(*) FROM albums')} álbumes · "
          f"{q('SELECT count(*) FROM songs')} canciones · último artista añadido {str(q('SELECT max(added_timestamp) FROM artists'))[:16]}")
    con.close()
    if SNAPSHOT.exists():
        print(f"💾 Instantánea: {dt.datetime.fromtimestamp(SNAPSHOT.stat().st_mtime):%Y-%m-%d %H:%M}")
    else:
        print("💾 Instantánea: ninguna")
    if EN_SERVIDOR:
        if HISTORIAL.exists():
            print("🕑 Últimas actualizaciones:")
            for linea in HISTORIAL.read_text().splitlines()[-5:]:
                print(f"   {linea.replace(chr(9), ' · ')}")
        return
    if INSTALADA.exists():
        print(f"📥 Instalada la del {dt.datetime.fromtimestamp(int(INSTALADA.read_text())):%Y-%m-%d %H:%M}")
    print(f"\n🖥  {SERVIDOR}:")
    if ssh(f"cd {REPO_SERVIDOR} && ./actualizar_db.py estado").returncode != 0:
        print("   no accesible")


# ── Menú interactivo ─────────────────────────────────────────────────────────

def menu(scripts: list[str]):
    imprimir_lista(scripts)
    print("\nEscribe números, grupos o presets separados por espacios "
          "(p.ej. «semanal», «discogs 12 14»), o: e=estado  x=exportar  q=salir")
    eleccion = input("› ").split()
    if not eleccion or eleccion == ["q"]:
        return 0
    if eleccion == ["e"]:
        estado()
        return 0
    if eleccion == ["x"]:
        return main_exportar(subir=True)
    lista = resolver(eleccion, scripts)
    print("\nSe ejecutará" + ("" if EN_SERVIDOR else f" en {SERVIDOR}") + ":\n  " + "\n  ".join(lista))
    if input("¿Continuar? [S/n] ").strip().lower() not in ("", "s", "si", "sí", "y"):
        return 0
    if not EN_SERVIDOR:
        return en_servidor(["run", *lista])
    return actualizar(lista, [])


def main_exportar(subir: bool) -> int:
    if not EN_SERVIDOR:
        return en_servidor(["exportar"] + ([] if subir else ["--sin-subir"]))
    if not exportar():
        return 1
    return 0 if not subir or desplegar() else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden")
    sub.add_parser("lista", help="Muestra scripts, grupos y presets")
    run = sub.add_parser("run", help="Ejecuta presets, grupos o scripts")
    run.add_argument("objetivos", nargs="+")
    run.add_argument("--param", action="append", default=[], help="key=value que se pasa a los scripts (repetible)")
    run.add_argument("--sin-exportar", action="store_true", help="No actualizar la instantánea al terminar")
    run.add_argument("--sin-subir", action="store_true", help="Exportar pero no desplegar para los contenedores")
    sub.add_parser("diario", help="Preset rapido (los domingos semanal) y despliegue; lo lanza el cron de pepecono")
    exp = sub.add_parser("exportar", help="Actualiza la instantánea y la despliega")
    exp.add_argument("--sin-subir", action="store_true", help="Solo la instantánea, sin desplegar")
    sub.add_parser("estado", help="Tamaño, contenido e instantáneas")
    sub.add_parser("traer", help="(PC) Instala la última instantánea de pepecono si la app está cerrada")
    args = ap.parse_args()

    scripts = scripts_disponibles()
    if args.orden == "lista":
        imprimir_lista(scripts)
        return 0
    if args.orden == "traer":
        if EN_SERVIDOR:
            sys.exit("«traer» es para el PC: en pepecono la db ya es la maestra")
        return 0 if traer() else 1
    if not DB.exists():
        sys.exit(f"No existe {DB}")

    if args.orden is None:
        return menu(scripts)
    if args.orden == "estado":
        estado()
    elif args.orden == "exportar":
        return main_exportar(not args.sin_subir)
    elif not EN_SERVIDOR:
        # run y diario: las actualizaciones solo se hacen en pepecono
        return en_servidor(sys.argv[1:])
    elif args.orden == "diario":
        preset = "semanal" if dt.date.today().weekday() == 6 else "rapido"
        print(f"📅 {dt.datetime.now():%Y-%m-%d %H:%M} · preset {preset}")
        return actualizar(resolver([preset], scripts), [])
    elif args.orden == "run":
        return actualizar(resolver(args.objetivos, scripts), args.param, not args.sin_exportar, not args.sin_subir)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit("\nInterrumpido.")
