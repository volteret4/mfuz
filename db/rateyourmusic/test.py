#!/usr/bin/env python3
"""
Script para probar los extractores de contenido con URLs de RateYourMusic
"""

import requests
import json
import sys
import re
from urllib.parse import quote_plus

def get_full_content(url, service_type):
    """
    Obtiene el contenido completo de una URL usando el servicio especificado
    """
    base_urls = {
        'five_filters': 'http://192.168.1.133:8000/extract.php?url=',
        'mercury': 'http://192.168.1.133:3001/parser',
        'readability': 'http://192.168.1.133:3002'
    }
    
    if service_type not in base_urls:
        raise ValueError(f"Servicio no soportado: {service_type}")
    
    try:
        if service_type == 'five_filters':
            params = {'url': url}
            response = requests.get(base_urls[service_type], params=params, timeout=30)
        elif service_type == 'mercury':
            params = {'url': url}
            response = requests.get(base_urls[service_type], params=params, timeout=30)
        elif service_type == 'readability':
            data = {'url': url}
            response = requests.post(base_urls[service_type], json=data, timeout=30)
        
        if response.status_code == 200:
            return response.json() if service_type in ['mercury', 'readability'] else response.text
        else:
            return f"Error: {response.status_code}, {response.text}"
    
    except Exception as e:
        return f"Exception: {str(e)}"

def test_all_services_with_rym(rym_url):
    """
    Prueba todos los servicios con una URL de RateYourMusic
    """
    services = ['five_filters', 'mercury', 'readability']
    results = {}
    
    print(f"Probando extracción de contenido para: {rym_url}\n")
    
    for service in services:
        print(f"=== Probando {service.upper()} ===")
        
        try:
            result = get_full_content(rym_url, service)
            
            if isinstance(result, str) and result.startswith(('Error:', 'Exception:')):
                print(f"❌ {service}: {result}")
                results[service] = {'status': 'error', 'message': result}
            else:
                # Analizar el contenido obtenido
                analysis = analyze_content(result, service)
                results[service] = analysis
                
                print(f"✅ {service}: {analysis['summary']}")
                
                # Buscar información específica de artista en el contenido
                artist_info = extract_artist_info_from_content(result, service)
                if artist_info:
                    results[service]['artist_info'] = artist_info
                    print(f"   🎵 Info encontrada: {list(artist_info.keys())}")
        
        except Exception as e:
            print(f"❌ {service}: Error - {str(e)}")
            results[service] = {'status': 'error', 'message': str(e)}
        
        print()
    
    return results

def analyze_content(content, service_type):
    """
    Analiza el contenido obtenido de cada servicio
    """
    if service_type == 'five_filters':
        # five_filters devuelve HTML directo
        content_length = len(content) if isinstance(content, str) else 0
        return {
            'status': 'success',
            'type': 'html',
            'length': content_length,
            'summary': f'HTML de {content_length} caracteres'
        }
    
    elif service_type in ['mercury', 'readability']:
        # Mercury y readability devuelven JSON
        if isinstance(content, dict):
            title = content.get('title', 'Sin título')
            text_content = content.get('content', content.get('text', ''))
            content_length = len(text_content) if text_content else 0
            
            return {
                'status': 'success',
                'type': 'json',
                'title': title,
                'length': content_length,
                'summary': f'"{title}" - {content_length} caracteres',
                'raw_data': content
            }
        else:
            return {
                'status': 'error',
                'message': 'Respuesta no es JSON válido'
            }

