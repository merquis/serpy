import re
import ssl
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup
import streamlit as st

def testear_proxy_google(query):
    ssl._create_default_https_context = ssl._create_unverified_context

    proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
    encoded_query = urllib.parse.quote(query)
    search_url = f'https://www.google.com/search?q={encoded_query}'

    st.write(f"🔗 URL que se va a consultar: [{search_url}]({search_url})")

    try:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({
                'http': proxy_url,
                'https': proxy_url
            })
        )
        response = opener.open(search_url, timeout=30)
        html = response.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, "html.parser")

        enlaces_posts = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith("/url?q=https"):
                # Limpiar el enlace real
                url_limpia = re.split(r'&', href.replace("/url?q=", ""))[0]
                # Omitir enlaces de Google o que claramente no son resultados
                if not "google.com" in url_limpia:
                    enlaces_posts.append(url_limpia)

        if enlaces_posts:
            st.success(f"🔗 Se extrajeron {len(enlaces_posts)} URLs de resultados reales.")
            for i, url in enumerate(enlaces_posts, 1):
                st.markdown(f"**{i}.** [{url}]({url})")
        else:
            st.warning("⚠️ No se encontraron enlaces de resultados reales.")

        # Expansor opcional para depuración
        with st.expander("📄 Ver HTML parcial"):
            st.code(html[:2000], language='html')

    except Exception as e:
        st.error(f"❌ Error al conectar vía proxy BrightData: {str(e)}")
