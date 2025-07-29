from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
import logging

from backend.models.market import Ticker, OrderBook, SymbolInfo, Trade, Candle
from backend.services.exchange_manager import exchange_manager
from backend.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/tickers", response_model=List[Ticker])
async def get_all_tickers(
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name")
):
    """Get all tickers from the specified exchange"""
    try:
        return await exchange_manager.fetch_all_tickers(exchange)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching tickers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/ticker/{symbol}", response_model=Ticker)
async def get_ticker(
    symbol: str,
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name")
):
    """Get ticker for a specific symbol"""
    try:
        return await exchange_manager.fetch_ticker(exchange, symbol)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching ticker for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/symbol/{symbol}", response_model=SymbolInfo)
async def get_symbol_info(
    symbol: str,
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name")
):
    """Get detailed information about a trading symbol"""
    try:
        return await exchange_manager.fetch_symbol_info(exchange, symbol)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching symbol info for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/orderbook/{symbol}", response_model=OrderBook)
async def get_orderbook(
    symbol: str,
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of price levels")
):
    """Get orderbook for a specific symbol"""
    # This would need implementation in exchange_manager
    raise HTTPException(status_code=501, detail="Orderbook endpoint not yet implemented")


@router.get("/trades/{symbol}", response_model=List[Trade])
async def get_recent_trades(
    symbol: str,
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name"),
    limit: int = Query(default=100, ge=1, le=1000, description="Number of trades")
):
    """Get recent trades for a specific symbol"""
    # This would need implementation in exchange_manager
    raise HTTPException(status_code=501, detail="Trades endpoint not yet implemented")


@router.get("/candles/{symbol}", response_model=List[Candle])
async def get_candles(
    symbol: str,
    interval: str = Query(default="1h", description="Candle interval (1m, 5m, 15m, 1h, 4h, 1d)"),
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name"),
    limit: int = Query(default=100, ge=1, le=1000, description="Number of candles"),
    start_time: Optional[int] = Query(default=None, description="Start time in milliseconds"),
    end_time: Optional[int] = Query(default=None, description="End time in milliseconds")
):
    """Get historical candles for a specific symbol"""
    try:
        candles = await exchange_manager.fetch_ohlcv(exchange, symbol, interval, limit)
        return candles
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching candles for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/exchanges", response_model=List[str])
async def get_available_exchanges():
    """Get list of available exchanges"""
    return await exchange_manager.get_connected_exchanges()