def extract_artist_info_from_content(content, service_type):
    """
    Extrae información específica del artista del contenido obtenido
    """
    text = ""
    
    # Obtener texto según el tipo de servicio
    if service_type == 'five_filters':
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
    elif service_type in ['mercury', 'readability'] and isinstance(content, dict):
        text = content.get('content', content.get('text', ''))
        if text:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(text, 'html.parser')
            text = soup.get_text()
    
    if not text:
        return None
    
    # Buscar patrones específicos de información de artista
    artist_info = {}
    
    # Patrones de búsqueda mejorados
    patterns = {
        'birth': [
            r'Born:?\s*([^,\n]+(?:,\s*[^,\n]+)*)',
            r'b\.\s*([^,\n]+)',
            r'Birth:?\s*([^,\n]+)',
            r'(\d{1,2}\s+\w+\s+\d{4})',  # 8 January 1975
            r'(\w+\s+\d{1,2},\s+\d{4})'  # January 8, 1975
        ],
        'death': [
            r'Died:?\s*([^,\n]+(?:,\s*[^,\n]+)*)',
            r'd\.\s*([^,\n]+)',
            r'Death:?\s*([^,\n]+)'
        ],
        'genres': [
            r'Genre[s]?:?\s*([^\n]+)',
            r'Style[s]?:?\s*([^\n]+)',
            r'Primary genre[s]?:?\s*([^\n]+)'
        ],
        'origin': [
            r'Origin:?\s*([^\n]+)',
            r'From:?\s*([^\n]+)',
            r'Location:?\s*([^\n]+)'
        ],
        'years_active': [
            r'Years active:?\s*([^\n]+)',
            r'Active:?\s*([^\n]+)',
            r'(\d{4}[-–]\d{4})',
            r'(\d{4}[-–]present)'
        ],
        'also_known_as': [
            r'(?:Also known as|AKA|a\.k\.a\.):?\s*([^\n]+)',
            r'Aliases?:?\s*([^\n]+)'
        ]
    }
    
    for info_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                if value and len(value) > 1:
                    artist_info[info_type] = value
                    break
    
    # Buscar información en estructura de tabla (si existe)
    if service_type == 'five_filters':
        artist_info.update(extract_from_html_tables(content))
    
    return artist_info if artist_info else None

def extract_from_html_tables(html_content):
    """
    Extrae información de tablas HTML específicamente
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'html.parser')
    table_info = {}
    
    # Buscar tablas con información del artista
    tables = soup.find_all('table', class_=['artist_info', 'infobox'])
    
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                header = cells[0].get_text().strip().lower()
                value = cells[1].get_text().strip()
                
                if 'born' in header or 'birth' in header:
                    table_info['birth_info'] = value
                elif 'died' in header or 'death' in header:
                    table_info['death_info'] = value
                elif 'genre' in header:
                    table_info['genres_table'] = value
                elif 'origin' in header or 'from' in header:
                    table_info['origin_table'] = value
    
    return table_info

def save_detailed_results(results, rym_url):
    """
    Guarda resultados detallados para análisis posterior
    """
    filename = f"rym_extraction_test_{rym_url.split('/')[-1]}.json"
    
    # Preparar datos para guardar
    save_data = {
        'url': rym_url,
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'results': results
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    
    print(f"📁 Resultados detallados guardados en: {filename}")

def main():
    """
    Función principal para testing
    """
    # URLs de ejemplo de RateYourMusic para probar
    test_urls = [
        "https://rateyourmusic.com/artist/radiohead",
        "https://rateyourmusic.com/artist/aphex-twin",
        "https://rateyourmusic.com/artist/bjork"
    ]
    
    if len(sys.argv) > 1:
        # Usar URL proporcionada como argumento
        rym_url = sys.argv[1]
        test_urls = [rym_url]
    
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"PROBANDO: {url}")
        print(f"{'='*60}")
        
        results = test_all_services_with_rym(url)
        save_detailed_results(results, url)
        
        # Mostrar resumen
        print("\n📊 RESUMEN:")
        for service, result in results.items():
            if result.get('status') == 'success':
                info_count = len(result.get('artist_info', {}))
                print(f"   {service}: ✅ ({info_count} campos de info)")
            else:
                print(f"   {service}: ❌ {result.get('message', 'Error')}")
        
        print("\n" + "="*60)

if __name__ == "__main__":
    main()