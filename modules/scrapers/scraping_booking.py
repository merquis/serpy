# modules/scrapers/scraping_booking.py

import requests
from bs4 import BeautifulSoup
import time

# Ejemplo mínimo: obtener el nombre del hotel desde Bright Data dado un input tipo búsqueda

def obtener_nombre_hoteles():
    url = "https://api.brightdata.com/datasets/v3/trigger"
    headers = {
        "Authorization": "Bearer 69211469c36607f6bafed9292a36f0b630f22d017a12702c3662574655d999e7",
        "Content-Type": "application/json"
    }
    params = {
        "dataset_id": "gd_m4bf7a917zfezv9d5",
        "include_errors": "true"
    }
    data = [
        {
            "url": "https://www.booking.com",
            "location": "Paris",
            "check_in": "2025-04-30T00:00:00.000Z",
            "check_out": "2025-05-07T00:00:00.000Z",
            "adults": 2,
            "rooms": 1,
            "country": "FR",
            "currency": ""
        }
    ]

    response = requests.post(url, headers=headers, params=params, json=data)
    job = response.json()

    if "job_id" not in job:
        print("Error lanzando scraping:", job)
        return

    print("Job lanzado con ID:", job["job_id"])
    time.sleep(5)

    # Obtener resultados
    result_url = f"https://api.brightdata.com/datasets/v3/data?dataset_id={params['dataset_id']}&limit=1"
    result_resp = requests.get(result_url, headers=headers)
    results = result_resp.json()

    if results and isinstance(results, list):
        html = results[0].get("_html", "")
        soup = BeautifulSoup(html, "html.parser")
        titulo = soup.find("h2")
        if titulo:
            print("🏨 Nombre del hotel:", titulo.get_text(strip=True))
        else:
            print("No se encontró el nombre del hotel.")
    else:
        print("No se devolvieron resultados aún.")


if __name__ == "__main__":
    obtener_nombre_hoteles()
