import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="大盤融資抄底監控", layout="wide")

# 1. 側邊欄參數設定
with st.sidebar:
    st.header("回測參數設定")
    start_date = st.date_input("開始日期", value=pd.to_datetime("2020-01-01"))
    buy_line = st.slider("抄底觸發線 (維持率 %)", 130, 160, 150)
    sell_line = st.slider("獲利/警示線 (維持率 %)", 165, 185, 175)
    # 這裡可以加入 API Token (如果有註冊 FinMind)
    api_token = st.text_input("FinMind Token (選填)", type="password")

# 2. 資料抓取函數
@st.cache_data(ttl=3600) # 快取一小時，避免重複請求
def get_full_data(start_date, token):
    dl = DataLoader()
    if token:
        dl.login(api_variant="token", token=token)
    
    # 抓融資資料
    df_margin = dl.taiwan_stock_margin_purchase_short_sale(
        stock_id="TAIEX", start_date=str(start_date)
    )
    
    # 抓大盤收盤價
    df_price = dl.taiwan_stock_daily(
        stock_id="TAIEX", start_date=str(start_date)
    )
    
    # 合併資料 (根據日期)
    df = pd.merge(df_price[['date', 'close']], 
                  df_margin[['date', 'MarginPurchaseMaintenance']], 
                  on='date')
    return df

# 3. 執行抓取
try:
    df = get_full_data(start_date, api_token)
    st.success(f"成功抓取 {len(df)} 筆交易日資料！")

    # 4. 繪製圖表
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        subplot_titles=("加權指數 K 線", "大盤融資維持率"),
                        row_heights=[0.7, 0.3])

    # 上圖：收盤價
    fig.add_trace(go.Scatter(x=df['date'], y=df['close'], name="加權指數", line=dict(color='gold')), row=1, col=1)

    # 下圖：維持率
    fig.add_trace(go.Scatter(x=df['date'], y=df['MarginPurchaseMaintenance'], 
                             name="融資維持率", fill='tozeroy'), row=2, col=1)

    # 加上你的「標準線」
    fig.add_hline(y=buy_line, line_dash="dash", line_color="red", 
                  annotation_text=f"抄底線 {buy_line}%", row=2, col=1)
    
    fig.update_layout(height=800, template="plotly_dark", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # 5. 簡單數據統計
    current_ratio = df['MarginPurchaseMaintenance'].iloc[-1]
    st.metric("當前融資維持率", f"{current_ratio}%", 
              delta=f"{round(current_ratio - buy_line, 2)}% 距離抄底線")

except Exception as e:
    st.error(f"資料抓取失敗: {e}")
