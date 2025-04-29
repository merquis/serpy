"""relaciones_cpt_module.py
Gestión de relaciones JetEngine (reseñas ↔ alojamientos) y utilidades de serializado.
Lectura segura de credenciales desde st.secrets.
"""

from __future__ import annotations
import base64
import json
import re
from typing import Dict, List

import streamlit as st
import pandas as pd
import requests

# ─────────────────── Configuración ─────────────────────────────
REL_ID   = 12
JET_URL  = f"https://triptoislands.com/wp-json/jet-rel/{REL_ID}"
SEP      = re.compile(r"[,\s\.]+")

# ─────────────────── Helpers de Autenticación ──────────────────
def build_headers() -> Dict[str, str]:
    """Devuelve headers para autenticación Basic Auth."""
    user = st.secrets["wordpress"]["user"]
    app  = st.secrets["wordpress"]["app_password"]
    token = base64.b64encode(f"{user}:{app}".encode()).decode()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {token}"
    }

# ─────────────────── Funciones API ─────────────────────────────
def api_get_children(pid: int) -> List[dict]:
    """Obtiene reseñas relacionadas a un alojamiento."""
    headers = build_headers()
    try:
        res = requests.get(f"{JET_URL}/children/{pid}", headers=headers, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"Error al obtener reseñas: {e}")
        return []

def api_change_child(pid: int, cid: int, action: str) -> bool:
    """Añade o elimina una relación (action: 'update' o 'replace')."""
    headers = build_headers()
    body = {
        "parent_id": pid,
        "child_id":  cid,
        "context":   "child",
        "store_items_type": action,
    }
    try:
        res = requests.post(JET_URL, headers=headers, json=body, timeout=10)
        res.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Error en la operación API: {e}")
        return False

def php_serialize(ids: List[str]) -> str:
    """Serializa IDs al formato PHP: a:{count}:{...}"""
    return "a:{}:{{{}}}".format(
        len(ids),
        "".join(f'i:{i};s:{len(v)}:"{v}";' for i, v in enumerate(ids))
    )

# ─────────────────── Streamlit UI ─────────────────────────────
def render() -> None:
    st.title("🔗 Relaciones CPT (JetEngine)")

    accion = st.sidebar.radio(
        "Acción",
        ("Ver reseñas vinculadas", "Añadir reseña", "Quitar reseña", "Serializar IDs")
    )

    if accion == "Ver reseñas vinculadas":
        pid = st.number_input("ID del alojamiento", min_value=1, step=1)
        if st.button("Mostrar") and pid:
            data = api_get_children(pid)
            st.dataframe(pd.DataFrame(data) if data else pd.DataFrame(), use_container_width=True)

    elif accion in ("Añadir reseña", "Quitar reseña"):
        pid = st.number_input("ID del alojamiento", min_value=1, step=1, key="pid")
        cid = st.number_input("ID de la reseña", min_value=1, step=1, key="cid")
        if st.button("Ejecutar") and pid and cid:
            success = api_change_child(pid, cid, "update" if accion == "Añadir reseña" else "replace")
            if success:
                st.success("✅ Operación completada.")
            else:
                st.error("❌ Falló la operación.")

    elif accion == "Serializar IDs":
        raw_ids = st.text_input("IDs separados por coma / espacio / punto")
        if st.button("Serializar") and raw_ids.strip():
            ids = [x for x in SEP.split(raw_ids) if x.isdigit()]
            if ids:
                st.code(php_serialize(ids))
            else:
                st.warning("No se encontraron IDs válidos.")
