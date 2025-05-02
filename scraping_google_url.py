import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json, ssl
from drive_utils import subir_json_a_drive

def obtener_urls_google(query, num_results):
    proxy = 'http://brd...superproxy.io:33335'
    step = 10
    resultados = []
    ssl_context = ssl._create_unverified_context()
    for term in [q.strip() for q in query.split(',') if q.strip()]:
        urls=[]
        for start in range(0, num_results, step):
            try:
                url=f'https://www.google.com/search?q={urllib.parse.quote(term)}&start={start}'
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':proxy,'https':proxy}), urllib.request.HTTPSHandler(context=ssl_context))
                html=opener.open(url, timeout=90).read().decode('utf-8',errors='ignore')
                soup=BeautifulSoup(html,'html.parser')
                for a in soup.select('a:has(h3)'):
                    href=a.get('href')
                    if href and href.startswith('http') and len(urls)<num_results:
                        urls.append(href)
            except Exception as e:
                st.error(f"Error {e}")
                break
        resultados.append({'busqueda':term,'urls':urls})
    return resultados

def render_scraping_google_urls():
    st.title("🔍 Scraping desde Google")
    q=st.text_input("Términos (coma sep)")
    n=st.selectbox("# resultados", list(range(10,101,10)))
    if st.button("🔎 Buscar") and q:
        res=obtener_urls_google(q,int(n))
        bname='-'.join([t.strip() for t in q.split(',')])+'.json'
        jb=json.dumps(res,ensure_ascii=False,indent=2).encode('utf-8')
        st.json(res)
        st.download_button("⬇️ Exportar JSON", data=jb, file_name=bname, mime="application/json")
        if st.button("📤 Subir Drive"):
            link=subir_json_a_drive(bname,jb,st.session_state.proyecto_id)
            st.success(f"Ver: {link}")
