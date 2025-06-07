import requests
import sys

def get_full_content(url, service_type):
    """
    Obtiene el contenido completo de una URL usando el servicio especificado
    
    Args:
        url: La URL del artículo
        service_type: El servicio a usar ('five_filters', 'mercury', 'readability')
    
    Returns:
        El contenido procesado del artículo
    """
    base_urls = {
        'five_filters': 'http://192.168.1.133:8000/extract.php?url=',
        'mercury': 'http://192.168.1.133:3001/parser',
        'readability': 'http://192.168.1.133:3002'
    }
    
    if service_type not in base_urls:
        raise ValueError(f"Servicio no soportado: {service_type}")
    
    if service_type == 'five_filters':
        params = {'url': url}
        response = requests.get(base_urls[service_type], params=params)
    elif service_type == 'mercury':
        params = {'url': url}
        response = requests.get(base_urls[service_type], params=params)
    elif service_type == 'readability':
        data = {'url': url}
        response = requests.post(base_urls[service_type], json=data)
    
    if response.status_code == 200:
        return response.json() if service_type in ['mercury', 'readability'] else response.text
    else:
        return f"Error: {response.status_code}, {response.text}"

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python script.py <url> <service_type>")
        sys.exit(1)
    
    url = sys.argv[1]
    service_type = sys.argv[2]
    
    result = get_full_content(url, service_type)
    print(result)