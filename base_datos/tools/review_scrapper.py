#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import sys
import urllib.parse
import os

def buscar_album(artista, album):
    """
    Busca un álbum específico de un artista en AnyDecentMusic.
    
    Args:
        artista (str): Nombre del artista a buscar
        album (str): Nombre del álbum a buscar
        
    Returns:
        bool: True si el álbum del artista fue encontrado, False en caso contrario
    """
    # Construir la URL de búsqueda (podemos buscar por el nombre del álbum)
    termino_busqueda = artista
    url_busqueda = f"http://www.anydecentmusic.com/search-results.aspx?search={urllib.parse.quote(termino_busqueda)}"
    
    print(f"Buscando: {termino_busqueda}")
    print(f"URL de búsqueda: {url_busqueda}")
    
    # Realizar la petición HTTP
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        respuesta = requests.get(url_busqueda, headers=headers)
        respuesta.raise_for_status()  # Verificar si hay errores en la respuesta
    except requests.exceptions.RequestException as e:
        print(f"Error al realizar la petición: {e}")
        return False
    
    # Parsear el HTML con BeautifulSoup
    soup = BeautifulSoup(respuesta.text, 'html.parser')
    
    # Buscar todos los resultados de la lista
    resultados = soup.select('form > div > div > div > ul > li > div')
    
    if not resultados:
        print("No se encontraron resultados para la búsqueda.")
        return False
    
    print(f"Se encontraron {len(resultados)} resultados.")
    
    # Verificar cada resultado para encontrar coincidencias de artista y álbum
    encontrado = False
    for idx, resultado in enumerate(resultados, 1):
        # Intentar obtener el nombre del artista y álbum
        artista_elemento = resultado.select_one('a:nth-of-type(2) > h2')
        album_elemento = resultado.select_one('a:nth-of-type(3) > h3')
        
        if artista_elemento and album_elemento:
            nombre_artista = artista_elemento.text.strip()
            nombre_album = album_elemento.text.strip()
            
            print(f"Resultado {idx}:")
            print(f"  Artista: {nombre_artista}")
            print(f"  Álbum: {nombre_album}")
            
            # Verificar si coincide con lo que estamos buscando
            # Usamos .lower() para hacer la comparación sin distinguir mayúsculas/minúsculas
            if (artista.lower() in nombre_artista.lower() and 
                album.lower() in nombre_album.lower()):
                print(f"¡Coincidencia encontrada! Artista: {nombre_artista}, Álbum: {nombre_album}")
                encontrado = True
                # También podemos obtener la URL del álbum
                album_url = resultado.select_one('a:nth-of-type(3)')['href']
                album_url_completa = f"http://www.anydecentmusic.com/{album_url}"
                print(f"URL del álbum: {album_url_completa}")
                
                # Llamar a la nueva función para extraer los enlaces
                enlaces = extraer_enlaces_album(album_url_completa)
                
                # Guardar los enlaces en un archivo si es necesario
                if enlaces:
                    nombre_archivo = f"{nombre_artista} - {nombre_album} - enlaces.txt"
                    with open(nombre_archivo, 'w', encoding='utf-8') as f:
                        f.write(f"Enlaces para {nombre_artista} - {nombre_album}\n")
                        f.write("=" * 50 + "\n\n")
                        for enlace in enlaces:
                            f.write(f"{enlace['numero']}. {enlace['texto']}\n")
                            f.write(f"   URL: {enlace['url']}\n")
                            f.write(f"   Estado: {enlace['estado']}\n\n")
                    print(f"Enlaces 'Read Review' guardados en el archivo: {nombre_archivo}")
    if not encontrado:
        print(f"No se encontró el álbum '{album}' para el artista '{artista}'.")
    
    return encontrado


