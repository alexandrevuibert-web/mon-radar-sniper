import streamlit as st
import yfinance as yf
import pandas as pd

# Configuration
st.set_page_config(page_title="Sniper Radar Multi-Assets", layout="wide")

# Interface
st.title("🎯 Sniper Radar : Actions & Crypto")
montant_gbp = st.number_input("Montant à investir (£)", value=3000, step=100)

# Paramètres (Compromis RSI 42)
TICKERS_STOCKS = ["TSLA", "NVDA", "META", "GOOGL", "LMND", "PLTR"]
TICKERS_CRYPTO = ["BTC-USD", "ETH-USD"]
ALL_ASSETS = TICKERS_STOCKS + TICKERS_CRYPTO

TP_PCT, SL_PCT = 1.05, 0.93
RSI_TGT, VIX_TGT, VOL_TGT = 42, 30, 100

@st.cache_data(ttl=300)
def get_market_data():
    vix = yf.download("^VIX", period="1d", progress=False)['Close'].iloc[-1]
    fx_rate = yf.download("GBPUSD=X", period="1d", progress=False)['Close'].iloc[-1]
    data = yf.download(ALL_ASSETS, period="1y", interval="1d", progress=False)
    return float(vix), float(fx_rate), data

try:
    vix_now, fx_rate, data = get_market_data()
    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.write(f"**VIX :** {vix_now:.2f} (Cible: < {VIX_TGT})")
    with col_info2:
        st.write(f"**Taux GBP/USD :** {fx_rate:.4f}")
    
    results = []
    for ticker in ALL_ASSETS:
        df = data['Close'][ticker].dropna()
        vol_df = data['Volume'][ticker].dropna()
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
        
        # Logique de signal
        is_buy = (p_now <= ema_200 * 1.03 or p_now <= boll_inf * 1.01) and rsi_now <= RSI_TGT and vix_now <= VIX_TGT and vol_ratio >= VOL_TGT
        
        # P&L
        p_gain = montant_gbp * 0.05
        p_loss = montant_gbp * 0.07

        results.append({
            "Ticker": ticker.replace("-USD", ""),
            "Prix ($)": f"{p_now:.2f}",
            "EMA200": f"{ema_200:.2f}",
            "Boll_Inf": f"{boll_inf:.2f}",
            f"RSI (<{RSI_TGT})": f"{rsi_now:.2f}",
            f"Vol (>{VOL_TGT}%)": f"{int(vol_ratio)}%",
            "DÉCISION": "🚨 ACHAT" if is_buy else "☕ HOLD",
            "Unités": round((montant_gbp * fx_rate) / p_now, 4),
            "Sortie TP": f"{(p_now*TP_PCT):.2f}$",
            "Sortie SL": f"{(p_now*SL_PCT):.2f}$",
            "P&L (£)": f"+{p_gain:.0f} / -{p_loss:.0f}"
        })

    # Distinction visuelle entre Actions et Crypto
    df_res = pd.DataFrame(results).set_index('Ticker')
    st.table(df_res)

except Exception as e:
    st.error(f"Erreur technique : {e}")
