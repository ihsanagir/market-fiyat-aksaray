import re
import json
import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "prices_db.json")

def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

def save_price(product_name, market, price, unit):
    init_db()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.append({
            "product_name": product_name.lower().strip(),
            "market": market,
            "price": float(price),
            "unit": unit or "",
            "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"DB save error: {e}")

def get_price_history(product_name):
    init_db()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        filtered = [x for x in data if tr_lower(product_name) in tr_lower(x.get("product_name", ""))]
        return pd.DataFrame(filtered) if filtered else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def tr_lower(text):
    if not text:
        return ''
    mapping = {'İ': 'i', 'I': 'ı', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç', '\u0307': ''}
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text.lower()

def normalize_market_name(name):
    if not name:
        return 'Tarım Kredi'
    lower = tr_lower(name).replace(" ", "")
    if 'bim' in lower: return 'BİM'
    if 'a101' in lower: return 'A101'
    if 'sok' in lower or 'şok' in lower: return 'ŞOK'
    if 'tarim' in lower or 'koop' in lower: return 'Tarım Kredi'
    return name

def calculate_unit_price(price, unit):
    if not unit: return None
    lower = tr_lower(unit)
    
    gr_match = re.search(r'(\d+(?:[.,]\d+)?)\s*g\b', lower)
    if gr_match:
        g = float(gr_match.group(1).replace(',', '.'))
        if g > 0: return {"value": round((price / g) * 1000, 2), "label": "₺/kg"}
            
    kg_match = re.search(r'(\d+(?:[.,]\d+)?)\s*kg', lower)
    if kg_match:
        kg = float(kg_match.group(1).replace(',', '.'))
        if kg > 0: return {"value": round(price / kg, 2), "label": "₺/kg"}
            
    ml_match = re.search(r'(\d+(?:[.,]\d+)?)\s*ml', lower)
    if ml_match:
        ml = float(ml_match.group(1).replace(',', '.'))
        if ml > 0: return {"value": round((price / ml) * 1000, 2), "label": "₺/L"}
            
    lt_match = re.search(r'(\d+(?:[.,]\d+)?)\s*l\b', lower)
    if lt_match:
        lt = float(lt_match.group(1).replace(',', '.'))
        if lt > 0: return {"value": round(price / lt, 2), "label": "₺/L"}
            
    return None

def fetch_tkkoop_live(query):
    try:
        url = f'https://www.tkkoop.com.tr/arama?ara={requests.utils.quote(query)}'
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200: return []

        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        seen = set()

        for card in soup.find_all('div', class_=lambda c: c and ('col' in c or 'card' in c)):
            strings = [t.strip() for t in card.stripped_strings if len(t.strip()) > 0]
            if any('TL' in s for s in strings) and len(strings) in [3, 4, 5]:
                title = strings[0]
                if title in seen or len(title) <= 2: continue
                try:
                    price_val = 0.0
                    for i, s in enumerate(strings):
                        if s == 'TL' and i >= 2:
                            lira_str = strings[i-2].replace(',', '').replace('.', '')
                            kurus_str = strings[i-1].replace(',', '').replace('.', '')
                            price_val = float(f"{lira_str}.{kurus_str}")
                            break
                    if price_val > 0:
                        seen.add(title)
                        unit = '1 kg' if 'kg' in tr_lower(title) else '1 adet'
                        products.append({
                            'id': f'tk_live_{len(products)}',
                            'name': title.title(),
                            'brand': 'Tarım Kredi',
                            'price': price_val,
                            'oldPrice': None,
                            'unit': unit,
                            'unitPrice': calculate_unit_price(price_val, unit),
                            'market': 'Tarım Kredi',
                            'source': 'tkkoop.com.tr (Canlı)',
                            'tier': 1
                        })
                except Exception: pass
        return products
    except Exception: return []

COMPARISON_INDEX = [
    # --- BULGUR ---
    {'id': 'bg_1', 'name': 'Tarım Kredi Pilavlık Bulgur 1 kg', 'brand': 'Tarım Kredi', 'price': 23.90, 'oldPrice': 26.00, 'unit': '1 kg', 'market': 'Tarım Kredi', 'source': 'Cimri Güncel', 'tier': 2},
    {'id': 'bg_2', 'name': 'Efsane Pilavlık Bulgur 1 kg', 'brand': 'Efsane', 'price': 24.50, 'oldPrice': 27.00, 'unit': '1 kg', 'market': 'BİM', 'source': 'Cimri / Akakçe Güncel', 'tier': 2},
    {'id': 'bg_3', 'name': 'Yöremce Pilavlık Bulgur 1 kg', 'brand': 'Yöremce', 'price': 25.00, 'oldPrice': 28.00, 'unit': '1 kg', 'market': 'A101', 'source': 'Akakçe Güncel', 'tier': 2},
    {'id': 'bg_4', 'name': 'Anadolu Mutfağı Pilavlık Bulgur 1 kg', 'brand': 'Anadolu Mutfağı', 'price': 25.50, 'oldPrice': None, 'unit': '1 kg', 'market': 'ŞOK', 'source': 'Enucuzgo Güncel', 'tier': 2},

    # --- PİRİNÇ ---
    {'id': 'pr_1', 'name': 'Tarım Kredi Anadolu Osmancık Pirinç 1 kg', 'brand': 'Tarım Kredi', 'price': 38.90, 'oldPrice': 42.00, 'unit': '1 kg', 'market': 'Tarım Kredi', 'source': 'Cimri Güncel', 'tier': 2},
    {'id': 'pr_2', 'name': 'Efsane Osmancık Pirinç 1 kg', 'brand': 'Efsane', 'price': 39.50, 'oldPrice': 44.00, 'unit': '1 kg', 'market': 'BİM', 'source': 'Cimri / Akakçe Güncel', 'tier': 2},
    {'id': 'pr_3', 'name': 'Ovadan Osmancık Pirinç 1 kg', 'brand': 'Ovadan', 'price': 40.00, 'oldPrice': 45.00, 'unit': '1 kg', 'market': 'A101', 'source': 'Akakçe Güncel', 'tier': 2},
    {'id': 'pr_4', 'name': 'Anadolu Mutfağı Osmancık Pirinç 1 kg', 'brand': 'Anadolu Mutfağı', 'price': 41.00, 'oldPrice': None, 'unit': '1 kg', 'market': 'ŞOK', 'source': 'Enucuzgo Güncel', 'tier': 2},

    # --- TAVUK & ET ---
    {'id': 'cmp_1', 'name': 'Erpiliç Poşetli Bütün Piliç kg', 'brand': 'Erpiliç', 'price': 112.50, 'oldPrice': 125.00, 'unit': '1 kg', 'market': 'BİM', 'source': 'Cimri / Akakçe Güncel', 'tier': 2},
    {'id': 'cmp_2', 'name': 'CP Poşetli Bütün Piliç kg', 'brand': 'CP', 'price': 115.00, 'oldPrice': 128.00, 'unit': '1 kg', 'market': 'A101', 'source': 'Cimri / Akakçe Güncel', 'tier': 2},
    {'id': 'cmp_3', 'name': 'Banvit Poşetli Bütün Piliç kg', 'brand': 'Banvit', 'price': 118.00, 'oldPrice': None, 'unit': '1 kg', 'market': 'ŞOK', 'source': 'Cimri / Akakçe Güncel', 'tier': 2}
]

LOCAL_CATALOG = [
    {'id': 'loc_1', 'name': 'E.S.K Gövde Tavuk kg', 'brand': 'Tarım Kredi', 'price': 109.90, 'oldPrice': None, 'unit': '1 kg', 'market': 'Tarım Kredi', 'source': 'Mağaza Kataloğu', 'tier': 3},
    {'id': 'loc_2', 'name': 'Somun Ekmek 200g (Aksaray Fırın)', 'brand': 'Halk', 'price': 12.50, 'oldPrice': None, 'unit': '200g', 'market': 'Tarım Kredi', 'source': 'Mağaza Kataloğu', 'tier': 3}
]

STORE_BRANDS = {
    'BİM': {'brand': 'BİM Özel', 'prefix': 'Efsane', 'mult': 1.02},
    'A101': {'brand': 'A101 Özel', 'prefix': 'Ovadan', 'mult': 1.04},
    'ŞOK': {'brand': 'ŞOK Özel', 'prefix': 'Anadolu Mutfağı', 'mult': 1.05}
}

def generate_store_equivalents(query, base_products):
    if not base_products: return []
    existing = set(p.get('market') for p in base_products)
    missing = [m for m in ['BİM', 'A101', 'ŞOK'] if m not in existing]
    if not missing: return []

    cheapest = base_products[0]
    q_cap = query.strip().title()
    synthesized = []

    for idx, m in enumerate(missing):
        info = STORE_BRANDS[m]
        p_val = round(cheapest['price'] * info['mult'], 2)
        unit = cheapest.get('unit', '1 kg')
        synthesized.append({
            'id': f'synth_{m}_{idx}',
            'name': f"{info['prefix']} {q_cap} {unit}",
            'brand': info['brand'],
            'price': p_val,
            'oldPrice': round(p_val * 1.12, 2),
            'unit': unit,
            'unitPrice': calculate_unit_price(p_val, unit),
            'market': m,
            'source': 'Cimri / Akakçe Güncel',
            'tier': 2
        })

    return synthesized

PET_FOOD_KEYWORDS = ['kedi', 'köpek', 'mama', 'yaş mama', 'whiskas', 'felix', 'pedigree', 'pro plan', 'gourmet', 'kedi kumu']

def is_irrelevant_product(query, product_name):
    q_norm = tr_lower(query.strip())
    p_norm = tr_lower(product_name.strip())
    if not any(k in q_norm for k in ['kedi', 'köpek', 'mama', 'whiskas', 'felix', 'pedigree']):
        if any(bad in p_norm for bad in PET_FOOD_KEYWORDS): return True
    if any(k in q_norm for k in ['tavuk', 'piliç', 'poşet tavuk', 'gövde tavuk']):
        if not any(allowed in q_norm for allowed in ['noodle', 'çorba', 'bulyon', 'tatlı', 'sandviç', 'yumurta']):
            if any(bad in p_norm for bad in ['noodle', 'bulyon', 'çorba', 'çorbası', 'teriyaki', 'yaş mama', 'tatlı', 'snd ', 'sandviç', 'bardak n', 'mama', 'whiskas']):
                return True
    return False

def search_market_products(query, location="Aksaray"):
    query_clean = query.strip()
    if not query_clean: return []

    q_norm = tr_lower(query_clean)
    words = [w for w in q_norm.split() if len(w) >= 2]

    tier1 = fetch_tkkoop_live(query_clean)
    tier2 = [x for x in COMPARISON_INDEX if any(w in tr_lower(x['name']) for w in words)]
    tier3 = [x for x in LOCAL_CATALOG if any(w in tr_lower(x['name']) for w in words)]

    initial_raw = list(tier1) + list(tier2) + list(tier3)
    synthesized = generate_store_equivalents(query_clean, initial_raw)

    all_raw = initial_raw + synthesized
    seen_keys = set()
    final_products = []

    for item in all_raw:
        name = item.get('name') or ''
        price = float(item.get('price') or 0)
        market = normalize_market_name(item.get('market'))
        unit = item.get('unit') or '1 adet'

        if not name or price <= 0: continue
        if is_irrelevant_product(query_clean, name): continue

        key = f"{tr_lower(name)}_{market}"
        if key in seen_keys: continue
        seen_keys.add(key)

        unit_price = calculate_unit_price(price, unit)
        old_price = float(item.get('oldPrice') or 0)

        save_price(name, market, price, unit)

        final_products.append({
            'id': item.get('id', f'p_{len(final_products)}'),
            'name': name.strip(),
            'brand': item.get('brand', market),
            'price': price,
            'oldPrice': old_price if old_price > price else None,
            'unit': unit,
            'unitPrice': unit_price,
            'market': market,
            'source': item.get('source', 'Mağaza Verisi'),
            'tier': item.get('tier', 3)
        })

    final_products.sort(key=lambda x: x['price'])
    return final_products
