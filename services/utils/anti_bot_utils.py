import random
from datetime import datetime
import time

USER_AGENTS = [
    # Chrome en Windows (más común)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    
    # Chrome en Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    
    # Edge en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
    
    # Firefox en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0",
    
    # Firefox en Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:138.0) Gecko/20100101 Firefox/138.0",
    
    # Chrome en Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    
    # Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 OPR/118.0.0.0",
    
    # Safari en Mac (real Safari user agent)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
]

ACCEPTS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
]

ACCEPT_LANGUAGES = [
    "es-ES,es;q=0.9,en;q=0.8",
    "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "es,en;q=0.9",
    "es-ES,es;q=0.8,en-GB;q=0.5,en;q=0.3",
    "es-ES,es;q=0.9",
]

ACCEPT_ENCODINGS = [
    "gzip, deflate, br",
    "gzip, deflate, br, zstd",
    "gzip, deflate",
]

SEC_CH_UA_PLATFORMS = [
    '"Windows"',
    '"macOS"',
    '"Linux"',
]

REFERRERS = [
    "https://www.google.com/",
    "https://www.google.es/",
    "https://www.google.com/search?q=tripadvisor",
    "https://www.google.com/search?q=hoteles",
    "https://www.google.com/search?q=viajes",
    "https://www.google.es/search?q=vacaciones",
    "https://www.bing.com/",
    "",  # Direct navigation (no referer)
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def get_random_accept():
    return random.choice(ACCEPTS)

def get_random_accept_language():
    return random.choice(ACCEPT_LANGUAGES)

def get_random_accept_encoding():
    return random.choice(ACCEPT_ENCODINGS)

def get_random_referer():
    return random.choice(REFERRERS)

def get_random_sec_ch_ua_platform():
    return random.choice(SEC_CH_UA_PLATFORMS)

def get_random_cookie():
    """Genera cookies dinámicas más realistas"""
    # Generar timestamps actuales
    timestamp = int(time.time())
    client_id = random.randint(1000000000, 9999999999)
    session_id = random.randint(100000000, 999999999)
    
    # Generar fecha actual para cookies
    current_date = datetime.now().strftime("%Y-%m-%d-%H")
    
    # Diferentes combinaciones de cookies
    cookie_templates = [
        f"CONSENT=YES+1; NID=511={session_id}; SOCS=CAI",
        f"CONSENT=YES+1; _ga=GA1.2.{client_id}.{timestamp}; _gid=GA1.2.{random.randint(1000000000, 9999999999)}.{timestamp}",
        f"CONSENT=YES+1; 1P_JAR={current_date}; DV={''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=5))}",
        f"CONSENT=PENDING+{random.randint(100, 999)}; _ga=GA1.2.{client_id}.{timestamp}",
        "",  # Sin cookies (navegación privada)
    ]
    
    return random.choice(cookie_templates)

def get_chrome_version_from_ua(user_agent):
    """Extrae la versión de Chrome del User-Agent"""
    import re
    match = re.search(r'Chrome/(\d+)\.', user_agent)
    if match:
        return match.group(1)
    return "124"  # Default fallback

def get_realistic_headers():
    """Genera un conjunto completo de headers realistas y coherentes"""
    user_agent = get_random_user_agent()
    chrome_version = get_chrome_version_from_ua(user_agent)
    platform = get_random_sec_ch_ua_platform()
    
    # Determinar si es móvil basándose en el UA
    is_mobile = "Mobile" in user_agent or "Android" in user_agent
    
    headers = {
        "User-Agent": user_agent,
        "Accept": get_random_accept(),
        "Accept-Language": get_random_accept_language(),
        "Accept-Encoding": get_random_accept_encoding(),
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": random.choice(["none", "same-origin", "cross-site"]),
        "Sec-Fetch-User": "?1",
        "Cache-Control": random.choice(["max-age=0", "no-cache"]),
    }
    
    # Headers específicos de Chrome/Chromium
    if "Chrome" in user_agent:
        headers.update({
            "Sec-Ch-Ua": f'"Chromium";v="{chrome_version}", "Not-A.Brand";v="99", "Google Chrome";v="{chrome_version}"',
            "Sec-Ch-Ua-Mobile": "?1" if is_mobile else "?0",
            "Sec-Ch-Ua-Platform": platform,
        })
    
    # Añadir referer con probabilidad
    if random.random() > 0.3:  # 70% de probabilidad de tener referer
        referer = get_random_referer()
        if referer:
            headers["Referer"] = referer
    
    # Añadir cookies con probabilidad
    if random.random() > 0.2:  # 80% de probabilidad de tener cookies
        cookie = get_random_cookie()
        if cookie:
            headers["Cookie"] = cookie
    
    # Headers adicionales opcionales
    if random.random() > 0.5:
        headers["DNT"] = "1"
    
    if random.random() > 0.7:
        headers["Pragma"] = "no-cache"
    
    # Viewport para navegadores de escritorio
    if not is_mobile and random.random() > 0.6:
        headers["Viewport-Width"] = str(random.choice([1920, 1366, 1536, 1440, 1280]))
    
    return headers

def get_mobile_headers():
    """Genera headers específicos para dispositivos móviles"""
    mobile_user_agents = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    ]
    
    user_agent = random.choice(mobile_user_agents)
    
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": get_random_accept_language(),
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    return headers

def rotate_headers():
    """Función para rotar headers en cada petición"""
    # 85% desktop, 15% mobile
    if random.random() > 0.15:
        return get_realistic_headers()
    else:
        return get_mobile_headers()
