#!/bin/bash
# 啟動腳本：同時運行 FastAPI + Streamlit
set -e

echo "=== FastAPI 啟動中 (port 8000) ==="
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "=== Streamlit 啟動中 (port 8501) ==="
python3 -m streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 &
STREAMLIT_PID=$!

echo "=== 服務已啟動 ==="
echo "FastAPI:   http://localhost:8000 (API)"
echo "Streamlit: http://localhost:8501 (UI)"
echo "API Health: http://localhost:8000/health"

# 等待任一程序結束
trap "kill $API_PID $STREAMLIT_PID 2>/dev/null" EXIT
wait