import random

USER_AGENTS = [
     
    #"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    #"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
    #"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0",
    #"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    #"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 OPR/118.0.0.0",
    #"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    #"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    #"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) obsidian/1.6.5 Chrome/124.0.6367.243 Electron/30.1.2 Safari/537.36",
    #"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    #"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:138.0) Gecko/20100101 Firefox/138.0",
    #"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    
    ]

ACCEPTS = [
    #"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
]

ACCEPT_LANGUAGES = [
   # "es-ES,es;q=0.9,en;q=0.8",
    "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
    #"es,en;q=0.9",
]

GOOGLE_REFERRERS = [
    "https://www.google.com/",
    #"https://www.google.es/",
    #"https://www.google.com/search?q=noticias",
    #"https://www.google.com/search?q=hoteles",
    #"https://www.google.com/search?q=viajes",
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def get_random_accept():
    return random.choice(ACCEPTS)

def get_random_accept_language():
    return random.choice(ACCEPT_LANGUAGES)

def get_random_referer():
    return random.choice(GOOGLE_REFERRERS)

def get_random_cookie():
    from datetime import datetime
    import time
    
    # Generar fecha actual para la cookie 1P_JAR
    current_date = datetime.now().strftime("%Y-%m-%d-%H")
    
    # Generar valores realistas para Google Analytics
    timestamp = int(time.time())
    client_id = random.randint(1000000000, 9999999999)
    
    dynamic_cookies = [
        #"CONSENT=YES+1; NID=511=abc123; SOCS=CAI",
        #f"CONSENT=YES+1; _ga=GA1.2.{client_id}.{timestamp}; _gid=GA1.2.{random.randint(1000000000, 9999999999)}.{timestamp}",
        #f"CONSENT=YES+1; 1P_JAR={current_date}; DV=abcde",
        "CONSENT=YES+1; 1P_JAR=2025-05-27-22; DV=abcde",
    ]
    
    return random.choice(dynamic_cookies)

def get_realistic_headers():
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": get_random_accept(),
        "Accept-Language": get_random_accept_language(),
        "Referer": get_random_referer(),
        "Cookie": get_random_cookie(),
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
    }
    return headers
