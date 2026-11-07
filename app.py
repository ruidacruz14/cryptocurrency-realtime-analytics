
import sqlite3
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ---------------- KONFIGURASAUN ----------------
DB_PATH = "crypto_data.db"
API_BASE = "https://api.binance.com/api/v3"

KOIN = {
    "Bitcoin": "BTCUSDT",
    "Ethereum": "ETHUSDT",
    "BNB": "BNBUSDT",
    "Solana": "SOLUSDT",
}

st.set_page_config(
    page_title="Analiza Cryptocurrency Real-Time",
    page_icon="₿",
    layout="wide",
)

# ---------------- DATABASE ----------------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                coin TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                price_change_percent REAL,
                volume REAL,
                quote_volume REAL,
                high_24h REAL,
                low_24h REAL
            )
        """)
        conn.commit()


# Rai dadus merkadu iha database
def save_rows(rows):
    if not rows:
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany("""
            INSERT INTO market_data
            (timestamp, coin, symbol, price, price_change_percent,
             volume, quote_volume, high_24h, low_24h)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()


# Foti istória dadus husi database
def load_history(limit=2000):
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM market_data ORDER BY id DESC LIMIT ?",
            conn,
            params=(limit,),
        )

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp")

    return df


# ---------------- HALO REKOLHA DADUS ----------------
@st.cache_data(ttl=4, show_spinner=False)
def fetch_market_data():
    results = []
    errors = []
    timestamp = datetime.now(timezone.utc).isoformat()

    for coin, symbol in KOIN.items():
        try:
            response = requests.get(
                f"{API_BASE}/ticker/24hr",
                params={"symbol": symbol},
                timeout=10,
            )

            response.raise_for_status()
            item = response.json()

            results.append({
                "timestamp": timestamp,
                "coin": coin,
                "symbol": symbol,
                "price": float(item["lastPrice"]),
                "price_change_percent": float(item["priceChangePercent"]),
                "volume": float(item["volume"]),
                "quote_volume": float(item["quoteVolume"]),
                "high_24h": float(item["highPrice"]),
                "low_24h": float(item["lowPrice"]),
            })

        except (requests.RequestException, KeyError, ValueError) as exc:
            errors.append(f"{symbol}: {exc}")

    return results, errors


# ---------------- DASHBOARD PRINCIPAL ----------------
init_db()

st.title("₿ SISTEMA ANALIZA CRYPTOCURRENCY REAL-TIME")

st.caption(
    "Monitorizasaun merkadu Cryptocurrency iha tempu real "
    "uza Binance API | Atualizasaun kada segundu 5"
)

# Atualiza dashboard automaticamente kada segundu 5
st_autorefresh(interval=5000, key="crypto_refresh")

with st.spinner("Hasai dadus merkadu hela..."):
    market, errors = fetch_market_data()


# Rai dadus foun ba database
if market:
    rows = [
        (
            item["timestamp"], item["coin"], item["symbol"],
            item["price"], item["price_change_percent"],
            item["volume"], item["quote_volume"],
            item["high_24h"], item["low_24h"],
        )
        for item in market
    ]

    save_rows(rows)


# Hatudu mensajen erro
if errors:
    for error in errors:
        st.warning(f"La konsege foti dadus: {error}")


if not market:
    st.error(
        "Dadus merkadu seidauk konsege hetan. "
        "Favor haree koneksaun internet ka koko fali."
    )
    st.stop()


# ---------------- REZUMU PRESU ----------------
st.subheader("Rezumu Presu Cryptocurrency")

cols = st.columns(len(market))

for col, item in zip(cols, market):
    change = item["price_change_percent"]

    col.metric(
        label=f'{item["coin"]} ({item["symbol"]})',
        value=f'${item["price"]:,.4f}',
        delta=f"{change:+.2f}% (oras 24)",
    )


st.divider()


# ---------------- INFORMASAUN SISTEMA ----------------
left, right = st.columns([2, 1])

with left:
    st.subheader("Grafiku Mudansa Presu")

    selected_coin = st.selectbox(
        "Hili Cryptocurrency",
        list(KOIN.keys())
    )

with right:
    st.subheader("Informasaun Sistema")

    st.write(
        f"**Oras Atualizasaun:** "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    st.write("**Intervalu Atualizasaun:** Segundu 5")
    st.write(f"**Total Ativu ne'ebé Monitoriza:** {len(KOIN)}")


# ---------------- GRAFIKU ISTÓRIA PRESU ----------------
history = load_history()

coin_history = (
    history[history["coin"] == selected_coin]
    if not history.empty
    else pd.DataFrame()
)

if not coin_history.empty:

    chart = px.line(
        coin_history,
        x="timestamp",
        y="price",
        title=f"Istória Presu {selected_coin}",
        labels={
            "timestamp": "Oras",
            "price": "Presu (USDT)",
        },
    )

    chart.update_layout(hovermode="x unified")

    st.plotly_chart(chart, use_container_width=True)

else:
    st.info(
        "Dadus istória seidauk sufisiente. "
        "Grafiku sei mosu depois atualizasaun balun."
    )


# ---------------- GRAFIKU VOLUME NEGOSIU ----------------
st.subheader("Volume Negosiu Durante Oras 24")

volume_df = pd.DataFrame(market)

volume_chart = px.bar(
    volume_df,
    x="coin",
    y="quote_volume",
    color="coin",
    labels={
        "coin": "Cryptocurrency",
        "quote_volume": "Volume Negosiu (USDT)",
    },
)

st.plotly_chart(volume_chart, use_container_width=True)


# ---------------- TABELA DADUS MERKADU ----------------
st.subheader("Dadus Merkadu Foun")

table_df = pd.DataFrame(market)[
    [
        "coin",
        "symbol",
        "price",
        "price_change_percent",
        "volume",
        "quote_volume",
        "high_24h",
        "low_24h",
    ]
].rename(columns={
    "coin": "Cryptocurrency",
    "symbol": "Símbolu",
    "price": "Presu (USDT)",
    "price_change_percent": "Mudansa Presu Oras 24 (%)",
    "volume": "Volume Ativu",
    "quote_volume": "Volume Negosiu USDT",
    "high_24h": "Presu Sa'e Liña As",
    "low_24h": "Presu Tun Liña As",
})

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True
)


# ---------------- ISTÓRIA DADUS NE'EBÉ RAI ----------------
st.subheader("Istória Dadus ne'ebé Rai Ona")

st.caption(
    f"Total dadus istória ne'ebé hatudu: {len(history):,} liña"
)

if not history.empty:

    st.dataframe(
        history.tail(20).sort_values(
            "timestamp",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )

    # Download istória dadus iha formatu CSV
    csv = history.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Istória Dadus (CSV)",
        csv,
        "istoria_crypto.csv",
        "text/csv"
    )


# ---------------- INFORMASAUN FONTE DADUS ----------------
st.caption(
    "Fonte Dadus: Binance Public Market API. "
    "Dadus hirak ne'e uza ba monitorizasaun no análize, "
    "la'ós konsellu investimentu."
)
