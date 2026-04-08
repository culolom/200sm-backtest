import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 網頁佈局 ---
st.set_page_config(page_title="倉鼠量化戰情室：融資抄底監控", layout="wide")

st.title("🐹 倉鼠量化戰情室：大盤融資維持率監控")
st.markdown("> **穩定性更新 2.0：** 加強 API 異常診斷與 Token 容錯。")

# --- 側邊欄參數 ---
with st.sidebar:
    st.header("⚙️ 設定參數")
    default_start = datetime.now() - timedelta(days=3*365)
    start_date = st.date_input("資料起始日期", value=default_start)
    
    st.divider()
    buy_line = st.slider("🔴 抄底觸發線 (%)", 130, 160, 150)
    sell_line = st.slider("🟢 警示過熱線 (%)", 165, 185, 175)
    
    st.divider()
    # 自動清除 Token 可能帶有的前後空白
    raw_token = st.text_input("FinMind Token (建議填寫)", type="password")
    api_token = raw_token.strip()

# --- 【核心 API 抓取邏輯】 ---
def call_finmind_api(dataset, data_id=None, start_dt=None, token=""):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": dataset,
        "start_date": str(start_dt),
        "token": token,
    }
    if data_id:
        params["data_id"] = data_id
        
    try:
        res = requests.get(url, params=params, timeout=15)
        # 檢查 HTTP 狀態碼
        if res.status_code != 200:
            st.error(f"連線失敗，HTTP 狀態碼: {res.status_code}")
            return pd.DataFrame()
            
        res_data = res.json()
        
        # 診斷：如果 API 回傳不是 success，顯示完整內容
        if res_data.get('msg') == 'success':
            return pd.DataFrame(res_data['data'])
        else:
            # 這裡能幫我們抓出到底 API 說了什麼（例如：Invalid Token）
            st.error(f"API 拒絕請求 (Dataset: {dataset})")
            st.warning(f"原始回傳內容: {res_data}")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"系統發生異常: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_full_data(start_dt, token):
    # 1. 抓取大盤價格
    df_price = call_finmind_api("TaiwanStockDaily", "TAIEX", start_dt, token)
    
    # 2. 抓取大盤融資維持率
    df_margin = call_finmind_api("TaiwanStockMarginPurchaseMaintenance", None, start_dt, token)
    
    if df_price is None or df_price.empty or df_margin is None or df_margin.empty:
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

# --- 主程式執行 ---
if st.button("🚀 執行/重新整理資料"):
    st.cache_data.clear() # 強制清除舊快取

data = fetch_full_data(start_date, api_token)

if data is not None and not data.empty:
    curr_price = data['close'].iloc[-1]
    curr_ratio = data['MarginPurchaseMaintenance'].iloc[-1]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("加權指數 (TAIEX)", f"{curr_price:,.2f}")
    c2.metric("大盤融資維持率", f"{curr_ratio:.2f}%")
    
    # 簡單的風險提示
    risk = "🟢 正常"
    if curr_ratio < buy_line: risk = "🔴 斷頭潮 (抄底機會)"
    c3.metric("籌碼狀態", risk)

    # 繪製圖表
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
                        subplot_titles=("加權指數", "大盤融資維持率 (%)"), row_heights=[0.7, 0.3])

    fig.add_trace(go.Scatter(x=data['date'], y=data['close'], name="指數", line=dict(color='#FBC02D')), row=1, col=1)
    fig.add_trace(go.Scatter(x=data['date'], y=data['MarginPurchaseMaintenance'], name="維持率", fill='tozeroy', line=dict(color='#26A69A')), row=2, col=1)
    fig.add_hline(y=buy_line, line_dash="dash", line_color="red", row=2, col=1)
    
    fig.update_layout(height=700, template="plotly_dark", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("⌛ 正在等待 API 回應。如果持續看到此訊息，請檢查您的 Token 是否正確。")
