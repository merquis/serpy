#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
streamlit_app.py  —  entry-point de Serpy
----------------------------------------
Carga la interfaz principal y llama a:

• relaciones_cpt_module.render()
• scraping_module.render()
"""

import streamlit as st
import relaciones_cpt_module as relaciones
import scraping_module as scraping

# Config general de la página
st.set_page_config(page_title="Serpy – Suite WordPress", layout="wide")

# Menú principal en la barra lateral
seccion = st.sidebar.selectbox(
    "Módulo",
    ("Relaciones CPT", "Scraping")
)

# Delegamos al módulo correspondiente
if seccion == "Relaciones CPT":
    relaciones.render()
else:   # Scraping
    scraping.render()
