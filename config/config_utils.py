import json
import yaml
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Clase utilitaria para manejar archivos de configuración tanto en formato YAML como JSON.
    Provee métodos para leer y escribir configuraciones con manejo de errores.
    """
    
    @staticmethod
    def read_config(file_path, default_config=None):
        """
        Lee un archivo de configuración en formato YAML o JSON.
        
        Args:
            file_path (str): Ruta al archivo de configuración.
            default_config (dict, optional): Configuración por defecto si no se puede leer el archivo.
            
        Returns:
            dict: Datos de configuración cargados o configuración por defecto.
        """
        if default_config is None:
            default_config = {}
            
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"Archivo de configuración no encontrado: {file_path}")
            return default_config
            
        try:
            # Determinar el formato basado en la extensión
            ext = file_path.suffix.lower()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                if ext == '.yaml' or ext == '.yml':
                    config = yaml.safe_load(f)
                    logger.info(f"Configuración YAML cargada desde {file_path}")
                elif ext == '.json':
                    config = json.load(f)
                    logger.info(f"Configuración JSON cargada desde {file_path}")
                else:
                    # Intentar ambos formatos
                    try:
                        # Primero probar YAML
                        f.seek(0)
                        config = yaml.safe_load(f)
                        logger.info(f"Configuración interpretada como YAML desde {file_path}")
                    except:
                        # Si falla, probar JSON
                        f.seek(0)
                        config = json.load(f)
                        logger.info(f"Configuración interpretada como JSON desde {file_path}")
            
            return config if config is not None else default_config
                
        except Exception as e:
            logger.error(f"Error al leer archivo de configuración {file_path}: {e}")
            return default_config
    
    @staticmethod
    def write_config(file_path, config_data, format='yaml'):
        """
        Escribe datos de configuración a un archivo en formato YAML o JSON.
        
        Args:
            file_path (str): Ruta al archivo donde guardar la configuración.
            config_data (dict): Datos de configuración a guardar.
            format (str): Formato a usar ('yaml' o 'json').
            
        Returns:
            bool: True si se guardó correctamente, False en caso contrario.
        """
        file_path = Path(file_path)
        
        # Asegurar que el directorio existe
        os.makedirs(file_path.parent, exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if format.lower() == 'yaml':
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
                    logger.info(f"Configuración guardada en formato YAML en {file_path}")
                else:
                    json.dump(config_data, f, indent=2)
                    logger.info(f"Configuración guardada en formato JSON en {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error al escribir archivo de configuración {file_path}: {e}")
            return False
    
    @staticmethod
    def convert_json_to_yaml(json_path, yaml_path):
        """
        Convierte un archivo JSON a formato YAML.
        
        Args:
            json_path (str): Ruta al archivo JSON.
            yaml_path (str): Ruta donde guardar el archivo YAML.
            
        Returns:
            bool: True si la conversión fue exitosa, False en caso contrario.
        """
        try:
            config = ConfigManager.read_config(json_path, {})
            return ConfigManager.write_config(yaml_path, config, 'yaml')
        except Exception as e:
            logger.error(f"Error al convertir JSON a YAML: {e}")
            return False
    
    @staticmethod
    def make_path_relative(path, base_path):
        """
        Convierte una ruta absoluta en relativa respecto a una ruta base.
        
        Args:
            path (str): Ruta a convertir.
            base_path (str): Ruta base de referencia.
            
        Returns:
            str: Ruta relativa si es posible, o la original si no.
        """
        if not path or not isinstance(path, str):
            return path
            
        try:
            if os.path.isabs(path):
                rel_path = os.path.relpath(path, base_path)
                return rel_path
        except ValueError:
            # Ocurre si las rutas están en unidades diferentes en Windows
            pass
            
        return path
    
    @staticmethod
    def process_paths_in_config(config, base_path, process_func=None):
        """
        Procesa todas las rutas en un diccionario de configuración recursivamente.
        
        Args:
            config (dict): Configuración a procesar.
            base_path (str): Ruta base para resolver rutas relativas.
            process_func (callable): Función para procesar cada ruta.
            
        Returns:
            dict: Configuración con rutas procesadas.
        """
        if process_func is None:
            process_func = lambda p, b: ConfigManager.make_path_relative(p, b)
            
        def _process_item(item):
            if isinstance(item, dict):
                return {k: _process_item(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [_process_item(i) for i in item]
            elif isinstance(item, str) and (
                    os.path.isabs(item) or 
                    item.endswith('.py') or
                    item.endswith('.sqlite') or
                    '/home/' in item or 
                    '\\' in item or
                    '/' in item
                ):
                # Probablemente es una ruta
                return process_func(item, base_path)
            else:
                return item
                
        return _process_item(config)