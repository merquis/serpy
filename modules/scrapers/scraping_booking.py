def obtener_datos_booking(urls):
    token = st.secrets["brightdata"]["token"]
    api_url = "https://api.brightdata.com/request"
    resultados_json = []

    for url in urls:
        payload = {
            "zone": "serppy",
            "url": url,
            "format": "raw"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            st.write(f"📡 Scrapeando URL: {url}")
            response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=30)

            if not response.ok:
                st.error(f"❌ Error {response.status_code} para URL {url}: {response.text}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Debug print: título de la página
            if soup.title:
                st.write(f"📄 Título de la página: {soup.title.string}")

            nombre_hotel = soup.find("h2", class_="d2fee87262 pp-header__title")
            if nombre_hotel:
                st.write(f"🏨 Nombre encontrado: {nombre_hotel.text.strip()}")
            else:
                st.warning(f"⚠️ Nombre de hotel NO encontrado en {url}")

            valoracion = soup.find("div", class_="b5cd09854e d10a6220b4")
            direccion = soup.find("span", class_="hp_address_subtitle")
            numero_opiniones = soup.find("div", class_="d8eab2cf7f c90c0a70d3 db63693c62")
            precio = soup.find("div", class_="fcab3ed991 bd73d13072")

            resultados_json.append({
                "url": url,
                "nombre_hotel": nombre_hotel.text.strip() if nombre_hotel else None,
                "valoracion": valoracion.text.strip() if valoracion else None,
                "direccion": direccion.text.strip() if direccion else None,
                "numero_opiniones": numero_opiniones.text.strip() if numero_opiniones else None,
                "precio": precio.text.strip() if precio else None
            })

        except Exception as e:
            st.error(f"❌ Error con la URL '{url}': {e}")

    return resultados_json
