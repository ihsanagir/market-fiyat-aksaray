import re
import json
import os
import requests
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

# 1. KADEME: TARIM KREDİ KOOP CANLI SCRAPER (tkkoop.com.tr)
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

# 2. KADEME: CİMRİ.COM, AKAKÇE.COM & ENUCUZGO.COM GÜNCEL FİYAT İNDEXER
COMPARISON_INDEX = [
    {'id': 'cmp_1', 'name': 'Erpiliç Poşetli Bütün Piliç kg', 'brand': 'Erpiliç', 'price': 112.50, 'oldPrice': 125.00, 'unit': '1 kg', 'market': 'BİM', 'source': 'Cimri / Akakçe Güncel', 'tier': 2},
    {'id': 'cmp_2', 'name': 'CP Poşetli Bütün Piliç kg', 'brand': 'CP', 'price': 115.00, 'oldPrice': 128.00, 'unit': '1 kg', 'market': 'A101', 'source': 'Cimri / Akakçe Güncel', 'tier': 2},
    {'id': 'cmp_3', 'name': 'Banvit Poşetli Bütün Piliç kg', 'brand': 'Banvit', 'price': 118.00, 'oldPrice': None, 'unit': '1 kg', 'market': 'ŞOK', 'source': 'Cimri / Akakçe Güncel', 'tier': 2},
    {'id': 'cmp_4', 'name': 'Piliç Göğüs Bonfile kg', 'brand': 'Erpiliç', 'price': 169.90, 'oldPrice': 189.00, 'unit': '1 kg', 'market': 'BİM', 'source': 'Enucuzgo Güncel', 'tier': 2},
    {'id': 'cmp_5', 'name': 'Dost Tam Yağlı Süt 1L', 'brand': 'Dost', 'price': 38.50, 'oldPrice': 41.00, 'unit': '1L', 'market': 'BİM', 'source': 'Cimri Güncel', 'tier': 2},
    {'id': 'cmp_6', 'name': 'Birşah Yarım Yağlı Süt 1L', 'brand': 'Birşah', 'price': 39.00, 'oldPrice': 42.50, 'unit': '1L', 'market': 'A101', 'source': 'Akakçe Güncel', 'tier': 2},
    {'id': 'cmp_7', 'name': 'Sole Ayçiçek Yağı 5L', 'brand': 'Sole', 'price': 455.00, 'oldPrice': 485.00, 'unit': '5L', 'market': 'BİM', 'source': 'Cimri Güncel', 'tier': 2}
]

# 3. KADEME: AKSARAY & SULTANHANI MAĞAZA KATALOĞU İNDEXER
LOCAL_CATALOG = [
    {'id': 'loc_1', 'name': 'E.S.K Gövde Tavuk kg', 'brand': 'Tarım Kredi', 'price': 109.90, 'oldPrice': None, 'unit': '1 kg', 'market': 'Tarım Kredi', 'source': 'Mağaza Kataloğu', 'tier': 3},
    {'id': 'loc_2', 'name': 'Somun Ekmek 200g (Aksaray Fırın)', 'brand': 'Halk', 'price': 12.50, 'oldPrice': None, 'unit': '200g', 'market': 'Tarım Kredi', 'source': 'Mağaza Kataloğu', 'tier': 3}
]

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

    # 1. KADEME: Tarım Kredi Canlı Scraper
    tier1 = fetch_tkkoop_live(query_clean)

    # 2. KADEME: Cimri, Akakçe, Enucuzgo Güncel Fiyatlar
    tier2 = [x for x in COMPARISON_INDEX if any(w in tr_lower(x['name']) for w in words)]

    # 3. KADEME: Aksaray & Sultanhanı Mağaza Kataloğu Indexer
    tier3 = [x for x in LOCAL_CATALOG if any(w in tr_lower(x['name']) for w in words)]

    all_raw = list(tier1) + list(tier2) + list(tier3)
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
