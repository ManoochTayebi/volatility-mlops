################################################################################
###                                                                          ###
### Created by Mahdi Manoochehrtayebi, 2025                                  ###
###                                                                          ###
################################################################################

# backend/app.py
import uvicorn

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from backend.compute import compute_asset_volatility, compute_portfolio_volatility

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Asset Volatility ---
@app.get("/api")
def api_root():
    return {
        "message": "Volatility API is running",
        "endpoints": [
            "/api/health",
            "/api/asset_volatility",
            "/api/portfolio_volatility",
        ],
    }

@app.get("/api/asset_volatility")
def asset_volatility(asset: str, days: int = Query(5, ge=1, le=7), historical_period: int = Query(30, ge=7, le=365)):
    return compute_asset_volatility(asset, days, historical_period)

# --- Portfolio Volatility ---
class PortfolioRequest(BaseModel):
    assets: List[str]
    days: int = 5
    historical_period: int = 30

@app.post("/api/portfolio_volatility")
def portfolio_volatility(request: PortfolioRequest):
    return compute_portfolio_volatility(request.assets, request.days, request.historical_period)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "volatility-api"}

# Mount the frontend directory to serve static files (after API routes)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# Handle favicon requests
@app.get("/favicon.ico")
def favicon():
    return {"message": "No favicon available"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
