"""relaciones_cpt_module.py
Herramientas JetEngine (reseñas ↔ alojamientos) y serializador.
"""
import base64
import re
from typing import Dict, List

import pandas as pd
import requests
import streamlit as st

# ───────── CONFIG ───────── #
REL_ID = 12
JET_BASE = f"https://triptoislands.com/wp-json/jet-rel/{REL_ID}"
HEADERS: Dict[str, str] = {"Content-Type": "application/json"}

user = st.secrets.get("wp_user", "")
app = st.secrets.get("wp_app_pass", "")
if user and app:
    HEADERS["Authorization"] = "Basic " + base64.b64encode(f"{user}:{app}".encode()).decode()

# API helpers
def api_get_children(pid: int):
    return requests.get(f"{JET_BASE}/children/{pid}", headers=HEADERS, timeout=10).json()

def api_add_child(pid: int, cid: int):
    body = {"parent_id": pid, "child_id": cid, "context": "child", "store_items_type": "update"}
    return requests.post(JET_BASE, headers=HEADERS, json=body, timeout=10).ok

def api_remove_child(pid: int, cid: int):
    body = {"parent_id": pid, "child_id": cid, "context": "child", "store_items_type": "replace"}
    return requests.post(JET_BASE, headers=HEADERS, json=body, timeout=10).ok

# Serialización
SEP = re.compile(r"[,\s\.]+")

def php_serialize(ids: List[str]) -> str:
    return "a:{}:{{{}}}".format(len(ids), "".join(f"i:{i};s:{len(v)}:\"{v}\";" for i, v in enumerate(ids)))

# ---------- UI render ---------- #

def render():
    st.title("🛠️ Relaciones CPT")

    sub = st.sidebar.radio("Acción", ("Ver reseñas", "Añadir reseña", "Desvincular reseña", "Serializar IDs"))

    if sub == "Ver reseñas":
        pid = st.number_input("ID alojamiento", min_value=1, step=1)
        if st.button("Mostrar") and pid:
            data = api_get_children(pid)
            st.dataframe(pd.DataFrame(data) if data else pd.DataFrame(), use_container_width=True)

    elif sub == "Añadir reseña":
        pid = st.number_input("ID alojamiento", min_value=1, step=1, key="add_pid")
        cid = st.number_input("ID reseña", min_value=1, step=1, key="add_cid")
        if st.button("Vincular") and pid and cid:
            st.success("¡Ok!") if api_add_child(pid, cid) else st.error("Falló API")

    elif sub == "Desvincular reseña":
        pid = st.number_input("ID alojamiento", min_value=1, step=1, key="rem_pid")
        cid = st.number_input("ID reseña", min_value=1, step=1, key="rem_cid")
        if st.button("Quitar") and pid and cid:
            st.success("¡Desvinculada!") if api_remove_child(pid, cid) else st.error("Falló API")

    else:  # Serializar
        raw = st.text_input("IDs (coma / espacio / punto)")
        if st.button("Serializar") and raw.strip():
            ids = [x for x in SEP.split(raw) if x.isdigit()]
            if ids:
                st.code(php_serialize(ids))
            else:
                st.warning("No IDs válidos")
