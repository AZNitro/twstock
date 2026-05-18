# 台股 K 線查詢系統

## 快速啟動

### 本地開發
```bash
# 安裝依賴
pip install --break-system-packages -r requirements.txt

# 啟動（需要設定 FINMIND_TOKEN）
export FINMIND_TOKEN="your_token_here"
bash start.sh
```

### Docker
```bash
export FINMIND_TOKEN="your_token_here"
docker-compose up --build
```

打開瀏覽器：
- **Streamlit UI**: http://localhost:8501
- **FastAPI Docs**: http://localhost:8000/docs

## 功能

- [x] 股票日K查詢（FinMind API）
- [x] Plotly 互動式 K線圖（支援放大/縮小/拖曳）
- [x] MA5 / MA20 / MA60 均線疊加
- [x] 成交量長條圖（紅漲/綠跌）
- [x] SQLite 本地快取
- [x] 日K / 週K / 月K / 分K 頻率切換

## 架構

```
backend/main.py   — FastAPI（統一 API 閘口）
frontend/app.py   — Streamlit（圖形介面）
```

## 技術堆疊

| 層次 | 工具 |
|------|------|
| 前端 | Streamlit |
| 圖表 | Plotly |
| 後端 | FastAPI |
| 資料源 | FinMind API |
| 快取 | SQLite |

## 預計擴充

- [ ] KD、RSI、MACD 技術指標
- [ ] 回測框架
- [ ] 多股票比較
- [ ] 策略績效報表