import { NextResponse } from 'next/server';
import axios from 'axios';
import * as cheerio from 'cheerio';

// Türkçe Harf Normalizasyonu
function trLower(text) {
  if (!text) return '';
  const mapping = { 'İ': 'i', 'I': 'ı', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç', '\u0307': '' };
  let str = text;
  for (const [k, v] of Object.entries(mapping)) {
    str = str.replaceAll(k, v);
  }
  return str.toLowerCase();
}

// Market İsim Normalizasyonu
function normalizeMarketName(name) {
  if (!name) return 'Tarım Kredi';
  const lower = trLower(name).replace(/\s+/g, '');
  if (lower.includes('bim')) return 'BİM';
  if (lower.includes('a101')) return 'A101';
  if (lower.includes('sok') || lower.includes('şok')) return 'ŞOK';
  if (lower.includes('tarim') || lower.includes('koop')) return 'Tarım Kredi';
  return name;
}

// Birim Fiyat Hesaplama (₺/kg veya ₺/L)
function calculateUnitPrice(price, unit) {
  if (!unit) return null;
  const lower = trLower(unit);

  const grMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*g\b/);
  if (grMatch) {
    const g = parseFloat(grMatch[1].replace(',', '.'));
    if (g > 0) return { value: Number(((price / g) * 1000).toFixed(2)), label: '₺/kg' };
  }

  const kgMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*kg/);
  if (kgMatch) {
    const kg = parseFloat(kgMatch[1].replace(',', '.'));
    if (kg > 0) return { value: Number((price / kg).toFixed(2)), label: '₺/kg' };
  }

  const mlMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*ml/);
  if (mlMatch) {
    const ml = parseFloat(mlMatch[1].replace(',', '.'));
    if (ml > 0) return { value: Number(((price / ml) * 1000).toFixed(2)), label: '₺/L' };
  }

  const ltMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*l\b/);
  if (ltMatch) {
    const lt = parseFloat(ltMatch[1].replace(',', '.'));
    if (lt > 0) return { value: Number((price / lt).toFixed(2)), label: '₺/L' };
  }

  return null;
}

// Akıllı Alakasız Ürün Filtresi (Kedi Maması / Noodle / Bulyon Engelleme)
const PET_FOOD_KEYWORDS = ['kedi', 'köpek', 'mama', 'yaş mama', 'whiskas', 'felix', 'pedigree', 'pro plan', 'gourmet', 'konserve mama', 'kedi kumu'];

function isIrrelevantProduct(query, productName) {
  const qNorm = trLower(query.trim());
  const pNorm = trLower(productName.trim());

  // 1. Evcil hayvan maması engeli
  if (!['kedi', 'köpek', 'mama', 'whiskas', 'felix', 'pedigree'].some(k => qNorm.includes(k))) {
    if (PET_FOOD_KEYWORDS.some(bad => pNorm.includes(bad))) return true;
  }

  // 2. Tavuk aramalarında Noodle, Bulyon, Çorba, Sandviç engeli
  if (['tavuk', 'piliç', 'poşet tavuk', 'gövde tavuk'].some(k => qNorm.includes(k))) {
    if (!['noodle', 'çorba', 'bulyon', 'tatlı', 'sandviç', 'yumurta'].some(a => qNorm.includes(a))) {
      if (['noodle', 'bulyon', 'çorba', 'çorbası', 'teriyaki', 'yaş mama', 'tatlı', 'snd ', 'sandviç', 'bardak n', 'mama', 'whiskas'].some(bad => pNorm.includes(bad))) {
        return true;
      }
    }
  }

  return false;
}

