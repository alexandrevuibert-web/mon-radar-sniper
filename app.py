import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Sniper Radar", layout="wide")

st.title("🎯 Sniper Radar 75%")
col1, col2 = st.columns(2)
with col1:
    montant_gbp = st.number_input("Montant (£)", value=3000, step=100)
with col2:
    fx_rate = st.number_input("GBP/USD", value=1.34, format="%.2f")

TICKERS = ["TSLA", "NVDA", "META", "GOOGL", "LMND", "PLTR"]
TP_PCT, SL_PCT = 1.05, 0.93
RSI_TARGET, VIX_LIMIT, VOL_TARGET = 45, 30, 100

@st.cache_data(ttl=300)
def get_market_data():
    vix = yf.download("^VIX", period="1d", progress=False)['Close'].iloc[-1]
    data = yf.download(TICKERS, period="1y", interval="1d", progress=False)
    return float(vix), data

try:
    vix_now, data = get_market_data()
    st.write(f"**VIX Actuel :** {vix_now:.1f} ({'✅ OK' if vix_now <= VIX_LIMIT else '❌ RISQUE'})")
    
    results = []
    for ticker in TICKERS:
        df = data['Close'][ticker].dropna()
        vol_df = data['Volume'][ticker].dropna()
        p_now = float(df.iloc[-1])
        ema_200 = df.ewm(span=200, adjust=False).mean().iloc[-1]
        delta = df.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi_now = (100 - (100 / (1 + gain/loss))).iloc[-1]
        sma_20 = df.rolling(window=20).mean()
        std_20 = df.rolling(window=20).std()
        boll_inf = (sma_20 - (2 * std_20)).iloc[-1]
        vol_ratio = (vol_df.iloc[-1] / vol_df.rolling(window=20).mean().iloc[-1]) * 100
        
        is_buy = (p_now <= ema_200 * 1.03 or p_now <= boll_inf * 1.01) and rsi_now <= RSI_TARGET and vix_now <= VIX_LIMIT and vol_ratio >= VOL_TARGET
        
        results.append({
            "Ticker": ticker,
            "Prix": f"{p_now:.1f}$",
            "EMA200": f"{ema_200:.1f}$",
            "RSI": f"{int(rsi_now)}",
            "Vol %": f"{int(vol_ratio)}%",
            "DÉCISION": "🚨 ACHAT" if is_buy else "☕ HOLD",
            "Actions": int((montant_gbp * fx_rate) / p_now) if is_buy else "-",
            "TP (+5%)": f"{p_now*TP_PCT:.2f}$" if is_buy else "-",
            "SL (-7%)": f"{p_now*SL_PCT:.2f}$" if is_buy else "-"
        })

    st.table(pd.DataFrame(results))
except Exception as e:
    st.error("Erreur de connexion aux marchés.")
