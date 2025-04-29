"""relaciones_cpt_module.py
Gestión de relaciones JetEngine (reseñas ↔ alojamientos) y utilidades de serializado.
La lectura de secretos es perezosa: si no existen, el módulo funciona en modo solo lectura.
"""
from __future__ import annotations
import base64
import os
import re
from typing import Dict, List

import streamlit as st
import pandas as pd
import requests

# ─────────────────────────── CONFIG GENERAL ───────────────────────────────
REL_ID = 12
JET    = f"https://triptoislands.com/wp-json/jet-rel/{REL_ID}"
SEP    = re.compile(r"[,\s\.]+")  # separador para IDs libres

# ──────────────────────── CABECERAS CON AUTENTICACIÓN ─────────────────────
def _build_headers() -> Dict[str, str]:
    """Devuelve cabeceras con Authorization si hay credenciales."""
    user = st.secrets.get("wp_user", os.getenv("WP_USER", ""))
    app  = st.secrets.get("wp_app_pass", os.getenv("WP_APP_PASS", ""))
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if user and app:
        token = base64.b64encode(f"{user}:{app}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    return headers

# ──────────────────────────── HELPERS REST API ────────────────────────────
def api_get_children(pid: int):
    return requests.get(
        f"{JET}/children/{pid}",
        headers=_build_headers(),
        timeout=10,
    ).json()

def api_change_child(pid: int, cid: int, store: str) -> bool:
    body = {
        "parent_id": pid,
        "child_id":  cid,
        "context":   "child",
        "store_items_type": store,  # "update" | "replace"
    }
    return requests.post(JET, headers=_build_headers(), json=body, timeout=10).ok

# ──────────────────────────── SERIALIZACIÓN PHP ───────────────────────────
def php_serialize(ids: List[str]) -> str:
    """Convierte ['12','34'] → a:2:{i:0;s:2:"12";i:1;s:2:"34";}"""
    return "a:{}:{{{}}}".format(
        len(ids),
        "".join(f'i:{i};s:{len(v)}:"{v}";' for i, v in enumerate(ids)),
    )

# ───────────────────────────────── UI ──────────────────────────────────────
def render() -> None:
    st.title("🛠️ Relaciones CPT")

    headers = _build_headers()
    if "Authorization" not in headers:
        st.info("Modo **solo lectura** – añade `wp_user` y `wp_app_pass` a tus secrets "
                "para habilitar operaciones de escritura.")

    accion = st.sidebar.radio(
        "Acción",
        ("Ver reseñas", "Añadir reseña", "Quitar reseña", "Serializar IDs"),
    )

    # ------- Ver reseñas vinculadas -------
    if accion == "Ver reseñas":
        pid = st.number_input("ID alojamiento", min_value=1, step=1)
        if st.button("Mostrar") and pid:
            data = api_get_children(pid)
            st.dataframe(
                pd.DataFrame(data) if data else pd.DataFrame(),
                use_container_width=True,
            )

    # ------- Añadir / Quitar -------
    elif accion in ("Añadir reseña", "Quitar reseña"):
        if "Authorization" not in headers:
            st.error("Necesitas credenciales (wp_user / wp_app_pass) para esta acción.")
            return

        pid = st.number_input("ID alojamiento", 1, step=1, key="pid")
        cid = st.number_input("ID reseña",      1, step=1, key="cid")
        if st.button("Ejecutar") and pid and cid:
            ok = api_change_child(
                pid, cid,
                "update" if accion == "Añadir reseña" else "replace",
            )
            st.success("✅ Operación completada") if ok else st.error("❌ Falló la API")

    # ------- Serializar IDs -------
    else:  # Serializar IDs
        raw_ids = st.text_input("IDs separados por coma / espacio / punto")
        if st.button("Serializar") and raw_ids.strip():
            ids = [x for x in SEP.split(raw_ids) if x.isdigit()]
            st.code(php_serialize(ids) if ids else "⚠️ No se encontraron IDs numéricos.")
