import os
import sqlite3
import requests
import time
import argparse
import spotipy
import hashlib
import re
from io import BytesIO
from PIL import Image
from spotipy.oauth2 import SpotifyClientCredentials
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from collections import Counter
from pathlib import Path

def parse_arguments():
    """Configura y parsea los argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(description='Descarga imágenes únicas de artistas desde Last.fm, Spotify y Google o elimina duplicados.')
    parser.add_argument('--db', '-d', help='Ruta al archivo de la base de datos SQLite')
    parser.add_argument('--output', '-o', help='Carpeta donde se guardarán las imágenes')
    parser.add_argument('--max-images', '-m', type=int, default=3, help='Número máximo de imágenes por artista (por defecto: 3)')
    parser.add_argument('--spotify-client-id', help='Spotify Client ID')
    parser.add_argument('--spotify-client-secret', help='Spotify Client Secret')
    parser.add_argument('--lastfm-apikey', help='Lastfm apikey')
    parser.add_argument('--similarity-threshold', '-t', type=float, default=0.85, 
                        help='Umbral para considerar dos imágenes como similares (0-1, por defecto: 0.85)')
    parser.add_argument('--force-all', '-f', action='store_true', 
                        help='Procesar todos los artistas, incluso los que ya tienen imágenes')
    parser.add_argument('--clean-duplicates', '-c', help='Eliminar imágenes duplicadas de la carpeta especificada')
    return parser.parse_args()

def get_artist_data_from_db(db_path):
    """Obtiene información detallada de artistas desde la base de datos"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Obtenemos artistas de la tabla 'artists' con sus IDs y URLs externas
    cursor.execute("""
        SELECT id, name, musicbrainz_url, spotify_url, discogs_url, 
               youtube_url, rateyourmusic_url
        FROM artists 
        WHERE name IS NOT NULL AND name != ''
    """)
    artists_data = {}
    for row in cursor.fetchall():
        artist_id, name, mb_url, spotify_url, discogs_url, youtube_url, rym_url = row
        artists_data[name] = {
            'id': artist_id,
            'musicbrainz_url': mb_url,
            'spotify_url': spotify_url,
            'discogs_url': discogs_url,
            'youtube_url': youtube_url,
            'rateyourmusic_url': rym_url
        }
    
    # También obtenemos nombres de artistas desde la tabla 'songs' y sus MBIDs
    cursor.execute("SELECT DISTINCT artist, mbid FROM songs WHERE artist IS NOT NULL AND artist != ''")
    for row in cursor.fetchall():
        artist_name, mbid = row
        if artist_name not in artists_data:
            artists_data[artist_name] = {
                'id': None,
                'musicbrainz_url': f"https://musicbrainz.org/artist/{mbid}" if mbid else None,
                'spotify_url': None,
                'discogs_url': None,
                'youtube_url': None,
                'rateyourmusic_url': None
            }
        elif mbid and not artists_data[artist_name].get('musicbrainz_url'):
            artists_data[artist_name]['musicbrainz_url'] = f"https://musicbrainz.org/artist/{mbid}"
    
    conn.close()
    
    return artists_data

def check_existing_images(output_dir, artist_name):
    """Verifica cuántas imágenes existen para un artista específico"""
    filename_base = artist_name.replace(' ', '_')
    filename_base = ''.join(c for c in filename_base if c.isalnum() or c in ['_', '-'])
    
    # Contar archivos que coinciden con el patrón del nombre del artista
    count = 0
    for file in os.listdir(output_dir):
        if file.startswith(filename_base + '_') and file.endswith('.jpg'):
            count += 1
    
    return count

def format_filename(artist_name, image_number):
    """Convierte el nombre del artista en un nombre de archivo válido"""
    # Reemplazar espacios por guiones bajos
    filename = artist_name.replace(' ', '_')
    # Eliminar caracteres no válidos para nombres de archivo
    filename = ''.join(c for c in filename if c.isalnum() or c in ['_', '-'])
    # Añadir número de imagen y extensión
    return f"{filename}_{image_number}.jpg"

