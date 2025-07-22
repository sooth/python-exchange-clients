"""
Exchange Interface - Abstract base class for all exchange implementations

This module defines the unified interface that all exchange adapters must implement.
It provides a consistent API for interacting with different exchanges.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass
import time


# Data structures
@dataclass
class ExchangeOrderRequest:
    """Unified order request structure"""
    symbol: str
    side: str  # "BUY" or "SELL" 
    orderType: str  # "LIMIT" or "MARKET"
    qty: float
    price: Optional[float] = None
    orderLinkId: Optional[str] = None
    timeInForce: str = "GTC"
    
    # BitUnix specific
    positionIdx: Optional[int] = None  # 0: one-way, 1: buy-side, 2: sell-side
    closeOnTrigger: Optional[bool] = None
    reduceOnly: Optional[bool] = None
    
    # General
    tradingType: str = "PERP"  # "PERP" or "SPOT"


@dataclass
class ExchangeOrderResponse:
    """Unified order response structure"""
    orderId: str
    symbol: str
    side: str
    orderType: str
    qty: float
    price: Optional[float]
    status: str
    timeInForce: str
    createTime: int
    clientId: Optional[str] = None
    rawResponse: Optional[Dict] = None
    
    def __init__(self, raw_response: Dict):
        """Initialize from exchange response"""
        self.rawResponse = raw_response
        # Subclasses should override to extract fields


class ExchangeTicker:
    """Unified ticker structure"""
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.lastPrice: float = 0.0
        self.bidPrice: float = 0.0
        self.askPrice: float = 0.0
        self.volume: float = 0.0
        self.price: float = 0.0  # Alias for lastPrice


@dataclass
class ExchangePosition:
    """Unified position structure"""
    symbol: str
    size: float  # Positive for long, negative for short
    entryPrice: float
    markPrice: float
    pnl: float
    pnlPercentage: float
    positionIdx: Optional[int] = None
    side: Optional[str] = None


@dataclass
class ExchangeBalance:
    """Unified balance structure"""
    asset: str
    balance: float
    available: float
    locked: float


@dataclass
class ExchangeOrder:
    """Unified order structure"""
    orderId: str
    symbol: str
    side: str
    orderType: str
    qty: float
    price: Optional[float]
    status: str
    timeInForce: str
    createTime: int
    clientId: Optional[str] = None
    executedQty: Optional[float] = None


# Protocol/Interface definition
class ExchangeProtocol(ABC):
    """
    Abstract base class defining the interface for all exchange implementations.
    """
    
    @abstractmethod
    def fetchTickers(self, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch all tickers"""
        pass
    
    @abstractmethod
    def placeOrder(self, request: ExchangeOrderRequest, completion: Callable[[Tuple[str, Any]], None]):
        """Place an order"""
        pass
    
    @abstractmethod
    def fetchBalance(self, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch account balance"""
        pass
    
    @abstractmethod
    def fetchPositions(self, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch open positions"""
        pass
    
    @abstractmethod
    def fetchOrders(self, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch open orders"""
        pass
    
    @abstractmethod
    def cancelOrder(self, orderID: str = None, clOrderID: str = None, symbol: str = None, completion=None):
        """Cancel an order"""
        pass


# Standard position side constants
class PositionSide:
    """Standard position side constants used across all exchanges"""
    LONG = "LONG"
    SHORT = "SHORT"


# Trading type constants
class TradingType:
    """Trading type constants - default is PERP"""
    PERP = "PERP"
    SPOT = "SPOT"


class ExchangeInterface(ABC):
    """
    Abstract base class defining the interface for all exchange implementations.
    
    All methods follow the callback pattern used by the existing exchanges,
    where completion is a callable that receives a tuple of (status, data).
    Status is either "success" or "failure", and data is the result or exception.
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the exchange (e.g., 'BitUnix', 'LMEX')"""
        pass
    
    @abstractmethod
    def get_symbol_format(self, base_symbol: str) -> str:
        """
        Convert a base symbol to exchange-specific format.
        E.g., 'BTCUSDT' for BitUnix, 'BTC-PERP' for LMEX
        """
        pass
    
    @abstractmethod
    def translate_side_to_exchange(self, side: str) -> str:
        """
        Translate standard side (PositionSide.LONG/SHORT) to exchange-specific format.
        
        Args:
            side: PositionSide.LONG or PositionSide.SHORT
            
        Returns:
            Exchange-specific side string (e.g., 'BUY'/'SELL' for BitUnix)
        """
        pass
    
    @abstractmethod
    def translate_side_from_exchange(self, exchange_side: str) -> str:
        """
        Translate exchange-specific side to standard format.
        
        Args:
            exchange_side: Exchange-specific side (e.g., 'BUY', 'SELL')
            
        Returns:
            Standard side: PositionSide.LONG or PositionSide.SHORT
        """
        pass
    
    # Market Data Methods
    @abstractmethod
    def fetchTickers(self, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch ticker information for all symbols.
        
        Args:
            completion: Callback function that receives (status, data)
                       status: "success" or "failure"
                       data: List[ExchangeTicker] on success, Exception on failure
        """
        pass
    
    @abstractmethod
    def fetchSymbolInfo(self, symbol: str, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch detailed information for a specific symbol.
        
        Args:
            symbol: The trading symbol
            completion: Callback function that receives (status, data)
        """
        pass
    
    # Trading Methods
    @abstractmethod
    def placeOrder(self, request: ExchangeOrderRequest, completion: Callable[[Tuple[str, Any]], None]):
        """
        Place an order on the exchange.
        
        Args:
            request: ExchangeOrderRequest with order details
            completion: Callback function that receives (status, data)
                       data: ExchangeOrderResponse on success
        """
        pass
    
    @abstractmethod
    def cancelOrder(self, 
                   orderID: Optional[str] = None,
                   clOrderID: Optional[str] = None,
                   symbol: Optional[str] = None,
                   completion: Optional[Callable[[Tuple[str, Any]], None]] = None):
        """
        Cancel an order by orderID or clOrderID.
        
        Args:
            orderID: Server-assigned order ID
            clOrderID: Client-assigned order ID
            symbol: Trading symbol (required by some exchanges)
            completion: Callback function that receives (status, data)
        """
        pass
    
    @abstractmethod
    def fetchOrders(self, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch all open orders.
        
        Args:
            completion: Callback function that receives (status, data)
                       data: List[ExchangeOrder] on success
        """
        pass
    
    # Account Methods
    @abstractmethod
    def fetchBalance(self, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch account balance information.
        
        Args:
            completion: Callback function that receives (status, data)
                       data: List[ExchangeBalance] on success
        """
        pass
    
    @abstractmethod
    def fetchPositions(self, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch all open positions.
        
        Args:
            completion: Callback function that receives (status, data)
                       data: List[ExchangePosition] on success
        """
        pass
    
    @abstractmethod
    def fetchAccountEquity(self, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch total account equity value.
        
        Args:
            completion: Callback function that receives (status, data)
                       data: float (total equity in USD) on success
        """
        pass