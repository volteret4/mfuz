#!/usr/bin/env python3
"""
Script para verificar dependencias del sistema antes de ejecutar la aplicación.
"""

import subprocess
import sys
import platform

def check_system_dependencies():
    """Verifica dependencias específicas del sistema operativo."""
    
    system = platform.system()
    print(f"Sistema detectado: {system}")
    
    if system == "Linux":
        try:
            with open('/etc/os-release', 'r') as f:
                os_info = f.read()
            
            if 'debian' in os_info.lower() or 'ubuntu' in os_info.lower():
                return check_debian_dependencies()
            elif 'arch' in os_info.lower():
                return check_arch_dependencies()
            else:
                print("Distribución no reconocida, verificación manual requerida")
                return True
                
        except Exception as e:
            print(f"Error detectando distribución: {e}")
            return True
    
    return True

def check_debian_dependencies():
    """Verifica dependencias en sistemas Debian/Ubuntu."""
    required_packages = [
        'libxcb-cursor0',
        'libqt6gui6', 
        'libqt6widgets6',
        'libqt6core6'
    ]
    
    missing = []
    for package in required_packages:
        try:
            result = subprocess.run(['dpkg', '-l', package], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                missing.append(package)
        except:
            missing.append(package)
    
    if missing:
        print("❌ Faltan dependencias:")
        for pkg in missing:
            print(f"   - {pkg}")
        print(f"\n📦 Instalar con: sudo apt install {' '.join(missing)}")
        return False
    else:
        print("✅ Todas las dependencias del sistema están instaladas")
        return True

def check_arch_dependencies():
    """Verifica dependencias en sistemas Arch."""
    required_packages = ['qt6-base', 'xcb-util-cursor']
    
    missing = []
    for package in required_packages:
        try:
            result = subprocess.run(['pacman', '-Q', package], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                missing.append(package)
        except:
            missing.append(package)
    
    if missing:
        print("❌ Faltan dependencias:")
        for pkg in missing:
            print(f"   - {pkg}")
        print(f"\n📦 Instalar con: sudo pacman -S {' '.join(missing)}")
        return False
    else:
        print("✅ Todas las dependencias del sistema están instaladas")
        return True

if __name__ == "__main__":
    if check_system_dependencies():
        print("\n🚀 Sistema listo para ejecutar la aplicación")
        sys.exit(0)
    else:
        print("\n❌ Instala las dependencias faltantes antes de continuar")
        sys.exit(1)