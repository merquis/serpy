"""
Script para instalar rebrowser-playwright y configurar el entorno
"""
import subprocess
import sys
import os

def install_rebrowser():
    """Instala rebrowser-playwright y sus dependencias"""
    print("🔧 Instalando rebrowser-playwright...\n")
    
    try:
        # Desinstalar playwright normal si existe
        print("1. Desinstalando playwright normal (si existe)...")
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "playwright", "-y"], 
                      capture_output=True, text=True)
        
        # Instalar rebrowser-playwright
        print("2. Instalando rebrowser-playwright...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "rebrowser-playwright==1.52.0"],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Error al instalar: {result.stderr}")
            return False
        
        print("✅ rebrowser-playwright instalado correctamente")
        
        # Instalar navegadores
        print("\n3. Instalando navegadores...")
        result = subprocess.run(
            ["playwright", "install", "chromium"],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            print(f"⚠️  Advertencia al instalar navegadores: {result.stderr}")
            print("   Puedes instalarlos manualmente con: playwright install chromium")
        else:
            print("✅ Navegador Chromium instalado")
        
        # Verificar instalación
        print("\n4. Verificando instalación...")
        try:
            import playwright
            print(f"✅ Playwright importado correctamente")
            print(f"   Versión: {playwright.__version__ if hasattr(playwright, '__version__') else 'No disponible'}")
            
            # Verificar que es rebrowser-playwright
            from playwright.async_api import async_playwright
            print("✅ API async disponible")
            
            return True
            
        except ImportError as e:
            print(f"❌ Error al importar playwright: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

def main():
    print("=== Instalador de Rebrowser-Playwright ===\n")
    
    # Verificar si ya está instalado
    try:
        import playwright
        print("⚠️  Playwright ya está instalado.")
        response = input("¿Deseas reinstalarlo con rebrowser-playwright? (s/n): ")
        if response.lower() != 's':
            print("Instalación cancelada.")
            return
    except ImportError:
        pass
    
    # Instalar
    if install_rebrowser():
        print("\n✅ ¡Instalación completada con éxito!")
        print("\nPuedes probar rebrowser-playwright ejecutando:")
        print("  python test_rebrowser_playwright.py")
    else:
        print("\n❌ La instalación falló. Por favor, revisa los errores anteriores.")
        print("\nPuedes intentar instalar manualmente con:")
        print("  pip uninstall playwright -y")
        print("  pip install rebrowser-playwright==1.52.0")
        print("  playwright install chromium")

if __name__ == "__main__":
    main()