def calculate_image_hash(image_data):
    """Calcula un hash perceptual simple de una imagen para comparación"""
    try:
        # Abrir la imagen desde los bytes
        img = Image.open(BytesIO(image_data))
        
        # Redimensionar a un tamaño pequeño (8x8) y convertir a blanco y negro para simplificar
        img = img.resize((8, 8)).convert('L')
        
        # Obtener los valores de píxeles
        pixels = list(img.getdata())
        
        # Calcular el valor medio
        avg_pixel = sum(pixels) / len(pixels)
        
        # Crear un hash binario: 1 si el pixel es mayor que la media, 0 en caso contrario
        bits = ''.join('1' if pixel > avg_pixel else '0' for pixel in pixels)
        
        # Convertir el hash binario a un valor hexadecimal
        hex_hash = hex(int(bits, 2))[2:].zfill(16)
        
        return hex_hash
    except Exception as e:
        print(f"Error calculando hash de imagen: {str(e)}")
        # En caso de error, devolver un hash aleatorio basado en el contenido
        return hashlib.md5(image_data).hexdigest()[:16]

def hamming_distance(hash1, hash2):
    """Calcula la distancia de Hamming entre dos hashes (representados como strings)"""
    # Verificar que los hashes tienen la misma longitud
    if len(hash1) != len(hash2):
        return float('inf')  # Valores completamente diferentes
        
    # Convertir hexadecimal a binario
    bin1 = bin(int(hash1, 16))[2:].zfill(64)
    bin2 = bin(int(hash2, 16))[2:].zfill(64)
    
    # Calcular diferencias
    return sum(bit1 != bit2 for bit1, bit2 in zip(bin1, bin2))

def is_similar_to_existing(new_img_hash, existing_hashes, threshold=0.85):
    """Verifica si una imagen es similar a alguna de las existentes"""
    if not existing_hashes:
        return False
        
    max_distance = 64  # Máxima distancia posible (64 bits)
    
    for existing_hash in existing_hashes:
        distance = hamming_distance(new_img_hash, existing_hash)
        similarity = 1 - (distance / max_distance)
        
        if similarity >= threshold:
            return True
            
    return False

def extract_musicbrainz_id(url):
    """Extrae el ID de MusicBrainz de una URL"""
    if not url:
        return None
    pattern = r'musicbrainz\.org/artist/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def extract_spotify_id(url):
    """Extrae el ID de Spotify de una URL"""
    if not url:
        return None
    pattern = r'spotify\.com/artist/([a-zA-Z0-9]{22})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def clean_artist_name(name):
    """Limpia el nombre del artista eliminando colaboraciones"""
    # Patrones comunes de colaboraciones
    patterns = [
        r'\s+feat\..*$',
        r'\s+featuring.*$',
        r'\s+with.*$',
        r'\s+&.*$',
        r'\s+ft\..*$',
        r'\s+vs\..*$',
        r'\s+\+.*$'
    ]
    
    cleaned_name = name
    for pattern in patterns:
        cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE)
    
    return cleaned_name.strip()

