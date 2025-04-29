"""relaciones_cpt_module.py – JetEngine helper (reseñas ↔ alojamientos)."""
from __future__ import annotations
import base64, os, re
from typing import Dict, List

import streamlit as st
import pandas as pd
import requests

REL_ID = 12
JET    = f"https://triptoislands.com/wp-json/jet-rel/{REL_ID}"
SEP    = re.compile(r"[,\s\.]+")

# ── Helpers de cabecera ───────────────────────────────────────────────────
def _build_headers() -> Dict[str, str]:
    """Devuelve cabeceras con Authorization si hay credenciales."""
    user = st.secrets.get("wp_user", os.getenv("WP_USER", ""))
    app  = st.secrets.get("wp_app_pass", os.getenv("WP_APP_PASS", ""))
    hdr  = {"Content-Type": "application/json"}
    if user and app:
        hdr["Authorization"] = (
            "Basic "
            + base64.b64encode(f"{user}:{app}".encode()).decode()
        )
    return hdr


HEADERS = _headers()
REL_ID  = 12
JET     = f"https://triptoislands.com/wp-json/jet-rel/{REL_ID}"

def api_get_children(pid: int):
    return requests.get(f"{JET}/children/{pid}", headers=HEADERS, timeout=10).json()

def api_change_child(pid: int, cid: int, store: str):
    body = {"parent_id": pid, "child_id": cid,
            "context": "child", "store_items_type": store}
    return requests.post(JET, headers=HEADERS, json=body, timeout=10).ok

SEP = re.compile(r"[,\s\.]+")
php_serialize = lambda ids: "a:{}:{{{}}}".format(
        len(ids), "".join(f'i:{i};s:{len(v)}:"{v}";' for i, v in enumerate(ids)))

def render() -> None:
    st.title("🛠️ Relaciones CPT")
    if "Authorization" not in HEADERS:
        st.info("Modo **solo lectura** – añade `wp_user` y `wp_app_pass` en secrets para habilitar escritura.")

    accion = st.sidebar.radio("Acción", ("Ver reseñas", "Añadir", "Quitar", "Serializar IDs"))

    if accion == "Ver reseñas":
        pid = st.number_input("ID alojamiento", 1, step=1)
        if st.button("Mostrar") and pid:
            df = pd.DataFrame(api_get_children(pid))
            st.dataframe(df, use_container_width=True)

    elif accion in ("Añadir", "Quitar"):
        if "Authorization" not in HEADERS:
            st.error("Necesitas credenciales para esta operación.")
            return
        pid = st.number_input("ID alojamiento", 1, step=1, key="pid")
        cid = st.number_input("ID reseña",      1, step=1, key="cid")
        if st.button("Ejecutar") and pid and cid:
            ok = api_change_child(pid, cid, "update" if accion == "Añadir" else "replace")
            st.success("✅ Éxito") if ok else st.error("❌ Falló la API")

    else:  # Serializar
        ids_raw = st.text_input("IDs separados por coma / espacio / punto")
        if st.button("Serializar") and ids_raw.strip():
            ids = [x for x in SEP.split(ids_raw) if x.isdigit()]
            st.code(php_serialize(ids) if ids else "⚠️ No se encontraron IDs numéricos.")
