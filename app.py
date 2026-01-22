import streamlit as st
import requests
import pandas as pd
from pokemontcgsdk import Card, RestClient

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="PokeProfit AI", layout="wide", page_icon="📈")

# Clean API Key Loading (Removes potential invisible spaces)
try:
    pokemon_key = st.secrets["POKEMON_TCG_API_KEY"].strip()
    just_tcg_key = st.secrets["JUST_TCG_KEY"].strip()
    RestClient.configure(pokemon_key)
except Exception as e:
    st.error(f"⚠️ Setup Error: {e}")
    st.stop()

# Initialize Collection
if 'collection' not in st.session_state:
    st.session_state.collection = []

# --- 2. THE AI BRAIN ---
def get_ai_advice(raw_price, psa10_price):
    if not raw_price or raw_price <= 0:
        return "NO DATA", "⚪", "Price not available for analysis."
    
    # Grading arbitrage logic
    profit_margin = psa10_price - raw_price - 25  # $25 est. grading fee
    roi = (profit_margin / raw_price) * 100
    
    if roi > 120 and raw_price > 20:
        return "STRONG BUY", "🔥", f"High ROI potential ({roi:.0f}%). Significant gap between Raw and PSA 10."
    elif roi > 40:
        return "SPECULATIVE", "💎", "Healthy margins. Buy if card centering is perfect."
    else:
        return "HOLD", "📊", "Raw price is too close to graded value. High risk flip."

# --- 3. SIDEBAR PORTFOLIO ---
st.sidebar.header("💼 My Portfolio")
if st.session_state.collection:
    df_col = pd.DataFrame(st.session_state.collection)
    total_val = df_col["Buy Price"].sum()
    st.sidebar.metric("Total Investment", f"${total_val:,.2f}")
    if st.sidebar.button("Clear All"):
        st.session_state.collection = []
        st.rerun()

# --- 4. MAIN INTERFACE ---
st.title("🚀 PokePrice AI: Search & Portfolio Advisor")
query = st.text_input("Enter Pokémon Name:", placeholder="e.g. Rayquaza...")

if query:
    with st.spinner('Scanning the Pokédex...'):
        all_cards = Card.where(q=f'name:"{query}*"')

    if all_cards:
        # PAGINATION
        CARDS_PER_PAGE = 10
        total_found = len(all_cards)
        num_pages = max(1, (total_found // CARDS_PER_PAGE) + (1 if total_found % CARDS_PER_PAGE > 0 else 0))
        page = st.select_slider("Select Page", options=range(1, num_pages + 1))
        
        start_idx = (page - 1) * CARDS_PER_PAGE
        cards_to_show = all_cards[start_idx : start_idx + CARDS_PER_PAGE]

        for card in cards_to_show:
            with st.container(border=True):
                col1, col2, col3 = st.columns([1, 2, 1.5])
                
                with col1:
                    st.image(card.images.small)
                
                with col2:
                    st.subheader(f"{card.name} ({card.set.name})")
                    st.write(f"**ID:** `{card.id}` | **Rarity:** {getattr(card, 'rarity', 'Common')}")
                    
                    # COUNTERMEASURE: Safe TCGplayer ID Fetch
                    raw_price = 0.0
                    tcg_info = getattr(card, 'tcgplayer', None)
                    
                    if tcg_info:
                        try:
                            # Use the JustTCG API to get market variants
                            tcg_id = tcg_info.id
                            jt_url = f"https://api.justtcg.com/v1/cards?tcgplayerId={tcg_id}"
                            jt_res = requests.get(jt_url, headers={"x-api-key": just_tcg_key}, timeout=5).json()
                            
                            if "data" in jt_res and jt_res["data"]:
                                variants = jt_res["data"][0].get("variants", [])
                                # Auto-pick the first available price as the 'Raw' baseline
                                if variants:
                                    raw_price = variants[0]['price']
                                    st.metric("Market Price (Raw)", f"${raw_price:,.2f}")
                        except:
                            st.write("⚠️ Price lookup failed.")

                    if st.button(f"Add to Portfolio", key=f"btn_{card.id}"):
                        st.session_state.collection.append({
                            "Name": card.name, "Set": card.set.name, "Buy Price": raw_price
                        })
                        st.toast(f"Saved {card.name}!")

                with col3:
                    st.markdown("### 🤖 AI Prediction")
                    # Estimated PSA 10 value (Aggressive multiplier for vintage, conservative for modern)
                    est_psa10 = raw_price * 4 if raw_price > 10 else raw_price + 40
                    
                    status, icon, reason = get_ai_advice(raw_price, est_psa10)
                    st.info(f"{icon} **{status}**\n\n{reason}")
                    
                    # Helpful Links
                    pc_q = f"{card.name} {card.set.name} {card.number}".replace(" ", "+")
                    st.link_button("View Graded Sold History 📈", f"https://www.pricecharting.com/search-products?q={pc_q}")

    else:
        st.warning("No cards found for that name.")
