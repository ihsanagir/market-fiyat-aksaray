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
    import unicodedata
    s = text.replace('İ', 'i').replace('I', 'ı').replace('Ş', 'ş').replace('Ğ', 'ğ').replace('Ü', 'ü').replace('Ö', 'ö').replace('Ç', 'ç')
    s = unicodedata.normalize('NFD', s)
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()

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

AUTHENTIC_MARKET_DATABASE = [
    # --- ZEYTİN (YEŞİL & SİYAH) ---
    {'id': 'zy_g1', 'name': 'Tarım Kredi Kırma Yeşil Zeytin 400g', 'brand': 'Tarım Kredi', 'price': 64.50, 'oldPrice': 72.00, 'unit': '400g', 'market': 'Tarım Kredi', 'source': 'Cimri Güncel', 'tier': 2},
    {'id': 'zy_g2', 'name': 'İnci Çizik Yeşil Zeytin 400g', 'brand': 'İnci', 'price': 65.00, 'oldPrice': 74.00, 'unit': '400g', 'market': 'BİM', 'source': 'Cimri Güncel', 'tier': 2},
    {'id': 'zy_g3', 'name': 'İnci Biberli Yeşil Zeytin 400g', 'brand': 'İnci', 'price': 68.50, 'oldPrice': 78.00, 'unit': '400g', 'market': 'BİM', 'source': 'Akakçe Güncel', 'tier': 2},
    {'id': 'zy_g4', 'name': 'Zeo Kırma Yeşil Zeytin 400g', 'brand': 'Zeo', 'price': 69.00, 'oldPrice': 79.00, 'unit': '400g', 'market': 'A101', 'source': 'Akakçe Güncel', 'tier': 2},
    {'id': 'zy_g5', 'name': 'Lio Çizik Yeşil Zeytin 400g', 'brand': 'Lio', 'price': 69.50, 'oldPrice': None, 'unit': '400g', 'market': 'ŞOK', 'source': 'Enucuzgo Güncel', 'tier': 2},
    {'id': 'zy_g6', 'name': 'Zeo Biberli Yeşil Zeytin 400g', 'brand': 'Zeo', 'price': 70.00, 'oldPrice': 80.00, 'unit': '400g', 'market': 'A101', 'source': 'Akakçe Güncel', 'tier': 2},
    {'id': 'zy_g7', 'name': 'Lio Biberli Yeşil Zeytin 400g', 'brand': 'Lio', 'price': 71.00, 'oldPrice': None, 'unit': '400g', 'market': 'ŞOK', 'source': 'Enucuzgo Güncel', 'tier': 2},

    {'id': 'zy_s1', 'name': 'Tarım Kredi Yağlı Sele Siyah Zeytin 500g', 'brand': 'Tarım Kredi', 'price': 92.00, 'oldPrice': 105.00, 'unit': '500g', 'market': 'Tarım Kredi', 'source': 'Cimri Güncel', 'tier': 2},
    {'id': 'zy_s2', 'name': 'İnci Doğal Sele Siyah Zeytin 500g', 'brand': 'İnci', 'price': 95.00, 'oldPrice': 108.00, 'unit': '500g', 'market': 'BİM', 'source': 'Cimri Güncel', 'tier': 2},
    {'id': 'zy_s3', 'name': 'Zeo Siyah Zeytin 500g', 'brand': 'Zeo', 'price': 96.00, 'oldPrice': 110.00, 'unit': '500g', 'market': 'A101', 'source': 'Akakçe Güncel', 'tier': 2},
    {'id': 'zy_s4', 'name': 'Lio Siyah Zeytin 500g', 'brand': 'Lio', 'price': 97.00, 'oldPrice': None, 'unit': '500g', 'market': 'ŞOK', 'source': 'Enucuzgo Güncel', 'tier': 2},

    # --- YAĞLAR ---
    {'id': 'yg_1', 'name': 'Tarım Kredi Anadolu Ayçiçek Yağı 5L', 'brand': 'Tarım Kredi', 'price': 445.00, 'oldPrice': 475.00, 'unit': '5L', 'market': 'Tarım Kredi', 'source': 'Cimri / Akakçe Güncel', 'tier': 2},
    {'id': 'yg_2', 'name': 'Sole Ayçiçek Yağı 5L', 'brand': 'Sole', 'price': 455.00, 'oldPrice': 485.00, 'unit': '5L', 'market': 'BİM', 'source': 'Cimri / Akakçe Güncel', 'tier': 2},
    {'id': 'yg_3', 'name': 'Evin Ayçiçek Yağı 5L', 'brand': 'Evin', 'price': 458.00, 'oldPrice': None, 'unit': '5L', 'market': 'ŞOK', 'source': 'Enucuzgo Güncel', 'tier': 2},
    {'id': 'yg_4', 'name': 'Vera Ayçiçek Yağı 5L', 'brand': 'Vera', 'price': 459.00, 'oldPrice': 490.00, 'unit': '5L', 'market': 'A101', 'source': 'Akakçe Güncel', 'tier': 2}
]

PET_FOOD_KEYWORDS = ['kedi', 'köpek', 'mama', 'yaş mama', 'whiskas', 'felix', 'pedigree', 'pro plan', 'gourmet', 'kedi kumu']

def is_irrelevant_product(query, product_name):
    q_norm = tr_lower(query.strip())
    p_norm = tr_lower(product_name.strip())
    if not any(k in q_norm for k in ['kedi', 'köpek', 'mama', 'whiskas', 'felix', 'pedigree']):
        if any(bad in p_norm for bad in PET_FOOD_KEYWORDS): return True

    if 'zeytin' in q_norm and 'yag' not in q_norm and 'yağ' not in q_norm:
        if any(bad in p_norm for bad in ['zeytinyağ', 'yağı', 'yagi']):
            return True
    return False

def search_market_products(query, location="Aksaray"):
    query_clean = query.strip()
    if not query_clean: return []

    q_norm = tr_lower(query_clean)
    words = [w for w in q_norm.split() if len(w) >= 2]

    tier1 = fetch_tkkoop_live(query_clean)
    authentic_matches = [x for x in AUTHENTIC_MARKET_DATABASE if all(w in tr_lower(x['name']) for w in words)]

    all_raw = list(tier1) + authentic_matches
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
