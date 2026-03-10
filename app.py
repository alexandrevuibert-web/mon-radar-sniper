import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Configuration
st.set_page_config(page_title="Sniper Radar Algos", layout="wide")
st.title("🎯 Sniper Radar : Supports & TP/SL Dynamiques")

# Interface de contrôle
col_ctrl1, col_ctrl2 = st.columns([1, 1])
with col_ctrl1:
    montant_gbp = st.number_input("Montant à investir (£)", value=3000, step=100)
with col_ctrl2:
    rsi_options = {30: "30 (85%)", 35: "35 (82%)", 40: "40 (80%)", 42: "42 (76%)", 45: "45 (72%)"}
    rsi_selected = st.selectbox("Cible RSI", options=list(rsi_options.keys()), format_func=lambda x: rsi_options[x], index=3)

# Configuration
TICKERS = ["TSLA", "NVDA", "META", "GOOGL", "LMND", "PLTR", "BTC-USD", "ETH-USD"]
VIX_TGT, VOL_TGT = 30, 100

@st.cache_data(ttl=300)
def get_data():
    vix = yf.download("^VIX", period="1d", progress=False)['Close'].iloc[-1]
    fx = yf.download("GBPUSD=X", period="1d", progress=False)['Close'].iloc[-1]
    raw = yf.download(TICKERS, period="1y", interval="1d", progress=False)
    return float(vix), float(fx), raw

try:
    vix_now, fx_rate, data = get_data()
    results = []

    for t in TICKERS:
        df = data['Close'][t].dropna()
        p_now = float(df.iloc[-1])
        
        # --- Indicateurs Classiques ---
        ema200 = df.ewm(span=200, adjust=False).mean().iloc[-1]
        delta = df.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + gain/loss))).iloc[-1]
        vol_ratio = (data['Volume'][t].iloc[-1] / data['Volume'][t].rolling(20).mean().iloc[-1]) * 100
        
        # --- Supports & Résistances (20j) ---
        res_h = df.rolling(20).max().iloc[-1]  # Résistance
        sup_l = df.rolling(20).min().iloc[-1]  # Support
        
        # --- Logique de Signal ---
        rsi_ok = rsi <= rsi_selected
        vol_ok = vol_ratio >= VOL_TGT
        price_ok = (p_now <= ema200 * 1.03) or (p_now <= (df.rolling(20).mean() - 2*df.rolling(20).std()).iloc[-1] * 1.01)
        
        is_buy = rsi_ok and vol_ok and price_ok and vix_now <= VIX_TGT

        if is_buy:
            decision = "🚨 ACHAT"
            # TP Dynamique : 99% de la Résistance (pour être sûr de sortir)
            tp_price = res_h * 0.99
            # SL Dynamique : 98% du Support
            sl_price = sup_l * 0.98
            
            # Sécurité : Si TP trop proche (<2%), on force le +5% historique
            if (tp_price / p_now) < 1.02: tp_price = p_now * 1.05
            
            yield_pct = ((tp_price / p_now) - 1) * 100
            unites = round((montant_gbp * fx_rate) / p_now, 4) if "USD" in t else int((montant_gbp * fx_rate) / p_now)
            pl = f"+{yield_pct:.1f}% / -{((1 - sl_price/p_now)*100):.1f}%"
            tp_str, sl_str = f"{tp_price:.2f}$", f"{sl_price:.2f}$"
        else:
            decision, tp_str, sl_str, pl, unites = "☕ HOLD", "-", "-", "-", "-"

        results.append({
            "Ticker": t.replace("-USD", ""),
            "DÉCISION": decision,
            "Prix ($)": f"{p_now:.2f}",
            "RSI": f"{rsi:.1f} {'✅' if rsi_ok else ''}",
            "S. Hist (20j)": f"{sup_l:.2f}",
            "R. Hist (20j)": f"{res_h:.2f}",
            "EMA200": f"{ema200:.2f}",
            "Unités": unites,
            "TP Dyn": tp_str,
            "SL Dyn": sl_str,
            "P&L Est.": pl
        })

    st.table(pd.DataFrame(results).set_index('Ticker'))

except Exception as e:
    st.error(f"Erreur : {e}")
