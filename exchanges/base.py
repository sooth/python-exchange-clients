"""
Exchange Interface - Abstract base class for all exchange implementations

This module defines the unified interface that all exchange adapters must implement.
It provides a consistent API for the Discord bot to interact with different exchanges.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass
import time
import logging
from exchange_logging import ExchangeLogger

# Import shared data structures from BitUnix (they're identical in both exchanges)
from BitUnix import (
    ExchangeOrderRequest,
    ExchangeOrderResponse,
    ExchangeTicker,
    ExchangePosition,
    ExchangeBalance,
    ExchangeOrder
)


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
    
    def __init__(self):
        """Initialize the exchange interface with logging"""
        self.logger = None
    
    def _init_logger(self):
        """Initialize logger for the exchange (called by subclasses)"""
        if not self.logger:
            self.logger = ExchangeLogger.get_logger(self.get_name())
    
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
        Fetch all available tickers from the exchange.
        
        Args:
            completion: Callback with (status, data) where:
                - success: data is List[ExchangeTicker]
                - failure: data is Exception
        """
        pass
    
    @abstractmethod
    def subscribeToTicker(self, symbol: str):
        """Subscribe to real-time ticker updates for a symbol."""
        pass
    
    @abstractmethod
    def lastTradePrice(self, symbol: str) -> float:
        """Get the last trade price for a symbol."""
        pass
    
    # Account Methods
    @abstractmethod
    def fetchBalance(self, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch account balances.
        
        Args:
            completion: Callback with (status, data) where:
                - success: data is List[ExchangeBalance]
                - failure: data is Exception
        """
        pass
    
    @abstractmethod
    def fetchAccountEquity(self, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch total account equity value.
        
        Args:
            completion: Callback with (status, data) where:
                - success: data is float (total equity in USDT)
                - failure: data is Exception
        """
        pass
    
    @abstractmethod
    def fetchAccountFeeInfo(self, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch account fee information including VIP level.
        
        Args:
            completion: Callback with (status, data) where:
                - success: data is dict with keys:
                    - vipLevel: int
                    - makerFee: float (as decimal, e.g., 0.0002 for 0.02%)
                    - takerFee: float
                    - source: str (e.g., 'trade_analysis', 'default')
                - failure: data is Exception
        """
        pass
    
    # Position Methods
    @abstractmethod
    def fetchPositions(self, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch all open positions.
        
        Args:
            completion: Callback with (status, data) where:
                - success: data is List[ExchangePosition]
                - failure: data is Exception
        """
        pass
    
    @abstractmethod
    def fetchPositionTiers(self, symbol: str, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch position tier/risk limit information for a symbol.
        
        Args:
            symbol: Trading symbol
            completion: Callback with (status, data) where:
                - success: data is list of tier information
                - failure: data is Exception
        """
        pass
    
    @abstractmethod
    def fetchAccountRiskLimit(self, symbol: str, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch account's current risk limit/tier for a symbol.
        
        Args:
            symbol: Trading symbol
            completion: Callback with (status, data) where:
                - success: data is dict with risk limit info
                - failure: data is Exception
        """
        pass
    
    # Order Methods
    @abstractmethod
    def placeOrder(self, request: ExchangeOrderRequest, completion: Callable[[Tuple[str, Any]], None]):
        """
        Place a new order.
        
        Args:
            request: Order details
            completion: Callback with (status, data) where:
                - success: data is ExchangeOrderResponse
                - failure: data is Exception
        """
        pass
    
    @abstractmethod
    def cancelOrder(self, orderID: str = None, clOrderID: str = None, symbol: str = None, 
                   completion: Callable[[Tuple[str, Any]], None] = None):
        """
        Cancel an existing order.
        
        Args:
            orderID: Exchange-assigned order ID
            clOrderID: Client-assigned order ID
            symbol: Trading symbol (required for some exchanges)
            completion: Callback with (status, data) where:
                - success: data is cancel confirmation
                - failure: data is Exception
        """
        pass
    
    @abstractmethod
    def fetchOrders(self, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch all open orders.
        
        Args:
            completion: Callback with (status, data) where:
                - success: data is List[ExchangeOrder]
                - failure: data is Exception
        """
        pass
    
    @abstractmethod
    def fetchHistoryOrders(self, start_time: int = None, end_time: int = None, 
                          symbol: str = None, limit: int = 50,
                          completion: Callable[[Tuple[str, Any]], None] = None):
        """
        Fetch order history.
        
        Args:
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds
            symbol: Filter by symbol (optional)
            limit: Maximum number of orders to return
            completion: Callback with (status, data) where:
                - success: data is list of historical orders
                - failure: data is Exception
        """
        pass
    
    @abstractmethod
    def fetchHistoryTrades(self, start_time: int = None, end_time: int = None,
                          symbol: str = None, orderId: str = None, limit: int = 50,
                          completion: Callable[[Tuple[str, Any]], None] = None):
        """
        Fetch trade history.
        
        Args:
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds
            symbol: Filter by symbol (optional)
            orderId: Filter by order ID (optional)
            limit: Maximum number of trades to return
            completion: Callback with (status, data) where:
                - success: data is list of historical trades
                - failure: data is Exception
        """
        pass
    
    # Leverage Methods
    @abstractmethod
    def fetchLeverageAndMarginMode(self, symbol: str, marginCoin: str = "USDT",
                                  completion: Callable[[Tuple[str, Any]], None] = None):
        """
        Fetch current leverage and margin mode settings.
        
        Args:
            symbol: Trading symbol
            marginCoin: Margin currency (default: USDT)
            completion: Callback with (status, data) where:
                - success: data is dict with leverage and margin mode
                - failure: data is Exception
        """
        pass
    
    @abstractmethod
    def setLeverage(self, symbol: str, leverage: int, marginCoin: str = "USDT",
                   completion: Callable[[Tuple[str, Any]], None] = None):
        """
        Set leverage for a symbol.
        
        Args:
            symbol: Trading symbol
            leverage: Leverage multiplier (e.g., 10 for 10x)
            marginCoin: Margin currency (default: USDT)
            completion: Callback with (status, data) where:
                - success: data is confirmation
                - failure: data is Exception
        """
        pass
    
    # Utility Methods
    @abstractmethod
    def get_min_trade_volume(self, symbol: str) -> float:
        """Get minimum trade volume for a symbol."""
        pass
    
    @abstractmethod
    def get_price_precision(self, symbol: str) -> int:
        """Get price decimal precision for a symbol."""
        pass
    
    @abstractmethod
    def get_quantity_precision(self, symbol: str) -> int:
        """Get quantity decimal precision for a symbol."""
        pass
    
    # Price Management Methods
    @abstractmethod
    def getCurrentPrice(self, symbol: str) -> float:
        """
        Get current market price for symbol in USD/USDT.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Current price in USD/USDT
        """
        pass
    
    @abstractmethod
    def validateAndAdjustPrice(self, symbol: str, price: float, side: str) -> float:
        """
        Validate and adjust price to meet exchange requirements.
        
        Args:
            symbol: Trading symbol
            price: Proposed price
            side: Order side (BUY/SELL, LONG/SHORT)
            
        Returns:
            Adjusted price that meets exchange requirements
        """
        pass
    
    # Quantity Management Methods
    @abstractmethod
    def normalizeQuantity(self, symbol: str, qty: float, price: float) -> float:
        """
        Convert standard BTC quantity to exchange-specific unit.
        
        Args:
            symbol: Trading symbol
            qty: Quantity in standard units (e.g., BTC amount)
            price: Order price (needed for contract calculation)
            
        Returns:
            Quantity in exchange-specific units
        """
        pass
    
    @abstractmethod
    def getMinimumOrderSize(self, symbol: str, price: float) -> float:
        """
        Get minimum order size in standard units (e.g., BTC).
        
        Args:
            symbol: Trading symbol
            price: Order price (needed for value calculation)
            
        Returns:
            Minimum order size in standard units
        """
        pass
    
    # WebSocket Methods
    @abstractmethod
    def subscribeToOrders(self, symbols: List[str]):
        """Subscribe to real-time order updates for multiple symbols."""
        pass