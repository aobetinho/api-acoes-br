# 🇧🇷 API de Ações Brasileiras

Backend simples para consultar dados de ações da B3 via BrAPI.

## Endpoints

| Endpoint | Descrição | Exemplo |
|----------|-----------|---------|
| `GET /` | Info da API | - |
| `GET /health` | Status | - |
| `GET /quote/{ticker}` | Cotação simples | `/quote/PETR4` |
| `GET /quote/{ticker}/full` | Cotação + fundamentos | `/quote/PETR4/full` |
| `GET /quote/{ticker}/history` | Dados históricos | `/quote/PETR4/history?range=3mo` |
| `GET /quotes` | Múltiplas cotações | `/quotes?tickers=PETR4,VALE3` |

## Ranges disponíveis para histórico

- `1d` - 1 dia
- `5d` - 5 dias
- `1mo` - 1 mês
- `3mo` - 3 meses
- `6mo` - 6 meses
- `1y` - 1 ano
- `2y` - 2 anos
- `5y` - 5 anos

## Cache

Os dados são cacheados por 5 minutos para economizar chamadas à API.

## Deploy no Railway

1. Faça fork/upload deste repositório no GitHub
2. Conecte o Railway ao seu GitHub
3. Selecione o repositório
4. Railway detecta automaticamente e faz deploy

## Tecnologias

- Python 3.11+
- FastAPI
- httpx
- uvicorn
