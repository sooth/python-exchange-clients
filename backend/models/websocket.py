from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum


class WSMessageType(str, Enum):
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    INFO = "info"
    TICKER = "ticker"
    ORDERBOOK = "orderbook"
    TRADES = "trades"
    ORDERS = "orders"
    POSITIONS = "positions"
    BALANCE = "balance"


class WSSubscription(BaseModel):
    type: WSMessageType
    channel: str
    symbols: List[str]
    params: Optional[Dict[str, Any]] = None


class WSMessage(BaseModel):
    type: WSMessageType
    channel: Optional[str] = None
    symbol: Optional[str] = None
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sequence: Optional[int] = None


class WSError(BaseModel):
    code: int
    message: str
    details: Optional[Dict[str, Any]] = None