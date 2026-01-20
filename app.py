import streamlit as st
import requests
import pandas as pd
from pokemontcgsdk import Card, RestClient

# --- INITIAL SETUP ---
st.set_page_config(page_title="PokeProfit AI", layout="wide", page_icon="📈")

# Load Secrets
try:
    RestClient.configure(st.secrets["POKEMON_TCG_API_KEY"])
    JUST_TCG_KEY = st.secrets["JUST_TCG_API_KEY"]
except:
    st.error("Missing API Keys! Add them to Streamlit Secrets.")
    st.stop()

# Initialize Collection in Session State
if 'collection' not in st.session_state:
    st.session_state.collection = []

# --- AI LOGIC FUNCTIONS ---
def get_ai_advice(raw_price, psa10_price):
    if not raw_price or not psa10_price or psa10_price == 0:
        return "N/A", "⚪", "Insufficient data for AI analysis."
    
    profit = psa10_price - raw_price - 25  # Subtracting ~$25 for grading fees
    roi = (profit / raw_price) * 100 if raw_price > 0 else 0
    
    if roi > 120 and raw_price > 30:
        return "STRONG BUY", "🔥", f"High ROI ({roi:.0f}%). Major gap between Raw and PSA 10."
    elif roi > 40:
        return "SPECULATIVE", "💎", "Healthy upside. Ensure card condition is Mint before grading."
    else:
        return "HOLD / AVOID", "⚠️", "Low margins. Grading costs may exceed profit."

# --- SIDEBAR: COLLECTION SUMMARY ---
st.sidebar.header("💼 My Portfolio")
if st.session_state.collection:
    df_col = pd.DataFrame(st.session_state.collection)
    total_invested = df_col["Buy Price"].sum()
    # In a production app, you'd re-fetch prices here to show 'Current Value'
    st.sidebar.metric("Total Investment", f"${total_invested:,.2f}")
    if st.sidebar.button("Clear Collection"):
        st.session_state.collection = []
        st.rerun()
else:
    st.sidebar.info("Collection is empty.")

# --- MAIN UI ---
st.title("🚀 PokeProfit AI: Search & Portfolio Advisor")
query = st.text_input("Enter Pokémon Name (e.g. Gengar):", placeholder="Charizard...")

if query:
    # 1. Fetch ALL matching cards
    with st.spinner('Searching entire database...'):
        all_cards = Card.where(q=f'name:"{query}*"') # Using wildcard for better results

    if all_cards:
        # PAGINATION
        CARDS_PER_PAGE = 10
        total_found = len(all_cards)
        num_pages = (total_found // CARDS_PER_PAGE) + (1 if total_found % CARDS_PER_PAGE > 0 else 0)
        
        st.write(f"Showing {total_found} results matching '{query}'")
        page = st.select_slider("Select Page", options=range(1, num_pages + 1))
        
        start_idx = (page - 1) * CARDS_PER_PAGE
        end_idx = start_idx + CARDS_PER_PAGE
        
        for card in all_cards[start_idx:end_idx]:
            with st.container(border=True):
                col1, col2, col3 = st.columns([1, 2, 1.5])
                
                with col1:
                    st.image(card.images.small)
                
                with col2:
                    st.subheader(f"{card.name} ({card.set.name})")
                    st.write(f"**Number:** {card.number}/{card.set.printedTotal} | **Rarity:** {card.rarity}")
                    
                    # Fetch JustTCG Pricing
                    tcg_id = card.tcgplayer.id if card.tcgplayer else None
                    raw_price = 0.0
                    if tcg_id:
                        jt_url = f"https://api.justtcg.com/v1/cards?tcgplayerId={tcg_id}"
                        jt_res = requests.get(jt_url, headers={"x-api-key": JUST_TCG_KEY}).json()
                        if "data" in jt_res and jt_res["data"]:
                            variants = jt_res["data"][0].get("variants", [])
                            # Find Near Mint price as the 'Raw' baseline
                            for v in variants:
                                if "Near Mint" in v['condition']:
                                    raw_price = v['price']
                                    st.metric("Raw (NM) Price", f"${raw_price:,.2f}")
                                    break
                    
                    if st.button(f"➕ Add to Collection", key=f"add_{card.id}"):
                        st.session_state.collection.append({
                            "Name": card.name, "Set": card.set.name, "Buy Price": raw_price, "ID": card.id
                        })
                        st.toast("Added to portfolio!")

                with col3:
                    st.markdown("### 🤖 AI Investment Advice")
                    # Using a placeholder for PSA 10 (In reality, you'd scrape PriceCharting here)
                    # For demo: Estimating PSA 10 as roughly 3.5x Raw price or $50 minimum
                    est_psa10 = raw_price * 3.5 if raw_price > 5 else 50.0
                    
                    status, icon, reason = get_ai_advice(raw_price, est_psa10)
                    st.info(f"{icon} **{status}**\n\n{reason}")
                    
                    pc_url = f"https://www.pricecharting.com/search-products?q={card.name}+{card.set.name}+{card.number}".replace(" ", "+")
                    st.link_button("Verify Graded Sold History 📈", pc_url)

    else:
        st.error("No cards found. Try a different name.")
