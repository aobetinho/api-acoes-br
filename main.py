"""
Backend de Dados de Ações Brasileiras
=====================================
API simples que consulta a BrAPI e faz cache dos dados.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from datetime import datetime, timedelta
from typing import Optional
import json

app = FastAPI(
    title="API de Ações BR",
    description="Backend para consultar dados de ações brasileiras via BrAPI",
    version="1.0.0"
)

# Permitir acesso de qualquer origem (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# ===========================================
# CACHE SIMPLES EM MEMÓRIA
# ===========================================
cache = {}
CACHE_TTL_MINUTES = 5  # Dados válidos por 5 minutos

def get_from_cache(key: str) -> Optional[dict]:
    """Retorna dados do cache se ainda válidos"""
    if key in cache:
        data, timestamp = cache[key]
        if datetime.now() - timestamp < timedelta(minutes=CACHE_TTL_MINUTES):
            return data
    return None

def save_to_cache(key: str, data: dict):
    """Salva dados no cache"""
    cache[key] = (data, datetime.now())

# ===========================================
# FUNÇÕES DE CONSULTA À BRAPI
# ===========================================
BRAPI_BASE_URL = "https://brapi.dev/api"

async def fetch_quote(ticker: str) -> dict:
    """Busca cotação atual de um ticker"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{BRAPI_BASE_URL}/quote/{ticker}"
        response = await client.get(url)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erro ao consultar BrAPI")
        
        data = response.json()
        
        if "results" not in data or len(data["results"]) == 0:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} não encontrado")
        
        return data["results"][0]

async def fetch_quote_with_details(ticker: str) -> dict:
    """Busca cotação com fundamentos e dividendos"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{BRAPI_BASE_URL}/quote/{ticker}?fundamental=true&dividends=true"
        response = await client.get(url)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erro ao consultar BrAPI")
        
        data = response.json()
        
        if "results" not in data or len(data["results"]) == 0:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} não encontrado")
        
        return data["results"][0]

async def fetch_historical(ticker: str, range_period: str = "1mo") -> dict:
    """Busca dados históricos"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{BRAPI_BASE_URL}/quote/{ticker}?range={range_period}&interval=1d"
        response = await client.get(url)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erro ao consultar BrAPI")
        
        data = response.json()
        
        if "results" not in data or len(data["results"]) == 0:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} não encontrado")
        
        return data["results"][0]

# ===========================================
# ENDPOINTS DA API
# ===========================================

@app.get("/")
async def root():
    """Endpoint raiz - informações da API"""
    return {
        "status": "online",
        "message": "API de Ações Brasileiras",
        "endpoints": {
            "/quote/{ticker}": "Cotação simples",
            "/quote/{ticker}/full": "Cotação com fundamentos",
            "/quote/{ticker}/history": "Dados históricos",
            "/quotes": "Múltiplas cotações",
            "/health": "Status da API"
        },
        "exemplo": "/quote/PETR4"
    }

@app.get("/health")
async def health_check():
    """Verifica se a API está funcionando"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/quote/{ticker}")
async def get_quote(ticker: str):
    """
    Retorna cotação de um ticker
    
    Exemplo: /quote/PETR4
    """
    ticker = ticker.upper().strip()
    cache_key = f"quote_{ticker}"
    
    # Verifica cache
    cached = get_from_cache(cache_key)
    if cached:
        return {"source": "cache", "data": cached}
    
    # Busca na API
    data = await fetch_quote(ticker)
    save_to_cache(cache_key, data)
    
    return {"source": "api", "data": data}

@app.get("/quote/{ticker}/full")
async def get_quote_full(ticker: str):
    """
    Retorna cotação com fundamentos e dividendos
    
    Exemplo: /quote/PETR4/full
    """
    ticker = ticker.upper().strip()
    cache_key = f"quote_full_{ticker}"
    
    # Verifica cache
    cached = get_from_cache(cache_key)
    if cached:
        return {"source": "cache", "data": cached}
    
    # Busca na API
    data = await fetch_quote_with_details(ticker)
    save_to_cache(cache_key, data)
    
    return {"source": "api", "data": data}

@app.get("/quote/{ticker}/history")
async def get_history(ticker: str, range: str = "1mo"):
    """
    Retorna dados históricos
    
    Parâmetros:
    - ticker: código da ação (ex: PETR4)
    - range: período (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y)
    
    Exemplo: /quote/PETR4/history?range=3mo
    """
    ticker = ticker.upper().strip()
    cache_key = f"history_{ticker}_{range}"
    
    # Verifica cache
    cached = get_from_cache(cache_key)
    if cached:
        return {"source": "cache", "data": cached}
    
    # Busca na API
    data = await fetch_historical(ticker, range)
    save_to_cache(cache_key, data)
    
    return {"source": "api", "data": data}

@app.get("/quotes")
async def get_multiple_quotes(tickers: str):
    """
    Retorna cotações de múltiplos tickers
    
    Parâmetro:
    - tickers: lista separada por vírgula (ex: PETR4,VALE3,ITUB4)
    
    Exemplo: /quotes?tickers=PETR4,VALE3,ITUB4
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    results = []
    
    for ticker in ticker_list:
        try:
            cache_key = f"quote_{ticker}"
            cached = get_from_cache(cache_key)
            
            if cached:
                results.append({"ticker": ticker, "source": "cache", "data": cached})
            else:
                data = await fetch_quote(ticker)
                save_to_cache(cache_key, data)
                results.append({"ticker": ticker, "source": "api", "data": data})
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})
    
    return {"results": results}

# ===========================================
# PARA RODAR LOCALMENTE (DESENVOLVIMENTO)
# ===========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