def download_and_check_image(url, artist_name, image_number, output_dir, existing_hashes, threshold=0.85):
    """Descarga una imagen, verifica que no sea similar a las existentes, y la guarda"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Verificar si es una imagen válida (tamaño mínimo)
        if len(response.content) < 1000:
            return None, False
            
        # Calcular el hash de la imagen
        img_hash = calculate_image_hash(response.content)
        
        # Verificar si es similar a alguna imagen existente
        if is_similar_to_existing(img_hash, existing_hashes, threshold):
            print(f"Imagen descartada por ser similar a una existente para {artist_name}")
            return None, False
            
        # Crear nombre de archivo
        image_filename = format_filename(artist_name, image_number)
        image_path = Path(output_dir, image_filename)
        
        # Guardar la imagen
        with open(image_path, 'wb') as img_file:
            img_file.write(response.content)
            
        print(f"Descargada imagen {image_number} para {artist_name}: {image_filename}")
        return img_hash, True
    except Exception as e:
        print(f"Error descargando/verificando imagen {image_number} para {artist_name}: {str(e)}")
        return None, False

def search_lastfm_images(artist_name, max_images=3, api_key=None, mbid=None, existing_hashes=None, output_dir=None, threshold=0.85):
    """Busca imágenes del artista en Last.fm, usando MBID si está disponible y descarga solo imágenes únicas"""
    if not api_key:
        print(f"Error: No se proporcionó API key para Last.fm")
        return []
    
    if existing_hashes is None:
        existing_hashes = []
        
    base_url = "http://ws.audioscrobbler.com/2.0/"
    
    # Consultar información del artista
    params = {
        "method": "artist.getinfo",
        "api_key": api_key,
        "format": "json"
    }
    
    # Si tenemos MBID, usarlo en lugar del nombre
    if mbid:
        params["mbid"] = mbid
    else:
        params["artist"] = artist_name
    
    downloaded_images = []
    downloaded_hashes = list(existing_hashes)  # Copiar la lista para no modificar la original
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "artist" in data and "image" in data["artist"]:
            # Last.fm proporciona varias resoluciones para cada imagen
            for image in data["artist"]["image"]:
                # Filtrar imágenes por defecto/placeholder
                if (image["size"] == "extralarge" and 
                    image["#text"] and 
                    not image["#text"].endswith("/2a96cbd8b46e442fc41c2b86b821562f.png") and
                    not "/noimage/" in image["#text"] and
                    not "placeholder" in image["#text"].lower()):
                    
                    # Descargar y verificar que no es un duplicado
                    img_hash, success = download_and_check_image(
                        image["#text"], artist_name, len(downloaded_images) + len(existing_hashes) + 1, 
                        output_dir, downloaded_hashes, threshold
                    )
                    
                    if success and img_hash:
                        downloaded_images.append((image["#text"], img_hash))
                        downloaded_hashes.append(img_hash)
                        
                        if len(downloaded_images) >= max_images:
                            break
        
        # Si no tenemos suficientes imágenes, intentar con getImages
        if len(downloaded_images) < max_images:
            params["method"] = "artist.getImages"
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                data = response.json()
                if "images" in data and "image" in data["images"]:
                    for img_data in data["images"]["image"]:
                        if len(downloaded_images) >= max_images:
                            break
                        if "sizes" in img_data and "size" in img_data["sizes"]:
                            for size in img_data["sizes"]["size"]:
                                if (size["name"] == "original" and 
                                    size["#text"] and 
                                    not size["#text"].endswith("/2a96cbd8b46e442fc41c2b86b821562f.png") and
                                    not "/noimage/" in size["#text"] and
                                    not "placeholder" in size["#text"].lower()):
                                    
                                    # Descargar y verificar que no es un duplicado
                                    img_hash, success = download_and_check_image(
                                        size["#text"], artist_name, len(downloaded_images) + len(existing_hashes) + 1, 
                                        output_dir, downloaded_hashes, threshold
                                    )
                                    
                                    if success and img_hash:
                                        downloaded_images.append((size["#text"], img_hash))
                                        downloaded_hashes.append(img_hash)
                                        
                                        if len(downloaded_images) >= max_images:
                                            break
    except Exception as e:
        print(f"Error buscando en Last.fm para {artist_name}: {str(e)}")
    
    # Si no obtuvimos suficientes imágenes y usamos MBID, intentar con el nombre
    if len(downloaded_images) < max_images and mbid:
        try:
            params = {
                "method": "artist.getinfo",
                "artist": artist_name,
                "api_key": api_key,
                "format": "json"
            }
            
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "artist" in data and "image" in data["artist"]:
                for image in data["artist"]["image"]:
                    if len(downloaded_images) >= max_images:
                        break
                    
                    if (image["size"] == "extralarge" and 
                        image["#text"] and 
                        not image["#text"].endswith("/2a96cbd8b46e442fc41c2b86b821562f.png") and
                        not "/noimage/" in image["#text"] and
                        not "placeholder" in image["#text"].lower()):
                        
                        # Verificar que no es una URL ya procesada
                        if not any(url == image["#text"] for url, _ in downloaded_images):
                            # Descargar y verificar que no es un duplicado
                            img_hash, success = download_and_check_image(
                                image["#text"], artist_name, len(downloaded_images) + len(existing_hashes) + 1, 
                                output_dir, downloaded_hashes, threshold
                            )
                            
                            if success and img_hash:
                                downloaded_images.append((image["#text"], img_hash))
                                downloaded_hashes.append(img_hash)
        except Exception as e:
            print(f"Error en segundo intento de Last.fm para {artist_name}: {str(e)}")
    
    return downloaded_images


def search_spotify_images(artist_name, spotify_id, sp, max_images=3, existing_hashes=None, output_dir=None, threshold=0.85):
    """Busca imágenes del artista en Spotify usando spotipy y descarga solo imágenes únicas"""
    if existing_hashes is None:
        existing_hashes = []
        
    downloaded_images = []
    downloaded_hashes = list(existing_hashes)  # Copiar la lista para no modificar la original
    
    try:
        # Primero intentamos usar el ID si está disponible
        if spotify_id:
            try:
                artist_data = sp.artist(spotify_id)
                if artist_data and "images" in artist_data and artist_data["images"]:
                    # Ordenar por tamaño y tomar las más grandes
                    sorted_images = sorted(artist_data["images"], key=lambda x: x.get("width", 0) * x.get("height", 0), reverse=True)
                    for img in sorted_images:
                        if len(downloaded_images) >= max_images:
                            break
                            
                        if "url" in img:
                            # Descargar y verificar que no es un duplicado
                            img_hash, success = download_and_check_image(
                                img["url"], artist_name, len(downloaded_images) + len(existing_hashes) + 1, 
                                output_dir, downloaded_hashes, threshold
                            )
                            
                            if success and img_hash:
                                downloaded_images.append((img["url"], img_hash))
                                downloaded_hashes.append(img_hash)
            except Exception as inner_e:
                print(f"Error con Spotify ID para {artist_name}: {str(inner_e)}")
        
        # Si no tenemos suficientes imágenes, hacer una búsqueda por nombre
        if len(downloaded_images) < max_images:
            # Limpiar el nombre del artista para mejor coincidencia
            clean_name = clean_artist_name(artist_name)
            results = sp.search(q=f"artist:{clean_name}", type="artist", limit=5)
            
            if results and "artists" in results and "items" in results["artists"]:
                for artist in results["artists"]["items"]:
                    if len(downloaded_images) >= max_images:
                        break
                        
                    # Verificar si el nombre coincide
                    if (artist["name"].lower() == clean_name.lower() or 
                        clean_name.lower() in artist["name"].lower() or
                        artist["name"].lower() in clean_name.lower()):
                        
                        if "images" in artist and artist["images"]:
                            # Ordenar por tamaño y tomar las más grandes
                            sorted_images = sorted(artist["images"], key=lambda x: x.get("width", 0) * x.get("height", 0), reverse=True)
                            for img in sorted_images:
                                if len(downloaded_images) >= max_images:
                                    break
                                    
                                if "url" in img:
                                    # Verificar que no es una URL ya procesada
                                    if not any(url == img["url"] for url, _ in downloaded_images):
                                        # Descargar y verificar que no es un duplicado
                                        img_hash, success = download_and_check_image(
                                            img["url"], artist_name, len(downloaded_images) + len(existing_hashes) + 1, 
                                            output_dir, downloaded_hashes, threshold
                                        )
                                        
                                        if success and img_hash:
                                            downloaded_images.append((img["url"], img_hash))
                                            downloaded_hashes.append(img_hash)
    except Exception as e:
        print(f"Error buscando en Spotify para {artist_name}: {str(e)}")
    
    return downloaded_images

def search_google_images(artist_name, max_images=3, existing_hashes=None, output_dir=None, threshold=0.85):
    """Busca imágenes del artista en Google y descarga solo imágenes únicas"""
    if existing_hashes is None:
        existing_hashes = []
        
    # Limpiar el nombre del artista para mejor búsqueda
    clean_name = clean_artist_name(artist_name)
    search_url = f"https://www.google.com/search?q={quote_plus(clean_name)}+musician+artist+photo&tbm=isch"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    downloaded_images = []
    downloaded_hashes = list(existing_hashes)  # Copiar la lista para no modificar la original
    
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        image_tags = soup.find_all('img')
        
        # Saltamos la primera imagen que suele ser el logo de Google
        for img in image_tags[1:]:
            if len(downloaded_images) >= max_images:
                break
                
            src = img.get('src')
            if src and src.startswith('http'):
                # Verificar que no es una URL ya procesada
                if not any(url == src for url, _ in downloaded_images):
                    # Descargar y verificar que no es un duplicado
                    img_hash, success = download_and_check_image(
                        src, artist_name, len(downloaded_images) + len(existing_hashes) + 1, 
                        output_dir, downloaded_hashes, threshold
                    )
                    
                    if success and img_hash:
                        downloaded_images.append((src, img_hash))
                        downloaded_hashes.append(img_hash)
    except Exception as e:
        print(f"Error buscando en Google para {artist_name}: {str(e)}")
    
    return downloaded_images


def find_and_remove_duplicates(folder_path, similarity_threshold=0.85):
    """Encuentra y elimina imágenes duplicadas en la carpeta especificada"""
    print(f"Buscando imágenes duplicadas en {folder_path}...")
    
    # Verificar que la carpeta existe
    if not os.path.exists(folder_path):
        print(f"Error: La carpeta {folder_path} no existe")
        return
    
    # Obtener lista de todas las imágenes
    image_files = []
    for file in os.listdir(folder_path):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            image_files.append(file)
    
    if not image_files:
        print("No se encontraron imágenes en la carpeta")
        return
    
    print(f"Encontradas {len(image_files)} imágenes. Calculando hashes...")
    
    # Calcular hash de cada imagen
    image_hashes = {}
    for file in image_files:
        file_path = Path(folder_path, file)
        try:
            with open(file_path, 'rb') as f:
                img_data = f.read()
                img_hash = calculate_image_hash(img_data)
                image_hashes[file] = img_hash
        except Exception as e:
            print(f"Error procesando {file}: {str(e)}")
    
    print("Comparando imágenes para encontrar duplicados...")
    
    # Agrupar imágenes por similitud
    duplicates = []
    processed = set()
    
    for file1 in image_files:
        if file1 in processed:
            continue
            
        group = [file1]
        processed.add(file1)
        
        for file2 in image_files:
            if file2 == file1 or file2 in processed:
                continue
                
            # Calcular similitud
            max_distance = 64  # Máxima distancia posible (64 bits)
            distance = hamming_distance(image_hashes[file1], image_hashes[file2])
            similarity = 1 - (distance / max_distance)
            
            if similarity >= similarity_threshold:
                group.append(file2)
                processed.add(file2)
        
        if len(group) > 1:
            duplicates.append(group)
    
    # Eliminar duplicados (preservando una imagen de cada grupo)
    total_removed = 0
    for group in duplicates:
        print(f"Grupo de imágenes similares:")
        for idx, file in enumerate(group):
            file_path = Path(folder_path, file)
            file_size = os.path.getsize(file_path) / 1024  # KB
            print(f"  {idx+1}. {file} ({file_size:.1f} KB)")
        
        # Preservar la primera imagen (potencialmente la de mejor calidad o más grande)
        keep = group[0]
        remove = group[1:]
        
        print(f"  Manteniendo: {keep}")
        print(f"  Eliminando: {', '.join(remove)}")
        
        for file in remove:
            try:
                os.remove(Path(folder_path, file))
                total_removed += 1
            except Exception as e:
                print(f"  Error al eliminar {file}: {str(e)}")
    
    print(f"\nProceso completado. Se eliminaron {total_removed} imágenes duplicadas.")
    if total_removed == 0 and not duplicates:
        print("No se encontraron imágenes duplicadas.")



def main():
    """Función principal del script"""
    args = parse_arguments()
    
    # Verificar si se debe ejecutar el modo de limpieza de duplicados
    if args.clean_duplicates:
        find_and_remove_duplicates(args.clean_duplicates, args.similarity_threshold)
        return
        
    # El resto de la función main original se mantiene igual
    lastfm_apikey = args.lastfm_apikey

    # Verificar que la base de datos existe
    if not os.path.isfile(args.db):
        print(f"Error: No se encontró la base de datos en {args.db}")
        return
    
    # Crear la carpeta de salida si no existe
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # Configurar Spotify si se proporcionaron credenciales
    spotify_enabled = False
    sp = None
    if args.spotify_client_id and args.spotify_client_secret:
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=args.spotify_client_id,
                client_secret=args.spotify_client_secret
            )
            sp = spotipy.Spotify(auth_manager=auth_manager)
            spotify_enabled = True
            print("Autenticación con Spotify configurada correctamente")
        except Exception as e:
            print(f"Error configurando Spotify: {str(e)}")
    else:
        print("No se proporcionaron credenciales de Spotify. Se omitirá la búsqueda en Spotify.")
    
    # Obtener datos de artistas de la base de datos
    artists_data = get_artist_data_from_db(args.db)
    print(f"Encontrados {len(artists_data)} artistas en la base de datos")
    
    # Estadísticas para el recuento final
    stats = {
        'total_artists': len(artists_data),
        'processed': 0,
        'with_0_images': 0,
        'with_1_images': 0,
        'with_2_images': 0,
        'with_3_images': 0,
        'with_max_images': 0,
        'with_missing_images': 0
    }
    
    # Lista para almacenar artistas con fotos incompletas
    incomplete_artists = []
    
    # Primero, verificar todos los artistas y sus imágenes actuales
    print("\nVerificando imágenes existentes de artistas...")
    for artist_name, artist_info in artists_data.items():
        existing_images = check_existing_images(args.output, artist_name)
        
        if existing_images >= args.max_images and not args.force_all:
            stats['with_max_images'] += 1
            print(f"✅ {artist_name}: Ya tiene {existing_images}/{args.max_images} imágenes")
        else:
            stats[f'with_{existing_images}_images'] += 1
            stats['with_missing_images'] += 1
            incomplete_artists.append((artist_name, existing_images, artist_info))
            print(f"⚠️ {artist_name}: Solo tiene {existing_images}/{args.max_images} imágenes")
    
    # Procesar artistas con imágenes incompletas
    print(f"\nProcesando {len(incomplete_artists)} artistas con imágenes incompletas...")
    
    for i, (artist, existing_count, artist_info) in enumerate(incomplete_artists):
        print(f"\nProcesando artista {i+1}/{len(incomplete_artists)}: {artist} ({existing_count}/{args.max_images} imágenes)")
        
        # Extraer IDs para servicios externos
        mbid = extract_musicbrainz_id(artist_info.get('musicbrainz_url'))
        spotify_id = extract_spotify_id(artist_info.get('spotify_url'))
        
        # Si hay imágenes existentes, necesitamos cargar sus hashes para evitar duplicados
        image_hashes = []
        if existing_count > 0:
            for i in range(1, existing_count + 1):
                img_path = Path(args.output, format_filename(artist, i))
                if os.path.exists(img_path):
                    try:
                        with open(img_path, 'rb') as f:
                            img_data = f.read()
                            img_hash = calculate_image_hash(img_data)
                            image_hashes.append(img_hash)
                    except Exception as e:
                        print(f"Error leyendo imagen existente: {str(e)}")
        
        # Número de imágenes que necesitamos encontrar
        needed_images = args.max_images - existing_count
        total_downloaded = existing_count
        
        # 1. Buscar y descargar imágenes de Last.fm
        print(f"Buscando imágenes de {artist} en Last.fm...")
        lastfm_downloads = search_lastfm_images(
            artist, needed_images, lastfm_apikey, mbid, 
            image_hashes, args.output, args.similarity_threshold
        )
        
        # Actualizar contadores y hashes
        total_downloaded += len(lastfm_downloads)
        for _, img_hash in lastfm_downloads:
            image_hashes.append(img_hash)
        
        # Verificar si ya tenemos suficientes imágenes
        if total_downloaded >= args.max_images:
            print(f"✅ Se completaron las {args.max_images} imágenes para {artist} usando Last.fm")
        else:
            # 2. Buscar y descargar imágenes de Spotify si está configurado
            if spotify_enabled:
                print(f"Buscando imágenes de {artist} en Spotify...")
                spotify_downloads = search_spotify_images(
                    artist, spotify_id, sp, args.max_images - total_downloaded,
                    image_hashes, args.output, args.similarity_threshold
                )
                
                # Actualizar contadores y hashes
                total_downloaded += len(spotify_downloads)
                for _, img_hash in spotify_downloads:
                    image_hashes.append(img_hash)
            
            # Verificar si ya tenemos suficientes imágenes
            if total_downloaded >= args.max_images:
                print(f"✅ Se completaron las {args.max_images} imágenes para {artist} usando Last.fm y Spotify")
            else:
                # 3. Buscar y descargar imágenes de Google como último recurso
                print(f"Buscando imágenes de {artist} en Google...")
                google_downloads = search_google_images(
                    artist, args.max_images - total_downloaded,
                    image_hashes, args.output, args.similarity_threshold
                )
                
                # Actualizar contadores
                total_downloaded += len(google_downloads)
        
        # Actualizar estadísticas
        stats['processed'] += 1
        
        if total_downloaded == existing_count:
            print(f"⚠️ No se pudieron encontrar más imágenes para {artist}")
        elif total_downloaded < args.max_images:
            print(f"⚠️ Solo se pudieron encontrar {total_downloaded}/{args.max_images} imágenes para {artist}")
            # Actualizar estadísticas
            stats[f'with_{existing_count}_images'] -= 1
            stats[f'with_{total_downloaded}_images'] += 1
        else:
            print(f"✅ Se completaron las {args.max_images} imágenes para {artist}")
            # Actualizar estadísticas
            stats[f'with_{existing_count}_images'] -= 1
            stats['with_max_images'] += 1
            stats['with_missing_images'] -= 1
        
        # Pausa entre artistas para evitar ser bloqueado
        time.sleep(1)
    
    # Imprimir estadísticas finales
    print("\n" + "="*50)
    print("RESUMEN DE PROCESAMIENTO")
    print("="*50)
    print(f"Total de artistas: {stats['total_artists']}")
    print(f"Artistas procesados: {stats['processed']}")
    print(f"Artistas con 0 imágenes: {stats['with_0_images']}")
    print(f"Artistas con 1 imagen: {stats['with_1_images']}")
    print(f"Artistas con 2 imágenes: {stats['with_2_images']}")
    print(f"Artistas con {args.max_images} imágenes completas: {stats['with_max_images']}")
    print(f"Artistas con imágenes incompletas: {stats['with_missing_images']}")
    print("="*50)
    
    print(f"\nProceso completado. Las imágenes han sido guardadas en la carpeta '{args.output}'")

if __name__ == "__main__":
    main()