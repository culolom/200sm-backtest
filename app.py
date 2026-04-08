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
本工具用於監控台股**大盤融資維持率**。歷史經驗顯示，當維持率跌破 **150%** 時，通常代表市場進入恐慌斷頭潮，是長線佈局的參考點。
""")

# --- 側邊欄參數設定 ---
with st.sidebar:
    st.header("⚙️ 設定參數")
    # 預設從 3 年前開始看，回測較有感
    default_start = datetime.now() - timedelta(days=3*365)
    start_date = st.date_input("資料起始日期", value=default_start)
    
    st.divider()
    
    buy_line = st.slider("🔴 抄底觸發線 (%)", 130, 160, 150, help="低於此線通常代表市場集體斷頭")
    sell_line = st.slider("🟢 警示過熱線 (%)", 165, 185, 175, help="高於此線代表籌碼可能過熱")
    
    st.divider()
    
    api_token = st.text_input("FinMind Token (建議填寫)", type="password", help="註冊 FinMind 免費帳號可獲得，抓取大量資料較穩定")

# --- 資料抓取與處理 ---
@st.cache_data(ttl=3600) # 快取 1 小時
def fetch_quant_data(start_dt, token):
    dl = DataLoader()
    if token:
        dl.login(api_variant="token", token=token)
    
    # 1. 抓取大盤價格 (TAIEX)
    df_price = dl.taiwan_stock_daily(
        stock_id="TAIEX", 
        start_date=str(start_dt)
    )
    
    # 2. 抓取大盤融資維持率 (這是專屬函式，不需帶 stock_id)
    df_margin = dl.taiwan_stock_margin_purchase_maintenance(
        start_date=str(start_dt)
    )
    
    if df_price.empty or df_margin.empty:
        return None

    # 資料清洗：確保日期格式一致並合併
    df_price['date'] = pd.to_datetime(df_price['date'])
    df_margin['date'] = pd.to_datetime(df_margin['date'])
    
    # 合併價格與維持率
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
    # 1. 顯示當前數值看板
    curr_price = data['close'].iloc[-1]
    curr_ratio = data['MarginPurchaseMaintenance'].iloc[-1]
    prev_ratio = data['MarginPurchaseMaintenance'].iloc[-2]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("當前加權指數", f"{curr_price:,.2f}")
    col2.metric("當前融資維持率", f"{curr_ratio:.2f}%", f"{curr_ratio - prev_ratio:.2f}%")
    
    status = "🛡️ 安全區"
    if curr_ratio < buy_line:
        status = "🔥 抄底機會 (斷頭潮)"
    elif curr_ratio > sell_line:
        status = "⚠️ 籌碼過熱"
    col3.metric("市場狀態評估", status)

    # 2. 繪製雙層圖表
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.1, 
        subplot_titles=("加權指數 (TAIEX)", "大盤融資維持率 (%)"),
        row_heights=[0.7, 0.3]
    )

    # 上圖：收盤價
    fig.add_trace(
        go.Scatter(x=data['date'], y=data['close'], name="加權指數", line=dict(color='#FBC02D', width=2)),
        row=1, col=1
    )

    # 下圖：維持率
    fig.add_trace(
        go.Scatter(x=data['date'], y=data['MarginPurchaseMaintenance'], 
                   name="維持率", fill='tozeroy', line=dict(color='#26A69A')),
        row=2, col=1
    )

    # 加上抄底線與過熱線
    fig.add_hline(y=buy_line, line_dash="dash", line_color="red", 
                  annotation_text="抄底區域", row=2, col=1)
    fig.add_hline(y=sell_line, line_dash="dash", line_color="orange", 
                  annotation_text="過熱區域", row=2, col=1)

    fig.update_layout(height=700, template="plotly_dark", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # 3. 顯示原始資料 (可選)
    with st.expander("查看原始數據"):
        st.dataframe(data.sort_values('date', ascending=False), use_container_width=True)

else:
    st.warning("⚠️ 無法抓取資料。請檢查：1. 是否正確輸入 Token 2. 網路連線 3. 起始日期是否為休市日")
