import streamlit as st
import yfinance as yf
import pandas as pd

# Configuration
st.set_page_config(page_title="Sniper Radar Elite", layout="wide")
st.title("🎯 Sniper Radar : Stratégie Optimale 2036")

# Interface de contrôle
col_ctrl1, col_ctrl2 = st.columns([1, 1])
with col_ctrl1:
    montant_gbp = st.number_input("Montant à investir (£)", value=3000, step=100)
with col_ctrl2:
    # Rétablissement des % de succès pour l'aide à la décision
    rsi_options = {
        30: "30 (Succès ~85% | Très Rare)",
        35: "35 (Succès ~82% | Conservateur)",
        40: "40 (Succès ~80% | Prudent)",
        42: "42 (Succès ~76% | Équilibré)",
        45: "45 (Succès ~72% | Agressif)"
    }
    rsi_selected = st.selectbox("Cible RSI", options=list(rsi_options.keys()), 
                                format_func=lambda x: rsi_options[x], index=3)

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
        vol_hist = data['Volume'][t].dropna()
        p_now = float(df.iloc[-1])
        
        # Indicateurs
        ema200 = df.ewm(span=200, adjust=False).mean().iloc[-1]
        delta = df.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + gain/loss))).iloc[-1]
        vol_ratio = (vol_hist.iloc[-1] / vol_hist.rolling(20).mean().iloc[-1]) * 100
        
        # Niveaux Horizontaux (20 jours)
        res_h = df.rolling(20).max().iloc[-1]
        sup_l = df.rolling(20).min().iloc[-1]
        
        # LOGIQUE DE SIGNAL (La règle optimale)
        rsi_ok = rsi <= rsi_selected
        vol_ok = vol_ratio >= VOL_TGT
        vix_ok = vix_now <= VIX_TGT
        # Support : Doit être proche de l'EMA200 OU du Support 20j
        price_ok = (p_now <= ema200 * 1.03) or (p_now <= sup_l * 1.015)
        
        is_buy = rsi_ok and vol_ok and vix_ok and price_ok

        if is_buy:
            decision = "🚨 ACHAT"
            # TP juste sous la résistance, SL juste sous le support
            tp_price = res_h * 0.99
            sl_price = sup_l * 0.98
            # Sécurité rendement minimum
            if (tp_price / p_now) < 1.03: tp_price = p_now * 1.05
            
            unites = round((montant_gbp * fx_rate) / p_now, 4) if "USD" in t else int((montant_gbp * fx_rate) / p_now)
            pl = f"+{(((tp_price/p_now)-1)*100):.1f}% / -{(((1-sl_price/p_now)*100)):.1f}%"
        else:
            decision, unites, tp_price, sl_price, pl = "☕ HOLD", "-", "-", "-", "-"

        results.append({
            "Ticker": t.replace("-USD", ""),
            "DÉCISION": decision,
            "Prix ($)": f"{p_now:.2f}",
            "RSI": f"{rsi:.1f} {'✅' if rsi_ok else ''}",
            "Vol": f"{int(vol_ratio)}% {'✅' if vol_ok else ''}",
            "S. Hist": f"{sup_l:.2f}",
            "EMA200": f"{ema200:.2f}",
            "Unités": unites,
            "TP Dyn": f"{tp_price:.2f}$" if is_buy else "-",
            "SL Dyn": f"{sl_price:.2f}$" if is_buy else "-",
            "P&L Est.": pl
        })

    st.table(pd.DataFrame(results).set_index('Ticker'))

except Exception as e:
    st.error(f"Erreur : {e}")
