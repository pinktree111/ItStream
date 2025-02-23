import json
import os
import re
import urllib.parse
import requests

from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# URL della sorgente dei canali
CHANNELS_URL = 'https://vavoo.to/channels'

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carica il dizionario dei loghi (il file "dizionario.json" deve trovarsi nella stessa cartella)
dizionario_path = os.path.join(os.path.dirname(__file__), "dizionario.json")
with open(dizionario_path, "r", encoding="utf-8") as f:
    CHANNEL_LOGOS = json.load(f)

# Lista delle categorie e relative parole chiave per la categorizzazione
CATEGORY_KEYWORDS = {
    "SKY": ["sky cin", "tv 8", "fox", "comedy central", "animal planet", "nat geo", "tv8", "sky atl", "sky uno", "sky prima", "sky serie", "sky arte", "sky docum", "sky natu", "cielo", "history", "sky tg"],
    "RAI": ["rai"],
    "MEDIASET": ["mediaset", "canale 5", "rete 4", "italia", "focus", "tg com 24", "tgcom 24", "premium crime", "iris", "mediaset iris", "cine 34", "27 twenty seven", "27 twentyseven"],
    "DISCOVERY": ["discovery", "real time", "investigation", "top crime", "wwe", "hgtv", "nove", "dmax", "food network", "warner tv"],
    "SPORT": ["sport", "dazn", "tennis", "moto", "f1", "golf", "sportitalia", "sport italia", "solo calcio", "solocalcio"],
    "BAMBINI": ["boing", "cartoon", "k2", "discovery k2", "nick", "super", "frisbee"],
    "ALTRI": []
}

def categorize_channel(channel_name: str) -> list:
    cleaned = re.sub(r'\(.*?\)', '', channel_name).strip().lower()
    genres = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in cleaned:
                genres.append(category)
                break
    if not genres:
        genres.append("ALTRI")
    return genres

def generate_poster_url(channel_name: str) -> str:
    cleaned = re.sub(r'\(.*?\)', '', channel_name).strip().lower()
    return CHANNEL_LOGOS.get(cleaned, "")

def get_italian_channels(proxy_url: str, password: str):
    """
    Recupera i canali italiani dalla sorgente e genera l'URL dello stream
    utilizzando il proxy e la password forniti.
    """
    try:
        response = requests.get(CHANNELS_URL)
        response.raise_for_status()
    except Exception:
        return []
    
    data = response.json()
    channels = []
    for entry in data:
        if entry.get('country') == 'Italy':
            # Codifica l'URL dello stream originale
            encoded_stream = urllib.parse.quote(f"https://vavoo.to/play/{entry['id']}/index.m3u8", safe='')
            base_proxy = proxy_url.rstrip('/')
            stream_url = (
                f"{base_proxy}/proxy/hls/manifest.m3u8?"
                f"api_password={password}&d={encoded_stream}"
                f"&h_user-agent={urllib.parse.quote('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36')}"
                f"&h_referer={urllib.parse.quote('https://newembedplay.xyz/')}"
                f"&h_origin={urllib.parse.quote('https://newembedplay.xyz')}"
            )
            poster = generate_poster_url(entry['name'])
            channels.append({
                "id": f"tv:{entry['id']}",
                "name": entry['name'],
                "url": stream_url,
                "poster": poster,
                "genres": categorize_channel(entry['name'])
            })
    return channels

# Creiamo un router per gli endpoint dell'addon.
router = APIRouter()

@router.get("/manifest.json")
async def manifest(encoded_proxy_url: str, encoded_password: str):
    # Decodifica i parametri: encoded_proxy_url viene passato come tipo "path", quindi potrebbe contenere "/"
    proxy_url = urllib.parse.unquote(encoded_proxy_url)
    password = urllib.parse.unquote(encoded_password)
    manifest = {
        "id": "org.stremio.italian.channels",
        "version": "1.0.0",
        "name": "Italian Channels",
        "description": "Catalogo IPTV Italiano per Stremio",
        "types": ["tv"],
        "catalogs": [
            {
                "id": "italian_channels",
                "name": "Italian IPTV",
                "type": "tv",
                "extra": [
                    {"name": "search", "isRequired": False},
                    {"name": "genre", "isRequired": False}
                ]
            }
        ],
        "resources": ["catalog", "stream", "meta"],
        "idPrefixes": ["tv:"],
        "logo": "https://i.imgur.com/3Tv3KQ1.png"
    }
    return manifest