// Canlı Tarım Kredi Scraping (tkkoop.com.tr)
async function fetchTkKoopLive(query) {
  try {
    const url = `https://www.tkkoop.com.tr/arama?ara=${encodeURIComponent(query)}`;
    const response = await axios.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
      },
      timeout: 5000
    });

    if (response.status !== 200) return [];

    const $ = cheerio.load(response.data);
    const products = [];
    const seen = new Set();

    $('div').each((_, elem) => {
      const text = $(elem).text().trim();
      const strings = text.split('\n').map(s => s.trim()).filter(s => s.length > 0);
      if (strings.some(s => s === 'TL') && strings.length >= 3 && strings.length <= 6) {
        const title = strings[0];
        if (!title || seen.has(title) || title.length <= 2 || title.includes('TL')) return;

        let priceVal = 0;
        for (let i = 0; i < strings.length; i++) {
          if (strings[i] === 'TL' && i >= 2) {
            const liraStr = strings[i - 2].replace(/[,.]/g, '');
            const kurusStr = strings[i - 1].replace(/[,.]/g, '');
            priceVal = parseFloat(`${liraStr}.${kurusStr}`);
            break;
          }
        }

        if (priceVal > 0) {
          seen.add(title);
          let unit = '1 adet';
          const tLow = trLower(title);
          if (tLow.includes('kg')) unit = '1 kg';
          else if (tLow.includes('1l') || tLow.includes('litre')) unit = '1L';
          else if (tLow.includes('30 lu') || tLow.includes('30lu')) unit = '30lu';
          else if (tLow.includes('10 lu') || tLow.includes('10lu')) unit = '10lu';
          else if (tLow.includes('5 kg') || tLow.includes('5kg')) unit = '5 kg';

          products.append ? null : products.push({
            id: `tk_live_${products.length}`,
            name: title.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' '),
            brand: 'Tarım Kredi',
            price: priceVal,
            oldPrice: null,
            unit: unit,
            unitPrice: calculateUnitPrice(priceVal, unit),
            market: 'Tarım Kredi',
            discount: 0
          });
        }
      }
    });

    return products;
  } catch (e) {
    console.error('TK Live Scrape Error:', e.message);
    return [];
  }
}

