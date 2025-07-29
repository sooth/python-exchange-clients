from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal


class Ticker(BaseModel):
    symbol: str
    base: str
    quote: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    high: Decimal
    low: Decimal
    volume: Decimal
    quote_volume: Decimal
    change: Decimal
    change_percent: Decimal
    timestamp: datetime


class OrderBookLevel(BaseModel):
    price: Decimal
    amount: Decimal
    total: Optional[Decimal] = None


class OrderBook(BaseModel):
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: datetime
    sequence: Optional[int] = None


class Trade(BaseModel):
    id: str
    symbol: str
    price: Decimal
    amount: Decimal
    side: str
    timestamp: datetime


class Candle(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class SymbolInfo(BaseModel):
    symbol: str
    base: str
    quote: str
    active: bool
    type: str  # spot, futures, perpetual
    contract_size: Optional[Decimal] = None
    tick_size: Decimal
    lot_size: Decimal
    min_notional: Optional[Decimal] = None
    max_leverage: Optional[int] = None
    maker_fee: Decimal
    taker_fee: Decimal