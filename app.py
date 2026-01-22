import streamlit as st
import requests
import pandas as pd
from pokemontcgsdk import Card, RestClient

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="PokeProfit AI", layout="wide", page_icon="📈")

try:
    pokemon_key = st.secrets["POKEMON_TCG_API_KEY"].strip()
    just_tcg_key = st.secrets["JUST_TCG_KEY"].strip()
    RestClient.configure(pokemon_key)
except Exception as e:
    st.error(f"⚠️ Setup Error: {e}")
    st.stop()

if 'collection' not in st.session_state:
    st.session_state.collection = []

# --- 2. ENHANCED AI ADVISOR ---
def get_ai_advice(raw_price, psa10_price):
    if not raw_price or raw_price <= 0:
        return "NO DATA", "⚪", "Price not available for analysis."
    
    # AI Logic: Grading Arbitrage
    # We estimate $25 for grading + shipping fees
    profit_margin = psa10_price - raw_price - 25 
    roi = (profit_margin / raw_price) * 100 if raw_price > 0 else 0
    
    if roi > 150 and raw_price > 15:
        return "STRONG BUY", "🔥", f"Massive ROI ({roi:.0f}%). Significant PSA 10 premium found."
    elif roi > 50:
        return "SPECULATIVE", "💎", "Healthy margins. Buy if centering/surface is Mint."
    elif roi < 0:
        return "AVOID", "🛑", "Grading this would likely result in a net loss."
    else:
        return "HOLD", "📊", "Market is stable. PSA 10 premium is standard."

# --- 3. MAIN UI ---
st.title("🚀 PokeProfit AI: Master Advisor")
query = st.text_input("Search for a card:", placeholder="e.g. Umbreon VMAX...")

if query:
    cards = Card.where(q=f'name:"{query}*"')
    
    if cards:
        # Simple Pagination
        total = len(cards)
        st.write(f"Found {total} results.")
        page = st.sidebar.number_input("Page", min_value=1, value=1)
        start = (page - 1) * 10
        
        for card in cards[start : start + 10]:
            with st.container(border=True):
                col1, col2, col3 = st.columns([1, 2, 1.5])
                
                with col1:
                    st.image(card.images.small)
                
                with col2:
                    st.subheader(f"{card.name} ({card.set.name})")
                    
                    # --- PRICE LOOKUP LOGIC ---
                    raw_price = 0.0
                    
                    # Try JustTCG First (For variants)
                    tcg_data = getattr(card, 'tcgplayer', None)
                    if tcg_data:
                        try:
                            tid = tcg_data.id
                            # Added 'game=pokemon' parameter for better matching
                            jt_url = f"https://api.justtcg.com/v1/cards?tcgplayerId={tid}&game=pokemon"
                            jt_res = requests.get(jt_url, headers={"x-api-key": just_tcg_key}, timeout=5).json()
                            if "data" in jt_res and jt_res["data"]:
                                variants = jt_res["data"][0].get("variants", [])
                                if variants:
                                    raw_price = variants[0]['price']
                        except:
                            pass

                    # FALLBACK: Use SDK Market Price if JustTCG fails
                    if raw_price == 0.0 and tcg_data:
                        prices = getattr(tcg_data, 'prices', None)
                        if prices:
                            # Try Holofoil market, then Normal market
                            if hasattr(prices, 'holofoil'): raw_price = prices.holofoil.market
                            elif hasattr(prices, 'normal'): raw_price = prices.normal.market
                            elif hasattr(prices, 'reverseHolofoil'): raw_price = prices.reverseHolofoil.market

                    if raw_price > 0:
                        st.metric("Current Market Price", f"${raw_price:,.2f}")
                    else:
                        st.warning("⚠️ No pricing data available.")

                    if st.button("Add to Collection", key=f"add_{card.id}"):
                        st.session_state.collection.append({"name": card.name, "price": raw_price})
                        st.toast("Saved!")

                with col3:
                    st.markdown("### 🤖 AI Prediction")
                    # Dynamic PSA 10 Multiplier (estimated)
                    est_psa10 = raw_price * 3.8 if raw_price > 5 else 45.0
                    
                    advice, icon, reason = get_ai_advice(raw_price, est_psa10)
                    st.info(f"{icon} **{advice}**\n\n{reason}")
                    
                    # Direct Link for Verification
                    search_slug = f"{card.name} {card.set.name} {card.number}".replace(" ", "+")
                    st.link_button("Check Graded History 📈", f"https://www.pricecharting.com/search-products?q={search_slug}")

# --- 4. SIDEBAR PORTFOLIO ---
st.sidebar.divider()
st.sidebar.header("Portfolio Value")
if st.session_state.collection:
    total_val = sum(item['price'] for item in st.session_state.collection)
    st.sidebar.subheader(f"${total_val:,.2f}")
