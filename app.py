import streamlit as st
import numpy as np
import pandas as pd
from hamster_data.loader import load_price, list_symbols
import plotly.graph_objects as go


st.set_page_config(page_title="200SMA 回測系統", page_icon="📈", layout="wide")
st.title("📈 200SMA Strategy 回測系統（CSV 模式）")


# -------------------------
# UI：商品 + 日期選擇
# -------------------------
symbols = list_symbols()
if not symbols:
    st.error("⚠ 未找到資料。請把 CSV 放到 data/ 資料夾。")
    st.stop()

symbol = st.selectbox("選擇商品", symbols, index=0)
df = load_price(symbol)

start_date = st.date_input("開始日期", df.index.min())
end_date = st.date_input("結束日期", df.index.max())

window = st.slider("均線天數 (SMA)", 10, 250, 200)
initial_capital = st.number_input("投入本金（元）", value=10000, step=1000)


# -------------------------
# 回測按鈕
# -------------------------
if st.button("開始回測 🚀"):

    df_bt = df.loc[str(start_date):str(end_date)].copy()

    if len(df_bt) < window:
        st.error("資料天數不足，無法計算均線！")
        st.stop()

    # MA
    df_bt["MA"] = df_bt["Price"].rolling(window).mean()
    df_bt = df_bt.dropna().copy()

    # 訊號
    signal = []
    current = 1  # 第一筆強制持有

    for i in range(len(df_bt)):
        if i == 0:
            signal.append(1)
            continue

        prev_price = df_bt["Price"].iloc[i - 1]
        prev_ma = df_bt["MA"].iloc[i - 1]
        price = df_bt["Price"].iloc[i]
        ma = df_bt["MA"].iloc[i]

        if price > ma and prev_price <= prev_ma:
            current = 1
        elif price < ma and prev_price >= prev_ma:
            current = 0

        signal.append(current)

    df_bt["Position"] = signal
    df_bt["Strategy_Return"] = df_bt["Return"] * df_bt["Position"]

    # 資金曲線
    df_bt["Equity_SMA"] = (1 + df_bt["Strategy_Return"]).cumprod()
    df_bt["Equity_BH"] = (1 + df_bt["Return"]).cumprod()

    # 調整本⾦
    df_bt["Capital_SMA"] = df_bt["Equity_SMA"] * initial_capital
    df_bt["Capital_BH"] = df_bt["Equity_BH"] * initial_capital

    # -------------------------
    # KPI
    # -------------------------
    final_sma = df_bt["Capital_SMA"].iloc[-1]
    final_bh = df_bt["Capital_BH"].iloc[-1]

    st.subheader("📌 核心績效")
    col1, col2 = st.columns(2)
    col1.metric("200SMA 最終資產", f"{final_sma:,.0f} 元")
    col2.metric("Buy & Hold 最終資產", f"{final_bh:,.0f} 元")

    # CAGR
    days = (df_bt.index[-1] - df_bt.index[0]).days
    years = days / 365

    cagr_sma = df_bt["Equity_SMA"].iloc[-1] ** (1 / years) - 1
    cagr_bh = df_bt["Equity_BH"].iloc[-1] ** (1 / years) - 1

    col1, col2 = st.columns(2)
    col1.metric("200SMA CAGR", f"{cagr_sma:.2%}")
    col2.metric("Buy&Hold CAGR", f"{cagr_bh:.2%}")

    # -------------------------
    # 圖表
    # -------------------------
    st.subheader("📈 資金曲線")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_bt.index, y=df_bt["Equity_SMA"], name="200SMA"))
    fig.add_trace(go.Scatter(x=df_bt.index, y=df_bt["Equity_BH"], name="Buy&Hold"))

    st.plotly_chart(fig, use_container_width=True)
