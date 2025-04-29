#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Serpy – Punto de entrada principal.
Carga dinámica de módulos según selección del usuario.
"""

import streamlit as st
import importlib

# ───────────────────── Configuración General ─────────────────────
st.set_page_config(
    page_title="Serpy – Suite WordPress",
    layout="wide",
)

# ───────────────────── Módulos Disponibles ───────────────────────
MODULOS = {
    "Relaciones CPT": "

