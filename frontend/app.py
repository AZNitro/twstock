"""
台股 K 線查詢系統 - Streamlit 前端
"""
import os
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ─── Config ───
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(page_title="台股K線查詢", layout="wide")
st.title("📈 台股 K 線查詢系統")

# ─── Sidebar controls ───
st.sidebar.header("查詢條件")

stock_id = st.sidebar.text_input("股票代碼", value="2330").strip()
dataset_labels = {
    "TaiwanStockPrice":     "📅 日K",
    "TaiwanStockWeekPrice": "📆 週K",
    "TaiwanStockMonthPrice":"📆 月K",
    "TaiwanStockKBar":      "⏱ 分K",
}
dataset = st.sidebar.selectbox("頻率", list(dataset_labels.keys()),
                                format_func=lambda x: dataset_labels[x])

# Default date range
end_date   = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
start_input = st.sidebar.date_input("開始日期", datetime.strptime(start_date, "%Y-%m-%d"))
end_input   = st.sidebar.date_input("結束日期", datetime.strptime(end_date, "%Y-%m-%d"))
start_str = start_input.strftime("%Y-%m-%d")
end_str   = end_input.strftime("%Y-%m-%d")

# MA 參數
st.sidebar.header("技術指標")
ma5_enabled  = st.sidebar.checkbox("MA5",  value=True)
ma20_enabled = st.sidebar.checkbox("MA20", value=True)
ma60_enabled = st.sidebar.checkbox("MA60", value=False)

if st.sidebar.button("🔍 查詢", type="primary"):
    if not stock_id:
        st.warning("請輸入股票代碼")
    else:
        with st.spinner("載入資料中..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/query",
                    json={
                        "stock_id":  stock_id,
                        "start_date": start_str,
                        "end_date":   end_str,
                        "dataset":    dataset,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                result = resp.json()

                if not result["data"]:
                    st.warning("查無資料，請確認股票代碼與日期範圍")
                else:
                    df = pd.DataFrame(result["data"])
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.sort_values("date").reset_index(drop=True)

                    # Rename columns for Plotly (handles both API and cached data)
                    col_map = {
                        "open": "Open", "max": "High", "high": "High",
                        "min": "Low", "low": "Low",
                        "close": "Close",
                        "Trading_Volume": "Volume", "volume": "Volume",
                    }
                    df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)

                    # ── Candlestick + Volume chart ──
                    fig = make_subplots(
                        rows=2, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.05,
                        row_heights=[0.75, 0.25],
                        subplot_titles=(f"{stock_id} {dataset_labels[dataset]}", "成交量"),
                    )

                    # Candlestick
                    fig.add_trace(
                        go.Candlestick(
                            x=df["date"],
                            open=df["Open"],   high=df["High"],
                            low=df["Low"],     close=df["Close"],
                            increasing_line_color="#ff4136",
                            decreasing_line_color="#2ecc40",
                            name="K線",
                        ),
                        row=1, col=1,
                    )

                    # MA lines
                    df["MA5"]  = df["Close"].rolling(5).mean()
                    df["MA20"] = df["Close"].rolling(20).mean()
                    df["MA60"] = df["Close"].rolling(60).mean()

                    if ma5_enabled:
                        fig.add_trace(
                            go.Scatter(x=df["date"], y=df["MA5"],
                                       line=dict(color="#ff9800", width=1.5),
                                       name="MA5"), row=1, col=1)
                    if ma20_enabled:
                        fig.add_trace(
                            go.Scatter(x=df["date"], y=df["MA20"],
                                       line=dict(color="#2196f3", width=1.5),
                                       name="MA20"), row=1, col=1)
                    if ma60_enabled:
                        fig.add_trace(
                            go.Scatter(x=df["date"], y=df["MA60"],
                                       line=dict(color="#9c27b0", width=1.5),
                                       name="MA60"), row=1, col=1)

                    # Volume bars (colored by price direction)
                    colors = ["#ff4136" if df["Close"].iloc[i] >= df["Open"].iloc[i]
                              else "#2ecc40" for i in range(len(df))]
                    fig.add_trace(
                        go.Bar(x=df["date"], y=df["Volume"],
                               marker_color=colors, name="成交量"),
                        row=2, col=1,
                    )

                    fig.update_layout(
                        height=700,
                        showlegend=True,
                        xaxis_rangeslider_visible=False,
                        template="plotly_dark",
                    )
                    fig.update_xaxes(title_text="日期", row=2, col=1)
                    fig.update_yaxes(title_text="價格", row=1, col=1)
                    fig.update_yaxes(title_text="成交量", row=2, col=1)

                    st.plotly_chart(fig, use_container_width=True)

                    # ── 摘要 statistics ──
                    col1, col2, col3, col4, col5 = st.columns(5)
                    latest = df.iloc[-1]
                    col1.metric("最新收盤", f"{latest['Close']:.2f}")
                    col2.metric("期間最高", f"{df['High'].max():.2f}")
                    col3.metric("期間最低", f"{df['Low'].min():.2f}")
                    col4.metric("總交易日", len(df))
                    col5.metric("資料筆數", result["rows"])

            except requests.exceptions.ConnectionError:
                st.error("⚠️ 無法連線到 API 伺服器，請確認後端已啟動（uvicorn main:app）")
            except Exception as e:
                st.error(f"查詢失敗：{e}")