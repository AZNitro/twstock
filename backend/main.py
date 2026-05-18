"""
台股 K 線查詢系統 - FastAPI 後端
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import sqlite3
import os
from datetime import datetime, timedelta

app = FastAPI(title="台股K線API", version="1.0.0")

# CORS 允許 Streamlit 直接呼叫
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config ───
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN", "")
FINMIND_BASE  = "https://api.finmindtrade.com/api/v4/data"
DB_PATH       = os.path.join(os.path.dirname(__file__), "kline_cache.db")

# ─── DB Init ───
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_cache (
            stock_id TEXT,
            dataset  TEXT,
            date     TEXT,
            open, high, low, close, volume REAL,
            fetched_at TEXT,
            PRIMARY KEY (stock_id, dataset, date)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ─── Pydantic Models ───
class QueryReq(BaseModel):
    stock_id: str
    start_date: str   # YYYY-MM-DD
    end_date: str     # YYYY-MM-DD
    dataset: str = "TaiwanStockPrice"  # 日K預設

class QueryResp(BaseModel):
    stock_id: str
    dataset: str
    start_date: str
    end_date: str
    rows: int
    data: list

# ─── Cache helpers ───
def get_cached(stock_id: str, dataset: str, start: str, end: str) -> list:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.execute(
        "SELECT date,open,high,low,close,volume FROM price_cache "
        "WHERE stock_id=? AND dataset=? AND date BETWEEN ? AND ? "
        "ORDER BY date",
        (stock_id, dataset, start, end)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def save_cached(stock_id: str, dataset: str, rows: list):
    now = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(
        "INSERT OR REPLACE INTO price_cache "
        "(stock_id,dataset,date,open,high,low,close,volume,fetched_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        [(stock_id, dataset, r["date"],
          r.get("open"), r.get("max"), r.get("min"),
          r.get("close"), r.get("Trading_Volume"), now) for r in rows]
    )
    conn.commit()
    conn.close()

# ─── FinMind fetch ───
def fetch_finmind(stock_id: str, dataset: str, start: str, end: str) -> list:
    if not FINMIND_TOKEN:
        return []

    params = {
        "dataset": dataset,
        "data_id": stock_id,
        "start_date": start,
        "end_date": end,
        "token": FINMIND_TOKEN,
    }
    try:
        resp = requests.get(FINMIND_BASE, params=params, timeout=15)
        resp.raise_for_status()
        json_data = resp.json()
        data = json_data.get("data", [])
        return data
    except Exception as e:
        print(f"[FinMind Error] {e}")
        return []

# ─── Routes ───
@app.get("/health")
def health():
    return {"status": "ok", "token_set": bool(FINMIND_TOKEN)}

@app.post("/query", response_model=QueryResp)
def query_kline(req: QueryReq):
    # 1. Try cache first
    cached = get_cached(req.stock_id, req.dataset, req.start_date, req.end_date)

    if cached:
        data = [
            {"date": r[0], "open": r[1], "high": r[2],
             "low": r[3], "close": r[4], "volume": r[5]}
            for r in cached
        ]
        return QueryResp(
            stock_id=req.stock_id, dataset=req.dataset,
            start_date=req.start_date, end_date=req.end_date,
            rows=len(data), data=data
        )

    # 2. Fetch from FinMind
    data = fetch_finmind(req.stock_id, req.dataset, req.start_date, req.end_date)
    if data:
        save_cached(req.stock_id, req.dataset, data)

    return QueryResp(
        stock_id=req.stock_id, dataset=req.dataset,
        start_date=req.start_date, end_date=req.end_date,
        rows=len(data), data=data
    )

@app.get("/datasets")
def list_datasets():
    """可用 dataset 對照表"""
    return {
        "TaiwanStockPrice":     "日K",
        "TaiwanStockWeekPrice": "週K",
        "TaiwanStockMonthPrice":"月K",
        "TaiwanStockKBar":      "分K（5/15/30/60分）",
    }