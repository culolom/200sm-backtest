import os
import pandas as pd
from typing import List


DATA_DIR = "data"


def list_symbols() -> List[str]:
    """列出所有可用的 CSV（不含 .csv 副檔名）"""
    if not os.path.exists(DATA_DIR):
        return []

    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    return [os.path.splitext(f)[0] for f in files]


def load_price(symbol: str) -> pd.DataFrame:
    """
    從 data/{symbol}.csv 載入資料
    需求欄位：Date, Open, High, Low, Close, Volume
    """
    path = os.path.join(DATA_DIR, f"{symbol}.csv")

    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到檔案：{path}")

    df = pd.read_csv(path)

    # 基本清洗
    df.columns = [c.strip().capitalize() for c in df.columns]

    required_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"{symbol}.csv 缺少必要欄位：{col}")

    # 日期處理
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.drop_duplicates(subset=["Date"]).sort_values("Date")
    df = df.set_index("Date")

    # 統一欄位
    df["Price"] = df["Close"].astype(float)

    # 日報酬
    df["Return"] = df["Price"].pct_change().fillna(0)

    return df
