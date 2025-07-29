from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime
from decimal import Decimal
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT = "take_profit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"
    BOTH = "both"


class CreateOrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    type: OrderType
    amount: Decimal = Field(gt=0)
    price: Optional[Decimal] = Field(None, gt=0)
    stop_price: Optional[Decimal] = Field(None, gt=0)
    time_in_force: Optional[Literal["GTC", "IOC", "FOK", "GTX"]] = "GTC"
    post_only: Optional[bool] = False
    reduce_only: Optional[bool] = False
    client_order_id: Optional[str] = None


class OrderResponse(BaseModel):
    id: str
    client_order_id: Optional[str] = None
    symbol: str
    side: str  # Changed from OrderSide enum to str
    type: str  # Changed from OrderType enum to str
    status: str  # Changed from OrderStatus enum to str
    price: Optional[float] = None
    average_price: Optional[float] = None
    amount: float
    filled: float
    remaining: float
    fee: Optional[float] = None
    fee_currency: Optional[str] = None
    timestamp: datetime
    updated: Optional[datetime] = None
    # Additional fields for TP/SL identification
    stop_price: Optional[float] = None
    trigger_price: Optional[float] = None
    reduce_only: Optional[bool] = None
    post_only: Optional[bool] = None
    time_in_force: Optional[str] = None
    # Raw order data for debugging
    raw_type: Optional[str] = None


class CancelOrderRequest(BaseModel):
    order_id: str
    symbol: Optional[str] = None


class Position(BaseModel):
    symbol: str
    side: str  # Changed from PositionSide enum to str
    size: float
    entry_price: float
    mark_price: float
    liquidation_price: Optional[float] = None
    unrealized_pnl: float
    realized_pnl: float
    margin: float
    leverage: int
    percentage: float
    timestamp: datetime
    # TP/SL order prices
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None