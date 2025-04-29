#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serpy – entry-point con carga perezosa de módulos."""
import streamlit as st
import importlib

# Configuración general de la página
st.set_page_config(page_title="Serpy – Suite WordPress", layout="wide")

# Diccionario de módulos disponibles
MODULOS = {
    "Relaciones CPT": "relaciones_cpt_module",
    "Scraping": "scraping_module",
}

# Selector en barra lateral
opcion = st.sidebar.selectbox("Módulo", MODULOS.keys())

# Importación dinámica del módulo seleccionado
mod = importlib.import_module(MODULOS[opcion])
mod.render()
