"""relaciones_cpt_module.py
Gestión de relaciones JetEngine (reseñas ↔ alojamientos) con conexión manual (sin secrets).
"""

import base64
import json
import re
from typing import Dict, List

import streamlit as st
import pandas as pd
import requests

# ─────────────────── CONFIGURACIÓN ───────────────────
REL_ID = 12
JET_URL = f"https://triptoislands.com/wp-json/jet-rel/{REL_ID}"
SEP = re.compile(r"[,\s\.]+")

# Token WordPress (usuario + app password codificados manualmente)
WP_USER = "TU_USUARIO_WORDPRESS"
WP_APP_PASS = "TU_APP_PASSWORD_WORDPRESS"
TOKEN = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()

def build_headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {TOKEN}",
    }

# ────────── Funciones API ──────────
def api_get_children(pid: int) -> List[dict]:
    try:
        res = requests.get(f"{JET_URL}/children/{pid}", headers=build_headers(), timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"Error obteniendo reseñas: {e}")
        return []

def api_change_child(pid: int, cid: int, action: str) -> bool:
    body = {
        "parent_id": pid,
        "child_id": cid,
        "context": "child",
        "store_items_type": action,  # "update" o "replace"
    }
    try:
        res = requests.post(JET_URL, headers=build_headers(), json=body, timeout=10)
        res.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Error modificando relación: {e}")
        return False

def php_serialize(ids: List[str]) -> str:
    return "a:{}:{{{}}}".format(
        len(ids),
        "".join(f'i:{i};s:{len(v)}:"{v}";' for i, v in enumerate(ids))
    )

# ────────── STREAMLIT UI ──────────
def render() -> None:
    st.title("🔗 Gestión de Relaciones CPT (JetEngine)")

    accion = st.sidebar.radio(
        "Acción",
        ("Ver reseñas vinculadas", "Añadir reseña", "Quitar reseña", "Serializar IDs"),
    )

    if accion == "Ver reseñas vinculadas":
        pid = st.number_input("ID del alojamiento", min_value=1, step=1)
        if st.button("Mostrar reseñas vinculadas") and pid:
            data = api_get_children(pid)
            st.dataframe(pd.DataFrame(data) if data else pd.DataFrame(), use_container_width=True)

    elif accion in ("Añadir reseña", "Quitar reseña"):
        pid = st.number_input("ID del alojamiento", min_value=1, step=1, key="pid")
        cid = st.number_input("ID de la reseña", min_value=1, step=1, key="cid")
        if st.button("Ejecutar acción") and pid and cid:
            success = api_change_child(
                pid, cid,
                "update" if accion == "Añadir reseña" else "replace",
            )
            if success:
                st.success("✅ Relación modificada correctamente.")
            else:
                st.error("❌ Falló la operación.")

    elif accion == "Serializar IDs":
        raw_ids = st.text_input("IDs separados por coma, espacio o punto")
        if st.button("Serializar") and raw_ids.strip():
            ids = [x for x in SEP.split(raw_ids) if x.isdigit()]
            if ids:
                st.code(php_serialize(ids))
            else:
                st.warning("⚠️ No se encontraron IDs válidos.")
