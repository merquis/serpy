#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Serpy – JetEngine Helper
========================

Herramientas incluidas
----------------------
1. **Relaciones CPT**
   • Ver reseñas vinculadas a un alojamiento (parent_id).
   • Añadir / Desvincular reseñas (child_id) al alojamiento.

2. **Serializador JetEngine**
   • Introducir IDs (separados por coma, espacio o punto).
   • Devolver la cadena serializada estilo PHP (`a:N:{i:0;s:...;...}`).
"""

import base64
import re
from typing import List, Dict

import pandas as pd
import requests
import streamlit as st

# ───────── CONFIGURACIÓN ───────── #
REL_ID = 12                                           # ID de tu relación JetEngine
JET_BASE = f"https://triptoislands.com/wp-json/jet-rel/{REL_ID}"
HEADERS: Dict[str, str] = {"Content-Type": "application/json"}

user = st.secrets.get("wp_user", "")
app  = st.secrets.get("wp_app_pass", "")
if user and app:
    token = base64.b64encode(f"{user}:{app}".encode()).decode()
    HEADERS["Authorization"] = f"Basic {token}"

# ───────── FUNCIONES RELACIONES ───────── #
def api_get_children(parent_id: int):
    url = f"{JET_BASE}/children/{parent_id}"
    return requests.get(url, headers=HEADERS, timeout=10).json()

def api_add_child(parent_id: int, child_id: int) -> bool:
    body = {"parent_id": parent_id, "child_id": child_id,
            "context": "child", "store_items_type": "update"}
    r = requests.post(JET_BASE, headers=HEADERS, json=body, timeout=10)
    return r.ok

def api_remove_child(parent_id: int, child_id: int) -> bool:
    body = {"parent_id": parent_id, "child_id": child_id,
            "context": "child", "store_items_type": "replace"}
    r = requests.post(JET_BASE, headers=HEADERS, json=body, timeout=10)
    return r.ok

# ───────── FUNCIONES SERIALIZACIÓN ───────── #
SEP = re.compile(r"[,\s\.]+")

def php_serialize(ids: List[str]) -> str:
    """Devuelve string estilo PHP serialize para JetEngine."""
    return "a:{}:{{{}}}".format(
        len(ids),
        "".join(f"i:{i};s:{len(v)}:\"{v}\";" for i, v in enumerate(ids))
    )

# ───────── STREAMLIT UI ───────── #
st.set_page_config(page_title="Serpy – JetEngine Helper", layout="wide")
menu = st.sidebar.selectbox("Módulo", ("Relaciones CPT", "Serializador"))

# — 1) RELACIONES CPT —
if menu == "Relaciones CPT":
    st.title("🛠️ Relaciones CPT")

    accion = st.sidebar.radio(
        "Elige acción",
        ("Ver reseñas", "Añadir reseña", "Desvincular reseña")
    )

    if accion == "Ver reseñas":
        pid = st.number_input("ID alojamiento (parent_id)", min_value=1, step=1)
        if st.button("Mostrar") and pid:
            data = api_get_children(pid)
            if not data:
                st.info("Sin reseñas vinculadas.")
            else:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)

    elif accion == "Añadir reseña":
        pid = st.number_input("ID alojamiento", min_value=1, step=1)
        cid = st.number_input("ID reseña a añadir", min_value=1, step=1)
        if st.button("Vincular") and pid and cid:
            ok = api_add_child(pid, cid)
            st.success("¡Vinculada!") if ok else st.error("Error API")

    else:  # Desvincular
        pid = st.number_input("ID alojamiento", min_value=1, step=1, key="r_pid")
        cid = st.number_input("ID reseña a quitar", min_value=1, step=1, key="r_cid")
        if st.button("Desvincular") and pid and cid:
            ok = api_remove_child(pid, cid)
            st.success("¡Desvinculada!") if ok else st.error("Error API")

# — 2) SERIALIZADOR —
elif menu == "Serializador":
    st.title("🛠️ Serializador JetEngine")
    raw = st.text_input("IDs (coma / espacio / punto)")
    if st.button("Serializar") and raw.strip():
        ids = [x for x in SEP.split(raw) if x.isdigit()]
        if ids:
            result = php_serialize(ids)
            st.code(result, language="text")
        else:
            st.warning("No se detectaron IDs válidos.")
