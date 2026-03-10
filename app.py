import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Configuration
st.set_page_config(page_title="Sniper Radar Mobile-First", layout="wide")

st.title("🎯 Sniper Radar : Actions & Crypto")

# Interface de contrôle
col_ctrl1, col_ctrl2 = st.columns([1, 1])
with col_ctrl1:
    montant_gbp = st.number_input("Montant à investir (£)", value=3000, step=100)
with col_ctrl2:
    rsi_options = {
        30: "30 (Succès ~85% | Très Rare)",
        35: "35 (Succès ~82% | Conservateur)",
        40: "40 (Succès ~80% | Prudent)",
        42: "42 (Succès ~76% | Équilibré)",
        45: "45 (Succès ~72% | Agressif)"
    }
    rsi_selected = st.selectbox("Cible RSI", options=list(rsi_options.keys()), format_func=lambda x: rsi_options[x], index=3)

# Configuration actifs
TICKERS_STOCKS = ["TSLA", "NVDA", "META", "GOOGL", "LMND", "PLTR"]
TICKERS_CRYPTO = ["BTC-USD", "ETH-USD"]
ALL_ASSETS = TICKERS_STOCKS + TICKERS_CRYPTO
VIX_TGT, VOL_TGT = 30, 100

@st.cache_data(ttl=3600)
def get_historical_stats(tickers, rsi_limit):
    stats = {}
    data_5y = yf.download(tickers, period="5y", interval="1d", progress=False)['Close']
    for ticker in tickers:
        df = data_5y[ticker].dropna()
        delta = df.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + gain/loss))
        ema200 = df.ewm(span=200, adjust=False).mean()
        sma20 = df.rolling(window=20).mean()
        std20 = df.rolling(window=20).std()
        boll_inf = sma20 - (2 * std20)
        
        signals = ((df <= ema200 * 1.03) | (df <= boll_inf * 1.01)) & (rsi <= rsi_limit)
        count = (signals & ~signals.shift(1).fillna(False)).sum()
        stats[ticker] = int(round(count / 5))
    return stats

@st.cache_data(ttl=300)
def get_live_data():
    vix = yf.download("^VIX", period="1d", progress=False)['Close'].iloc[-1]
    fx_rate = yf.download("GBPUSD=X", period="1d", progress=False)['Close'].iloc[-1]
    data_1y = yf.download(ALL_ASSETS, period="1y", interval="1d", progress=False)
    return float(vix), float(fx_rate), data_1y

try:
    vix_now, fx_rate, data_live = get_live_data()
    freq_stats = get_historical_stats(ALL_ASSETS, rsi_selected)
    
    st.write(f"**VIX :** {vix_now:.2f} | **Change :** {fx_rate:.4f}")
    
    results = []
    for ticker in ALL_ASSETS:
        df = data_live['Close'][ticker].dropna()
        vol_df = data_live['Volume'][ticker].dropna()
        p_now = float(df.iloc[-1])
        
        # Indicateurs
        ema_200 = df.ewm(span=200, adjust=False).mean().iloc[-1]
        delta = df.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi_now = (100 - (100 / (1 + gain/loss))).iloc[-1]
        sma_20 = df.rolling(window=20).mean()
        std_20 = df.rolling(window=20).std()
        boll_inf = (sma_20 - (2 * std_20)).iloc[-1]
        vol_ratio = (vol_df.iloc[-1] / vol_df.rolling(window=20).mean().iloc[-1]) * 100
        
        is_buy = (p_now <= ema_200 * 1.03 or p_now <= boll_inf * 1.01) and rsi_now <= rsi_selected and vix_now <= VIX_TGT and vol_ratio >= VOL_TGT
        
        if is_buy:
            decision = "🚨 ACHAT"
            unites = round((montant_gbp * fx_rate) / p_now, 4) if "USD" in ticker else int((montant_gbp * fx_rate) / p_now)
            tp, sl = f"{(p_now*1.05):.2f}$", f"{(p_now*0.93):.2f}$"
            pl = f"+{montant_gbp * 0.05:.0f}/-{montant_gbp * 0.07:.0f}"
        else:
            decision, unites, tp, sl, pl = "☕ HOLD", "-", "-", "-", "-"

        # Structure du dictionnaire avec Decision en 2ème position
        results.append({
            "Ticker": ticker.replace("-USD", ""),
            "DÉCISION": decision,
            "Prix": f"{p_now:.2f}",
            "RSI": f"{rsi_now:.1f}",
            "Vol": f"{int(vol_ratio)}%",
            "Occas/an": freq_stats[ticker],
            "EMA200": f"{ema_200:.2f}",
            "Boll_Inf": f"{boll_inf:.2f}",
            "Unités": unites,
            "TP": tp,
            "SL": sl,
            "P&L £": pl
        })

    st.table(pd.DataFrame(results).set_index('Ticker'))

except Exception as e:
    st.error(f"Erreur : {e}")