def extraer_enlaces_album(url_album):
    """
    Accede a la página del álbum y extrae todos los enlaces "Read Review".
    Verifica también si los enlaces están activos, retornan 404 o redireccionan.
    También registra errores no estándar (diferentes de 404 o 403).
    
    Args:
        url_album (str): URL de la página del álbum
        
    Returns:
        tuple: (enlaces_validos, enlaces_error) donde ambos son listas de enlaces
    """
    print(f"Accediendo a la página del álbum: {url_album}")
    
    # Realizar la petición HTTP
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        respuesta = requests.get(url_album, headers=headers)
        respuesta.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a la página del álbum: {e}")
        return [], []
    
    # Parsear el HTML
    soup = BeautifulSoup(respuesta.text, 'html.parser')
    
    # Buscar todos los elementos de la lista que contienen los enlaces
    elementos_lista = soup.select('form > div > div > div > ol > li')
    
    enlaces_validos = []
    enlaces_error = []
    total_enlaces = 0
    total_read_review = 0
    
    for idx, elemento in enumerate(elementos_lista, 1):
        # Buscar el enlace dentro de cada elemento de la lista
        enlace_elemento = elemento.select_one('p > a')
        if enlace_elemento and enlace_elemento.has_attr('href'):
            total_enlaces += 1
            url = enlace_elemento['href']
            texto = enlace_elemento.text.strip()
            
            # Solo procesar los enlaces "Read Review"
            if "Read Review" in texto:
                total_read_review += 1
                
                # Verificar si el enlace está vivo
                url_completa = url if url.startswith('http') else f"http://www.anydecentmusic.com{url}"
                
                try:
                    # Configurar para seguir redirecciones pero guardar la URL final
                    resp = requests.head(
                        url_completa, 
                        headers=headers, 
                        allow_redirects=True, 
                        timeout=10
                    )
                    
                    # Determinar el estado del enlace
                    if resp.status_code == 200:
                        estado = "Activo"
                        # Verificar si hubo redirección
                        if resp.url != url_completa:
                            estado = f"Redirigido a: {resp.url}"
                            url_completa = resp.url  # Actualizar URL a la redirección
                        
                        enlaces_validos.append({
                            'numero': idx,
                            'texto': texto,
                            'url': url_completa,
                            'estado': estado
                        })
                    elif resp.status_code in [404, 403]:
                        estado = f"Error {resp.status_code} - No disponible"
                        # No registramos estos errores comunes
                    else:
                        estado = f"Error HTTP: {resp.status_code}"
                        enlaces_error.append({
                            'numero': idx,
                            'texto': texto,
                            'url': url_completa,
                            'estado': estado,
                            'codigo': resp.status_code
                        })
                        
                except requests.exceptions.RequestException as e:
                    estado = f"Error al verificar: {str(e)}"
                    enlaces_error.append({
                        'numero': idx,
                        'texto': texto,
                        'url': url_completa,
                        'estado': estado,
                        'excepcion': str(e)
                    })
                
                print(f"Enlace {idx}: {texto} - {url_completa} -> {estado}")
    
    print(f"Total de enlaces: {total_enlaces}")
    print(f"Total de enlaces 'Read Review': {total_read_review}")
    print(f"Enlaces válidos encontrados: {len(enlaces_validos)}")
    print(f"Enlaces con errores no estándar: {len(enlaces_error)}")
    
    return enlaces_validos, enlaces_error


def guardar_errores_enlace(archivo_errores, artista, album, enlaces_error):
    """
    Guarda los enlaces con errores no estándar en un archivo
    
    Args:
        archivo_errores (str): Ruta al archivo donde guardar los errores
        artista (str): Nombre del artista
        album (str): Nombre del álbum
        enlaces_error (list): Lista de enlaces con errores
        
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    if not enlaces_error:
        return True
        
    try:
        # Crear el directorio si no existe
        directorio = os.path.dirname(archivo_errores)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio)
            
        # Abrir en modo append para no sobrescribir errores anteriores
        with open(archivo_errores, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"Artista: {artista}\n")
            f.write(f"Álbum: {album}\n")
            f.write(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*50}\n\n")
            
            for enlace in enlaces_error:
                f.write(f"URL: {enlace['url']}\n")
                f.write(f"Texto: {enlace['texto']}\n")
                f.write(f"Estado: {enlace['estado']}\n")
                
                # Añadir detalles adicionales si están disponibles
                if 'codigo' in enlace:
                    f.write(f"Código HTTP: {enlace['codigo']}\n")
                if 'excepcion' in enlace:
                    f.write(f"Excepción: {enlace['excepcion']}\n")
                
                f.write("\n")
                
        print(f"Errores guardados en {archivo_errores}")
        return True
    except Exception as e:
        print(f"Error al guardar errores en archivo: {e}")
        return False    

if __name__ == "__main__":
    # Verificar argumentos
    if len(sys.argv) != 3:
        print("Uso: python script.py 'nombre_artista' 'nombre_album'")
        sys.exit(1)
    
    artista = sys.argv[1]
    album = sys.argv[2]
    
    buscar_album(artista, album)