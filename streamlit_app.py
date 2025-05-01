from scraping_module import render_scraping

# Diccionario de módulos disponibles
MODULOS = {
    "Scraping": render_scraping,
    # Aquí puedes agregar futuros módulos, por ejemplo:
    # "Análisis": render_analisis,
    # "Dashboards": render_dashboards,
}

# Ejecutar directamente el módulo que deseas trabajar
# Para esta versión, asumimos solo uno activo:
def main():
    render_scraping()

if __name__ == "__main__":
    main()
