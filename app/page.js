'use client';

import { useState, useEffect } from 'react';
import { Search, ShoppingCart, TrendingUp, MapPin, X, Plus, Trash2, CheckCircle2, Sparkles } from 'lucide-react';

export default function Home() {
  const [query, setQuery] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [location, setLocation] = useState('Aksaray Merkez');
  const [selectedMarket, setSelectedMarket] = useState('Tümü');
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [cart, setCart] = useState([]);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Arama Fonksiyonu
  const fetchProducts = async (searchTerm) => {
    if (!searchTerm || !searchTerm.trim()) {
      setProducts([]);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(searchTerm.trim())}`);
      const data = await res.json();
      setProducts(data.products || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (query) {
      fetchProducts(query);
    }
  }, [query]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setQuery(searchInput.trim());
    }
  };

  const handleQuickSearch = (term) => {
    setSearchInput(term);
    setQuery(term);
  };

  const addToCart = (product) => {
    setCart((prev) => {
      const existing = prev.find((item) => item.id === product.id);
      if (existing) {
        return prev.map((item) => (item.id === product.id ? { ...item, qty: item.qty + 1 } : item));
      }
      return [...prev, { ...product, qty: 1 }];
    });

    setToastMessage(`'${product.name}' alışveriş sepetine eklendi! 🛒`);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const removeFromCart = (id) => {
    setCart((prev) => prev.filter((item) => item.id !== id));
  };

  const updateCartQty = (id, delta) => {
    setCart((prev) =>
      prev.map((item) => {
        if (item.id === id) {
          const newQty = item.qty + delta;
          return newQty > 0 ? { ...item, qty: newQty } : item;
        }
        return item;
      })
    );
  };

  const cartTotal = cart.reduce((acc, item) => acc + item.price * item.qty, 0);
  const cartItemCount = cart.reduce((acc, item) => acc + item.qty, 0);

  const filteredProducts = selectedMarket === 'Tümü'
    ? products
    : products.filter((p) => p.market === selectedMarket);

  const top3 = filteredProducts.slice(0, 3);
  const others = filteredProducts.slice(3);

  const quickCategories = [
    { label: 'Pirinç', icon: '🍚' },
    { label: 'Poşet Tavuk', icon: '🍗' },
    { label: 'Süt', icon: '🥛' },
    { label: 'Ekmek', icon: '🍞' },
    { label: 'Şeker', icon: '🍬' },
    { label: 'Yumurta', icon: '🥚' },
    { label: 'Zeytinyağı', icon: '🫒' },
    { label: 'Un', icon: '🌾' },
    { label: 'Yağ', icon: '🌻' },
    { label: 'Çay', icon: '☕' },
    { label: 'Peynir', icon: '🧀' },
  ];

  const getMarketBadgeClass = (market) => {
    switch (market) {
      case 'BİM': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'A101': return 'bg-orange-50 text-orange-700 border-orange-200';
      case 'ŞOK': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'Tarım Kredi': return 'bg-emerald-50 text-emerald-800 border-emerald-300 font-bold';
      default: return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  return (
    <div className="min-h-screen bg-emerald-50/40 text-slate-900 font-sans pb-28">
      {/* Toast Bildirim */}
      {toastMessage && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-emerald-700 text-white px-5 py-3 rounded-full shadow-lg flex items-center gap-2 text-sm font-semibold animate-bounce">
          <CheckCircle2 className="w-5 h-5 text-emerald-300" />
          {toastMessage}
        </div>
      )}

      {/* HEADER BANNER */}
      <header className="bg-gradient-to-r from-emerald-800 via-emerald-700 to-green-600 text-white pt-6 pb-8 px-4 shadow-xl rounded-b-[2rem]">
        <div className="max-w-md mx-auto">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🛒</span>
              <h1 className="text-xl font-extrabold tracking-tight">Market Fiyat</h1>
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-400"></span>
              </span>
            </div>

            {/* Lokasyon Seçici */}
            <div className="flex items-center gap-1 bg-white/15 backdrop-blur-md px-3 py-1 rounded-full text-xs font-medium border border-white/20">
              <MapPin className="w-3.5 h-3.5 text-emerald-300" />
              <select
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="bg-transparent text-white border-none text-xs focus:ring-0 cursor-pointer outline-none"
              >
                <option value="Aksaray Merkez" className="text-slate-900">Aksaray Merkez</option>
                <option value="Sultanhanı" className="text-slate-900">Sultanhanı</option>
              </select>
            </div>
          </div>

          <p className="text-xs text-emerald-100/90 font-medium mb-4">
            Aksaray & Sultanhanı'nda BİM, A101, ŞOK ve Tarım Kredi'nin en ucuz ürünlerini anlık karşılaştırın.
          </p>

          {/* Arama Barı */}
          <form onSubmit={handleSearchSubmit} className="relative">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Ürün veya marka ara... (Örn: poşet tavuk)"
              className="w-full bg-white text-slate-900 placeholder-slate-400 text-sm font-medium pl-10 pr-10 py-3.5 rounded-2xl shadow-inner border-2 border-emerald-300 focus:border-emerald-500 focus:outline-none"
            />
            <Search className="w-5 h-5 text-emerald-600 absolute left-3.5 top-1/2 -translate-y-1/2" />
            {searchInput && (
              <button
                type="button"
                onClick={() => setSearchInput('')}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </form>
        </div>
      </header>

      {/* İÇERİK KONTEYNERİ */}
      <main className="max-w-md mx-auto px-4 -mt-3">
        {/* YATAY KATEGORİ ŞERİDİ (SWIPER) */}
        <section className="mb-5 overflow-x-auto no-scrollbar flex items-center gap-2 py-2">
          {quickCategories.map((cat) => {
            const isActive = query.toLowerCase() === cat.label.toLowerCase();
            return (
              <button
                key={cat.label}
                onClick={() => handleQuickSearch(cat.label)}
                className={`whitespace-nowrap px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-sm border flex items-center gap-1.5 ${
                  isActive
                    ? 'bg-emerald-600 text-white border-emerald-600 scale-105 shadow-emerald-200'
                    : 'bg-white text-slate-700 border-slate-200 hover:border-emerald-300 hover:bg-emerald-50'
                }`}
              >
                <span>{cat.icon}</span>
                <span>{cat.label}</span>
              </button>
            );
          })}
        </section>

        {/* MARKET FİLTRE HAPLARI */}
        <div className="flex items-center gap-1.5 mb-5 overflow-x-auto pb-1">
          {['Tümü', 'BİM', 'A101', 'ŞOK', 'Tarım Kredi'].map((m) => (
            <button
              key={m}
              onClick={() => setSelectedMarket(m)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                selectedMarket === m
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              {m}
            </button>
          ))}
        </div>

        {/* ARAMA BAŞLIĞI / BOŞ DURUM VEYA ÜRÜN LİSTESİ */}
        {!query ? (
          <div className="py-8 px-4 bg-white rounded-2xl border border-emerald-100 shadow-sm text-center">
            <div className="w-12 h-12 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center mx-auto mb-3 font-bold text-xl">
              🔍
            </div>
            <h3 className="text-sm font-extrabold text-slate-800 mb-1">Market Fiyat Karşılaştırması</h3>
            <p className="text-xs text-slate-500 font-medium max-w-xs mx-auto mb-4">
              Aramak istediğiniz ürünü yukarıdaki arama kutusuna yazabilir veya hızlı kategori butonlarına tıklayabilirsiniz.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {['🥛 Tam Yağlı Süt', '🍗 Poşet Tavuk', '🍞 Somun Ekmek', '🥚 30\'lu Yumurta', '🫒 Sızma Zeytinyağı'].map((item) => (
                <button
                  key={item}
                  onClick={() => handleQuickSearch(item.split(' ').slice(1).join(' '))}
                  className="bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold px-3 py-1.5 rounded-full hover:bg-emerald-100 transition-colors"
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-extrabold text-slate-800 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-emerald-600" />
                <span>En Ucuz 3 Ürün</span>
                <span className="text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full text-xs">
                  "{query}"
                </span>
              </h2>
              <span className="text-xs text-slate-500 font-medium">{filteredProducts.length} ürün bulundu</span>
            </div>

            {/* YÜKLENİYOR DURUMU */}
            {loading && (
              <div className="py-12 text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-emerald-600 border-t-transparent"></div>
                <p className="text-xs text-slate-500 font-medium mt-2">Güncel fiyatlar taranıyor...</p>
              </div>
            )}

            {/* 🏆 EN UCUZ 3 HİGHLİGHT KARTLARI */}
            {!loading && top3.length > 0 && (
              <div className="space-y-3.5 mb-6">
                {top3.map((product, idx) => {
                  const ranks = [
                    { badge: '🥇 1. En Ucuz', border: 'border-2 border-emerald-500 bg-gradient-to-b from-emerald-50/60 via-white to-white shadow-emerald-100', medal: '🥇' },
                    { badge: '🥈 2. Sıra', border: 'border border-slate-300 bg-white shadow-slate-100', medal: '🥈' },
                    { badge: '🥉 3. Sıra', border: 'border border-amber-300 bg-amber-50/30 shadow-amber-100', medal: '🥉' }
                  ];
                  const rank = ranks[idx] || ranks[1];

                  return (
                    <div
                      key={product.id}
                      className={`rounded-2xl p-4 shadow-sm relative transition-all hover:shadow-md ${rank.border}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <span className="text-2xl flex-shrink-0 mt-0.5">{rank.medal}</span>
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getMarketBadgeClass(product.market)}`}>
                                {product.market}
                              </span>
                              <span className="text-[10px] text-slate-400 font-semibold">{product.unit}</span>
                            </div>
                            <h3 className="text-sm font-bold text-slate-900 leading-snug">{product.name}</h3>
                            <p className="text-xs text-slate-500 font-medium">{product.brand}</p>
                          </div>
                        </div>

                        <div className="text-right flex-shrink-0">
                          {product.oldPrice && (
                            <div className="text-xs text-slate-400 line-through font-medium">{product.oldPrice.toFixed(2)} ₺</div>
                          )}
                          <div className="text-lg font-black text-slate-900 tracking-tight">{product.price.toFixed(2)} ₺</div>
                          {product.unitPrice && (
                            <div className="text-[11px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded mt-1 inline-block">
                              ⚡ {product.unitPrice.value} {product.unitPrice.label}
                            </div>
                          )}
                        </div>
                      </div>

                      <button
                        onClick={() => addToCart(product)}
                        className="w-full mt-3 bg-emerald-600 hover:bg-emerald-700 active:scale-[0.99] text-white py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-md shadow-emerald-200"
                      >
                        <Plus className="w-4 h-4" />
                        <span>Listeye Ekle</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            {/* 📋 DİĞER ÜRÜNLER */}
            {!loading && others.length > 0 && (
              <section className="mb-6">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Diğer Seçenekler</h3>
                <div className="space-y-2.5">
                  {others.map((product) => (
                    <div key={product.id} className="bg-white rounded-xl p-3.5 border border-slate-200 shadow-sm flex items-center justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getMarketBadgeClass(product.market)}`}>
                            {product.market}
                          </span>
                          <span className="text-[10px] text-slate-400 font-medium">{product.unit}</span>
                        </div>
                        <h4 className="text-xs font-bold text-slate-800">{product.name}</h4>
                      </div>

                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <div className="text-sm font-extrabold text-slate-900">{product.price.toFixed(2)} ₺</div>
                        </div>
                        <button
                          onClick={() => addToCart(product)}
                          className="bg-emerald-100 text-emerald-800 hover:bg-emerald-200 p-2 rounded-lg transition-colors"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {!loading && filteredProducts.length === 0 && (
              <div className="py-12 text-center bg-white rounded-2xl border border-slate-200 p-6">
                <p className="text-sm text-slate-600 font-medium">"{query}" araması için uygun ürün bulunamadı.</p>
              </div>
            )}
          </>
        )}
      </main>

      {/* 🛒 SABİT MOBİL SEPET ÇUBUĞU (STICKY BOTTOM BAR) */}
      {cart.length > 0 && (
        <div className="fixed bottom-3 left-0 right-0 px-4 z-40">
          <div className="max-w-md mx-auto bg-slate-900 text-white rounded-2xl p-3.5 shadow-2xl flex items-center justify-between border border-slate-700 backdrop-blur-lg">
            <div className="flex items-center gap-3">
              <div className="bg-emerald-500 text-white w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm">
                {cartItemCount}
              </div>
              <div>
                <div className="text-[11px] text-slate-400 font-semibold">Tahmini Sepet Tutarı</div>
                <div className="text-base font-black text-white">{cartTotal.toFixed(2)} ₺</div>
              </div>
            </div>

            <button
              onClick={() => setIsCartOpen(true)}
              className="bg-emerald-500 hover:bg-emerald-400 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition-all shadow-md flex items-center gap-1.5"
            >
              <span>Sepeti Gör</span>
              <ShoppingCart className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* 🛒 SEPET MODAL ÇEKMECESİ */}
      {isCartOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex justify-center items-end sm:items-center p-0 sm:p-4 animate-fade-in">
          <div className="bg-white w-full max-w-md rounded-t-3xl sm:rounded-3xl p-5 max-h-[85vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <ShoppingCart className="w-5 h-5 text-emerald-600" />
                <h3 className="text-base font-extrabold text-slate-900">Alışveriş Listem</h3>
              </div>
              <button
                onClick={() => setIsCartOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {cart.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-8">Sepetinizde ürün bulunmuyor.</p>
            ) : (
              <div className="space-y-3 mb-5">
                {cart.map((item) => (
                  <div key={item.id} className="flex items-center justify-between bg-slate-50 p-3 rounded-xl border border-slate-200">
                    <div>
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${getMarketBadgeClass(item.market)}`}>
                        {item.market}
                      </span>
                      <h4 className="text-xs font-bold text-slate-900 mt-1">{item.name}</h4>
                      <p className="text-[11px] text-slate-500">{item.price.toFixed(2)} ₺ / adet</p>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1.5 bg-white px-2 py-1 rounded-lg border border-slate-200">
                        <button
                          onClick={() => updateCartQty(item.id, -1)}
                          className="text-xs font-bold text-slate-600 px-1"
                        >
                          -
                        </button>
                        <span className="text-xs font-extrabold text-slate-900">{item.qty}</span>
                        <button
                          onClick={() => updateCartQty(item.id, 1)}
                          className="text-xs font-bold text-slate-600 px-1"
                        >
                          +
                        </button>
                      </div>

                      <button
                        onClick={() => removeFromCart(item.id)}
                        className="text-rose-500 hover:text-rose-700 p-1"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {cart.length > 0 && (
              <div className="border-t border-slate-100 pt-3">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-bold text-slate-600">Toplam</span>
                  <span className="text-lg font-black text-emerald-700">{cartTotal.toFixed(2)} ₺</span>
                </div>
                <button
                  onClick={() => setCart([])}
                  className="w-full bg-slate-100 text-slate-600 font-bold text-xs py-2.5 rounded-xl hover:bg-slate-200 transition-colors"
                >
                  Listeyi Temizle
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
