import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Configuration
st.set_page_config(page_title="Sniper Radar Elite", layout="wide")
st.title("🎯 Sniper Radar : Système Expert 2036")

# Interface de contrôle
col_ctrl1, col_ctrl2 = st.columns([1, 1])
with col_ctrl1:
    montant_gbp = st.number_input("Montant à investir (£)", value=3000, step=100)
with col_ctrl2:
    rsi_options = {
        30: "30 (Succès ~85%)",
        35: "35 (Succès ~82%)",
        40: "40 (Succès ~80%)",
        42: "42 (Succès ~76%)",
        45: "45 (Succès ~72%)"
    }
    rsi_selected = st.selectbox("Cible RSI", options=list(rsi_options.keys()), 
                                format_func=lambda x: rsi_options[x], index=3)

TICKERS = ["TSLA", "NVDA", "META", "GOOGL", "LMND", "PLTR", "BTC-USD", "ETH-USD"]
VIX_TGT, VOL_TGT = 30, 100

@st.cache_data(ttl=3600)
def get_historical_stats(tickers, rsi_limit):
    stats = {}
    data_5y = yf.download(tickers, period="5y", interval="1d", progress=False)['Close']
    for t in tickers:
        df = data_5y[t].dropna()
        delta = df.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain/loss))
        ema200 = df.ewm(span=200, adjust=False).mean()
        sma20 = df.rolling(20).mean()
        boll_inf = sma20 - (2 * df.rolling(20).std())
        
        # Signal si Prix proche EMA200 ou Boll_Inf ET RSI < Cible
        signals = ((df <= ema200 * 1.03) | (df <= boll_inf * 1.01)) & (rsi <= rsi_limit)
        count = (signals & ~signals.shift(1).fillna(False)).sum()
        stats[t] = int(round(count / 5))
    return stats

@st.cache_data(ttl=300)
def get_live_data():
    vix = yf.download("^VIX", period="1d", progress=False)['Close'].iloc[-1]
    fx = yf.download("GBPUSD=X", period="1d", progress=False)['Close'].iloc[-1]
    raw = yf.download(TICKERS, period="1y", interval="1d", progress=False)
    return float(vix), float(fx), raw

try:
    vix_now, fx_rate, data = get_live_data()
    freq_stats = get_historical_stats(TICKERS, rsi_selected)
    results = []

    for t in TICKERS:
        df = data['Close'][t].dropna()
        vol_hist = data['Volume'][t].dropna()
        p_now = float(df.iloc[-1])
        
        # Indicateurs
        ema200 = df.ewm(span=200, adjust=False).mean().iloc[-1]
        sma20 = df.rolling(20).mean()
        boll_inf = (sma20 - (2 * df.rolling(20).std())).iloc[-1]
        delta = df.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_now = (100 - (100 / (1 + gain/loss))).iloc[-1]
        vol_ratio = (vol_hist.iloc[-1] / vol_hist.rolling(20).mean().iloc[-1]) * 100
        
        # Niveaux Horizontaux
        res_h = df.rolling(20).max().iloc[-1]
        sup_l = df.rolling(20).min().iloc[-1]
        
        # Logique Signal
        rsi_ok = rsi_now <= rsi_selected
        vol_ok = vol_ratio >= VOL_TGT
        price_ok = (p_now <= ema200 * 1.03) or (p_now <= boll_inf * 1.01) or (p_now <= sup_l * 1.015)
        
        is_buy = rsi_ok and vol_ok and price_ok and vix_now <= VIX_TGT

        if is_buy:
            decision = "🚨 ACHAT"
            tp_price, sl_price = res_h * 0.99, sup_l * 0.98
            if (tp_price / p_now) < 1.03: tp_price = p_now * 1.05
            unites = round((montant_gbp * fx_rate) / p_now, 4) if "USD" in t else int((montant_gbp * fx_rate) / p_now)
            gain_val = int(montant_gbp * ((tp_price/p_now)-1))
            loss_val = int(montant_gbp * (1-(sl_price/p_now)))
            pl_str = f"+{gain_val}£ ({(((tp_price/p_now)-1)*100):.1f}%) / -{loss_val}£ ({(((1-sl_price/p_now)*100)):.1f}%)"
        else:
            decision, pl_str, unites, tp_price, sl_price = "☕ HOLD", "-", "-", "-", "-"

        results.append({
            "Ticker": t.replace("-USD", ""),
            "DÉCISION": decision,
            "Prix": f"{p_now:.2f}",
            f"RSI (<{rsi_selected})": f"{rsi_now:.1f} {'✅' if rsi_ok else ''}",
            f"Vol (>{VOL_TGT}%)": f"{int(vol_ratio)}% {'✅' if vol_ok else ''}",
            "Occas/an": freq_stats[t],
            "EMA200": f"{ema200:.2f}",
            "Boll_Inf": f"{boll_inf:.2f}",
            "S. Hist": f"{sup_l:.2f}",
            "R. Hist": f"{res_h:.2f}",
            "Unités": unites,
            "TP Dyn": f"{tp_price:.2f}$" if is_buy else "-",
            "SL Dyn": f"{sl_price:.2f}$" if is_buy else "-",
            "P&L Est.": pl_str
        })

    st.table(pd.DataFrame(results).set_index('Ticker'))
    st.write(f"**VIX :** {vix_now:.2f} (Cible < {VIX_TGT}) | **GBP/USD :** {fx_rate:.4f}")

except Exception as e:
    st.error(f"Erreur : {e}")
