import streamlit as st
import pandas as pd
import plotly.express as px
from scraper import search_market_products, get_price_history

st.set_page_config(
    page_title="Market Fiyat | Aksaray & Sultanhanı",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

try:
    st.cache_data.clear()
except Exception:
    pass

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #f0fdf4;
        color: #0f172a;
    }
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 480px !important;
    }
    .header-card {
        background: linear-gradient(135deg, #166534 0%, #15803d 100%);
        border-radius: 18px;
        padding: 1.1rem;
        color: #ffffff;
        text-align: center;
        box-shadow: 0 10px 25px rgba(22, 101, 52, 0.2);
        margin-bottom: 1rem;
    }
    .header-title {
        font-size: 1.4rem;
        font-weight: 800;
        color: #ffffff;
    }
    .header-badge {
        font-size: 0.72rem;
        font-weight: 700;
        background: rgba(255, 255, 255, 0.2);
        color: #ffffff;
        padding: 3px 10px;
        border-radius: 20px;
        display: inline-block;
        margin-top: 4px;
    }
    .product-box {
        background: #ffffff;
        border-radius: 16px;
        padding: 1rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        border: 1px solid #e2e8f0;
    }
    .box-gold { border: 2px solid #22c55e; background: #f0fdf4; }
    .box-silver { border: 1.5px solid #cbd5e1; }
    .box-bronze { border: 1.5px solid #fdba74; }
</style>
""", unsafe_allow_html=True)

if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

st.markdown("""
<div class="header-card">
    <div class="header-title">🛒 Market Fiyat</div>
    <div class="header-badge">📍 Aksaray & Sultanhanı</div>
    <div style="font-size:0.75rem; margin-top:6px; opacity:0.9;">BİM, A101, ŞOK ve Tarım Kredi'nin canlı en ucuz ürünleri.</div>
</div>
""", unsafe_allow_html=True)

location = st.selectbox("Konum", ["Aksaray Merkez", "Sultanhanı"], index=0, label_visibility="collapsed")
input_val = st.text_input("Ürün ara...", value=st.session_state.search_query, placeholder="Örn: poşet tavuk, süt, şeker", label_visibility="collapsed")

st.write("🔥 **Popüler Seçenekler:**")
quick_list = ["Süt", "Poşet Tavuk", "Ekmek", "Şeker", "Yumurta", "Zeytinyağı"]
cols = st.columns(len(quick_list))
for i, item in enumerate(quick_list):
    if cols[i].button(item, key=f"st_qk_{i}"):
        st.session_state.search_query = item
        st.rerun()

active_search = input_val if input_val.strip() else st.session_state.search_query

if active_search:
    with st.spinner(f"'{active_search}' taranıyor..."):
        products = search_market_products(active_search, location)

    if not products:
        st.warning("Ürün bulunamadı.")
    else:
        st.markdown(f"### 🏆 En Ucuz Ürünler (`{active_search}`)")
        for idx, p in enumerate(products[:3]):
            st.success(f"🥇 [{p['market']}] {p['name']} - **{p['price']:.2f} ₺** ({p['unit']})")
else:
    st.info("💡 Arama kutusuna ürün adı yazın veya yukarıdaki kısayollara tıklayın.")
