#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serpy – entry-point con carga perezosa de módulos."""
import streamlit as st
import importlib

st.set_page_config(page_title="Serpy – Suite WordPress", layout="wide")

MODULOS = {
    "Relaciones CPT": "relaciones_cpt_module",
    "Scraping":       "scraping_module",
}

opcion = st.sidebar.selectbox("Módulo", MODULOS.keys())
mod     = importlib.import_module(MODULOS[opcion])   # ↓ se importa aquí, una vez el usuario decide
mod.render()
