import streamlit as st
import base64, json, requests

# ─── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
SITE   = "https://triptoislands.com"
REL_ID = "12"         # ID de la relación JetEngine (padre-hijo)
CPT_REVIEW = "review" # slug CPT reseñas
CPT_HOTEL  = "hotel"  # slug CPT alojamiento

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
def render_cpt_sidebar():
    site_url = st.sidebar.text_input("🔗 URL de tu sitio WordPress", value=SITE, key="cpt_url")
    post_type = st.sidebar.text_input("📦 Custom Post Type (slug)", value=CPT_REVIEW, key="cpt_post_type")
    per_page = st.sidebar.number_input("📄 Número de ítems a traer", min_value=1, max_value=100, value=10, step=1, key="cpt_per_page")
    return site_url, post_type, per_page

# ─── AUTENTICACIÓN HEADERS ────────────────────────────────────────────────────
def get_headers():
    wp_user = st.secrets.get("wp_user")
    wp_app  = st.secrets.get("wp_app_pass")
    headers = {"Content-Type": "application/json"}
    if wp_user and wp_app:
        token = base64.b64encode(f"{wp_user}:{wp_app}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    return headers

# ─── API CALLS ─────────────────────────────────────────────────────────────────
def wp_get(site, endpoint, params=None):
    url = f"{site}/wp-json/wp/v2/{endpoint}"
    return requests.get(url, headers=get_headers(), params=params, timeout=15).json()

def wp_post(site, endpoint, payload):
    url = f"{site}/wp-json/wp/v2/{endpoint}"
    return requests.post(url, headers=get_headers(), json=payload, timeout=15).json()

def jet_rel(site, parent_id, child_id):
    url = f"{site}/wp-json/jet-rel/{REL_ID}"
    body = {"parent_id": parent_id, "child_id": child_id}
    return requests.post(url, headers=get_headers(), json=body, timeout=15).json()

# ─── INTERFAZ PRINCIPAL ────────────────────────────────────────────────────────
def render_cpt(site, post_type, per_page):
    st.title("🔗 Relaciones CPT - TripToIslands")

    menu = st.radio("Selecciona una acción:", (
        "Ver reseñas de alojamiento",
        "Añadir reseña + vincular",
        "Vincular reseña existente",
    ), horizontal=True)

    # --- Obtener alojamientos y reseñas ---
    hoteles = wp_get(site, CPT_HOTEL, {"per_page": per_page})
    reviews = wp_get(site, CPT_REVIEW, {"per_page": per_page})
    hotel_map  = {h.get("title", {}).get("rendered", f"Hotel #{h['id']}"): h["id"] for h in hoteles}
    review_map = {r.get("title", {}).get("rendered", f"Reseña #{r['id']}"): r["id"] for r in reviews}

    if menu == "Ver reseñas de alojamiento":
        sel = st.selectbox("Selecciona alojamiento", list(hotel_map.keys()), key="ver_hotel")
        if sel:
            hid = hotel_map[sel]
            st.subheader(f"Reseñas de «{sel}»")
            rels = wp_get(site, CPT_REVIEW, {"jet_related_to": hid, "per_page": per_page})
            for r in rels:
                st.write(f"- {r.get('title', {}).get('rendered', '(sin título)')} (ID {r['id']})")

    elif menu == "Añadir reseña + vincular":
        sel = st.selectbox("Alojamiento destino", list(hotel_map.keys()), key="nuevo_hotel")
        title = st.text_input("Título reseña", key="nuevo_titulo")
        content = st.text_area("Contenido", key="nuevo_contenido")
        if st.button("Crear y vincular") and sel and title:
            new = wp_post(site, CPT_REVIEW, {"title": title, "content": content, "status": "publish"})
            if "id" in new:
                res = jet_rel(site, hotel_map[sel], new["id"])
                st.success(f"✅ Reseña creada (ID {new['id']}) y vinculada.")
            else:
                st.error(f"❌ Error al crear reseña: {new}")

    elif menu == "Vincular reseña existente":
        sel_hotel  = st.selectbox("Alojamiento", list(hotel_map.keys()), key="vincular_hotel")
        sel_review = st.selectbox("Reseña existente", list(review_map.keys()), key="vincular_review")
        if st.button("Vincular"):
            out = jet_rel(site, hotel_map[sel_hotel], review_map[sel_review])
            msg = "✅ Vinculación creada" if "success" in json.dumps(out) else f"❌ Error: {out}"
            st.success(msg)
