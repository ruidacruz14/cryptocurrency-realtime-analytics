
import sqlite3
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh


# =========================================================
# 1. KONFIGURASAUN SISTEMA
# =========================================================

st.set_page_config(
    page_title="Cryptocurrency Real-Time Analytics",
    page_icon="₿",
    layout="wide"
)

DB_PATH = "crypto_data.db"

API_BASE = "https://api.coinpaprika.com/v1"

COINS = {
    "Bitcoin": "btc-bitcoin",
    "Ethereum": "eth-ethereum",
    "BNB": "bnb-binance-coin",
    "Solana": "sol-solana"
}


# =========================================================
# 2. ESTILU DASHBOARD
# =========================================================

st.markdown("""
<style>
    .main {
        background-color: #f7f9fc;
    }

    .block-container {
        padding-top: 1.5rem;
    }

    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #e6eaf0;
        padding: 15px;
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# 3. DATABASE SQLITE
# =========================================================

def init_db():
    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            coin TEXT,
            symbol TEXT,
            price REAL,
            price_change_percent REAL,
            volume REAL
        )
    """)

    conn.commit()
    conn.close()


def save_rows(rows):
    if not rows:
        return

    conn = sqlite3.connect(DB_PATH)

    conn.executemany("""
        INSERT INTO market_data (
            timestamp,
            coin,
            symbol,
            price,
            price_change_percent,
            volume
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        (
            row["timestamp"],
            row["coin"],
            row["symbol"],
            row["price"],
            row["price_change_percent"],
            row["volume"]
        )
        for row in rows
    ])

    conn.commit()
    conn.close()


def load_history(limit=2000):
    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query(
        """
        SELECT *
        FROM market_data
        ORDER BY id DESC
        LIMIT ?
        """,
        conn,
        params=(limit,)
    )

    conn.close()

    if not df.empty:
        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
            utc=True
        )

        df = df.sort_values("timestamp")

    return df


# =========================================================
# 4. FET DADUS HUSI COINPAPRIKA API
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_data():

    results = []
    errors = []

    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        response = requests.get(
            f"{API_BASE}/tickers",
            params={"quotes": "USD"},
            headers={
                "Accept": "application/json",
                "User-Agent": "CryptoRealTimeAnalytics/1.0"
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        data_by_id = {
            item["id"]: item
            for item in data
        }

        for coin, coin_id in COINS.items():

            item = data_by_id.get(coin_id)

            if item is None:
                errors.append(
                    f"Dadus {coin} la hetan iha API."
                )
                continue

            usd = item.get("quotes", {}).get("USD", {})

            price = usd.get("price")

            if price is None:
                errors.append(
                    f"Presu {coin} la disponivel."
                )
                continue

            results.append({
                "timestamp": timestamp,
                "coin": coin,
                "symbol": item.get("symbol", ""),
                "price": float(price),
                "price_change_percent": float(
                    usd.get("percent_change_24h") or 0
                ),
                "volume": float(
                    usd.get("volume_24h") or 0
                )
            })

    except requests.exceptions.Timeout:
        errors.append(
            "API timeout. Favor koko fali."
        )

    except requests.exceptions.HTTPError as exc:
        errors.append(
            f"Erro HTTP husi API: {exc}"
        )

    except requests.exceptions.RequestException as exc:
        errors.append(
            f"Problema koneksaun API: {exc}"
        )

    except (KeyError, ValueError, TypeError) as exc:
        errors.append(
            f"Erro prosesamentu dadus: {exc}"
        )

    return results, errors


# =========================================================
# 5. FORMATU VALOR
# =========================================================

def format_price(value):
    if pd.isna(value):
        return "N/A"

    if value < 1:
        return f"${value:,.6f}"

    return f"${value:,.2f}"


# =========================================================
# 6. INICIALIZA SISTEMA
# =========================================================

init_db()

st.title("₿ Cryptocurrency Real-Time Analytics")

st.caption(
    "Sistema monitorizasaun presu, volume no mudansa merkadu cryptocurrency."
)

st.markdown("---")


# =========================================================
# 7. SIDEBAR
# =========================================================

st.sidebar.title("⚙️ Kontrolu Dashboard")

selected_coin = st.sidebar.selectbox(
    "Hili Cryptocurrency",
    list(COINS.keys())
)

history_limit = st.sidebar.selectbox(
    "Kuidadu dadus historiku",
    [100, 500, 1000, 2000, 5000],
    index=3
)

st.sidebar.markdown("---")

st.sidebar.info(
    "Dashboard atualiza kada 5 minutus."
)

if st.sidebar.button("🔄 Atualiza Dadus Agora"):
    fetch_market_data.clear()
    st.rerun()


# =========================================================
# 8. AUTO REFRESH
# =========================================================

st_autorefresh(
    interval=300000,
    key="crypto_refresh"
)


# =========================================================
# 9. FET DADUS MERKADU
# =========================================================

with st.spinner("Hela foti dadus cryptocurrency..."):

    market_rows, api_errors = fetch_market_data()

    if market_rows:
        save_rows(market_rows)

df = load_history()


# =========================================================
# 10. STATUS API
# =========================================================

if market_rows:
    st.success(
        f"API konekta ho susesu. Dadus {len(market_rows)} hetan."
    )
else:
    st.warning(
        "La konsege hetan dadus foun. Sistema sei buka dadus historiku."
    )

for error in api_errors:
    st.warning(error)


# =========================================================
# 11. DASHBOARD PRINCIPAL
# =========================================================

if not df.empty:

    # Dadus ikus ba cryptocurrency ida-idak
    latest = (
        df.sort_values("timestamp")
        .groupby("coin")
        .tail(1)
        .copy()
    )

    latest = latest.set_index("coin")

    # -----------------------------------------------------
    # KPI METRICS
    # -----------------------------------------------------

    st.subheader("📊 Rezumu Merkadu")

    metric_columns = st.columns(4)

    for column, coin in zip(metric_columns, COINS.keys()):

        if coin in latest.index:

            row = latest.loc[coin]

            column.metric(
                label=f"{coin} ({row['symbol']})",
                value=format_price(row["price"]),
                delta=f"{row['price_change_percent']:.2f}%"
            )

        else:

            column.metric(
                label=coin,
                value="N/A"
            )

    st.markdown("---")

    # -----------------------------------------------------
    # GRAFIKU PRESU
    # -----------------------------------------------------

    st.subheader(
        f"📈 Analizaun Presu - {selected_coin}"
    )

    coin_history = df[
        df["coin"] == selected_coin
    ].copy()

    if not coin_history.empty:

        fig_price = px.line(
            coin_history,
            x="timestamp",
            y="price",
            title=f"Historiku Presu {selected_coin}",
            labels={
                "timestamp": "Tempu",
                "price": "Presu USD"
            },
            markers=True
        )

        fig_price.update_layout(
            hovermode="x unified",
            xaxis_title="Tempu",
            yaxis_title="Presu USD"
        )

        st.plotly_chart(
            fig_price,
            use_container_width=True
        )

    else:

        st.info(
            "Seidauk iha dadus historiku ba cryptocurrency ida-ne'e."
        )

    st.markdown("---")

    # -----------------------------------------------------
    # GRAFIKU VOLUME 24H
    # -----------------------------------------------------

    st.subheader("📊 Komparasaun Volume 24H")

    latest_volume = (
        df.sort_values("timestamp")
        .groupby("coin")
        .tail(1)
        .copy()
    )

    fig_volume = px.bar(
        latest_volume,
        x="coin",
        y="volume",
        color="coin",
        text="volume",
        title="Volume Transasaun Cryptocurrency 24H",
        labels={
            "coin": "Cryptocurrency",
            "volume": "Volume USD"
        }
    )

    fig_volume.update_traces(
        texttemplate="$%{y:.3s}",
        textposition="outside"
    )

    fig_volume.update_layout(
        showlegend=False,
        xaxis_title="Cryptocurrency",
        yaxis_title="Volume USD"
    )

    st.plotly_chart(
        fig_volume,
        use_container_width=True
    )

    st.markdown("---")

    # -----------------------------------------------------
    # TABELA DADUS MERKADU
    # -----------------------------------------------------

    st.subheader("📋 Dadus Merkadu Mais Foun")

    display_df = latest_volume[
        [
            "coin",
            "symbol",
            "price",
            "price_change_percent",
            "volume",
            "timestamp"
        ]
    ].copy()

    display_df.columns = [
        "Cryptocurrency",
        "Symbol",
        "Presu USD",
        "Mudansa 24H (%)",
        "Volume 24H USD",
        "Data no Oras"
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # -----------------------------------------------------
    # HISTORIKU DADUS
    # -----------------------------------------------------

    st.subheader("🗃️ Historiku Dadus")

    history_df = load_history(history_limit)

    st.dataframe(
        history_df.sort_values(
            "timestamp",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )

    # -----------------------------------------------------
    # DOWNLOAD CSV
    # -----------------------------------------------------

    csv_data = history_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="⬇️ Download Dadus CSV",
        data=csv_data,
        file_name="crypto_market_history.csv",
        mime="text/csv"
    )

    st.markdown("---")

    # -----------------------------------------------------
    # INFORMASAUN SISTEMA
    # -----------------------------------------------------

    st.subheader("ℹ️ Informasaun Sistema")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Dadus",
        f"{len(df):,}"
    )

    col2.metric(
        "Total Cryptocurrency",
        f"{df['coin'].nunique()}"
    )

    last_update = df["timestamp"].max()

    col3.metric(
        "Atualizasaun Ikus",
        last_update.strftime("%Y-%m-%d %H:%M:%S UTC")
        if pd.notna(last_update)
        else "N/A"
    )

else:

    st.error(
        "Seidauk iha dadus. Favor verifica koneksaun internet no API."
    )


# =========================================================
# 12. FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "Cryptocurrency Real-Time Analytics | "
    "Python + Streamlit + CoinPaprika API + SQLite"
)

st.caption(
    "Dadus CoinPaprika atualiza aproximadamente kada 5 minutus. "
    "Dashboard ne'e la'ós sistema trading."
)
