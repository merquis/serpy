import streamlit as st
from utils_scraping import get_scraper
import json

def render_scraping_urls_manuales():
    st.title("🧬 Scraping URLs manuales")
    inp=st.text_area("Pega URLs, coma sep",height=150)
    opts=[('title','title'),('desc','description'),('h1','h1'),('h2','h2'),('h3','h3')]
    etiquetas=[]
    cols=st.columns(len(opts))
    for c,(key,lab) in zip(cols,opts):
        if c.checkbox(lab): etiquetas.append(key)
    if st.button("🔎 Extraer"):
        urls=[u.strip() for u in inp.split(',') if u.strip()]
        scr=get_scraper('generic')
        res=scr(urls,etiquetas)
        st.json(res)
        st.download_button("⬇️ JSON",data=json.dumps(res,ensure_ascii=False,indent=2).encode('utf-8'),file_name='manual.json',mime='application/json')
