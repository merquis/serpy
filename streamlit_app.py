#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serpy – entry-point
Carga cada módulo SOLO cuando el usuario lo selecciona.
"""

import streamlit as st
import importlib

st.set_page_config(page_title="Serpy – Suite WordPress", layout="wide")

MODULOS = {
    "Relaciones CPT": "relaciones_cpt_module",
    "Scraping":       "scraping_module",
}

opcion = st.sidebar.selectbox("Módulo", MODULOS.keys())

mod = importlib.import_module(MODULOS[opcion])   # ← se importa aquí, ya dentro de Streamlit
mod.render()
