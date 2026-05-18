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

from indicators import compute_indicators

# ─── Config ───
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(page_title="台股K線查詢", layout="wide")
st.title("📈 台股 K 線查詢系統")

# ─── Sidebar controls ───
st.sidebar.header("查詢條件")

stock_id = st.sidebar.text_input("股票代碼", value="2330").strip()

dataset_labels = {
    "TaiwanStockPrice":     "📅 日K",
    "TaiwanStockWeekPrice": "📆 週K（需付費）",
    "TaiwanStockMonthPrice":"📆 月K（需付費）",
    "TaiwanStockKBar":      "⏱ 分K（需付費）",
}
dataset = st.sidebar.selectbox("頻率", list(dataset_labels.keys()),
                                format_func=lambda x: dataset_labels[x])

end_date   = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
start_input = st.sidebar.date_input("開始日期", datetime.strptime(start_date, "%Y-%m-%d"))
end_input   = st.sidebar.date_input("結束日期", datetime.strptime(end_date, "%Y-%m-%d"))
start_str = start_input.strftime("%Y-%m-%d")
end_str   = end_input.strftime("%Y-%m-%d")

# ─── Indicator toggles ───
st.sidebar.header("技術指標")
show_ma     = st.sidebar.checkbox("均線 MA5/10/20/60/120/240", value=True)
show_rsi    = st.sidebar.checkbox("RSI (14日)", value=True)
show_macd   = st.sidebar.checkbox("MACD", value=True)
show_kd     = st.sidebar.checkbox("KD (9日)", value=True)
show_bias   = st.sidebar.checkbox("乖離率 BIAS5/20", value=False)
show_will   = st.sidebar.checkbox("威廉指標 %R (14日)", value=False)

