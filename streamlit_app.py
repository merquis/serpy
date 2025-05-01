from scraping_module import render_scraping
from cpt_module import render_cpt_module

# Diccionario de módulos disponibles
MODULOS = {
    "Scraping": render_scraping,
    "CPT Wordpress": render_cpt_module,
}

def main():
    # Cada módulo se encarga de su GUI interna
    for nombre, funcion in MODULOS.items():
        if nombre in st.session_state and st.session_state[nombre]:
            funcion()
            return

    # Si no hay selección activa, ejecutamos el primero por defecto
    MODULOS["Scraping"]()

if __name__ == "__main__":
    main()
