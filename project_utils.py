from pathlib import Path

def find_project_root(marker_files=('requirements.txt', 'base_module.py', 'music_padre.py', 'designer_module.py')):
    """Busca la raíz del proyecto basándose en archivos distintivos."""
    path = Path(__file__).resolve().parent  # Directorio donde está el módulo actual
    while path != path.parent:
        if any((path / marker).exists() for marker in marker_files):
            return path
        path = path.parent
    return Path(__file__).resolve().parent.parent  # Fallback: asumir que estamos en un subdirectorio

# Definir la raíz del proyecto
PROJECT_ROOT = find_project_root()
