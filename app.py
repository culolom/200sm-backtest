import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 網頁佈局設定 ---
st.set_page_config(page_title="倉鼠量化戰情室：融資抄底監控", layout="wide")

st.title("🐹 倉鼠量化戰情室：大盤融資維持率監控")
st.markdown("本工具直接透過 REST API 抓取資料，避開套件版本衝突，穩定性最高。")

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

# --- 【API 抓取函數】 ---
def get_finmind_api(dataset, data_id=None, start_date=None, token=""):
    url = "https://api.finmindtrade.com/api/v4/data"
    parameter = {
        "dataset": dataset,
        "start_date": str(start_date),
        "token": token,
    }
    if data_id:
        parameter["data_id"] = data_id
        
    res = requests.get(url, params=parameter)
    data = res.json()
    if data['msg'] == 'success':
        return pd.DataFrame(data['data'])
    else:
        st.error(f"API 抓取失敗: {data['msg']}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_quant_data(start_dt, token):
    # 1. 抓取大盤價格
    df_price = get_finmind_api("TaiwanStockDaily", "TAIEX", start_dt, token)
    
    # 2. 抓取大盤融資維持率
    df_margin = get_finmind_api("TaiwanStockMarginPurchaseMaintenance", None, start_dt, token)
    
    if df_price.empty or df_margin.empty:
        return None

    # 日期轉換與合併
    df_price['date'] = pd.to_datetime(df_price['date'])
    df_margin['date'] = pd.to_datetime(df_margin['date'])
    
    df = pd.merge(
        df_price[['date', 'close']], 
        df_margin[['date', 'MarginPurchaseMaintenance']], 
        on='date', 
        how='inner'
    )
    return df.sort_values('date')

# --- 執行主程式 ---
data = fetch_quant_data(start_date, api_token)

if data is not None and not data.empty:
    curr_price = data['close'].iloc[-1]
    curr_ratio = data['MarginPurchaseMaintenance'].iloc[-1]
    
    c1, c2 = st.columns(2)
    c1.metric("加權指數", f"{curr_price:,.2f}")
    c2.metric("大盤融資維持率", f"{curr_ratio:.2f}%")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
                        subplot_titles=("加權指數 (TAIEX)", "大盤融資維持率 (%)"), row_heights=[0.7, 0.3])

    fig.add_trace(go.Scatter(x=data['date'], y=data['close'], name="加權指數", line=dict(color='#FBC02D')), row=1, col=1)
    fig.add_trace(go.Scatter(x=data['date'], y=data['MarginPurchaseMaintenance'], name="維持率", fill='tozeroy', line=dict(color='#26A69A')), row=2, col=1)
    fig.add_hline(y=buy_line, line_dash="dash", line_color="red", row=2, col=1)
    
    fig.update_layout(height=700, template="plotly_dark", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("⌛ 正在從 API 獲取最新資料...")
