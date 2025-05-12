import urllib.request
import ssl
import streamlit as st
from typing import Optional, Dict, Union
import requests
from requests.auth import HTTPProxyAuth

class ProxyConfig:
    @staticmethod
    def get_proxy_settings() -> Dict[str, str]:
        """Obtiene la configuración del proxy desde los secretos de Streamlit."""
        try:
            proxy_conf = st.secrets["brightdata_booking"]  # Cambiado a brightdata_booking
            return {
                "host": proxy_conf["host"],
                "port": str(proxy_conf["port"]),  # Convertir a string por si viene como número
                "username": proxy_conf["username"],
                "password": proxy_conf["password"]
            }
        except KeyError as e:
            st.warning(f"⚠️ Falta la configuración del proxy en st.secrets.brightdata_booking: {e}")
            return {}

    @staticmethod
    def get_proxy_url() -> Optional[str]:
        """Construye y retorna la URL completa del proxy."""
        settings = ProxyConfig.get_proxy_settings()
        if not all(settings.values()):
            return None
        return f"http://{settings['username']}:{settings['password']}@{settings['host']}:{settings['port']}"

    @staticmethod
    def get_requests_session() -> requests.Session:
        """Crea y retorna una sesión de requests configurada con el proxy."""
        session = requests.Session()
        proxy_url = ProxyConfig.get_proxy_url()
        if proxy_url:
            session.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            settings = ProxyConfig.get_proxy_settings()
            session.auth = HTTPProxyAuth(settings['username'], settings['password'])
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
        return session

    @staticmethod
    def get_playwright_proxy() -> Optional[Dict[str, Union[str, Dict[str, str]]]]:
        """Retorna la configuración del proxy para Playwright."""
        settings = ProxyConfig.get_proxy_settings()
        if not all(settings.values()):
            st.error("❌ No se pudo obtener la configuración del proxy. Verifica tus secrets.toml")
            return None
        
        # Configuración específica para Playwright con BrightData
        return {
            "server": f"http://{settings['host']}:{settings['port']}",
            "username": settings['username'],
            "password": settings['password']
        }

    @staticmethod
    def get_playwright_browser_config() -> Dict[str, Union[bool, Dict]]:
        """Retorna la configuración completa para el navegador de Playwright."""
        proxy_config = ProxyConfig.get_playwright_proxy()
        if not proxy_config:
            st.error("❌ No se pudo configurar el proxy para Playwright")
            return {"headless": True}  # Configuración mínima sin proxy
        
        return {
            "headless": True,
            "proxy": proxy_config,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                f"--proxy-server=http://{proxy_config['server'].split('http://')[-1]}"  # Asegurar que se use el proxy
            ]
        } 