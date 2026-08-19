
import re
import json
import sqlite3
import hashlib
import time
import math
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from urllib.parse import quote_plus, urljoin

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
import streamlit as st

try:
    import lbc
except Exception:
    lbc = None

st.set_page_config(page_title="Moto Scanner V4.1", page_icon="🏍️", layout="wide")
st.markdown("""
<style>
.block-container {padding-top:.6rem; padding-bottom:4rem; max-width:1180px;}
#MainMenu {visibility:hidden;} footer {visibility:hidden;}
header[data-testid="stHeader"] {height:0;}
.mobile-card {
    border:1px solid rgba(128,128,128,.25); border-radius:16px;
    padding:12px; margin:0 0 12px 0; box-shadow:0 2px 8px rgba(0,0,0,.04);
}
.mobile-title {font-size:1.15rem; font-weight:750;}
.mobile-price {font-size:1.25rem; font-weight:800; margin:.18rem 0;}
.mobile-meta {font-size:.92rem; opacity:.82; margin:.12rem 0;}
.mobile-tag {
    display:inline-block; padding:.16rem .5rem; margin:.25rem .2rem 0 0;
    border:1px solid rgba(128,128,128,.28); border-radius:999px; font-size:.8rem;
}
@media (max-width:768px) {
  .block-container {padding-left:.6rem; padding-right:.6rem; padding-top:.3rem;}
  h1 {font-size:1.5rem !important;}
  h2 {font-size:1.2rem !important;}
  .stButton button, .stLinkButton a {min-height:44px; border-radius:12px;}
}
</style>
""", unsafe_allow_html=True)


APP_DIR = Path.home() / ".moto_scanner_v3"
APP_DIR.mkdir(exist_ok=True)
DB_FILE = APP_DIR / "moto_scanner.db"
STATE_FILE = APP_DIR / "state.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7",
}

MODEL_CATALOG = [
    "Yamaha MT-07", "Yamaha Tracer 700", "Yamaha XJ6", "Yamaha R7",
    "Honda CB500X", "Honda CB500F", "Honda NC750X",
    "Kawasaki Z650", "Kawasaki Ninja 650", "Kawasaki Versys 650",
    "Kawasaki ER-6n", "Kawasaki ER-6f",
    "Suzuki SV650", "Suzuki V-Strom 650", "Suzuki GSX-8S",
    "BMW F 700 GS", "BMW F 800 R", "BMW F 800 GS",
    "Triumph Trident 660", "Triumph Tiger Sport 660",
    "Royal Enfield Interceptor 650", "Aprilia Tuono 660",
    "Moto Guzzi V7", "Benelli Leoncino 500", "Benelli TRK 502",
]

MODEL_ALIASES = {
    "Yamaha MT-07": [
        "Yamaha MT-07", "Yamaha MT07", "Yamaha MT 07",
        "MT-07", "MT07", "MT 07", "MT-07 A2", "MT07 A2", "MT 07 A2"
    ],
    "Yamaha Tracer 700": [
        "Yamaha Tracer 700", "Tracer 700", "MT-07 Tracer", "MT07 Tracer", "MT 07 Tracer"
    ],
    "Honda CB500X": ["Honda CB500X", "Honda CB 500 X", "CB500X", "CB 500 X"],
    "Honda CB500F": ["Honda CB500F", "Honda CB 500 F", "CB500F", "CB 500 F"],
    "Honda NC750X": ["Honda NC750X", "Honda NC 750 X", "NC750X", "NC 750 X"],
    "Kawasaki Z650": ["Kawasaki Z650", "Kawasaki Z 650", "Z650", "Z 650"],
    "Kawasaki Ninja 650": ["Kawasaki Ninja 650", "Ninja 650"],
    "Kawasaki Versys 650": ["Kawasaki Versys 650", "Versys 650"],
    "Kawasaki ER-6n": ["Kawasaki ER-6n", "ER6N", "ER 6N", "ER-6 N"],
    "Kawasaki ER-6f": ["Kawasaki ER-6f", "ER6F", "ER 6F", "ER-6 F"],
    "Suzuki SV650": ["Suzuki SV650", "Suzuki SV 650", "SV650", "SV 650"],
    "Suzuki V-Strom 650": ["Suzuki V-Strom 650", "V-Strom 650", "V Strom 650"],
    "Suzuki GSX-8S": ["Suzuki GSX-8S", "GSX8S", "GSX 8S", "GSX-8S"],
    "BMW F 700 GS": ["BMW F 700 GS", "BMW F700GS", "F700GS", "F 700 GS"],
    "BMW F 800 R": ["BMW F 800 R", "BMW F800R", "F800R", "F 800 R"],
    "BMW F 800 GS": ["BMW F 800 GS", "BMW F800GS", "F800GS", "F 800 GS"],
    "Triumph Trident 660": ["Triumph Trident 660", "Trident 660"],
    "Triumph Tiger Sport 660": ["Triumph Tiger Sport 660", "Tiger Sport 660"],
    "Royal Enfield Interceptor 650": ["Royal Enfield Interceptor 650", "Interceptor 650"],
    "Aprilia Tuono 660": ["Aprilia Tuono 660", "Tuono 660"],
    "Moto Guzzi V7": ["Moto Guzzi V7", "Guzzi V7", "V7"],
    "Benelli Leoncino 500": ["Benelli Leoncino 500", "Leoncino 500"],
    "Benelli TRK 502": ["Benelli TRK 502", "TRK 502"],
}

DEFAULT_MODELS = {
    "Yamaha MT-07": {},
    "Honda CB500X": {},
    "Kawasaki Z650": {},
    "Suzuki SV650": {},
    "Kawasaki Versys 650": {},
}

OPTION_PATTERNS = {
    "Top case": ["top case", "topcase", "top-case"],
    "Valises": ["valises", "valise", "bagagerie"],
    "Selle confort": ["selle confort", "selle comfort"],
    "Poignées chauffantes": ["poignées chauffantes", "poignees chauffantes"],
    "Crash bars / pare-carter": ["crash bar", "crashbars", "pare-carter", "pare carter"],
    "Protection / anti-scratch": ["anti scratch", "anti-rayure", "anti rayure", "protection réservoir", "protection reservoir"],
    "Support téléphone / GPS": ["quad lock", "support téléphone", "support telephone", "support gps"],
    "Bulle haute": ["bulle haute", "pare-brise", "pare brise", "saute vent"],
    "Ligne / échappement": ["akrapovic", "arrow", "échappement", "echappement", "ligne complète", "ligne complete"],
    "Pneus récents": ["pneus neufs", "pneus récents", "pneus recents"],
    "Kit chaîne récent": ["kit chaîne", "kit chaine"],
    "Prise USB": ["usb", "prise 12v"],
}

