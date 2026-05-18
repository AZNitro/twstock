"""
技術指標計算模組
全部從日K OHLCV 自己算出，不依賴第三方指標庫
"""
import pandas as pd
import numpy as np


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    傳入 OHLCV DataFrame（columns: Open, High, Low, Close, Volume）
    回傳附加了所有技術指標的 DataFrame
    """
    df = df.copy()

    # ── 均線 MA ──
    for window in [5, 10, 20, 60, 120, 240]:
        df[f"MA{window}"] = df["Close"].rolling(window=window, min_periods=1).mean()

    # ── KD ( RSV = (C - L9) / (H9 - L9) × 100 ) ──
    period_k = 9
    period_d = 3

    low_n  = df["Low"].rolling(window=period_k, min_periods=1).min()
    high_n = df["High"].rolling(window=period_k, min_periods=1).max()

    rsv = (df["Close"] - low_n) / (high_n - low_n + 1e-9) * 100
    df["K"] = rsv.ewm(alpha=1/period_d, adjust=False).mean()
    df["D"] = df["K"].ewm(alpha=1/period_d, adjust=False).mean()

    # ── RSI (14日) ──
    period_rsi = 14
    delta = df["Close"].diff()
    gain  = delta.where(delta > 0, 0.0)
    loss  = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period_rsi, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period_rsi, adjust=False).mean()
    rs  = avg_gain / (avg_loss + 1e-9)
    df["RSI"] = 100 - (100 / (rs + 1))

    # ── MACD ──
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["DIF"]   = ema12 - ema26
    df["MACD"]  = df["DIF"].ewm(span=9,  adjust=False).mean()    # Signal
    df["MACD_B"] = df["DIF"] - df["MACD"]                          # Histogram

    # ── 乖離率 (Bias) ──
    df["BIAS5"]  = (df["Close"] - df["MA5"])  / df["MA5"]  * 100
    df["BIAS20"] = (df["Close"] - df["MA20"]) / df["MA20"] * 100

    # ── 威廉指標 %R (14日) ──
    period_w = 14
    high_w = df["High"].rolling(window=period_w, min_periods=1).max()
    low_w  = df["Low"].rolling(window=period_w, min_periods=1).min()
    df["WILLiams"] = -100 * (high_w - df["Close"]) / (high_w - low_w + 1e-9)

    return df
