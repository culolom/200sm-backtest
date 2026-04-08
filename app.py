import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 網頁佈局 ---
st.set_page_config(page_title="倉鼠量化戰情室：融資抄底監控", layout="wide")

st.title("🐹 倉鼠量化戰情室：大盤融資維持率監控")
st.markdown("> **修正更新：** 解決 422 參數錯誤問題，強化 API 通訊穩定度。")

# --- 側邊欄參數 ---
with st.sidebar:
    st.header("⚙️ 設定參數")
    # 建議回測時間拉長，例如 2020 年
    default_start = datetime.now() - timedelta(days=3*365)
    start_date = st.date_input("資料起始日期", value=default_start)
    
    st.divider()
    buy_line = st.slider("🔴 抄底觸發線 (%)", 130, 160, 150)
    
    st.divider()
    # 自動清除 Token 前後空白
    raw_token = st.text_input("FinMind Token (建議填寫)", type="password")
    api_token = raw_token.strip()

# --- 【核心 API 抓取邏輯：修正 422 關鍵】 ---
def call_finmind_api(dataset, data_id="", start_dt=None, token=""):
    url = "https://api.finmindtrade.com/api/v4/data"
    
    # 修正點：確保即使沒有 data_id，也要傳送一個空字串，避開 422 錯誤
    params = {
        "dataset": dataset,
        "data_id": data_id if data_id else "",
        "start_date": str(start_dt),
        "token": token,
    }
    
    try:
        res = requests.get(url, params=params, timeout=15)
        
        # 如果不是 200，抓取伺服器回傳的詳細錯誤訊息
        if res.status_code != 200:
            try:
                error_detail = res.json()
            except:
                error_detail = res.text
            st.error(f"❌ API 請求失敗！狀態碼: {res.status_code}")
            st.warning(f"伺服器訊息: {error_detail}")
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
    # 1. 抓取大盤價格 (代號 TAIEX)
    df_price = call_finmind_api("TaiwanStockDaily", "TAIEX", start_dt, token)
    
    # 2. 抓取大盤融資維持率 (不需特定代號，但傳送空字串)
    df_margin = call_finmind_api("TaiwanStockMarginPurchaseMaintenance", "", start_dt, token)
    
    if df_price.empty or df_margin.empty:
        return None

    # 日期與資料對齊
    df_price['date'] = pd.to_datetime(df_price['date'])
    df_margin['date'] = pd.to_datetime(df_margin['date'])
    
    df = pd.merge(
        df_price[['date', 'close']], 
        df_margin[['date', 'MarginPurchaseMaintenance']], 
        on='date', 
        how='inner'
    )
    return df.sort_values('date')

# --- 主程式執行 ---
data = fetch_full_data(start_date, api_token)

if data is not None and not data.empty:
    curr_price = data['close'].iloc[-1]
    curr_ratio = data['MarginPurchaseMaintenance'].iloc[-1]
    
    c1, c2 = st.columns(2)
    c1.metric("加權指數 (TAIEX)", f"{curr_price:,.2f}")
    c2.metric("大盤融資維持率", f"{curr_ratio:.2f}%")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
                        subplot_titles=("加權指數", "大盤融資維持率 (%)"), row_heights=[0.7, 0.3])

    fig.add_trace(go.Scatter(x=data['date'], y=data['close'], name="指數", line=dict(color='#FBC02D')), row=1, col=1)
    fig.add_trace(go.Scatter(x=data['date'], y=data['MarginPurchaseMaintenance'], name="維持率", fill='tozeroy', line=dict(color='#26A69A')), row=2, col=1)
    fig.add_hline(y=buy_line, line_dash="dash", line_color="red", row=2, col=1)
    
    fig.update_layout(height=700, template="plotly_dark", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("⌛ 正在抓取資料... 若長時間無反應請檢查上方 Token 或錯誤提示。")