# -------------------------------------------------------------------
# Persistence
# -------------------------------------------------------------------
def init_db():
    con = sqlite3.connect(DB_FILE)
    con.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            ad_key TEXT PRIMARY KEY,
            source TEXT,
            model TEXT,
            year INTEGER,
            km INTEGER,
            price REAL,
            location TEXT,
            seller_type TEXT,
            description TEXT,
            options TEXT,
            url TEXT,
            distance_km REAL,
            first_seen TEXT,
            last_seen TEXT,
            last_price REAL,
            min_price REAL,
            max_price REAL,
            scan_count INTEGER DEFAULT 1,
            is_saved INTEGER DEFAULT 0
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_key TEXT,
            observed_at TEXT,
            price REAL
        )
    """)
    con.commit()
    con.close()

init_db()

# Lightweight schema migration for V3.2
_con = sqlite3.connect(DB_FILE)
_existing_cols = {r[1] for r in _con.execute("PRAGMA table_info(ads)").fetchall()}
if "distance_km" not in _existing_cols:
    _con.execute("ALTER TABLE ads ADD COLUMN distance_km REAL")
    _con.commit()
_con.close()

def default_state():
    return {
        "models": DEFAULT_MODELS,
        "filters": {
            "min_price": 2500,
            "max_price": 5000,
            "max_km": 20000,
            "min_year": 2017,
            "max_year": 2026,
            "annual_km": 4000,
            "price_weight": 50,
            "year_weight": 25,
            "km_weight": 25,
            "sources": ["La Centrale", "ParuVendu", "Zoomcar", "Leboncoin"],
            "postal_code": "75011",
            "radius_km": 50,
        },
        "last_page": "Scanner Live",
        "last_results_keys": [],
    }

def load_state():
    state = default_state()
    if STATE_FILE.exists():
        try:
            saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            state.update(saved)
        except Exception:
            pass
    return state

def save_state():
    STATE_FILE.write_text(json.dumps(st.session_state.state, ensure_ascii=False, indent=2), encoding="utf-8")

if "state" not in st.session_state:
    st.session_state.state = load_state()
S = st.session_state.state

# Migration from older versions: model-specific filters are removed in V3.3.
S["models"] = {m: {} for m in list(S.get("models", {}).keys())}

# V3.5.2 parser migration: old displayed-result keys may contain values parsed
# with the buggy V3.5 logic. Force a fresh scan once after upgrade.
if not S.get("parser_version") == "3.5.2":
    S["last_results_keys"] = []
    S["parser_version"] = "3.5.2"
    save_state()

# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------
def normalize(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())

def safe_int(s):
    if s is None:
        return None
    txt = str(s).replace("\u202f", " ").replace("\xa0", " ")
    m = re.search(r"(\d[\d\s.]*)", txt)
    if not m:
        return None
    try:
        return int(re.sub(r"[^\d]", "", m.group(1)))
    except Exception:
        return None

def parse_km(text):
    """
    Strict mileage fallback.

    We only accept km values that look like VEHICLE mileage:
    - an explicit "xxxxx km" token;
    - ignore very small values likely to be geographic distances;
    - if several values exist, prefer the largest plausible vehicle mileage.
    """
    txt = str(text)

    candidates = []
    for m in re.finditer(r"(?<!\d)(\d{1,3}(?:[\s\u202f\xa0.]?\d{3}){0,2})\s*km\b", txt, flags=re.I):
        v = safe_int(m.group(1))
        if v is None:
            continue
        if 0 <= v <= 300000:
            candidates.append(v)

    if not candidates:
        return None

    # Most location-distance values are < 500 km. Prefer a realistic odometer
    # figure if one exists; otherwise keep 0 only for truly new bikes.
    vehicle_like = [v for v in candidates if v >= 500]
    if vehicle_like:
        return max(vehicle_like)

    if 0 in candidates:
        return 0

    return None


def parse_year(text):
    """
    Strict MODEL YEAR fallback.

    Never use an arbitrary year from the whole page. We only accept years
    located next to vehicle-specific labels or in a short title-like prefix.
    This prevents current/publication year (e.g. 2026) from becoming the
    motorcycle model year.
    """
    txt = str(text)
    current = datetime.now().year

    labelled_patterns = [
        r"(?:année|annee)\s*(?:du\s+modèle|du\s+modele)?\s*[:\-]?\s*(19[89]\d|20[0-2]\d)",
        r"(?:millésime|millesime)\s*[:\-]?\s*(19[89]\d|20[0-2]\d)",
        r"(?:mise\s+en\s+circulation|1re\s+mise\s+en\s+circulation|première\s+mise\s+en\s+circulation|premiere\s+mise\s+en\s+circulation)"
        r"\s*[:\-]?\s*(?:\d{1,2}[\/\-.]\d{1,2}[\/\-.])?(19[89]\d|20[0-2]\d)",
        r"(?:regdate|reg_date|registration_date|registrationdate|vehicle_year|vehicleyear|model_year|modelyear)"
        r"\D{0,25}(19[89]\d|20[0-2]\d)",
    ]

    for pat in labelled_patterns:
        m = re.search(pat, txt, flags=re.I)
        if m:
            y = int(m.group(1))
            if 1980 <= y <= current + 1:
                return y

    # Conservative title/header fallback: only inspect the beginning.
    # Ignore the current year unless clearly vehicle-labelled above.
    head = txt[:180]
    years = [int(y) for y in re.findall(r"\b(19[89]\d|20[0-2]\d)\b", head)]
    years = [y for y in years if 1980 <= y <= current + 1 and y != current]

    # A title generally contains a single model year. If ambiguous, reject it
    # instead of guessing.
    unique = list(dict.fromkeys(years))
    if len(unique) == 1:
        return unique[0]

    return None


def parse_price(text):
    matches = re.findall(r"(\d[\d\s\u202f\xa0.]*)\s*€", str(text))
    vals = []
    for m in matches:
        v = safe_int(m)
        if v and 500 <= v <= 50000:
            vals.append(v)
    return vals[0] if vals else None


def extract_options(text):
    low = str(text).lower()
    found = []
    for label, patterns in OPTION_PATTERNS.items():
        if any(p in low for p in patterns):
            found.append(label)
    return ", ".join(found) if found else "—"

def closest_models(query, n=4):
    q = normalize(query)
    scored = [(SequenceMatcher(None, q, normalize(m)).ratio(), m) for m in MODEL_CATALOG]
    return [m for _, m in sorted(scored, reverse=True)[:n]]

def validate_model(query):
    q = normalize(query)
    for m in MODEL_CATALOG:
        if normalize(m) == q:
            return m, []
    return None, closest_models(query)

def aliases_for(model):
    if model in MODEL_ALIASES:
        return MODEL_ALIASES[model]

    # Generic aliases for a user-added model not present in the catalogue.
    # Example "CFMoto 700 MT" -> full text + brandless + spacing/hyphen variants.
    raw = " ".join(str(model).split())
    parts = raw.split()
    brandless = " ".join(parts[1:]) if len(parts) > 1 else raw

    variants = {
        raw,
        brandless,
        raw.replace("-", " "),
        raw.replace(" ", "-"),
        brandless.replace("-", " "),
        brandless.replace(" ", "-"),
        raw.replace(" ", ""),
        brandless.replace(" ", ""),
    }
    return [v for v in variants if len(v.strip()) >= 2]

def text_matches_model(text, model):
    """
    Match any accepted alias rather than requiring one canonical spelling.
    This intentionally handles MT07 / MT-07 / MT 07 / MT07 A2, etc.
    """
    low = normalize(text)
    for alias in aliases_for(model):
        if normalize(alias) in low:
            return True

    # Fallback token match for titles that contain extra punctuation/words.
    canonical = normalize(model)
    make = normalize(model.split()[0])
    reduced = canonical.replace(make, "", 1)
    return bool(reduced and reduced in low)

_GEO_CACHE = {}

def postcode_from_text(text):
    # France metropolitan + overseas 5-digit postal codes.
    matches = re.findall(r"(?<!\d)(\d{5})(?!\d)", str(text))
    for cp in matches:
        if cp[:2] != "00":
            return cp
    return None

def geocode_postcode(cp):
    cp = str(cp).strip()
    if cp in _GEO_CACHE:
        return _GEO_CACHE[cp]
    if not re.fullmatch(r"\d{5}", cp):
        return None

    url = "https://geo.api.gouv.fr/communes"
    params = {
        "codePostal": cp,
        "fields": "nom,code,codesPostaux,centre",
        "format": "json",
        "geometry": "centre"
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data:
        _GEO_CACHE[cp] = None
        return None

    centre = data[0].get("centre") or {}
    coords = centre.get("coordinates")
    if not coords or len(coords) != 2:
        _GEO_CACHE[cp] = None
        return None

    lon, lat = coords
    result = {"lat": float(lat), "lon": float(lon), "name": data[0].get("nom", cp)}
    _GEO_CACHE[cp] = result
    return result

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

def distance_from_search_postcode(ad):
    target_cp = str(S["filters"].get("postal_code","")).strip()
    target = geocode_postcode(target_cp)
    if not target:
        return None

    cp = postcode_from_text(ad.get("location","")) or postcode_from_text(ad.get("description",""))
    if not cp:
        return None
    point = geocode_postcode(cp)
    if not point:
        return None
    return haversine_km(target["lat"], target["lon"], point["lat"], point["lon"])

def ad_key(source, url, model="", year=None, km=None, price=None):
    if url:
        raw = f"{source}|{url}"
    else:
        raw = f"{source}|{model}|{year}|{km}|{price}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

def compact_text(node):
    return " ".join(node.get_text(" ", strip=True).split())


def parse_card_year(text):
    """For non-structured sites: prefer explicit vehicle year; do not guess."""
    return parse_year(text)

def parse_card_km(text):
    """For non-structured sites: mileage must be an explicit odometer-like km."""
    return parse_km(text)

def valid_vehicle_values(year, km):
    if year is None or km is None:
        return False
    if not (1980 <= int(year) <= datetime.now().year + 1):
        return False
    if not (0 <= int(km) <= 300000):
        return False
    return True


def fetch(url, timeout=15):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def fetch_soup(url, timeout=15):
    return BeautifulSoup(fetch(url, timeout=timeout), "html.parser")

def unique_by_url(ads):
    out = []
    seen = set()
    for ad in ads:
        u = str(ad.get("url",""))
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(ad)
    return out

def postcode_only(text):
    return postcode_from_text(text) or ""


# -------------------------------------------------------------------
# Live connectors
# -------------------------------------------------------------------
LC_MODEL_URLS = {
    "Yamaha MT-07": "https://www.lacentrale.fr/occasion-moto-modele-yamaha-mt_07.html",
    "Yamaha Tracer 700": "https://www.lacentrale.fr/occasion-moto-modele-yamaha-tracer.html",
    "Honda CB500X": "https://www.lacentrale.fr/occasion-moto-modele-honda-cb.html",
    "Honda CB500F": "https://www.lacentrale.fr/occasion-moto-modele-honda-cb.html",
    "Honda NC750X": "https://www.lacentrale.fr/occasion-moto-modele-honda-nc.html",
    "Kawasaki Z650": "https://www.lacentrale.fr/occasion-moto-modele-kawasaki-z.html",
    "Kawasaki Ninja 650": "https://www.lacentrale.fr/occasion-moto-modele-kawasaki-ninja.html",
    "Kawasaki Versys 650": "https://www.lacentrale.fr/occasion-moto-modele-kawasaki-versys.html",
    "Suzuki SV650": "https://www.lacentrale.fr/occasion-moto-modele-suzuki-sv.html",
    "Suzuki V-Strom 650": "https://www.lacentrale.fr/occasion-moto-modele-suzuki-v_strom.html",
    "BMW F 700 GS": "https://www.lacentrale.fr/occasion-moto-modele-bmw-f.html",
    "BMW F 800 R": "https://www.lacentrale.fr/occasion-moto-modele-bmw-f.html",
    "BMW F 800 GS": "https://www.lacentrale.fr/occasion-moto-modele-bmw-f.html",
}

def lacentrale_search(model):
    base_url = LC_MODEL_URLS.get(model)
    if not base_url:
        make, *rest = model.split()
        slug_model = "_".join(rest).lower().replace("-", "_")
        base_url = f"https://www.lacentrale.fr/occasion-moto-modele-{make.lower()}-{slug_model}.html"

    ads = []
    seen = set()

    # La Centrale exposes many listings; inspect several pagination forms.
    page_urls = [base_url]
    for p in range(2, 9):
        page_urls.extend([
            base_url.replace(".html", f"-{p}.html"),
            base_url + f"?page={p}",
        ])

    for page_url in page_urls:
        try:
            soup = fetch_soup(page_url)
        except Exception:
            continue

        page_added = 0
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            lowhref = href.lower()
            # Accept current and older individual listing URL forms.
            if not (
                "moto-occasion-annonce" in lowhref
                or ("/moto-occasion-" in lowhref and "annonce" in lowhref)
            ):
                continue

            full = urljoin("https://www.lacentrale.fr", href)
            if full in seen:
                continue

            node = a
            for _ in range(7):
                if node.parent is None:
                    break
                node = node.parent
                txt = compact_text(node)
                if "km" in txt.lower() and "€" in txt and len(txt) < 5000:
                    break
            txt = compact_text(node)
            if not text_matches_model(txt, model):
                continue

            year, km, price = parse_card_year(txt), parse_card_km(txt), parse_price(txt)
            if price is None or not valid_vehicle_values(year, km):
                continue

            cp = postcode_from_text(txt)
            seller = "Professionnel" if re.search(r"\b(pro|professionnel|garage)\b", txt, re.I) else "Particulier"
            ads.append({
                "source":"La Centrale","model":model,"year":int(year),"km":int(km),
                "price":float(price),"location":cp or "","seller_type":seller,
                "description":txt[:1600],"options":extract_options(txt),"url":full
            })
            seen.add(full)
            page_added += 1

        # Stop after repeated empty variants once we already have ads.
        if page_added == 0 and ads and "?page=" in page_url:
            pass

    return unique_by_url(ads)

PV_BRAND_URLS = {
    "Yamaha": "https://www.paruvendu.fr/a/moto-scooter/moto/yamaha/",
    "Honda": "https://www.paruvendu.fr/a/moto-scooter/moto/honda/",
    "Kawasaki": "https://www.paruvendu.fr/a/moto-scooter/moto/kawasaki/",
    "Suzuki": "https://www.paruvendu.fr/a/moto-scooter/moto/suzuki/",
    "BMW": "https://www.paruvendu.fr/a/moto-scooter/moto/bmw/",
    "Triumph": "https://www.paruvendu.fr/a/moto-scooter/moto/triumph/",
}

def paruvendu_search(model):
    make = model.split()[0]
    base_url = PV_BRAND_URLS.get(make)
    if not base_url:
        return []

    ads, seen = [], set()
    for p in range(1, 9):
        page_url = base_url if p == 1 else base_url + f"?p={p}"
        try:
            soup = fetch_soup(page_url)
        except Exception:
            continue

        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            full = urljoin("https://www.paruvendu.fr", href)
            if full in seen or full.rstrip("/") == base_url.rstrip("/"):
                continue

            # Individual ParuVendu ads frequently end with an alphanumeric ad id.
            if not (
                "/a/moto-scooter/moto/" in href
                and (re.search(r"\d{7,}[A-Z0-9]*", href, re.I) or href.count("/") >= 5)
            ):
                continue

            node = a
            for _ in range(7):
                if node.parent is None:
                    break
                node = node.parent
                txt = compact_text(node)
                if "km" in txt.lower() and "€" in txt and len(txt) < 5000:
                    break

            txt = compact_text(node)
            if not text_matches_model(txt, model):
                continue
            year, km, price = parse_card_year(txt), parse_card_km(txt), parse_price(txt)
            if price is None or not valid_vehicle_values(year, km):
                continue

            cp = postcode_from_text(txt)
            seller = "Professionnel" if re.search(r"\b(pro|professionnel|garage|garantie)\b", txt, re.I) else "Particulier"
            ads.append({
                "source":"ParuVendu","model":model,"year":int(year),"km":int(km),
                "price":float(price),"location":cp or "","seller_type":seller,
                "description":txt[:1600],"options":extract_options(txt),"url":full
            })
            seen.add(full)

    return unique_by_url(ads)

ZOOMCAR_SLUGS = {
    "Yamaha MT-07": "yamaha-mt07",
    "Yamaha Tracer 700": "yamaha-mt07-tracer",
    "Honda CB500X": "honda-cb500x",
    "Honda CB500F": "honda-cb500f",
    "Honda NC750X": "honda-nc750x",
    "Kawasaki Z650": "kawasaki-z650",
    "Kawasaki Ninja 650": "kawasaki-ninja-650",
    "Kawasaki Versys 650": "kawasaki-versys-650",
    "Suzuki SV650": "suzuki-sv650",
    "Suzuki V-Strom 650": "suzuki-v-strom-650",
}

def zoomcar_search(model):
    slug = ZOOMCAR_SLUGS.get(model)
    if not slug:
        return []
    base_url = f"https://www.ouestfrance-auto.com/moto-occasion/{slug}/"
    ads, seen = [], set()

    for p in range(1, 9):
        candidates = [base_url] if p == 1 else [base_url + f"?page={p}", base_url + f"{p}/"]
        for page_url in candidates:
            try:
                soup = fetch_soup(page_url)
            except Exception:
                continue

            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                full = urljoin("https://www.ouestfrance-auto.com", href)
                if full in seen or full.rstrip("/") == base_url.rstrip("/"):
                    continue
                if "moto-occasion" not in full:
                    continue

                node = a
                for _ in range(7):
                    if node.parent is None:
                        break
                    node = node.parent
                    txt = compact_text(node)
                    if "km" in txt.lower() and "€" in txt and len(txt) < 5000:
                        break
                txt = compact_text(node)
                if not text_matches_model(txt, model):
                    continue

                year, km, price = parse_card_year(txt), parse_card_km(txt), parse_price(txt)
                if not all(v is not None for v in [year, km, price]):
                    continue

                cp = postcode_from_text(txt)
                seller = "Professionnel" if re.search(r"\b(pro|garage|garantie)\b", txt, re.I) else "Particulier"
                ads.append({
                    "source":"Zoomcar","model":model,"year":int(year),"km":int(km),
                    "price":float(price),"location":cp or "","seller_type":seller,
                    "description":txt[:1600],"options":extract_options(txt),"url":full
                })
                seen.add(full)

    return unique_by_url(ads)

def _ad_attr_text(ad):
    parts = []
    for name in ["subject", "body", "title", "description"]:
        try:
            v = getattr(ad, name, None)
            if v:
                parts.append(str(v))
        except Exception:
            pass
    try:
        parts.append(str(vars(ad)))
    except Exception:
        pass
    return " ".join(parts)

def _extract_lbc_structured_ad(ad, model, target):
    text = _ad_attr_text(ad)
    if not text_matches_model(text, model):
        return None

    url = getattr(ad, "url", None)
    subject = getattr(ad, "subject", "") or ""

    price_obj = getattr(ad, "price", None)
    try:
        price = price_obj() if callable(price_obj) else price_obj
    except Exception:
        price = None

    if isinstance(price, (list, tuple)):
        price = price[0] if price else None

    try:
        price = float(price) if price is not None else parse_price(subject)
    except Exception:
        price = parse_price(subject)

    # First choice: real structured vehicle attributes only.
    year = structured_vehicle_year(ad)
    km = structured_vehicle_km(ad)

    # Fallback: ONLY the short subject/title, never vars(ad) / full serialization.
    if year is None:
        year = parse_year(subject)
    if km is None:
        km = parse_km(subject)

    if not url or price is None or not valid_vehicle_values(year, km):
        return None

    postcode = structured_postcode(ad)
    distance = None

    try:
        loc = getattr(ad, "location", None)
        if loc:
            lat = getattr(loc, "lat", None) or getattr(loc, "latitude", None)
            lon = getattr(loc, "lng", None) or getattr(loc, "lon", None) or getattr(loc, "longitude", None)
            if lat is not None and lon is not None and target:
                distance = haversine_km(
                    target["lat"], target["lon"], float(lat), float(lon)
                )
    except Exception:
        pass

    if postcode is None:
        postcode = postcode_from_text(text)

    return {
        "source": "Leboncoin",
        "model": model,
        "year": int(year),
        "km": int(km),
        "price": float(price),
        "location": postcode or "",
        "seller_type": "",
        "description": (subject + " " + text)[:1600],
        "options": extract_options(text),
        "url": str(url),
        "distance_km": distance,
    }

def _radius_ladder(selected_km):
    """
    Query inner radii as well as the requested radius.
    This guarantees that increasing 50 -> 100 km does not lose ads merely
    because the larger result set pushes nearby ads beyond the page limit.
    """
    selected = int(selected_km)
    standards = [10, 20, 30, 40, 50, 75, 100, 125, 150, 200, 250, 300]
    vals = [r for r in standards if r < selected]
    vals.append(selected)
    # Keep all strategically important inner radii, capped to avoid explosion.
    if len(vals) > 7:
        vals = vals[-7:]
        if 50 <= selected and 50 not in vals:
            vals.insert(0, 50)
    return sorted(set(vals))

def leboncoin_search(model):
    target_cp = str(S["filters"].get("postal_code", "75011"))
    target = geocode_postcode(target_cp)
    selected_radius = int(S["filters"].get("radius_km", 50))
    aliases = aliases_for(model)

    ads = []
    seen = set()

    # Structured search first, but NEVER let one library/API error kill the
    # whole connector. V3.5 accidentally removed this outer fallback.
    if lbc is not None and target is not None:
        try:
            client = lbc.Client()
            city_name = target.get("name") or target_cp

            for radius_km in _radius_ladder(selected_radius):
                try:
                    location = lbc.City(
                        lat=target["lat"],
                        lng=target["lon"],
                        radius=int(radius_km * 1000),
                        city=city_name,
                    )
                except Exception:
                    # If this library version expects a different City schema,
                    # skip structured mode and use HTML fallback below.
                    raise

                for page_num in range(1, 6):
                    try:
                        time.sleep(0.8)
                        result = client.search(
                            text=aliases,
                            locations=[location],
                            page=page_num,
                            limit=35,
                            search_in_title_only=False,
                        )
                    except Exception:
                        break

                    page_ads = getattr(result, "ads", []) or []
                    if not page_ads:
                        break

                    for raw in page_ads:
                        parsed = _extract_lbc_structured_ad(raw, model, target)
                        if not parsed or parsed["url"] in seen:
                            continue
                        if parsed.get("distance_km") is not None and parsed["distance_km"] > selected_radius:
                            continue
                        seen.add(parsed["url"])
                        ads.append(parsed)

            if ads:
                return ads
        except Exception:
            # Critical fix: fall through to the public HTML method instead of
            # propagating the exception to live_scan().
            ads = []
            seen = set()

    # HTML fallback. Do not let an unavailable structured API result in zero
    # listings if the public results page remains readable.
    errors = []
    for alias in aliases[:6]:
        q = quote_plus(alias)
        url = f"https://www.leboncoin.fr/recherche?text={q}&category=3"
        time.sleep(0.8)

        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
        except Exception as e:
            errors.append(f"{alias}: {type(e).__name__}")
            continue

        if r.status_code in (401,403,429):
            errors.append(f"{alias}: HTTP {r.status_code}")
            continue

        try:
            r.raise_for_status()
        except Exception:
            errors.append(f"{alias}: HTTP {r.status_code}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a.get("href","")
            if "/ad/" not in href:
                continue

            full = urljoin("https://www.leboncoin.fr", href)
            if full in seen:
                continue

            node = a
            for _ in range(8):
                if node.parent is None:
                    break
                node = node.parent
                txt = compact_text(node)
                if "€" in txt and re.search(r"\bkm\b", txt, re.I) and len(txt) < 4000:
                    break

            txt = compact_text(node)
            if not text_matches_model(txt, model):
                continue

            year, km, price = parse_card_year(txt), parse_card_km(txt), parse_price(txt)
            if price is None or not valid_vehicle_values(year, km):
                continue

            cp = postcode_from_text(txt)
            ad = {
                "source":"Leboncoin",
                "model":model,
                "year":int(year),
                "km":int(km),
                "price":float(price),
                "location":cp or "",
                "seller_type":"",
                "description":txt[:1600],
                "options":extract_options(txt),
                "url":full
            }
            ad["distance_km"] = distance_from_search_postcode(ad)

            if ad["distance_km"] is not None and ad["distance_km"] > selected_radius:
                continue

            seen.add(full)
            ads.append(ad)

    return unique_by_url(ads)

CONNECTORS = {
    "La Centrale": lacentrale_search,
    "ParuVendu": paruvendu_search,
    "Zoomcar": zoomcar_search,
    "Leboncoin": leboncoin_search,
}

# -------------------------------------------------------------------
# Database update/history
# -------------------------------------------------------------------
def persist_ads(ads):
    now = datetime.now().isoformat(timespec="seconds")
    con = sqlite3.connect(DB_FILE)
    keys = []
    for ad in ads:
        key = ad_key(ad["source"], ad["url"], ad["model"], ad["year"], ad["km"], ad["price"])
        keys.append(key)
        row = con.execute("SELECT last_price,min_price,max_price,scan_count FROM ads WHERE ad_key=?", (key,)).fetchone()

        if row is None:
            con.execute("""
                INSERT INTO ads(ad_key,source,model,year,km,price,location,seller_type,description,options,url,distance_km,
                                first_seen,last_seen,last_price,min_price,max_price,scan_count)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
            """, (key, ad["source"], ad["model"], ad["year"], ad["km"], ad["price"],
                  ad["location"], ad["seller_type"], ad["description"], ad["options"], ad["url"], ad.get("distance_km"),
                  now, now, ad["price"], ad["price"], ad["price"]))
            con.execute("INSERT INTO price_history(ad_key,observed_at,price) VALUES(?,?,?)",
                        (key, now, ad["price"]))
        else:
            last_price, min_price, max_price, scan_count = row
            if float(last_price) != float(ad["price"]):
                con.execute("INSERT INTO price_history(ad_key,observed_at,price) VALUES(?,?,?)",
                            (key, now, ad["price"]))
            con.execute("""
                UPDATE ads SET year=?,km=?,price=?,location=?,seller_type=?,description=?,options=?,distance_km=?,last_seen=?,
                    last_price=?,min_price=?,max_price=?,scan_count=?
                WHERE ad_key=?
            """, (ad["year"], ad["km"], ad["price"], ad["location"], ad["seller_type"],
                  ad["description"], ad["options"], ad.get("distance_km"), now, ad["price"],
                  min(float(min_price), float(ad["price"])),
                  max(float(max_price), float(ad["price"])),
                  int(scan_count)+1, key))
    con.commit()
    con.close()
    return keys

def load_ads(keys=None, saved_only=False):
    con = sqlite3.connect(DB_FILE)
    q = "SELECT * FROM ads"
    params = []
    clauses = []
    if keys:
        clauses.append("ad_key IN (%s)" % ",".join("?"*len(keys)))
        params.extend(keys)
    if saved_only:
        clauses.append("is_saved=1")
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    df = pd.read_sql_query(q, con, params=params)
    con.close()
    return df

def toggle_saved(key, value):
    con = sqlite3.connect(DB_FILE)
    con.execute("UPDATE ads SET is_saved=? WHERE ad_key=?", (1 if value else 0, key))
    con.commit()
    con.close()

# -------------------------------------------------------------------
# Score/resale
# -------------------------------------------------------------------
def apply_filters(df):
    if df.empty:
        return df
    f = S["filters"]
    d = df.copy()
    mask = (
        (d.price >= f["min_price"]) &
        (d.price <= f["max_price"]) &
        (d.km <= f["max_km"]) &
        (d.year >= f["min_year"]) &
        (d.year <= f["max_year"])
    )
    if "distance_km" in d.columns:
        radius = float(f.get("radius_km", 50))
        mask = mask & (d.distance_km.isna() | (d.distance_km <= radius))
    return d[mask]

def score_ads(df):
    if df.empty:
        return df
    d = df.copy()
    weights = np.array([
        S["filters"]["price_weight"],
        S["filters"]["year_weight"],
        S["filters"]["km_weight"]
    ], dtype=float)
    weights = weights / weights.sum() if weights.sum() else np.array([.5,.25,.25])

    def lower_better(s):
        return pd.Series(100.0, index=s.index) if s.max()==s.min() else 100*(s.max()-s)/(s.max()-s.min())
    def higher_better(s):
        return pd.Series(100.0, index=s.index) if s.max()==s.min() else 100*(s-s.min())/(s.max()-s.min())

    d["score_prix"] = lower_better(d.price.astype(float))
    d["score_annee"] = higher_better(d.year.astype(float))
    d["score_km"] = lower_better(d.km.astype(float))
    d["score"] = (
        d.score_prix*weights[0] + d.score_annee*weights[1] + d.score_km*weights[2]
    )

    # Peer market estimate: median by model +/-1 year when enough history exists.
    medians = []
    resale = []
    for _, r in d.iterrows():
        peers = d[(d.model==r.model) & (d.year.between(r.year-1, r.year+1))]
        mkt = float(peers.price.median()) if len(peers) >= 2 else float(r.price)
        medians.append(mkt)
        annual_km = S["filters"]["annual_km"]
        # Conservative heuristic: ~7%/yr age depreciation plus mileage effect.
        future = max(1500, mkt*(0.93**2) - annual_km*2*0.012)
        resale.append(future)
    d["prix_marche"] = medians
    d["revente_2_ans"] = resale
    d["decote_estimee"] = d.price - d.revente_2_ans
    d["variation_depuis_max"] = d.price - d.max_price
    return d.sort_values(["score","price"], ascending=[False,True])

# -------------------------------------------------------------------
# Live scan
# -------------------------------------------------------------------
def live_scan():
    all_ads = []
    status = []
    progress = st.progress(0)

    models = list(S["models"].keys())
    sources = S["filters"].get("sources") or list(CONNECTORS.keys())

    # Migration/safety: if an older saved state has an empty or invalid source
    # selection, use all available connectors rather than silently returning 0.
    sources = [s for s in sources if s in CONNECTORS]
    if not sources:
        sources = list(CONNECTORS.keys())
        S["filters"]["sources"] = sources

    tasks = [(src, m) for src in sources for m in models]
    total = max(1, len(tasks))

    for i, (src, model) in enumerate(tasks, 1):
        try:
            connector = CONNECTORS[src]
            ads = connector(model)

            for a in ads:
                cp = postcode_from_text(a.get("location","")) or postcode_from_text(a.get("description",""))
                a["location"] = cp or ""
                if "distance_km" not in a or a.get("distance_km") is None:
                    a["distance_km"] = distance_from_search_postcode(a)

            radius = float(S["filters"].get("radius_km", 50))
            ads = [
                a for a in ads
                if S["filters"]["min_year"] <= a["year"] <= S["filters"]["max_year"]
                and S["filters"]["min_price"] <= a["price"] <= S["filters"]["max_price"]
                and a["km"] <= S["filters"]["max_km"]
                and (a.get("distance_km") is None or a.get("distance_km") <= radius)
            ]

            all_ads.extend(ads)
            status.append({
                "Source": src, "Modèle": model, "Résultat": len(ads), "Statut": "OK"
            })
        except Exception as e:
            status.append({
                "Source": src, "Modèle": model, "Résultat": 0,
                "Statut": f"Erreur: {str(e)[:120]}"
            })

        progress.progress(i / total)

    # Persist any newly retrieved ads first.
    new_keys = persist_ads(all_ads) if all_ads else []

    # Load historical ads that still match the CURRENT selected models/sources
    # and CURRENT global filters. This makes a transient connector failure
    # non-destructive and prevents "13 ads -> 0 ads" regressions.
    historical = load_ads()
    if not historical.empty:
        historical = historical[
            historical["model"].isin(models) &
            historical["source"].isin(sources)
        ]
        historical = historical[
            historical["year"].between(1980, datetime.now().year + 1) &
            historical["km"].between(0, 300000)
        ]
        historical = apply_filters(historical)
    else:
        historical = pd.DataFrame()

    # New ads always take part; historical matches are merged/deduplicated by ad_key.
    current = load_ads(new_keys) if new_keys else pd.DataFrame()
    frames = [x for x in [current, historical] if x is not None and not x.empty]

    if frames:
        merged = pd.concat(frames, ignore_index=True)
        merged = merged.drop_duplicates("ad_key", keep="first")
        merged = score_ads(merged)
        result_keys = merged["ad_key"].tolist()
        S["last_results_keys"] = result_keys
        st.session_state.results = merged
    else:
        # Last-resort fallback: preserve previous displayed results if the entire
        # external scan failed. We do NOT overwrite the saved key list with [].
        previous_keys = S.get("last_results_keys", [])
        previous = load_ads(previous_keys) if previous_keys else pd.DataFrame()
        previous = apply_filters(previous) if not previous.empty else previous
        if not previous.empty:
            st.session_state.results = score_ads(previous)
        else:
            st.session_state.results = pd.DataFrame()

    save_state()
    st.session_state.scan_status = pd.DataFrame(status)

# -------------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------------
pages = ["Scanner Live","Modèles","Favoris","Historique","Leboncoin","Diagnostic","Installer sur iPhone","Import manuel"]
st.sidebar.title("🏍️ Moto Scanner V4.1")
last_page = S.get("last_page","Scanner Live")
page = st.sidebar.radio("Navigation", pages, index=pages.index(last_page) if last_page in pages else 0)
if page != last_page:
    S["last_page"] = page
    save_state()

st.sidebar.subheader("Filtres")
S["filters"]["min_price"], S["filters"]["max_price"] = st.sidebar.slider(
    "Prix (€)", 1000, 12000,
    (int(S["filters"]["min_price"]), int(S["filters"]["max_price"])), 100)
S["filters"]["max_km"] = st.sidebar.slider("Km maximum", 1000, 80000, int(S["filters"]["max_km"]), 500)
S["filters"]["min_year"], S["filters"]["max_year"] = st.sidebar.slider(
    "Année", 2005, 2026,
    (int(S["filters"]["min_year"]), int(S["filters"]["max_year"])))
S["filters"]["annual_km"] = st.sidebar.number_input("Km/an prévus", 500, 20000, int(S["filters"]["annual_km"]), 500)

st.sidebar.subheader("Zone géographique")
S["filters"]["postal_code"] = st.sidebar.text_input(
    "Code postal de départ", value=str(S["filters"].get("postal_code","75011")), max_chars=5
)
S["filters"]["radius_km"] = st.sidebar.slider(
    "Rayon autour du code postal (km)", 5, 300, int(S["filters"].get("radius_km",50)), 5
)
if not re.fullmatch(r"\d{5}", str(S["filters"]["postal_code"])):
    st.sidebar.warning("Entre un code postal français à 5 chiffres.")
else:
    try:
        _g = geocode_postcode(S["filters"]["postal_code"])
        if _g:
            st.sidebar.caption(f"Zone centrée sur : {_g['name']}")
    except Exception:
        st.sidebar.caption("Géocodage temporairement indisponible.")

st.sidebar.subheader("Sources live")
S["filters"]["sources"] = st.sidebar.multiselect(
    "Sources", list(CONNECTORS.keys()),
    default=[x for x in S["filters"]["sources"] if x in CONNECTORS]
)

st.sidebar.subheader("Score personnalisé")
S["filters"]["price_weight"] = st.sidebar.slider("Prix bas",0,100,int(S["filters"]["price_weight"]))
S["filters"]["year_weight"] = st.sidebar.slider("Année récente",0,100,int(S["filters"]["year_weight"]))
S["filters"]["km_weight"] = st.sidebar.slider("Faible kilométrage",0,100,int(S["filters"]["km_weight"]))
save_state()

# -------------------------------------------------------------------
# UI
# -------------------------------------------------------------------
st.title("🏍️ Moto Scanner France — V4.1 Mobile")

if page == "Scanner Live":
    st.write("Recherche en direct sur les sources sélectionnées. Les annonces sont enregistrées localement afin de suivre les nouvelles annonces et baisses de prix.")
    if st.button("🌐 Lancer le scan LIVE", type="primary", use_container_width=True):
        live_scan()

    if "results" not in st.session_state and S.get("last_results_keys"):
        st.session_state.results = score_ads(apply_filters(load_ads(S["last_results_keys"])))

    df = st.session_state.get("results", pd.DataFrame())
    if not df.empty:
        st.success(f"{len(df)} annonces correspondant aux critères.")

        counts = df["source"].value_counts().to_dict()
        st.caption("Résultats par source : " + " · ".join(f"{src}: {n}" for src,n in counts.items()))

        display_df = df.copy()
        display_df["is_saved"] = display_df["is_saved"].fillna(0).astype(int)
        display_df = display_df.sort_values(["is_saved","score","price"], ascending=[False,False,True])

        for _, r in display_df.iterrows():
            fav = bool(r.get("is_saved", 0))
            cp = str(r.get("location") or "—")
            distance = "?" if pd.isna(r.get("distance_km")) else f"{float(r['distance_km']):.0f} km"
            opts = str(r.get("options") or "—")
            src = str(r.get("source") or "—")

            st.markdown(
                f"""
                <div class="mobile-card">
                  <div class="mobile-title">{'❤️ ' if fav else ''}{r['model']} · {int(r['year'])}</div>
                  <div class="mobile-price">{float(r['price']):.0f} €</div>
                  <div class="mobile-meta">{int(r['km'])} km · {cp} · {distance}</div>
                  <div class="mobile-meta">{src}</div>
                  <div class="mobile-meta">Options : {opts}</div>
                  <span class="mobile-tag">Score {float(r['score']):.0f}/100</span>
                  <span class="mobile-tag">Revente 2 ans ≈ {float(r['revente_2_ans']):.0f} €</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            x1, x2 = st.columns([1, 3])
            new_fav = x1.checkbox("❤️", value=fav, key=f"fav_mobile_{r['ad_key']}")
            if new_fav != fav:
                toggle_saved(r["ad_key"], new_fav)
                st.rerun()
            x2.link_button("🔗 Ouvrir l’annonce", str(r["url"]), use_container_width=True)

        with st.expander("📊 Tableau complet"):
            st.dataframe(
                df[["score","model","year","km","price","options","source","location","distance_km","url"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "url": st.column_config.LinkColumn("Annonce", display_text="🔗 Ouvrir")
                }
            )
    elif "results" in st.session_state:
        if "scan_status" in st.session_state and not st.session_state.scan_status.empty:
            failures = st.session_state.scan_status[
                st.session_state.scan_status["Statut"].astype(str).str.startswith("Erreur")
            ]
            if len(failures) == len(st.session_state.scan_status):
                st.error(
                    "Les connecteurs ont échoué pendant ce scan. "
                    "Les filtres ne sont probablement pas en cause. "
                    "Ouvre le diagnostic du scan ci-dessous pour voir les erreurs."
                )
            else:
                st.warning("Aucune annonce trouvée avec les filtres actuels.")
        else:
            st.warning("Aucune annonce trouvée avec les filtres actuels.")

    if "scan_status" in st.session_state:
        scan_diag = st.session_state.scan_status
        with st.expander("🧪 Diagnostic du scan par source", expanded=False):
            st.dataframe(scan_diag, use_container_width=True, hide_index=True)

        if not scan_diag.empty:
            failed = scan_diag[scan_diag["Statut"].astype(str).str.startswith("Erreur")]
            if not failed.empty:
                st.warning(
                    "Une ou plusieurs sources ont échoué depuis ce serveur. "
                    "Le nombre d'annonces affiché peut donc être inférieur à celui obtenu sur ton PC."
                )

elif page == "Modèles":
    st.header("⚙️ Modèles recherchés")
    st.caption("Tu peux choisir un modèle connu ou ajouter librement un modèle absent de la liste.")

    query = st.text_input("Ajouter un modèle", placeholder="Ex. MT07, CFMoto 700 MT, Ducati Scrambler 800")
    if query.strip():
        exact, suggestions = validate_model(query)

        if exact:
            st.success(f"Modèle reconnu : **{exact}**")
            candidate = exact
        else:
            suggestion = suggestions[0] if suggestions else None
            if suggestion:
                st.info(f"Suggestion la plus proche : **{suggestion}**")
            mode = st.radio(
                "Que veux-tu faire ?",
                ["Utiliser la suggestion", "Ajouter exactement ce que j’ai écrit"],
                horizontal=False
            )
            candidate = suggestion if mode == "Utiliser la suggestion" and suggestion else query.strip()

        if st.button("➕ Ajouter ce modèle", use_container_width=True):
            candidate = str(candidate).strip()
            if candidate:
                if candidate not in S["models"]:
                    S["models"][candidate] = {}
                    save_state()
                    st.success(f"{candidate} ajouté.")
                    st.rerun()
                else:
                    st.info("Ce modèle est déjà présent.")

    st.subheader("Modèles actifs")
    active = list(S["models"].keys())
    if active:
        for model in active:
            c1, c2 = st.columns([5,1])
            c1.write(f"• {model}")
            if c2.button("🗑️", key=f"rm_{model}"):
                S["models"].pop(model, None)
                save_state()
                st.rerun()
    else:
        st.warning("Aucun modèle sélectionné.")
elif page == "Historique":
    st.header("📈 Historique des annonces")
    df = load_ads()
    if df.empty:
        st.info("Aucun historique pour le moment.")
    else:
        df = df.sort_values("last_seen", ascending=False)
        st.dataframe(
            df[["model","year","km","last_price","min_price","max_price","source","first_seen","last_seen","url"]],
            use_container_width=True,hide_index=True,
            column_config={"url":st.column_config.LinkColumn("Annonce",display_text="🔗 Ouvrir")}
        )

elif page == "Favoris":
    st.header("❤️ Favoris")
    df = load_ads(saved_only=True)
    if df.empty:
        st.info("Aucun favori. La V3 conserve déjà le champ favori dans la base ; tu peux aussi retrouver toutes les annonces dans Historique.")
    else:
        st.dataframe(df,use_container_width=True,hide_index=True,
                     column_config={"url":st.column_config.LinkColumn("Annonce",display_text="🔗 Ouvrir")})

elif page == "Leboncoin":
    st.header("🟠 Leboncoin Live")
    st.info(
        "V3.3 utilise en priorité une recherche structurée Leboncoin avec les alias du modèle "
        "et un rayon natif autour du code postal sélectionné. En cas d'échec, un fallback HTML est utilisé."
    )
    test_model = st.selectbox("Tester un modèle sur Leboncoin", list(S["models"]) if S["models"] else MODEL_CATALOG)
    if st.button("Tester Leboncoin Live"):
        try:
            ads = leboncoin_search(test_model)
            st.success(f"{len(ads)} annonces Leboncoin parsées.")
            if ads:
                st.dataframe(
                    pd.DataFrame(ads),
                    use_container_width=True,
                    hide_index=True,
                    column_config={"url": st.column_config.LinkColumn("Annonce", display_text="🔗 Ouvrir")}
                )
        except Exception as e:
            st.error(str(e))

    st.subheader("Recherches natives")
    for model,cfg in S["models"].items():
        q = quote_plus(model)
        url = f"https://www.leboncoin.fr/recherche?text={q}&category=3"
        st.markdown(f"**{model}** — [Ouvrir la recherche Leboncoin]({url})")

elif page == "Installer sur iPhone":
    st.header("📱 Installer sur iPhone")
    st.markdown("""
1. Ouvre l’URL de l’application dans **Safari**.
2. Appuie sur **Partager**.
3. Choisis **Sur l’écran d’accueil**.
4. Appuie sur **Ajouter**.
""")
    st.info("Le moteur de recherche de cette V4.1 est celui de la V3.5.2 PC ; seules la présentation et la gestion des modèles ont été adaptées au mobile.")

elif page == "Import manuel":
    st.header("📥 Ajouter des annonces externes")
    st.write("Tu peux ajouter des annonces provenant de Leboncoin ou d'une autre source sans scraping automatisé.")
    with st.form("manual_ad"):
        source = st.selectbox("Source",["Leboncoin","Autre"])
        model = st.selectbox("Modèle",list(S["models"]) if S["models"] else MODEL_CATALOG)
        year = st.number_input("Année",2000,2026,2019)
        km = st.number_input("Kilométrage",0,200000,15000,500)
        price = st.number_input("Prix (€)",500,30000,4500,100)
        location = st.text_input("Localisation")
        description = st.text_area("Description / options")
        url = st.text_input("Lien DIRECT de l'annonce")
        submitted = st.form_submit_button("Ajouter")
    if submitted:
        if not url.startswith("http"):
            st.error("Il faut une URL directe valide.")
        else:
            ad = {
                "source":source,"model":model,"year":int(year),"km":int(km),"price":float(price),
                "location":location,"seller_type":"","description":description,
                "options":extract_options(description),"url":url
            }
            persist_ads([ad])
            st.success("Annonce ajoutée à l'historique.")

elif page == "Diagnostic":
    st.header("🧪 Diagnostic")
    st.write(f"Base locale : `{DB_FILE}`")
    st.write(f"État : `{STATE_FILE}`")
    st.write("Teste chaque source indépendamment. Leboncoin utilise désormais plusieurs alias par modèle et déduplique les URLs :")
    model = st.selectbox("Modèle test",list(S["models"]) if S["models"] else MODEL_CATALOG)
    for name, connector in CONNECTORS.items():
        if st.button(f"Tester {name}", key=f"test_{name}"):
            try:
                ads = connector(model)
                st.success(f"{name}: {len(ads)} annonces uniques parsées avant filtres globaux.")
                if ads:
                    test_df = pd.DataFrame(ads)
                    st.dataframe(
                        test_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "year": st.column_config.NumberColumn("Année modèle", format="%d"),
                            "km": st.column_config.NumberColumn("Kilométrage", format="%d km"),
                            "location": st.column_config.TextColumn("Code postal"),
                            "url": st.column_config.LinkColumn("Annonce",display_text="🔗 Ouvrir")
                        }
                    )
            except Exception as e:
                st.error(f"{name}: {e}")

st.divider()
st.caption(
    "Les connecteurs live utilisent uniquement des pages web publiques, avec cadence limitée, sans contournement de CAPTCHA/anti-bot. "
    "Les structures HTML des sites peuvent évoluer ; utilise Diagnostic si une source cesse de fonctionner."
)