@router.get("/catalog/tv/italian_channels.json")
async def catalog(encoded_proxy_url: str, encoded_password: str, genre: str = ""):
    proxy_url = urllib.parse.unquote(encoded_proxy_url)
    password = urllib.parse.unquote(encoded_password)
    channels = get_italian_channels(proxy_url, password)
    metas = [{
        "id": ch["id"],
        "name": ch["name"],
        "type": "tv",
        "poster": ch["poster"],
        "genres": ch["genres"]
    } for ch in channels]
    if genre:
        genre = genre.lower()
        metas = [m for m in metas if any(genre in g.lower() for g in m.get("genres", []))]
    return {"metas": metas}

@router.get("/catalog/tv/italian_channels/search={query}.json")
async def search_catalog(query: str, encoded_proxy_url: str, encoded_password: str):
    proxy_url = urllib.parse.unquote(encoded_proxy_url)
    password = urllib.parse.unquote(encoded_password)
    channels = get_italian_channels(proxy_url, password)
    results = [{
        "id": ch["id"],
        "name": ch["name"],
        "type": "tv",
        "poster": ch["poster"],
        "genres": ch["genres"]
    } for ch in channels if query.lower() in ch["name"].lower()]
    return {"metas": results}

@router.get("/stream/tv/{channel_id}.json")
async def stream(channel_id: str, encoded_proxy_url: str, encoded_password: str):
    proxy_url = urllib.parse.unquote(encoded_proxy_url)
    password = urllib.parse.unquote(encoded_password)
    channels = get_italian_channels(proxy_url, password)
    for ch in channels:
        if ch["id"] == channel_id:
            return {"streams": [{"url": ch["url"], "title": ch["name"]}]}
    return {"streams": []}

@router.get("/meta/tv/{channel_id}.json")
async def meta(channel_id: str, encoded_proxy_url: str, encoded_password: str):
    proxy_url = urllib.parse.unquote(encoded_proxy_url)
    password = urllib.parse.unquote(encoded_password)
    channels = get_italian_channels(proxy_url, password)
    for ch in channels:
        if ch["id"] == channel_id:
            return {
                "meta": {
                    "id": ch["id"],
                    "name": ch["name"],
                    "type": "tv",
                    "poster": ch["poster"],
                    "background": "https://raw.githubusercontent.com/pinktree111/ittv/refs/heads/main/bg.jpg",
                    "logo": ch["poster"],
                    "description": f"Guarda {ch['name']} in streaming su Stremio.",
                    "genres": ch["genres"],
                    "streams": [{"url": ch["url"]}]
                }
            }
    return {"error": "Canale non trovato", "meta": None}

# Includiamo il router usando un prefisso con parametri nel path.
# Il parametro "encoded_proxy_url" è definito come "path" per consentire "/" all'interno del valore.
app.include_router(router, prefix="/mfp/{encoded_proxy_url:path}/PSW/{encoded_password}")

# Pagina HTML minimal per configurare proxy e password
@app.get("/", response_class=HTMLResponse)
async def home():
    html = """
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <title>Configura MediaFlow Proxy</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2em; }
    input { width: 100%; padding: 8px; margin-top: 8px; }
    button { padding: 10px; margin-top: 12px; }
  </style>
</head>
<body>
  <h1>Configura MediaFlow Proxy</h1>
  <form id="configForm">
    <input type="text" id="mediaflowUrl" placeholder="Inserisci URL completo (https://...)" required>
    <input type="text" id="mediaflowPassword" placeholder="Inserisci la password" required>
    <button type="submit">Genera Link Manifest</button>
  </form>
  <input type="text" id="manifestLink" readonly style="margin-top:20px;">
  <script>
    document.getElementById('configForm').addEventListener('submit', function(e) {
      e.preventDefault();
      var url = document.getElementById('mediaflowUrl').value.trim();
      var password = document.getElementById('mediaflowPassword').value.trim();
      var base = window.location.origin;
      // Genera il link nel formato richiesto, usando encodeURIComponent per entrambi i parametri.
      var link = base + '/mfp/' + encodeURIComponent(url) + '/PSW/' + encodeURIComponent(password) + '/manifest.json';
      document.getElementById('manifestLink').value = link;
    });
  </script>
</body>
</html>
    """
    return HTMLResponse(content=html)
