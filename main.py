"""
Backend de Dados de Ações Brasileiras
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from datetime import datetime, timedelta
from typing import Optional

app = FastAPI(title="API de Ações BR", version="1.0.0")

# CORS - PERMITE QUALQUER ORIGEM
@app.middleware("http")
async def add_cors_headers(request, call_next):
    if request.method == "OPTIONS":
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# Cache
cache = {}
CACHE_TTL_MINUTES = 5

def get_from_cache(key: str) -> Optional[dict]:
    if key in cache:
        data, timestamp = cache[key]
        if datetime.now() - timestamp < timedelta(minutes=CACHE_TTL_MINUTES):
            return data
    return None

def save_to_cache(key: str, data: dict):
    cache[key] = (data, datetime.now())

# BrAPI
BRAPI_BASE_URL = "https://brapi.dev/api"

async def fetch_brapi(endpoint: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BRAPI_BASE_URL}{endpoint}")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erro BrAPI")
        data = response.json()
        if "results" not in data or len(data["results"]) == 0:
            raise HTTPException(status_code=404, detail="Ticker não encontrado")
        return data["results"][0]

# Endpoints
@app.get("/")
async def root():
    return {"status": "online", "message": "API de Ações BR"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/quote/{ticker}")
async def get_quote(ticker: str):
    ticker = ticker.upper().strip()
    cache_key = f"quote_{ticker}"
    cached = get_from_cache(cache_key)
    if cached:
        return {"source": "cache", "data": cached}
    data = await fetch_brapi(f"/quote/{ticker}")
    save_to_cache(cache_key, data)
    return {"source": "api", "data": data}

@app.get("/quote/{ticker}/full")
async def get_quote_full(ticker: str):
    ticker = ticker.upper().strip()
    cache_key = f"quote_full_{ticker}"
    cached = get_from_cache(cache_key)
    if cached:
        return {"source": "cache", "data": cached}
    data = await fetch_brapi(f"/quote/{ticker}?fundamental=true&dividends=true")
    save_to_cache(cache_key, data)
    return {"source": "api", "data": data}

@app.get("/quote/{ticker}/history")
async def get_history(ticker: str, range: str = "1mo"):
    ticker = ticker.upper().strip()
    cache_key = f"history_{ticker}_{range}"
    cached = get_from_cache(cache_key)
    if cached:
        return {"source": "cache", "data": cached}
    data = await fetch_brapi(f"/quote/{ticker}?range={range}&interval=1d")
    save_to_cache(cache_key, data)
    return {"source": "api", "data": data}

@app.get("/quotes")
async def get_multiple(tickers: str):
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    results = []
    for ticker in ticker_list:
        try:
            cache_key = f"quote_{ticker}"
            cached = get_from_cache(cache_key)
            if cached:
                results.append({"ticker": ticker, "source": "cache", "data": cached})
            else:
                data = await fetch_brapi(f"/quote/{ticker}")
                save_to_cache(cache_key, data)
                results.append({"ticker": ticker, "source": "api", "data": data})
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
