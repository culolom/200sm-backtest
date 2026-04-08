import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 網頁佈局 ---
st.set_page_config(page_title="倉鼠量化戰情室：融資抄底監控", layout="wide")

st.title("🐹 倉鼠量化戰情室：大盤融資維持率監控")
st.markdown("> **修正更新 3.0：** 已根據 API 錯誤回饋，修正 Dataset 名稱對齊最新規範。")

# --- 側邊欄參數 ---
with st.sidebar:
    st.header("⚙️ 設定參數")
    default_start = datetime.now() - timedelta(days=3*365)
    start_date = st.date_input("資料起始日期", value=default_start)
    
    st.divider()
    buy_line = st.slider("🔴 抄底觸發線 (%)", 130, 160, 150)
    
    st.divider()
    raw_token = st.text_input("FinMind Token (建議填寫)", type="password")
    api_token = raw_token.strip()

# --- 【核心 API 抓取邏輯】 ---
def call_finmind_api(dataset, data_id="", start_dt=None, token=""):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": dataset,
        "data_id": data_id,
        "start_date": str(start_dt),
        "token": token,
    }
    
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code != 200:
            st.error(f"❌ API 請求失敗！狀態碼: {res.status_code}")
            st.warning(f"請檢查參數或 Token 是否有效。")
            return pd.DataFrame()
            
        res_data = res.json()
        if res_data.get('msg') == 'success':
            return pd.DataFrame(res_data['data'])
        else:
            st.error(f"⚠️ API 邏輯錯誤: {res_data.get('msg')}")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"🚨 系統連線異常: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_full_data(start_dt, token):
    # 1. 改為正確的大盤價格 Dataset 名稱
    df_price = call_finmind_api("TaiwanStockPrice", "TAIEX", start_dt, token)
    
    # 2. 改為正確的大盤維持率 Dataset 名稱
    df_margin = call_finmind_api("TaiwanTotalExchangeMarginMaintenance", "", start_dt, token)
    
    if df_price.empty or df_margin.empty:
        return None

    # 日期與資料對齊
    df_price['date'] = pd.to_datetime(df_price['date'])
    df_margin['date'] = pd.to_datetime(df_margin['date'])
    
    # 這裡加入一個保護機制，避免欄位名稱不符
    price_col = 'close' if 'close' in df_price.columns else df_price.columns[-1]
    margin_col = 'MarginPurchaseMaintenance' if 'MarginPurchaseMaintenance' in df_margin.columns else df_margin.columns[-1]
    
    df = pd.merge(
        df_price[['date', price_col]], 
        df_margin[['date', margin_col]], 
        on='date', 
        how='inner'
    )
    
    # 統一重新命名，方便繪圖使用
    df.rename(columns={price_col: 'close', margin_col: 'maintenance'}, inplace=True)
    return df.sort_values('date')

# --- 主程式執行 ---
data = fetch_full_data(start_date, api_token)

if data is not None and not data.empty:
    curr_price = data['close'].iloc[-1]
    curr_ratio = data['maintenance'].iloc[-1]
    
    c1, c2 = st.columns(2)
    c1.metric("加權指數 (TAIEX)", f"{curr_price:,.2f}")
    c2.metric("大盤融資維持率", f"{curr_ratio:.2f}%")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
                        subplot_titles=("加權指數", "大盤融資維持率 (%)"), row_heights=[0.7, 0.3])

    fig.add_trace(go.Scatter(x=data['date'], y=data['close'], name="指數", line=dict(color='#FBC02D')), row=1, col=1)
    fig.add_trace(go.Scatter(x=data['date'], y=data['maintenance'], name="維持率", fill='tozeroy', line=dict(color='#26A69A')), row=2, col=1)
    fig.add_hline(y=buy_line, line_dash="dash", line_color="red", row=2, col=1)
    
    fig.update_layout(height=700, template="plotly_dark", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("⌛ 正在抓取資料... 若出現錯誤提示請檢查 Token。")
