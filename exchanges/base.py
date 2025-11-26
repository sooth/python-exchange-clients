"""
Exchange Interface - Abstract base class for all exchange implementations

This module defines the unified interface that all exchange adapters must implement.
It provides a consistent API for interacting with different exchanges.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable, Tuple, List
from dataclasses import dataclass


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

    # LMEX Hedge Mode support
    positionMode: str = "HEDGE"  # "ONE_WAY", "HEDGE", or "ISOLATED"
    stopLoss: Optional[float] = None
    takeProfit: Optional[float] = None

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
    raw_response: Optional[Dict] = None  # Raw data from exchange


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
    # Additional fields for TP/SL
    stopPrice: Optional[float] = None
    triggerPrice: Optional[float] = None
    reduceOnly: Optional[bool] = None
    postOnly: Optional[bool] = None
    # Trigger order fields (for SL/TP orders)
    triggerOrder: bool = False
    triggerOrderType: Optional[int] = None  # 1001=Stop Loss, 1002=Take Profit
    txType: Optional[str] = None  # "STOP", "TAKEPROFIT"
    # Store raw order type for debugging
    rawOrderType: Optional[str] = None
    # Store raw response for additional fields
    rawResponse: Optional[dict] = None


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
    def placeOrder(self, request: ExchangeOrderRequest,
                   completion: Callable[[Tuple[str, Any]], None]):
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
    def cancelOrder(
            self,
            orderID: str = None,
            clOrderID: str = None,
            symbol: str = None,
            completion=None):
        """Cancel an order"""
        pass


# WebSocket Protocol definition
class WebSocketProtocol(ABC):
    """
    Abstract base class for WebSocket manager implementations.
    """

    @abstractmethod
    def connect(self, url: str, on_open: Callable = None, on_close: Callable = None) -> bool:
        """Connect to WebSocket endpoint"""
        pass

    @abstractmethod
    def disconnect(self):
        """Disconnect from WebSocket"""
        pass

    @abstractmethod
    def send(self, message: Dict[str, Any]) -> bool:
        """Send message to WebSocket"""
        pass

    @abstractmethod
    def subscribe(self, channels: List[Dict[str, Any]]) -> bool:
        """Subscribe to channels"""
        pass

    @abstractmethod
    def unsubscribe(self, channels: List[Dict[str, Any]]) -> bool:
        """Unsubscribe from channels"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected"""
        pass

    @abstractmethod
    def get_state(self) -> str:
        """Get connection state"""
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


# WebSocket channel constants
class WebSocketChannels:
    """Standard WebSocket channel names"""
    TICKER = "ticker"
    ORDERBOOK = "orderbook"
    TRADES = "trades"
    ORDERS = "orders"
    POSITIONS = "positions"
    BALANCE = "balance"
    ACCOUNT = "account"


# WebSocket related data structures
@dataclass
class WebSocketSubscription:
    """WebSocket subscription request"""
    channel: str  # e.g., "ticker", "orderbook", "trades", "orders", "positions"
    symbol: Optional[str] = None  # Symbol to subscribe to (None for account-wide channels)
    params: Optional[Dict[str, Any]] = None  # Additional channel-specific parameters


@dataclass
class WebSocketMessage:
    """Unified WebSocket message structure"""
    channel: str
    symbol: Optional[str]
    timestamp: int
    data: Any  # Channel-specific data (ticker, order, position, etc.)
    raw: Optional[Dict] = None  # Raw message from exchange


# WebSocket connection states
class WebSocketState:
    """WebSocket connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    RECONNECTING = "reconnecting"
    ERROR = "error"


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
    def placeOrder(self, request: ExchangeOrderRequest,
                   completion: Callable[[Tuple[str, Any]], None]):
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

    # Position Mode Methods (for futures/derivatives)
    def fetchPositionMode(self, completion: Callable[[Tuple[str, Any]], None]):
        """
        Fetch the current position mode (one-way or hedge mode).

        Args:
            completion: Callback function that receives (status, data)
                       data: dict with {"positionMode": "ONE_WAY" or "HEDGE"} on success

        Note: This is optional - not all exchanges support position modes
        """
        # Default implementation - not supported
        completion(("failure", Exception("Position mode not supported by this exchange")))

    def setPositionMode(self, mode: str, completion: Callable[[Tuple[str, Any]], None]):
        """
        Set the position mode (one-way or hedge mode).

        Args:
            mode: "ONE_WAY" or "HEDGE"
            completion: Callback function that receives (status, data)
                       data: dict with confirmation on success

        Note: This is optional - not all exchanges support position modes
        """
        # Default implementation - not supported
        completion(("failure", Exception("Position mode not supported by this exchange")))

    # WebSocket Methods
    @abstractmethod
    def connectWebSocket(self,
                         on_message: Callable[[WebSocketMessage], None],
                         on_state_change: Callable[[WebSocketState], None],
                         on_error: Callable[[Exception], None]) -> bool:
        """
        Connect to the exchange WebSocket.

        Args:
            on_message: Callback for incoming messages
            on_state_change: Callback for connection state changes
            on_error: Callback for errors

        Returns:
            True if connection initiated successfully
        """
        pass

    @abstractmethod
    def disconnectWebSocket(self):
        """Disconnect from the WebSocket"""
        pass

    @abstractmethod
    def subscribeWebSocket(self, subscriptions: List[WebSocketSubscription]) -> bool:
        """
        Subscribe to WebSocket channels.

        Args:
            subscriptions: List of channels to subscribe to

        Returns:
            True if subscription request sent successfully
        """
        pass

    @abstractmethod
    def unsubscribeWebSocket(self, subscriptions: List[WebSocketSubscription]) -> bool:
        """
        Unsubscribe from WebSocket channels.

        Args:
            subscriptions: List of channels to unsubscribe from

        Returns:
            True if unsubscription request sent successfully
        """
        pass

    @abstractmethod
    def getWebSocketState(self) -> WebSocketState:
        """Get current WebSocket connection state"""
        pass

    @abstractmethod
    def isWebSocketConnected(self) -> bool:
        """Check if WebSocket is connected and ready"""
        pass