# ─── Query button ───
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

                    # ── Column name normalization ──
                    col_map = {
                        "open":           "Open",
                        "max":            "High", "high": "High",
                        "min":            "Low",  "low":  "Low",
                        "close":          "Close",
                        "Trading_Volume": "Volume", "volume": "Volume",
                    }
                    df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)

                    # ── Compute technical indicators ──
                    df = compute_indicators(df)

                    # ── Count enabled indicators ──
                    extra_rows = sum([show_rsi, show_macd, show_kd, show_bias, show_will])
                    fig = make_subplots(
                        rows=2 + extra_rows, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.05,
                        row_heights=[0.45, 0.10] + [0.08] * extra_rows,
                        subplot_titles=(
                            [f"{stock_id} {dataset_labels[dataset]}"]
                            + ["成交量"]
                            + [n for n, s in [
                                ("RSI (14日)", show_rsi),
                                ("MACD (12/26/9)", show_macd),
                                ("KD (9日)", show_kd),
                                ("乖離率 %", show_bias),
                                ("威廉 %R (14日)", show_will),
                            ] if s]
                        ),
                    )

                    row = 1

                    # ── Candlestick + MA lines ──
                    fig.add_trace(
                        go.Candlestick(
                            x=df["date"],
                            open=df["Open"],  high=df["High"],
                            low=df["Low"],    close=df["Close"],
                            increasing_line_color="#ff4136",
                            decreasing_line_color="#2ecc40",
                            name="K線",
                        ),
                        row=row, col=1,
                    )
                    row += 1

                    # MA lines
                    if show_ma:
                        ma_colors = {
                            "MA5":   "#ff9800",
                            "MA10":  "#4caf50",
                            "MA20":  "#2196f3",
                            "MA60":  "#9c27b0",
                            "MA120": "#ff5722",
                            "MA240": "#795548",
                        }
                        for ma_col, color in ma_colors.items():
                            if ma_col in df.columns:
                                fig.add_trace(
                                    go.Scatter(x=df["date"], y=df[ma_col],
                                               line=dict(color=color, width=1.5),
                                               name=ma_col),
                                    row=1, col=1,
                                )

                    # ── Volume bars ──
                    vol_colors = ["#ff4136" if df["Close"].iloc[i] >= df["Open"].iloc[i]
                                  else "#2ecc40" for i in range(len(df))]
                    fig.add_trace(
                        go.Bar(x=df["date"], y=df["Volume"],
                               marker_color=vol_colors, name="成交量"),
                        row=row, col=1,
                    )
                    row += 1

                    # ── RSI subplot ──
                    if show_rsi:
                        fig.add_trace(
                            go.Scatter(x=df["date"], y=df["RSI"],
                                       line=dict(color="#e91e63", width=1.5),
                                       name="RSI"),
                            row=row, col=1,
                        )
                        fig.update_yaxes(range=[0, 100], row=row, col=1)
                        row += 1

                    # ── MACD subplot ──
                    if show_macd:
                        # Histogram (bars)
                        macd_colors = ["#ff4136" if v >= 0 else "#2ecc40"
                                       for v in df["MACD_B"]]
                        fig.add_trace(
                            go.Bar(x=df["date"], y=df["MACD_B"],
                                   marker_color=macd_colors, name="MACD棒"),
                            row=row, col=1,
                        )
                        # DIF line
                        fig.add_trace(
                            go.Scatter(x=df["date"], y=df["DIF"],
                                       line=dict(color="#2196f3", width=1.2),
                                       name="DIF"),
                            row=row, col=1,
                        )
                        # MACD Signal line
                        fig.add_trace(
                            go.Scatter(x=df["date"], y=df["MACD"],
                                       line=dict(color="#ff9800", width=1.2),
                                       name="MACD"),
                            row=row, col=1,
                        )
                        row += 1

                    # ── KD subplot ──
                    if show_kd:
                        fig.add_trace(
                            go.Scatter(x=df["date"], y=df["K"],
                                       line=dict(color="#2196f3", width=1.5),
                                       name="K"),
                            row=row, col=1,
                        )
                        fig.add_trace(
                            go.Scatter(x=df["date"], y=df["D"],
                                       line=dict(color="#ff9800", width=1.5),
                                       name="D"),
                            row=row, col=1,
                        )
                        fig.update_yaxes(range=[0, 100], row=row, col=1)
                        row += 1

                    # ── Bias subplot ──
                    if show_bias:
                        fig.add_trace(
                            go.Scatter(x=df["date"], y=df["BIAS5"],
                                       line=dict(color="#4caf50", width=1.2),
                                       name="BIAS5"),
                            row=row, col=1,
                        )
                        fig.add_trace(
                            go.Scatter(x=df["date"], y=df["BIAS20"],
                                       line=dict(color="#f44336", width=1.2),
                                       name="BIAS20"),
                            row=row, col=1,
                        )
                        row += 1

                    # ── Williams %R subplot ──
                    if show_will:
                        fig.add_trace(
                            go.Scatter(x=df["date"], y=df["WILLiams"],
                                       line=dict(color="#9c27b0", width=1.5),
                                       name="%R"),
                            row=row, col=1,
                        )
                        # Add -20 and -80 reference lines
                        fig.update_yaxes(range=[-100, 0], row=row, col=1)
                        row += 1

                    # ── Layout update ──
                    fig.update_layout(
                        height=200 + 280 * (1 + extra_rows),
                        showlegend=True,
                        xaxis_rangeslider_visible=False,
                        template="plotly_dark",
                    )
                    fig.update_xaxes(title_text="日期", row=2 + extra_rows, col=1)
                    fig.update_yaxes(title_text="價格",  row=1, col=1)
                    fig.update_yaxes(title_text="成交量", row=2, col=1)

                    st.plotly_chart(fig, use_container_width=True)

                    # ── 摘要 statistics ──
                    latest = df.iloc[-1]
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("最新收盤", f"{latest['Close']:.2f}")
                    col2.metric("期間最高", f"{df['High'].max():.2f}")
                    col3.metric("期間最低", f"{df['Low'].min():.2f}")
                    col4.metric("總交易日", len(df))
                    col5.metric("最後RSI", f"{latest.get('RSI', 0):.1f}" if pd.notna(latest.get('RSI')) else "N/A")

            except requests.exceptions.ConnectionError:
                st.error("⚠️ 無法連線到 API 伺服器，請確認後端已啟動（uvicorn main:app）")
            except Exception as e:
                st.error(f"查詢失敗：{e}")