// Ağustos 2026 Güncel Mağaza Kataloğu
const REAL_CATALOG = [
  // --- TAVUK & ET ---
  { id: 'tv1', name: 'E.S.K Gövde Tavuk kg', brand: 'Tarım Kredi', price: 109.90, oldPrice: null, unit: '1 kg', market: 'Tarım Kredi' },
  { id: 'tv2', name: 'Erpiliç Poşetli Bütün Piliç kg', brand: 'Erpiliç', price: 112.50, oldPrice: 125.00, unit: '1 kg', market: 'BİM' },
  { id: 'tv3', name: 'CP Poşetli Bütün Piliç kg', brand: 'CP', price: 115.00, oldPrice: 128.00, unit: '1 kg', market: 'A101' },
  { id: 'tv4', name: 'Banvit Poşetli Bütün Piliç kg', brand: 'Banvit', price: 118.00, oldPrice: null, unit: '1 kg', market: 'ŞOK' },
  { id: 'tv5', name: 'Köytav Poşetli Gezen Tavuk kg', brand: 'Köytav', price: 419.00, oldPrice: null, unit: '1 kg', market: 'Tarım Kredi' },
  { id: 'tv6', name: 'Erp Tavuk Nugget 300g', brand: 'Erpiliç', price: 135.00, oldPrice: 149.00, unit: '300g', market: 'Tarım Kredi' },
  { id: 'tv7', name: 'Erp Tavuk Schnitzel 300g', brand: 'Erpiliç', price: 135.00, oldPrice: null, unit: '300g', market: 'Tarım Kredi' },
  { id: 'tv8', name: 'Erp Tavuk Cordon Bleu 300g', brand: 'Erpiliç', price: 155.00, oldPrice: 175.00, unit: '300g', market: 'Tarım Kredi' },
  { id: 'tv9', name: 'Piliç Göğüs Bonfile kg', brand: 'Erpiliç', price: 169.90, oldPrice: 189.00, unit: '1 kg', market: 'BİM' },
  { id: 'tv10', name: 'Piliç Pirzola kg', brand: 'Banvit', price: 178.00, oldPrice: null, unit: '1 kg', market: 'ŞOK' },

  { id: 'et1', name: 'Tarım Kredi Dana Kıyma 500g', brand: 'Tarım Kredi', price: 185.00, oldPrice: null, unit: '500g', market: 'Tarım Kredi' },
  { id: 'et2', name: 'Emin Dana Kıyma 500g', brand: 'Emin', price: 189.00, oldPrice: 210.00, unit: '500g', market: 'BİM' },
  { id: 'et3', name: 'Kombinet Dana Kıyma 500g', brand: 'Kombinet', price: 192.00, oldPrice: null, unit: '500g', market: 'A101' },

  { id: 'sc1', name: 'Baştacı Kasap Sucuk 400g', brand: 'Baştacı', price: 145.00, oldPrice: 165.00, unit: '400g', market: 'BİM' },
  { id: 'sc2', name: 'Tarım Kredi Doyum Dana Sucuk 400g', brand: 'Tarım Kredi', price: 142.00, oldPrice: null, unit: '400g', market: 'Tarım Kredi' },

  // --- SÜT & YUMURTA & PEYNİR ---
  { id: 'y1', name: 'TK Gezen Tavuk Yumurta 10 lu', brand: 'Tarım Kredi', price: 95.00, oldPrice: null, unit: '10 lu', market: 'Tarım Kredi' },
  { id: 'y2', name: 'Tarım Kredi M Boy Yumurta 30lu', brand: 'Tarım Kredi', price: 135.00, oldPrice: null, unit: '30lu', market: 'Tarım Kredi' },
  { id: 'y3', name: 'Bili Bili L Boy Yumurta 30lu', brand: 'Bili Bili', price: 138.00, oldPrice: 155.00, unit: '30lu', market: 'BİM' },
  { id: 'y4', name: 'Keskinoğlu L Boy Yumurta 30lu', brand: 'Keskinoğlu', price: 140.00, oldPrice: 158.00, unit: '30lu', market: 'A101' },
  { id: 'y5', name: 'CP L Boy Yumurta 30lu', brand: 'CP', price: 142.00, oldPrice: 160.00, unit: '30lu', market: 'ŞOK' },

  { id: 's1', name: 'Tarım Kredi Yağlı Süt 1L', brand: 'Tarım Kredi', price: 38.00, oldPrice: null, unit: '1L', market: 'Tarım Kredi' },
  { id: 's2', name: 'Dost Tam Yağlı Süt 1L', brand: 'Dost', price: 38.50, oldPrice: 41.00, unit: '1L', market: 'BİM' },
  { id: 's3', name: 'Birşah Yarım Yağlı Süt 1L', brand: 'Birşah', price: 39.00, oldPrice: 42.50, unit: '1L', market: 'A101' },
  { id: 's4', name: 'Mis Tam Yağlı Süt 1L', brand: 'Mis', price: 39.50, oldPrice: null, unit: '1L', market: 'ŞOK' },

  { id: 'p1', name: 'Tarım Kredi Tam Yağlı Peynir 1 kg', brand: 'Tarım Kredi', price: 158.00, oldPrice: null, unit: '1 kg', market: 'Tarım Kredi' },
  { id: 'p2', name: 'Ahir Tam Yağlı Taze Peynir 1 kg', brand: 'Ahir', price: 160.00, oldPrice: 179.00, unit: '1 kg', market: 'A101' },
  { id: 'p3', name: 'Mis Tam Yağlı Beyaz Peynir 1 kg', brand: 'Mis', price: 162.50, oldPrice: null, unit: '1 kg', market: 'ŞOK' },
  { id: 'p4', name: 'Kaanlar Süzme Peynir 1 kg', brand: 'Kaanlar', price: 165.00, oldPrice: 185.00, unit: '1 kg', market: 'BİM' },
  { id: 'p5', name: 'Tarım Kredi Kaşar Peyniri 1 kg', brand: 'Tarım Kredi', price: 230.00, oldPrice: null, unit: '1 kg', market: 'Tarım Kredi' },
  { id: 'p6', name: 'Akyazıcı Taze Kaşar Peyniri 1 kg', brand: 'Akyazıcı', price: 235.00, oldPrice: 265.00, unit: '1 kg', market: 'BİM' },

  // --- TEMEL GIDA & YAĞ ---
  { id: 'sk1', name: 'Tarım Kredi Toz Şeker 5 kg', brand: 'Tarım Kredi', price: 225.00, oldPrice: null, unit: '5 kg', market: 'Tarım Kredi' },
  { id: 'sk2', name: 'Balkan Toz Şeker 5 kg', brand: 'Balkan', price: 228.00, oldPrice: 245.00, unit: '5 kg', market: 'BİM' },
  { id: 'sk3', name: 'Petek Toz Şeker 5 kg', brand: 'Petek', price: 229.00, oldPrice: 249.00, unit: '5 kg', market: 'A101' },
  { id: 'sk4', name: 'Bor Şeker Toz Şeker 5 kg', brand: 'Bor', price: 230.00, oldPrice: null, unit: '5 kg', market: 'ŞOK' },

  { id: 'zy1', name: 'Tarım Kredi Sızma Zeytinyağı 1L', brand: 'Tarım Kredi', price: 340.00, oldPrice: 365.00, unit: '1L', market: 'Tarım Kredi' },
  { id: 'zy2', name: 'Kırlangıç Riviera Zeytinyağı 1L', brand: 'Kırlangıç', price: 355.00, oldPrice: null, unit: '1L', market: 'BİM' },
  { id: 'zy3', name: 'Yudum Ege Sızma Zeytinyağı 1L', brand: 'Yudum', price: 360.00, oldPrice: 390.00, unit: '1L', market: 'ŞOK' },

  { id: 'ay1', name: 'Tarım Kredi Ayçiçek Yağı 5L', brand: 'Tarım Kredi', price: 449.00, oldPrice: null, unit: '5L', market: 'Tarım Kredi' },
  { id: 'ay2', name: 'Sole Ayçiçek Yağı 5L', brand: 'Sole', price: 455.00, oldPrice: 485.00, unit: '5L', market: 'BİM' },
  { id: 'ay3', name: 'Evin Ayçiçek Yağı 5L', brand: 'Evin', price: 458.00, oldPrice: null, unit: '5L', market: 'ŞOK' },
  { id: 'ay4', name: 'Vera Ayçiçek Yağı 5L', brand: 'Vera', price: 459.00, oldPrice: 490.00, unit: '5L', market: 'A101' },

  { id: 'e1', name: 'Somun Ekmek 200g (Aksaray Fırın)', brand: 'Halk', price: 12.50, oldPrice: null, unit: '200g', market: 'Tarım Kredi' },
  { id: 'e2', name: 'Kepekli Ekmek 350g', brand: 'Destan', price: 16.50, oldPrice: null, unit: '350g', market: 'BİM' }
];

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get('q') || 'süt';

  const qNorm = trLower(query.trim());
  const words = qNorm.split(/\s+/).filter(w => w.length >= 2);

  // 1. Canlı Tarım Kredi Verileri
  const liveTk = await fetchTkKoopLive(query);

  // 2. Kataloğumuzdaki Veriler
  const catalogMatches = REAL_CATALOG.filter(item => {
    const n = trLower(item.name);
    const b = trLower(item.brand);
    return words.some(w => n.includes(w) || b.includes(w));
  });

  const allRaw = [...liveTk, ...catalogMatches];
  const seen = new Set();
  const finalProducts = [];

  for (const item of allRaw) {
    if (!item.name || item.price <= 0) continue;
    if (isIrrelevantProduct(query, item.name)) continue;

    const market = normalizeMarketName(item.market);
    const key = `${trLower(item.name)}_${market}`;

    if (seen.has(key)) continue;
    seen.add(key);

    const oldPrice = item.oldPrice && item.oldPrice > item.price ? item.oldPrice : null;
    const discount = oldPrice ? Math.round(((oldPrice - item.price) / oldPrice) * 100) : 0;

    finalProducts.push({
      id: item.id || `p_${finalProducts.length}`,
      name: item.name,
      brand: item.brand || market,
      price: item.price,
      oldPrice: oldPrice,
      unit: item.unit || '1 adet',
      unitPrice: item.unitPrice || calculateUnitPrice(item.price, item.unit),
      market: market,
      discount: discount
    });
  }

  // Fiyata göre küçükten büyüğe
  finalProducts.sort((a, b) => a.price - b.price);

  return NextResponse.json({
    query: query,
    count: finalProducts.length,
    products: finalProducts
  });
}
