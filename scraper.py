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

def get_price_history(product_name):
    init_db()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        query = tr_lower(product_name.strip())
        filtered = [item for item in data if query in tr_lower(item["product_name"])]
        return filtered[-50:]
    except Exception as e:
        print(f"DB get error: {e}")
        return []

def tr_lower(text):
    if not text:
        return ''
    mapping = {'İ': 'i', 'I': 'ı', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç', '\u0307': ''}
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text.lower()

MARKET_NAME_MAP = {
    'bim': 'BİM',
    'a101': 'A101',
    'şok': 'ŞOK',
    'sok': 'ŞOK',
    'tarimkredi': 'Tarım Kredi',
    'tarım kredi': 'Tarım Kredi',
    'tarim kredi': 'Tarım Kredi',
    'koop': 'Tarım Kredi',
}

def normalize_market_name(name):
    if not name:
        return 'Tarım Kredi'
    lower = tr_lower(name).replace(" ", "")
    for key, val in MARKET_NAME_MAP.items():
        if key in lower:
            return val
    return name

def calculate_unit_price(price, unit):
    if not unit:
        return None
    lower = tr_lower(unit)
    
    gr_match = re.search(r'(\d+(?:[.,]\d+)?)\s*g\b', lower)
    if gr_match:
        g = float(gr_match.group(1).replace(',', '.'))
        if g > 0:
            return {"value": round((price / g) * 1000, 2), "label": "₺/kg"}
            
    kg_match = re.search(r'(\d+(?:[.,]\d+)?)\s*kg', lower)
    if kg_match:
        kg = float(kg_match.group(1).replace(',', '.'))
        if kg > 0:
            return {"value": round(price / kg, 2), "label": "₺/kg"}
            
    ml_match = re.search(r'(\d+(?:[.,]\d+)?)\s*ml', lower)
    if ml_match:
        ml = float(ml_match.group(1).replace(',', '.'))
        if ml > 0:
            return {"value": round((price / ml) * 1000, 2), "label": "₺/L"}
            
    lt_match = re.search(r'(\d+(?:[.,]\d+)?)\s*l\b', lower)
    if lt_match:
        lt = float(lt_match.group(1).replace(',', '.'))
        if lt > 0:
            return {"value": round(price / lt, 2), "label": "₺/L"}
            
    return None

def fetch_tkkoop_live(query):
    """Tarım Kredi Kooperatif Market (tkkoop.com.tr) Canlı Resmi Web Kazıma Motoru"""
    try:
        url = f'https://www.tkkoop.com.tr/arama?ara={requests.utils.quote(query)}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        response = requests.get(url, headers=headers, timeout=6)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        seen = set()

        for card in soup.find_all('div', class_=lambda c: c and ('col' in c or 'product' in c or 'card' in c or 'box' in c)):
            strings = [t.strip() for t in card.stripped_strings if len(t.strip()) > 0]
            if any('TL' in s for s in strings) and len(strings) in [3, 4, 5]:
                title = strings[0]
                if title in seen or len(title) <= 2 or 'TL' in title:
                    continue

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
                        
                        unit = '1 adet'
                        t_low = tr_lower(title)
                        if 'kg' in t_low: unit = '1 kg'
                        elif ' 1l' in t_low or ' 1 l' in t_low or 'litre' in t_low: unit = '1L'
                        elif '30 lu' in t_low or '30lu' in t_low: unit = '30lu'
                        elif '10 lu' in t_low or '10lu' in t_low: unit = '10lu'
                        elif '5 kg' in t_low or '5kg' in t_low: unit = '5 kg'

                        products.append({
                            'id': f'tk_live_{len(products)}',
                            'name': title.title(),
                            'brand': 'Tarım Kredi',
                            'price': price_val,
                            'oldPrice': None,
                            'unit': unit,
                            'unitPrice': calculate_unit_price(price_val, unit),
                            'market': 'Tarım Kredi',
                            'discount': 0
                        })
                except Exception:
                    pass

        return products
    except Exception as e:
        print(f"TK KOOP Live Scraping Error: {e}")
        return []

REAL_CATALOG = [
    # --- TAVUK & ET ---
    {'id': 'tv1', 'name': 'E.S.K Gövde Tavuk kg', 'brand': 'Tarım Kredi', 'price': 109.90, 'oldPrice': None, 'unit': '1 kg', 'market': 'Tarım Kredi', 'tags': ['tavuk', 'piliç', 'gövde tavuk', 'bütün tavuk', 'poşet tavuk', 'poşetli tavuk']},
    {'id': 'tv2', 'name': 'Erpiliç Poşetli Bütün Piliç kg', 'brand': 'Erpiliç', 'price': 112.50, 'oldPrice': 125.00, 'unit': '1 kg', 'market': 'BİM', 'tags': ['tavuk', 'piliç', 'bütün tavuk', 'poşet tavuk', 'poşetli tavuk', 'poşetli piliç']},
    {'id': 'tv3', 'name': 'CP Poşetli Bütün Piliç kg', 'brand': 'CP', 'price': 115.00, 'oldPrice': 128.00, 'unit': '1 kg', 'market': 'A101', 'tags': ['tavuk', 'piliç', 'bütün tavuk', 'poşet tavuk', 'poşetli tavuk', 'poşetli piliç']},
    {'id': 'tv4', 'name': 'Banvit Poşetli Bütün Piliç kg', 'brand': 'Banvit', 'price': 118.00, 'oldPrice': None, 'unit': '1 kg', 'market': 'ŞOK', 'tags': ['tavuk', 'piliç', 'bütün tavuk', 'poşet tavuk', 'poşetli tavuk', 'poşetli piliç']},
    {'id': 'tv5', 'name': 'Köytav Poşetli Gezen Tavuk kg', 'brand': 'Köytav', 'price': 419.00, 'oldPrice': None, 'unit': '1 kg', 'market': 'Tarım Kredi', 'tags': ['tavuk', 'gezen tavuk', 'poşet tavuk']},
    {'id': 'tv6', 'name': 'Erp Tavuk Nugget 300g', 'brand': 'Erpiliç', 'price': 135.00, 'oldPrice': 149.00, 'unit': '300g', 'market': 'Tarım Kredi', 'tags': ['tavuk', 'nugget']},
    {'id': 'tv7', 'name': 'Erp Tavuk Schnitzel 300g', 'brand': 'Erpiliç', 'price': 135.00, 'oldPrice': None, 'unit': '300g', 'market': 'Tarım Kredi', 'tags': ['tavuk', 'schnitzel']},
    {'id': 'tv8', 'name': 'Erp Tavuk Cordon Bleu 300g', 'brand': 'Erpiliç', 'price': 155.00, 'oldPrice': 175.00, 'unit': '300g', 'market': 'Tarım Kredi', 'tags': ['tavuk', 'cordon bleu']},
    {'id': 'tv9', 'name': 'Piliç Göğüs Bonfile kg', 'brand': 'Erpiliç', 'price': 169.90, 'oldPrice': 189.00, 'unit': '1 kg', 'market': 'BİM', 'tags': ['tavuk', 'bonfile', 'göğüs']},
    {'id': 'tv10', 'name': 'Piliç Pirzola kg', 'brand': 'Banvit', 'price': 178.00, 'oldPrice': None, 'unit': '1 kg', 'market': 'ŞOK', 'tags': ['tavuk', 'pirzola']},

    {'id': 'et1', 'name': 'Tarım Kredi Dana Kıyma 500g', 'brand': 'Tarım Kredi', 'price': 185.00, 'oldPrice': None, 'unit': '500g', 'market': 'Tarım Kredi', 'tags': ['kıyma', 'dana kıyma', 'et']},
    {'id': 'et2', 'name': 'Emin Dana Kıyma 500g', 'brand': 'Emin', 'price': 189.00, 'oldPrice': 210.00, 'unit': '500g', 'market': 'BİM', 'tags': ['kıyma', 'dana kıyma', 'et']},
    {'id': 'et3', 'name': 'Kombinet Dana Kıyma 500g', 'brand': 'Kombinet', 'price': 192.00, 'oldPrice': None, 'unit': '500g', 'market': 'A101', 'tags': ['kıyma', 'dana kıyma', 'et']},

    {'id': 'sc1', 'name': 'Baştacı Kasap Sucuk 400g', 'brand': 'Baştacı', 'price': 145.00, 'oldPrice': 165.00, 'unit': '400g', 'market': 'BİM', 'tags': ['sucuk', 'kasap sucuk']},
    {'id': 'sc2', 'name': 'Tarım Kredi Doyum Dana Sucuk 400g', 'brand': 'Tarım Kredi', 'price': 142.00, 'oldPrice': None, 'unit': '400g', 'market': 'Tarım Kredi', 'tags': ['sucuk']},

    # --- SÜT & YUMURTA & PEYNİR ---
    {'id': 'y1', 'name': 'TK Gezen Tavuk Yumurta 10 lu', 'brand': 'Tarım Kredi', 'price': 95.00, 'oldPrice': None, 'unit': '10 lu', 'market': 'Tarım Kredi', 'tags': ['yumurta', 'gezen tavuk yumurta']},
    {'id': 'y2', 'name': 'Tarım Kredi M Boy Yumurta 30lu', 'brand': 'Tarım Kredi', 'price': 135.00, 'oldPrice': None, 'unit': '30lu', 'market': 'Tarım Kredi', 'tags': ['yumurta', '30lu yumurta']},
    {'id': 'y3', 'name': 'Bili Bili L Boy Yumurta 30lu', 'brand': 'Bili Bili', 'price': 138.00, 'oldPrice': 155.00, 'unit': '30lu', 'market': 'BİM', 'tags': ['yumurta', '30lu yumurta']},
    {'id': 'y4', 'name': 'Keskinoğlu L Boy Yumurta 30lu', 'brand': 'Keskinoğlu', 'price': 140.00, 'oldPrice': 158.00, 'unit': '30lu', 'market': 'A101', 'tags': ['yumurta', '30lu yumurta']},
    {'id': 'y5', 'name': 'CP L Boy Yumurta 30lu', 'brand': 'CP', 'price': 142.00, 'oldPrice': 160.00, 'unit': '30lu', 'market': 'ŞOK', 'tags': ['yumurta', '30lu yumurta']},

    {'id': 's1', 'name': 'Tarım Kredi Yağlı Süt 1L', 'brand': 'Tarım Kredi', 'price': 38.00, 'oldPrice': None, 'unit': '1L', 'market': 'Tarım Kredi', 'tags': ['süt', 'tam yağlı süt']},
    {'id': 's2', 'name': 'Dost Tam Yağlı Süt 1L', 'brand': 'Dost', 'price': 38.50, 'oldPrice': 41.00, 'unit': '1L', 'market': 'BİM', 'tags': ['süt']},
    {'id': 's3', 'name': 'Birşah Yarım Yağlı Süt 1L', 'brand': 'Birşah', 'price': 39.00, 'oldPrice': 42.50, 'unit': '1L', 'market': 'A101', 'tags': ['süt']},
    {'id': 's4', 'name': 'Mis Tam Yağlı Süt 1L', 'brand': 'Mis', 'price': 39.50, 'oldPrice': None, 'unit': '1L', 'market': 'ŞOK', 'tags': ['süt']},

    {'id': 'p1', 'name': 'Tarım Kredi Tam Yağlı Peynir 1 kg', 'brand': 'Tarım Kredi', 'price': 158.00, 'oldPrice': None, 'unit': '1 kg', 'market': 'Tarım Kredi', 'tags': ['peynir', 'beyaz peynir']},
    {'id': 'p2', 'name': 'Ahir Tam Yağlı Taze Peynir 1 kg', 'brand': 'Ahir', 'price': 160.00, 'oldPrice': 179.00, 'unit': '1 kg', 'market': 'A101', 'tags': ['peynir', 'beyaz peynir']},
    {'id': 'p3', 'name': 'Mis Tam Yağlı Beyaz Peynir 1 kg', 'brand': 'Mis', 'price': 162.50, 'oldPrice': None, 'unit': '1 kg', 'market': 'ŞOK', 'tags': ['peynir', 'beyaz peynir']},
    {'id': 'p4', 'name': 'Kaanlar Süzme Peynir 1 kg', 'brand': 'Kaanlar', 'price': 165.00, 'oldPrice': 185.00, 'unit': '1 kg', 'market': 'BİM', 'tags': ['peynir', 'süzme peynir']},
    {'id': 'p5', 'name': 'Tarım Kredi Kaşar Peyniri 1 kg', 'brand': 'Tarım Kredi', 'price': 230.00, 'oldPrice': None, 'unit': '1 kg', 'market': 'Tarım Kredi', 'tags': ['peynir', 'kaşar', 'kaşar peyniri']},
    {'id': 'p6', 'name': 'Akyazıcı Taze Kaşar Peyniri 1 kg', 'brand': 'Akyazıcı', 'price': 235.00, 'oldPrice': 265.00, 'unit': '1 kg', 'market': 'BİM', 'tags': ['peynir', 'kaşar', 'kaşar peyniri']},

    # --- TEMEL GIDA & YAĞ ---
    {'id': 'sk1', 'name': 'Tarım Kredi Toz Şeker 5 kg', 'brand': 'Tarım Kredi', 'price': 225.00, 'oldPrice': None, 'unit': '5 kg', 'market': 'Tarım Kredi', 'tags': ['şeker', 'toz şeker']},
    {'id': 'sk2', 'name': 'Balkan Toz Şeker 5 kg', 'brand': 'Balkan', 'price': 228.00, 'oldPrice': 245.00, 'unit': '5 kg', 'market': 'BİM', 'tags': ['şeker', 'toz şeker']},
    {'id': 'sk3', 'name': 'Petek Toz Şeker 5 kg', 'brand': 'Petek', 'price': 229.00, 'oldPrice': 249.00, 'unit': '5 kg', 'market': 'A101', 'tags': ['şeker', 'toz şeker']},
    {'id': 'sk4', 'name': 'Bor Şeker Toz Şeker 5 kg', 'brand': 'Bor', 'price': 230.00, 'oldPrice': None, 'unit': '5 kg', 'market': 'ŞOK', 'tags': ['şeker', 'toz şeker']},

    {'id': 'zy1', 'name': 'Tarım Kredi Sızma Zeytinyağı 1L', 'brand': 'Tarım Kredi', 'price': 340.00, 'oldPrice': 365.00, 'unit': '1L', 'market': 'Tarım Kredi', 'tags': ['zeytinyağı', 'sızma zeytinyağı', 'yağ']},
    {'id': 'zy2', 'name': 'Kırlangıç Riviera Zeytinyağı 1L', 'brand': 'Kırlangıç', 'price': 355.00, 'oldPrice': None, 'unit': '1L', 'market': 'BİM', 'tags': ['zeytinyağı', 'yağ']},
    {'id': 'zy3', 'name': 'Yudum Ege Sızma Zeytinyağı 1L', 'brand': 'Yudum', 'price': 360.00, 'oldPrice': 390.00, 'unit': '1L', 'market': 'ŞOK', 'tags': ['zeytinyağı', 'yağ']},

    {'id': 'ay1', 'name': 'Tarım Kredi Ayçiçek Yağı 5L', 'brand': 'Tarım Kredi', 'price': 449.00, 'oldPrice': None, 'unit': '5L', 'market': 'Tarım Kredi', 'tags': ['yağ', 'ayçiçek yağı', 'sıvı yağ']},
    {'id': 'ay2', 'name': 'Sole Ayçiçek Yağı 5L', 'brand': 'Sole', 'price': 455.00, 'oldPrice': 485.00, 'unit': '5L', 'market': 'BİM', 'tags': ['yağ', 'ayçiçek yağı', 'sıvı yağ']},
    {'id': 'ay3', 'name': 'Evin Ayçiçek Yağı 5L', 'brand': 'Evin', 'price': 458.00, 'oldPrice': None, 'unit': '5L', 'market': 'ŞOK', 'tags': ['yağ', 'ayçiçek yağı', 'sıvı yağ']},
    {'id': 'ay4', 'name': 'Vera Ayçiçek Yağı 5L', 'brand': 'Vera', 'price': 459.00, 'oldPrice': 490.00, 'unit': '5L', 'market': 'A101', 'tags': ['yağ', 'ayçiçek yağı', 'sıvı yağ']},

    {'id': 'e1', 'name': 'Somun Ekmek 200g (Aksaray Fırın)', 'brand': 'Halk', 'price': 12.50, 'oldPrice': None, 'unit': '200g', 'market': 'Tarım Kredi', 'tags': ['ekmek', 'somun ekmek']},
    {'id': 'e2', 'name': 'Kepekli Ekmek 350g', 'brand': 'Destan', 'price': 16.50, 'oldPrice': None, 'unit': '350g', 'market': 'BİM', 'tags': ['ekmek']},
]

PET_FOOD_KEYWORDS = ['kedi', 'köpek', 'mama', 'yaş mama', 'whiskas', 'felix', 'pedigree', 'pro plan', 'gourmet', 'konserve mama', 'kedi kumu']

def is_irrelevant_product(query, product_name):
    q_norm = tr_lower(query.strip())
    p_norm = tr_lower(product_name.strip())

    if not any(k in q_norm for k in ['kedi', 'köpek', 'mama', 'whiskas', 'felix', 'pedigree']):
        if any(bad in p_norm for bad in PET_FOOD_KEYWORDS):
            return True

    if any(k in q_norm for k in ['tavuk', 'piliç', 'poşet tavuk', 'gövde tavuk']):
        if not any(allowed in q_norm for allowed in ['noodle', 'çorba', 'bulyon', 'tatlı', 'sandviç', 'yumurta']):
            if any(bad in p_norm for bad in ['noodle', 'bulyon', 'çorba', 'çorbası', 'teriyaki', 'yaş mama', 'tatlı', 'tavukgöğsü +', 'snd ', 'sandviç', 'bulyon 12', 'bardak n', 'mama', 'whiskas', 'felix']):
                return True

    return False

def search_real_catalog(query):
    q_norm = tr_lower(query.strip())
    words = [w for w in q_norm.split() if len(w) >= 2]
    if not words:
        return []

    matched = []
    for item in REAL_CATALOG:
        name_norm = tr_lower(item['name'])
        brand_norm = tr_lower(item['brand'])
        tags_norm = [tr_lower(t) for t in item.get('tags', [])]

        score = 0
        for w in words:
            if w in name_norm:
                score += 3
            if w in brand_norm:
                score += 2
            if any(w in t for t in tags_norm):
                score += 4

        if score > 0:
            matched.append((score, item))

    matched.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in matched]

def search_market_products(query, location="Aksaray"):
    query_clean = query.strip()
    if not query_clean:
        return []

    live_tk_products = fetch_tkkoop_live(query_clean)
    catalog_products = search_real_catalog(query_clean)

    all_raw = list(live_tk_products) + list(catalog_products)
    seen_keys = set()
    final_products = []

    for item in all_raw:
        name = item.get('name') or ''
        price = float(item.get('price') or 0)
        market = normalize_market_name(item.get('market'))
        unit = item.get('unit') or '1 adet'

        if not name or price <= 0:
            continue

        if is_irrelevant_product(query_clean, name):
            continue

        key = f"{tr_lower(name)}_{market}"
        if key in seen_keys:
            continue
        seen_keys.add(key)

        unit_price = calculate_unit_price(price, unit)
        old_price = float(item.get('oldPrice') or 0)
        discount = round(((old_price - price) / old_price) * 100) if old_price > price else 0

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
            'discount': discount
        })

    final_products.sort(key=lambda x: x['price'])
    return final_products
