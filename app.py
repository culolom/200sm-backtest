import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 網頁佈局設定 ---
st.set_page_config(page_title="倉鼠量化戰情室：融資抄底監控", layout="wide")

st.title("🐹 倉鼠量化戰情室：大盤融資維持率監控")
st.markdown("""
本工具用於監控台股**大盤融資維持率**。當維持率跌破 **150%** 時，代表市場進入恐慌斷頭潮。
""")

# --- 側邊欄參數設定 ---
with st.sidebar:
    st.header("⚙️ 設定參數")
    default_start = datetime.now() - timedelta(days=3*365)
    start_date = st.date_input("資料起始日期", value=default_start)
    
    st.divider()
    buy_line = st.slider("🔴 抄底觸發線 (%)", 130, 160, 150)
    sell_line = st.slider("🟢 警示過熱線 (%)", 165, 185, 175)
    
    st.divider()
    api_token = st.text_input("FinMind Token (建議填寫)", type="password")

# --- 【核心修正】資料抓取與處理 ---
@st.cache_data(ttl=3600)
def fetch_quant_data(start_dt, token):
    dl = DataLoader()
    if token:
        dl.login(api_variant="token", token=token)
    
    try:
        # 1. 抓取大盤價格 (使用通用 fetch_data 確保不報錯)
        df_price = dl.fetch_data(
            data_id="TaiwanStockDaily",
            stock_id="TAIEX",
            start_date=str(start_dt)
        )
        
        # 2. 抓取大盤融資維持率 (使用官網資料表 ID)
        df_margin = dl.fetch_data(
            data_id="TaiwanStockMarginPurchaseMaintenance",
            start_date=str(start_dt)
        )
        
        if df_price is None or df_margin is None or df_price.empty or df_margin.empty:
            return None

        # 資料清洗與日期轉換
        df_price['date'] = pd.to_datetime(df_price['date'])
        df_margin['date'] = pd.to_datetime(df_margin['date'])
        
        # 合併價格與維持率 (日期必須對齊)
        df = pd.merge(
            df_price[['date', 'close']], 
            df_margin[['date', 'MarginPurchaseMaintenance']], 
            on='date', 
            how='inner'
        )
        return df.sort_values('date')
    
    except Exception as e:
        st.error(f"發生錯誤: {e}")
        return None

# --- 執行主程式 ---
data = fetch_quant_data(start_date, api_token)

if data is not None and not data.empty:
    # 顯示指標看板
    curr_price = data['close'].iloc[-1]
    curr_ratio = data['MarginPurchaseMaintenance'].iloc[-1]
    
    col1, col2 = st.columns(2)
    col1.metric("加權指數", f"{curr_price:,.2f}")
    col2.metric("大盤融資維持率", f"{curr_ratio:.2f}%")

    # 繪製圖表
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.1, 
        subplot_titles=("加權指數 (TAIEX)", "大盤融資維持率 (%)"),
        row_heights=[0.7, 0.3]
    )

    fig.add_trace(go.Scatter(x=data['date'], y=data['close'], name="加權指數", line=dict(color='#FBC02D')), row=1, col=1)
    fig.add_trace(go.Scatter(x=data['date'], y=data['MarginPurchaseMaintenance'], name="維持率", fill='tozeroy', line=dict(color='#26A69A')), row=2, col=1)

    fig.add_hline(y=buy_line, line_dash="dash", line_color="red", row=2, col=1)
    fig.update_layout(height=700, template="plotly_dark", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("⌛ 正在讀取資料，或請檢查您的 API Token 與起始日期。")
