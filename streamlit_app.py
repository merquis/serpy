#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
streamlit_app.py — entry-point de Serpy
Carga la interfaz principal y, solo cuando el
usuario lo selecciona, importa el módulo correspondiente.
"""

import streamlit as st
import importlib

st.set_page_config(page_title="Serpy – Suite WordPress", layout="wide")

MODULOS = {
    "Relaciones CPT": "relaciones_cpt_module",
    "Scraping": "scraping_module",
}

seleccion = st.sidebar.selectbox("Módulo", tuple(MODULOS.keys()))

# ── Lazy-import ────────────────────────────────────────────────────────────
mod_name = MODULOS[seleccion]
mod = importlib.import_module(mod_name)
mod.render()
