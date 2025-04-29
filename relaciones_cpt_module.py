"""relaciones_cpt_module.py
Herramientas JetEngine (reseñas ↔ alojamientos) y serializador.
Tolera la ausencia de secretos para trabajar en modo solo lectura.
"""
from __future__ import annotations
import base64
import re
from typing import Dict, List

import streamlit as st
import pandas as pd
import requests
import os

# ───────── CONFIG API ───────── #
REL_ID = 12
JET_BASE = f"https://triptoislands.com/wp-json/jet-rel/{REL_ID}"

def _build_headers() -> Dict[str, str]:
    """Construye cabeceras; si no hay credenciales, devuelve solo Content-Type."""
    headers: Dict[str, str] = {"Content-Type": "application/json"}

    # Intentar vía st.secrets
    try:
        user = st.secrets["wp_user"]
        app  = st.secrets["wp_app_pass"]
    except (Exception,):  # no secrets en local
        user = os.getenv("WP_USER", "")
        app  = os.getenv("WP_APP_PASS", "")

    if user and app:
        token = base64.b64encode(f"{user}:{app}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    return headers

HEADERS = _build_headers()

# ───────── API helpers ───────── #
def api_get_children(pid: int):
    return requests.get(f"{JET_BASE}/children/{pid}", headers=HEADERS, timeout=10).json()

def api_add_child(pid: int, cid: int):
    body = {"parent_id": pid, "child_id": cid,
            "context": "child", "store_items_type": "update"}
    return requests.post(JET_BASE, headers=HEADERS, json=body, timeout=10).ok

def api_remove_child(pid: int, cid: int):
    body = {"parent_id": pid, "child_id": cid,
            "context": "child", "store_items_type": "replace"}
    return requests.post(JET_BASE, headers=HEADERS, json=body, timeout=10).ok

# ───────── Serialización ───────── #
SEP = re.compile(r"[,\s\.]+")

def php_serialize(ids: List[str]) -> str:
    return "a:{}:{{{}}}".format(len(ids),
        "".join(f"i:{i};s:{len(v)}:\"{v}\";" for i, v in enumerate(ids)))

# ──────────── UI ──────────────── #
def render() -> None:
    st.title("🛠️ Relaciones CPT")

    if "Authorization" not in HEADERS:
        st.warning("🔒 Sin credenciales: solo lectura / serialización disponible.")

    sub = st.sidebar.radio("Acción",
        ("Ver reseñas", "Añadir reseña", "Desvincular reseña", "Serializar IDs"))

    if sub == "Ver reseñas":
        pid = st.number_input("ID alojamiento", min_value=1, step=1)
        if st.button("Mostrar") and pid:
            data = api_get_children(pid)
            st.dataframe(pd.DataFrame(data) if data else pd.DataFrame(),
                         use_container_width=True)

    elif sub == "Añadir reseña":
        if "Authorization" not in HEADERS:
            st.error("Necesitas credenciales (wp_user / wp_app_pass) para esta acción.")
            return
        pid = st.number_input("ID alojamiento", min_value=1, step=1, key="add_pid")
        cid = st.number_input("ID reseña",   min_value=1, step=1, key="add_cid")
        if st.button("Vincular") and pid and cid:
            st.success("¡Ok!") if api_add_child(pid, cid) else st.error("Falló API")

    elif sub == "Desvincular reseña":
        if "Authorization" not in HEADERS:
            st.error("Necesitas credenciales (wp_user / wp_app_pass) para esta acción.")
            return
        pid = st.number_input("ID alojamiento", min_value=1, step=1, key="rem_pid")
        cid = st.number_input("ID reseña",   min_value=1, step=1, key="rem_cid")
        if st.button("Quitar") and pid and cid:
            st.success("¡Desvinculada!") if api_remove_child(pid, cid) else st.error("Falló API")

    else:  # Serializar
        raw = st.text_input("IDs (separados por coma / espacio / punto)")
        if st.button("Serializar") and raw.strip():
            ids = [x for x in SEP.split(raw) if x.isdigit()]
            st.code(php_serialize(ids) if ids else "⚠️ No IDs válidos")
