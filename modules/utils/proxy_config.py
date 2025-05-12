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
            proxy_conf = st.secrets["brightdata_proxy"]
            return {
                "host": proxy_conf["host"],
                "port": proxy_conf["port"],
                "username": proxy_conf["username"],
                "password": proxy_conf["password"]
            }
        except KeyError as e:
            st.warning(f"⚠️ Falta la configuración del proxy en st.secrets: {e}")
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
            # Configurar headers por defecto para parecer más un navegador real
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
    def get_urllib_opener() -> urllib.request.OpenerDirector:
        """Crea y retorna un opener de urllib configurado con el proxy."""
        proxy_url = ProxyConfig.get_proxy_url()
        if not proxy_url:
            return urllib.request.build_opener()

        proxy_handler = urllib.request.ProxyHandler({
            'http': proxy_url,
            'https': proxy_url
        })
        https_handler = urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
        return urllib.request.build_opener(proxy_handler, https_handler)

    @staticmethod
    def get_playwright_proxy() -> Optional[Dict[str, Union[str, Dict[str, str]]]]:
        """Retorna la configuración del proxy para Playwright.
        
        Returns:
            Dict con la configuración del proxy en formato compatible con Playwright:
            {
                "server": "http://host:port",
                "username": "user",
                "password": "pass",
                "bypass": "*.brdtest.com" # Opcional: dominios que no usan proxy
            }
        """
        settings = ProxyConfig.get_proxy_settings()
        if not all(settings.values()):
            return None
        
        return {
            "server": f"http://{settings['host']}:{settings['port']}",
            "username": settings['username'],
            "password": settings['password'],
            "bypass": "*.brdtest.com" # Bypass para dominios de prueba de BrightData
        }

    @staticmethod
    def get_playwright_browser_config() -> Dict[str, Union[bool, Dict]]:
        """Retorna la configuración completa para el navegador de Playwright.
        
        Returns:
            Dict con la configuración completa del navegador incluyendo proxy y otras opciones.
        """
        return {
            "headless": True,
            "proxy": ProxyConfig.get_playwright_proxy(),
            "args": [
                "--disable-dev-shm-usage",  # Útil en contenedores
                "--no-sandbox",  # Necesario en algunos entornos
                "--disable-setuid-sandbox",
                "--disable-gpu",  # Mejora la estabilidad
                "--disable-web-security",  # Si necesitas ignorar CORS
                "--disable-features=IsolateOrigins,site-per-process"  # Mejora la compatibilidad
            ]
        } 