"""BitUnix Exchange Implementation"""

from .base import (
    ExchangeProtocol,
    ExchangeOrderRequest,
    ExchangeOrderResponse,
    ExchangeTicker,
    ExchangePosition,
    ExchangeBalance,
    ExchangeOrder,
    ExchangeInterface,
    PositionSide,
    TradingType,
    WebSocketState,
    WebSocketMessage,
    WebSocketSubscription,
    WebSocketChannels
)
from .utils.precision import SymbolPrecisionManager
from .utils.api_keys import APIKeyStorage
from .websocket_manager import BaseWebSocketManager, ReconnectConfig

import requests
from typing import Optional, Type, Dict, Any, List, Callable, Tuple, Set
import json
import hashlib
import time
import uuid
import hmac
import urllib.parse
import logging
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()

class ExchangeWebSocketManagerProtocol:
    """Protocol for WebSocket managers"""
    def shared(self):
        raise NotImplementedError
    
    def subscribeToTicker(self, symbol: str):
        raise NotImplementedError
    
    def lastTradePrice(self, symbol: str) -> float:
        raise NotImplementedError
    
    def subscribeToOrders(self, symbols: list[str]):
        raise NotImplementedError

logger = logging.getLogger(__name__)


class BitUnixWebSocketManager(BaseWebSocketManager):
    """
    BitUnix WebSocket manager implementation.
    
    Supports both public and private channels:
    - Public: ticker, depth_books, kline, trade, market_price
    - Private: balance, order, position, tpsl
    """
    
    PUBLIC_URL = "wss://fapi.bitunix.com/public/"
    PRIVATE_URL = "wss://fapi.bitunix.com/private/"
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 on_message: Optional[Callable[[WebSocketMessage], None]] = None,
                 on_error: Optional[Callable[[Exception], None]] = None,
                 on_state_change: Optional[Callable[[WebSocketState], None]] = None):
        """
        Initialize BitUnix WebSocket manager.
        
        Args:
            api_key: API key for private channels
            api_secret: API secret for private channels
            on_message: Callback for processed messages
            on_error: Callback for errors
            on_state_change: Callback for connection state changes
        """
        super().__init__(
            exchange_name="BitUnix",
            on_message=on_message,
            on_error=on_error,
            on_state_change=on_state_change
        )
        
        self.api_key = api_key
        self.api_secret = api_secret
        self._is_private = bool(api_key and api_secret)
        self._authenticated = False
        
        # Cache for latest values
        self._ticker_cache: Dict[str, Dict[str, Any]] = {}
        self._order_cache: Dict[str, Dict[str, Any]] = {}
        self._position_cache: Dict[str, Dict[str, Any]] = {}
        self._balance_cache: Dict[str, Any] = {}
        
        # Track active subscriptions to prevent duplicates
        self._active_subscriptions: Set[str] = set()
    
    def connect_public(self) -> bool:
        """Connect to public WebSocket channels"""
        return self.connect(self.PUBLIC_URL)
    
    def connect_private(self) -> bool:
        """Connect to private WebSocket channels"""
        if not self._is_private:
            logger.error("BitUnix: Cannot connect to private channels without API credentials")
            return False
        return self.connect(self.PRIVATE_URL, on_open=self._authenticate)
    
    def subscribe_ticker(self, symbol: str) -> bool:
        """Subscribe to ticker updates for a symbol"""
        return self.subscribe([{
            "symbol": symbol,
            "ch": "ticker"
        }])
    
    def subscribe_orderbook(self, symbol: str, depth: int = 20) -> bool:
        """Subscribe to order book updates"""
        return self.subscribe([{
            "symbol": symbol,
            "ch": "depth_books",
            "depth": depth
        }])
    
    def subscribe_trades(self, symbol: str) -> bool:
        """Subscribe to trade updates"""
        return self.subscribe([{
            "symbol": symbol,
            "ch": "trade"
        }])
    
    def subscribe_orders(self) -> bool:
        """Subscribe to order updates (private channel)"""
        if not self._is_private:
            logger.error("BitUnix: Cannot subscribe to orders without API credentials")
            return False
        return self.subscribe([{"ch": "order"}])
    
    def subscribe_positions(self) -> bool:
        """Subscribe to position updates (private channel)"""
        if not self._is_private:
            logger.error("BitUnix: Cannot subscribe to positions without API credentials")
            return False
        return self.subscribe([{"ch": "position"}])
    
    def subscribe_balance(self) -> bool:
        """Subscribe to balance updates (private channel)"""
        if not self._is_private:
            logger.error("BitUnix: Cannot subscribe to balance without API credentials")
            return False
        return self.subscribe([{"ch": "balance"}])
    
    def get_cached_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached ticker data for a symbol"""
        return self._ticker_cache.get(symbol)
    
    def get_cached_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get cached order data"""
        return self._order_cache.get(order_id)
    
    def get_cached_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached position data"""
        return self._position_cache.get(symbol)
    
    def get_cached_balance(self) -> Optional[Dict[str, Any]]:
        """Get cached balance data"""
        return self._balance_cache
    
    def disconnect(self):
        """Disconnect from WebSocket and clear active subscriptions"""
        # Clear active subscriptions
        self._active_subscriptions.clear()
        # Call parent disconnect
        super().disconnect()
    
    def _authenticate(self, ws):
        """Authenticate for private channels"""
        if not self.api_key or not self.api_secret:
            return
        
        # Generate authentication parameters
        timestamp = int(time.time() * 1000)
        nonce = self._generate_nonce()
        
        # Create signature
        sign = self._create_signature(timestamp, nonce)
        
        # Send login request
        login_request = {
            "op": "login",
            "args": [{
                "apiKey": self.api_key,
                "timestamp": timestamp,
                "nonce": nonce,
                "sign": sign
            }]
        }
        
        self.send(login_request)
        logger.info("BitUnix: Sent authentication request")
    
    def _generate_nonce(self) -> str:
        """Generate a 32-character random nonce"""
        import random
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    
    def _create_signature(self, timestamp: int, nonce: str) -> str:
        """Create authentication signature"""
        # Step 1: Create first digest
        first_message = f"{nonce}{timestamp}{self.api_key}"
        first_digest = hashlib.sha256(first_message.encode()).hexdigest()
        
        # Step 2: Create final signature
        final_message = f"{first_digest}{self.api_secret}"
        final_signature = hashlib.sha256(final_message.encode()).hexdigest()
        
        return final_signature
    
    def _send_subscription_request(self, channels: List[Dict[str, Any]], subscribe: bool) -> bool:
        """Send subscription/unsubscription request"""
        op = "subscribe" if subscribe else "unsubscribe"
        
        # Filter out duplicate subscriptions
        if subscribe:
            filtered_channels = []
            for channel in channels:
                # Create a unique key for this subscription
                sub_key = f"{channel.get('symbol', '')}-{channel.get('ch', '')}"
                if sub_key not in self._active_subscriptions:
                    filtered_channels.append(channel)
                    self._active_subscriptions.add(sub_key)
                else:
                    logger.debug(f"BitUnix: Skipping duplicate subscription for {sub_key}")
            
            if not filtered_channels:
                logger.debug(f"BitUnix: All {len(channels)} channels already subscribed")
                return True
            channels = filtered_channels
        else:
            # Remove from active subscriptions when unsubscribing
            for channel in channels:
                sub_key = f"{channel.get('symbol', '')}-{channel.get('ch', '')}"
                self._active_subscriptions.discard(sub_key)
        
        request = {
            "op": op,
            "args": channels
        }
        
        logger.info(f"BitUnix: Sending {op} request for {len(channels)} channels: {channels}")
        return self.send(request)
    
    def _send_heartbeat(self):
        """Send ping to keep connection alive"""
        self.send({"op": "ping"})
    
    def _parse_timestamp(self, ts_value: Any) -> int:
        """Parse timestamp from various formats to milliseconds"""
        if ts_value is None:
            return int(time.time() * 1000)
        
        # If already an integer, return it
        if isinstance(ts_value, int):
            return ts_value
        
        # If it's a float, convert to int milliseconds
        if isinstance(ts_value, float):
            return int(ts_value * 1000) if ts_value < 1e10 else int(ts_value)
        
        # If it's a string, try to parse it
        if isinstance(ts_value, str):
            try:
                # Try parsing as integer first
                return int(ts_value)
            except ValueError:
                try:
                    # Try parsing as float
                    return int(float(ts_value) * 1000)
                except ValueError:
                    try:
                        # Try parsing as ISO format datetime
                        # Handle both with and without 'Z' suffix
                        if ts_value.endswith('Z'):
                            ts_value = ts_value[:-1] + '+00:00'
                        dt = datetime.fromisoformat(ts_value)
                        return int(dt.timestamp() * 1000)
                    except ValueError:
                        logger.warning(f"BitUnix: Unable to parse timestamp: {ts_value}")
                        return int(time.time() * 1000)
        
        # Default case
        return int(time.time() * 1000)
    
    def _process_message(self, message: Dict[str, Any]):
        """Process raw message from WebSocket"""
        # Handle different message types
        if "op" in message:
            self._handle_operation_response(message)
        elif "ch" in message:
            self._handle_channel_message(message)
        elif "channel" in message:
            # Alternative format
            self._handle_channel_message(message)
        else:
            logger.debug(f"BitUnix: Unhandled message format: {message}")
    
    def _handle_operation_response(self, message: Dict[str, Any]):
        """Handle operation responses (login, subscribe, etc.)"""
        op = message.get("op")
        
        if op == "login":
            # Check both possible response formats
            is_success = False
            if message.get("code") == 0:
                is_success = True
            elif message.get("data", {}).get("result") is True:
                is_success = True
            
            if is_success:
                logger.info("BitUnix: Authentication successful")
                self._authenticated = True
                self._set_state(WebSocketState.AUTHENTICATED)
                
                # Subscribe to pending private channels
                with self._lock:
                    if self._pending_subscriptions:
                        private_subs = [s for s in self._pending_subscriptions if s.get("ch") in ["order", "position", "balance", "tpsl"]]
                        if private_subs:
                            self._send_subscription_request(private_subs, True)
                            for sub in private_subs:
                                self._pending_subscriptions.remove(sub)
            else:
                logger.error(f"BitUnix: Authentication failed: {message}")
                self._authenticated = False
        
        elif op == "subscribe":
            # Check both possible response formats
            is_success = False
            if message.get("code") == 0:
                is_success = True
            elif message.get("data", {}).get("result") is True:
                is_success = True
            elif "result" in message and message["result"] is True:
                is_success = True
                
            if is_success:
                logger.info(f"BitUnix: Subscription successful")
            else:
                logger.error(f"BitUnix: Subscription failed: {message}")
        
        elif op == "pong":
            logger.debug("BitUnix: Received pong")
        
        elif op == "connect":
            # Handle connect response
            if message.get("data", {}).get("result") is True:
                logger.info("BitUnix: Connection acknowledged")
    
    def _handle_channel_message(self, message: Dict[str, Any]):
        """Handle channel data messages"""
        channel = message.get("ch")
        symbol = message.get("symbol")
        data = message.get("data")
        timestamp = self._parse_timestamp(message.get("ts"))
        
        if not channel or data is None:
            return
        
        # Process based on channel type
        if channel == "ticker":
            self._process_ticker(symbol, data, timestamp)
        elif channel == "depth_books":
            self._process_orderbook(symbol, data, timestamp)
        elif channel == "trade":
            self._process_trades(symbol, data, timestamp)
        elif channel == "order":
            self._process_order(data, timestamp)
        elif channel == "position":
            self._process_position(data, timestamp)
        elif channel == "balance":
            self._process_balance(data, timestamp)
        elif channel == "tpsl":
            self._process_tpsl(data, timestamp)
    
    def _process_ticker(self, symbol: str, data: Dict[str, Any], timestamp: int):
        """Process ticker data"""
        # Cache ticker data
        self._ticker_cache[symbol] = data
        
        # Create unified ticker
        ticker = ExchangeTicker(symbol)
        ticker.lastPrice = float(data.get("la", 0))
        ticker.bidPrice = float(data.get("b1", 0)) if "b1" in data else ticker.lastPrice
        ticker.askPrice = float(data.get("a1", 0)) if "a1" in data else ticker.lastPrice
        ticker.volume = float(data.get("b", 0))
        ticker.price = ticker.lastPrice
        
        # Send unified message
        unified_msg = self._create_unified_message(WebSocketChannels.TICKER, symbol, ticker)
        if self.on_message:
            self.on_message(unified_msg)
    
    def _process_orderbook(self, symbol: str, data: Dict[str, Any], timestamp: int):
        """Process order book data"""
        # Create orderbook structure
        orderbook = {
            "symbol": symbol,
            "bids": [[float(p), float(q)] for p, q in data.get("b", [])],
            "asks": [[float(p), float(q)] for p, q in data.get("a", [])],
            "timestamp": timestamp
        }
        
        # Send unified message
        unified_msg = self._create_unified_message(WebSocketChannels.ORDERBOOK, symbol, orderbook)
        if self.on_message:
            self.on_message(unified_msg)
    
    def _process_trades(self, symbol: str, data: List[Dict[str, Any]], timestamp: int):
        """Process trade data"""
        trades = []
        for trade in data:
            trades.append({
                "symbol": symbol,
                "price": float(trade.get("p", 0)),
                "quantity": float(trade.get("q", 0)),
                "side": trade.get("S", "BUY"),
                "timestamp": self._parse_timestamp(trade.get("t")) if trade.get("t") else timestamp
            })
        
        # Send unified message
        unified_msg = self._create_unified_message(WebSocketChannels.TRADES, symbol, trades)
        if self.on_message:
            self.on_message(unified_msg)
    
    def _process_order(self, data: Dict[str, Any], timestamp: int):
        """Process order update"""
        order_id = data.get("oi")
        if order_id:
            self._order_cache[order_id] = data
        
        # Create unified order
        order = ExchangeOrder(
            orderId=order_id,
            symbol=data.get("s", ""),
            side=data.get("S", ""),
            orderType=data.get("o", ""),
            qty=float(data.get("q", 0)),
            price=float(data.get("p", 0)) if data.get("p") else None,
            status=self._map_order_status(data.get("X", "")),
            timeInForce=data.get("f", "GTC"),
            createTime=self._parse_timestamp(data.get("ct")) if data.get("ct") else timestamp,
            clientId=data.get("coi"),
            executedQty=float(data.get("eq", 0))
        )
        
        # Send unified message
        unified_msg = self._create_unified_message(WebSocketChannels.ORDERS, order.symbol, order)
        if self.on_message:
            self.on_message(unified_msg)
    
    def _process_position(self, data: Dict[str, Any], timestamp: int):
        """Process position update"""
        symbol = data.get("s", "")
        if symbol:
            self._position_cache[symbol] = data
        
        # Create unified position
        size = float(data.get("pa", 0))
        side = data.get("S", "")
        if side == "SELL":
            size = -size
        
        position = ExchangePosition(
            symbol=symbol,
            size=size,
            entryPrice=float(data.get("ep", 0)),
            markPrice=float(data.get("mp", 0)),
            pnl=float(data.get("up", 0)),
            pnlPercentage=float(data.get("upp", 0)),
            side=side
        )
        
        # Send unified message
        unified_msg = self._create_unified_message(WebSocketChannels.POSITIONS, symbol, position)
        if self.on_message:
            self.on_message(unified_msg)
    
    def _process_balance(self, data: List[Dict[str, Any]], timestamp: int):
        """Process balance update"""
        self._balance_cache = {item["a"]: item for item in data}
        
        # Create unified balances
        balances = []
        for item in data:
            balance = ExchangeBalance(
                asset=item.get("a", ""),
                balance=float(item.get("wb", 0)),
                available=float(item.get("ab", 0)),
                locked=float(item.get("wb", 0)) - float(item.get("ab", 0))
            )
            balances.append(balance)
        
        # Send unified message
        unified_msg = self._create_unified_message(WebSocketChannels.BALANCE, None, balances)
        if self.on_message:
            self.on_message(unified_msg)
    
    def _process_tpsl(self, data: Dict[str, Any], timestamp: int):
        """Process take profit/stop loss update"""
        # Send as raw data for now
        unified_msg = self._create_unified_message("tpsl", data.get("s"), data)
        if self.on_message:
            self.on_message(unified_msg)
    
    def _map_order_status(self, status: str) -> str:
        """Map BitUnix order status to unified status"""
        status_map = {
            "NEW": "NEW",
            "FILLED": "FILLED",
            "PARTIALLY_FILLED": "PARTIALLY_FILLED",
            "CANCELED": "CANCELED",
            "REJECTED": "REJECTED"
        }
        return status_map.get(status, status)
    
    # Singleton pattern support for backward compatibility
    _shared_instance: Optional['BitUnixWebSocketManager'] = None
    
    @classmethod
    def shared(cls):
        """Get shared instance (singleton pattern)"""
        if cls._shared_instance is None:
            cls._shared_instance = cls()
        return cls._shared_instance
    
    def subscribeToTicker(self, symbol: str):
        """Legacy method for backward compatibility"""
        if not self.is_connected():
            self.connect_public()
        self.subscribe_ticker(symbol)
    
    def lastTradePrice(self, symbol: str) -> float:
        """Get the last trade price for a symbol from cache"""
        ticker = self._ticker_cache.get(symbol, {})
        return float(ticker.get("la", 0))
    
    def subscribeToOrders(self, symbols: list[str]):
        """Legacy method for backward compatibility"""
        if not self.is_connected():
            logger.warning("BitUnix: Cannot subscribe to orders without WebSocket connection")
            return
        for symbol in symbols:
            logger.info(f"BitUnix: Subscribing to orders for {symbol}")

class BitUnixExchange(ExchangeProtocol, ExchangeInterface):
    """
    A BitUnix-specific implementation of ExchangeProtocol (Python version).
    """
    
    def __init__(self):
        self.precision_manager = SymbolPrecisionManager.get_instance("BitUnix")
        self.base_url = "https://api.bitunix.com"
        self._ws_manager: Optional[BitUnixWebSocketManager] = None
        self._api_key: Optional[str] = None
        self._api_secret: Optional[str] = None

    @property
    def webSocketManager(self) -> ExchangeWebSocketManagerProtocol:
        """
        Provide a reference to the exchange's WebSocket manager
        so UI layers can subscribe to real-time data.
        """
        return BitUnixWebSocketManager.shared()

    # MARK: - WebSocket Support
    # We'll now call the webSocketManager internally as well.
    def subscribeToTicker(self, symbol: str):
        """
        Subscribe to ticker updates for a given symbol.
        """
        self.webSocketManager.subscribeToTicker(symbol)

    def lastTradePrice(self, symbol: str) -> float:
        """
        Retrieve the last trade price for a given symbol.
        """
        # First try to get from WebSocket manager cache
        cached_price = self.webSocketManager.lastTradePrice(symbol)
        if cached_price > 0:
            return cached_price
        
        # If no cached price, fetch current ticker
        ticker_data = None
        ticker_received = threading.Event()
        
        def ticker_callback(result):
            nonlocal ticker_data
            status, data = result
            if status == "success":
                ticker_data = data
            ticker_received.set()
        
        # Fetch ticker for this specific symbol
        self.fetchTicker(symbol, ticker_callback)
        
        if ticker_received.wait(timeout=5):
            if ticker_data and hasattr(ticker_data, 'lastPrice'):
                return float(ticker_data.lastPrice)
        
        # If still no price, try from all tickers
        all_tickers = None
        all_tickers_received = threading.Event()
        
        def all_tickers_callback(result):
            nonlocal all_tickers
            status, data = result
            if status == "success":
                all_tickers = data
            all_tickers_received.set()
        
        self.fetchTickers(all_tickers_callback)
        
        if all_tickers_received.wait(timeout=5):
            if all_tickers:
                for ticker in all_tickers:
                    if ticker.symbol == symbol:
                        # Return the last price
                        if hasattr(ticker, 'lastPrice'):
                            return float(ticker.lastPrice)
                        elif hasattr(ticker, 'price'):
                            return float(ticker.price)
        
        # Return 0 if no price found
        print(f"WARNING: Could not fetch real price for {symbol}")
        return 0.0

    # MARK: - Additional WebSocket
    def subscribeToOrders(self, symbols: list[str]):
        """
        Subscribe to order updates for a list of symbols.
        """
        self.webSocketManager.subscribeToOrders(symbols)

    # MARK: - REST API Calls
    def fetchTicker(self, symbol: str, completion):
        """
        Fetch ticker information for a specific symbol from BitUnix via REST API.
        """
        url = f"https://fapi.bitunix.com/api/v1/futures/market/ticker?symbol={symbol}"
        
        try:
            response = requests.get(url)
            
            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}")
            
            data = response.json()
            if data.get('code') == 0 and data.get('data'):
                ticker_data = data['data']
                # Create an ExchangeTicker with the price info
                ticker = ExchangeTicker(symbol)
                ticker.lastPrice = float(ticker_data.get('lastPrice', 0))
                ticker.bidPrice = float(ticker_data.get('bestBid', 0))
                ticker.askPrice = float(ticker_data.get('bestAsk', 0))
                ticker.volume = float(ticker_data.get('volume', 0))
                completion(("success", ticker))
            else:
                raise Exception(f"API error: {data}")
                
        except Exception as e:
            completion(("failure", e))
    
    def fetchSymbolInfo(self, symbol: str, completion):
        """
        Fetch detailed information for a specific symbol.
        
        Args:
            symbol: The trading symbol
            completion: Callback function that receives (status, data)
        """
        def ticker_callback(status_data):
            status, data = status_data
            if status == "success":
                # Find the specific symbol
                for ticker in data:
                    if ticker.symbol == symbol:
                        # Return ticker info as symbol info
                        symbol_info = {
                            "symbol": ticker.symbol,
                            "lastPrice": ticker.lastPrice,
                            "bidPrice": ticker.bidPrice,
                            "askPrice": ticker.askPrice,
                            "volume": ticker.volume,
                            "price": ticker.price
                        }
                        completion(("success", symbol_info))
                        return
                
                # Symbol not found
                completion(("failure", Exception(f"Symbol {symbol} not found")))
            else:
                completion(("failure", data))
        
        # Use fetchTickers to get symbol info
        self.fetchTickers(ticker_callback)
    
    def fetchTickers(self, completion):
        """
        Fetch ticker information from BitUnix via REST API.
        
        completion: A callback with a Result-like signature:
                    success -> list[ExchangeTicker]
                    failure -> Exception
        """
        url = "https://fapi.bitunix.com/api/v1/futures/market/tickers"

        # DEBUG: Print request info
        print(f"DEBUG: BitUnixExchange fetchTickers request URL: {url}")

        try:
            response = requests.get(url)
            # DEBUG: Print response info
            print(f"DEBUG: BitUnixExchange fetchTickers response statusCode: {response.status_code}")

            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}")

            data = response.json()
            # 
            # Example response format:
            # {
            #   "code": 0,
            #   "data": [
            #     {
            #       "symbol": "BTCUSDT",
            #       "markPrice": "57892.1",
            #       "lastPrice": "57891.2",
            #       ...
            #     }
            #   ],
            #   "msg": "Success"
            # }
            arr = data.get("data", [])
            tickers = []
            for item in arr:
                symbol = item.get("symbol")
                if symbol:
                    ticker = ExchangeTicker(symbol)
                    # Add price data to ticker
                    ticker.lastPrice = float(item.get("lastPrice", 0))
                    ticker.bidPrice = float(item.get("bestBid", 0))
                    ticker.askPrice = float(item.get("bestAsk", 0))
                    ticker.volume = float(item.get("volume", 0))
                    ticker.price = float(item.get("lastPrice", 0))  # Alias
                    tickers.append(ticker)
            completion(("success", tickers))

        except Exception as e:
            print(f"DEBUG: BitUnixExchange fetchTickers error: {str(e)}")
            completion(("failure", e))

    def fetchPositions(self, completion):
        """
        Fetch open positions via BitUnix REST API.
        According to docs: GET /api/v1/futures/position/get_pending_positions
        This requires API keys (private request).
        If no credentials, returns an empty list.
        
        completion: A callback with a Result-like signature:
                    success -> list[ExchangePosition]
                    failure -> Exception
        """
        url = "https://fapi.bitunix.com/api/v1/futures/position/get_pending_positions"
        keys = APIKeyStorage.shared().getKeys("BitUnix")

        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            # If no keys, return an empty array
            completion(("success", []))
            return

        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]

        # We'll do a GET with signing using the doc approach (Double SHA-256).
        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        queryParams = ""
        body = ""

        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)

        headers = {
            "api-key": apiKey,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": sign,
            "Content-Type": "application/json"
        }

        print(f"DEBUG: BitUnixExchange fetchPositions request URL: {url}")
        print(f"DEBUG: BitUnixExchange fetchPositions headers: {headers}")

        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: BitUnixExchange fetchPositions response statusCode: {response.status_code}")

            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}")

            data = response.text
            print(f"DEBUG: BitUnixExchange fetchPositions raw response: {data}")

            json_data = json.loads(data)
            arr = json_data.get("data", [])

            positions = []
            for item in arr:
                symbol = item.get("symbol")
                qtyStr = item.get("qty")
                side = item.get("side")
                entryValueStr = item.get("entryValue")

                if not (symbol and qtyStr and side and entryValueStr):
                    # If any critical field is missing, skip
                    continue

                try:
                    qty = float(qtyStr)
                    entryValue = float(entryValueStr)
                except ValueError:
                    # If conversion fails, skip
                    continue

                markPrice = 0.0 if qty == 0 else (entryValue / qty)
                entryPrice = markPrice
                unrealizedPNLStr = item.get("unrealizedPNL", "0")
                try:
                    unrealizedPNL = float(unrealizedPNLStr)
                except ValueError:
                    unrealizedPNL = 0.0

                pnlPercentage = 0.0
                if entryPrice != 0 and qty != 0:
                    pnlPercentage = (unrealizedPNL / (entryPrice * qty)) * 100

                size = -qty if side.upper() == "SHORT" else qty
                positions.append(
                    ExchangePosition(
                        symbol=symbol,
                        size=size,
                        entryPrice=entryPrice,
                        markPrice=markPrice,
                        pnl=unrealizedPNL,
                        pnlPercentage=pnlPercentage,
                        raw_response=item  # Include raw data
                    )
                )

            completion(("success", positions))

        except Exception as e:
            print(f"DEBUG: BitUnixExchange fetchPositions error: {str(e)}")
            completion(("failure", e))

    def placeOrder(self, request: ExchangeOrderRequest, completion):
        """
        Place an order via BitUnix REST API.
        According to docs: POST /api/v1/futures/trade/place_order
        Requires API keys (private request).
        
        completion: A callback with a Result-like signature:
                    success -> ExchangeOrderResponse
                    failure -> Exception
        """
        url = "https://fapi.bitunix.com/api/v1/futures/trade/place_order"
        keys = APIKeyStorage.shared().getKeys("BitUnix")

        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            completion(("failure", Exception("No BitUnix credentials found")))
            return

        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]

        # Get symbol precision info
        symbol = request.symbol
        price_precision = self.precision_manager.get_price_precision(symbol)
        quantity_precision = self.precision_manager.get_quantity_precision(symbol)
        min_volume = self.precision_manager.get_min_trade_volume(symbol)
        
        # Ensure quantity meets minimum requirements
        if request.qty < min_volume:
            print(f"DEBUG: Adjusting quantity from {request.qty} to minimum {min_volume} for {symbol}")
            actual_qty = min_volume
        else:
            actual_qty = request.qty

        # Translate LONG/SHORT to BUY/SELL
        side = request.side.upper()
        if side == "LONG":
            side = "BUY"
        elif side == "SHORT":
            side = "SELL"

        payload = {
            "symbol": symbol,
            "side": side,  # Using translated side
            "qty": f"{actual_qty:.{quantity_precision}f}",
            "orderType": request.orderType.upper(),
        }
        if request.price is not None:
            payload["price"] = f"{request.price:.{price_precision}f}"
        
        # Additional params in Swift code
        # For BitUnix, tradeSide and reduceOnly are independent
        # tradeSide: "OPEN" for new positions, "CLOSE" for closing
        # reduceOnly: additional safety to prevent increasing position
        
        # Always use OPEN for grid orders (they open and close naturally)
        payload["tradeSide"] = "OPEN"
        
        # Set reduceOnly based on request
        if hasattr(request, 'reduceOnly') and request.reduceOnly:
            payload["reduceOnly"] = "true"
        else:
            payload["reduceOnly"] = "false"
        payload["effect"] = request.timeInForce.upper()
        # Only include clientId if orderLinkId is not None
        if request.orderLinkId is not None:
            payload["clientId"] = request.orderLinkId

        if request.stopLoss is not None:
            payload["slPrice"] = f"{request.stopLoss:.{price_precision}f}"
            payload["slStopType"] = "LAST_PRICE"
        if request.takeProfit is not None:
            payload["tpPrice"] = f"{request.takeProfit:.{price_precision}f}"
            payload["tpStopType"] = "LAST_PRICE"

        bodyStr = json.dumps(payload)

        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        queryParams = ""

        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{bodyStr}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)

        headers = {
            "api-key": apiKey,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": sign,
            "Content-Type": "application/json"
        }

        print(f"DEBUG: BitUnixExchange placeOrder URL: {url}")
        print(f"DEBUG: BitUnixExchange placeOrder headers: {headers}")
        print(f"DEBUG: BitUnixExchange placeOrder body: {bodyStr}")

        try:
            response = requests.post(url, headers=headers, data=bodyStr)
            print(f"DEBUG: BitUnixExchange placeOrder response statusCode: {response.status_code}")
            
            responseStr = response.text
            print(f"DEBUG: BitUnixExchange placeOrder raw response: {responseStr}")

            # Add API error code handling
            json_data = json.loads(responseStr)
            if json_data.get('code', 0) != 0:
                error_msg = json_data.get('msg', 'Unknown error')
                raise Exception(f"API Error {json_data.get('code')}: {error_msg}")

            # Parse the response and create ExchangeOrderResponse
            response_data = json.loads(responseStr)
            order_data = response_data.get('data', {})
            
            # Create the order response with proper fields
            orderResponse = ExchangeOrderResponse(
                orderId=order_data.get('orderId', ''),
                symbol=request.symbol,
                side=request.side,
                orderType=request.orderType,
                qty=actual_qty,  # Use the adjusted quantity
                price=request.price,
                status='NEW',  # BitUnix doesn't return status in place order response
                timeInForce=request.timeInForce,
                createTime=int(time.time() * 1000),
                clientId=order_data.get('clientId'),
                rawResponse=response_data
            )
            completion(("success", orderResponse))
        except Exception as e:
            print(f"DEBUG: BitUnixExchange placeOrder error: {str(e)}")
            completion(("failure", e))

    def cancelOrder(self, orderID: str = None, clOrderID: str = None, symbol: str = None, completion=None):
        """
        Cancel an order via BitUnix REST API.
        According to docs: POST /api/v1/futures/trade/cancel_orders
        Requires API keys (private request).
        
        Args:
            orderID: Exchange-assigned order ID
            clOrderID: Client-assigned order ID (clientId in BitUnix)
            symbol: Trading symbol (required)
            completion: Callback with (status, data)
        """
        if not symbol:
            if completion:
                completion(("failure", Exception("symbol is required for cancel order")))
            return
            
        url = "https://fapi.bitunix.com/api/v1/futures/trade/cancel_orders"
        keys = APIKeyStorage.shared().getKeys("BitUnix")

        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            if completion:
                completion(("failure", Exception("No BitUnix credentials found")))
            return

        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]

        # BitUnix cancel_orders endpoint requires orderList array
        orderItem = {}
        if orderID:
            orderItem["orderId"] = orderID
        elif clOrderID:
            orderItem["clientId"] = clOrderID
        else:
            if completion:
                completion(("failure", Exception("Either orderID or clOrderID must be provided")))
            return

        payload = {
            "symbol": symbol,
            "orderList": [orderItem]
        }

        bodyStr = json.dumps(payload)

        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        queryParams = ""

        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{bodyStr}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)

        headers = {
            "api-key": apiKey,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": sign,
            "Content-Type": "application/json"
        }

        print(f"DEBUG: BitUnixExchange cancelOrder URL: {url}")
        print(f"DEBUG: BitUnixExchange cancelOrder headers: {headers}")
        print(f"DEBUG: BitUnixExchange cancelOrder body: {bodyStr}")

        try:
            response = requests.post(url, headers=headers, data=bodyStr)
            print(f"DEBUG: BitUnixExchange cancelOrder response statusCode: {response.status_code}")
            
            responseStr = response.text
            print(f"DEBUG: BitUnixExchange cancelOrder raw response: {responseStr}")

            # Add API error code handling
            json_data = json.loads(responseStr)
            if json_data.get('code', 0) != 0:
                error_msg = json_data.get('msg', 'Unknown error')
                raise Exception(f"API Error {json_data.get('code')}: {error_msg}")

            if completion:
                completion(("success", json_data))
        except Exception as e:
            print(f"DEBUG: BitUnixExchange cancelOrder error: {str(e)}")
            if completion:
                completion(("failure", e))

    def fetchAccountEquity(self, completion):
        """
        Fetch the actual account equity from BitUnix.
        Equity = available + unrealizedPnL + margin
        
        completion: A callback with a Result-like signature:
                    success -> float (total equity in USDT)
                    failure -> Exception
        """
        keys = APIKeyStorage.shared().getKeys("BitUnix")

        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            completion(("success", 0.0))
            return

        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]

        # Use the working endpoint with proper BitUnix signature format
        url = "https://fapi.bitunix.com/api/v1/futures/account?marginCoin=USDT"
        queryParams = "marginCoinUSDT"  # BitUnix format: name1value1name2value2
        
        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        body = ""

        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)

        headers = {
            "api-key": apiKey,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": sign,
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                completion(("failure", Exception(f"HTTP error: {response.status_code}")))
                return

            json_data = json.loads(response.text)
            
            if json_data.get('code', 0) == 0:
                data_obj = json_data.get("data", {})
                
                # Handle both single object and array responses
                if isinstance(data_obj, list):
                    arr = data_obj
                else:
                    arr = [data_obj] if data_obj else []

                for item in arr:
                    marginCoin = item.get("marginCoin", "USDT")
                    
                    if marginCoin == "USDT":
                        # Debug output disabled - set debug=True to enable
                        debug = False
                        if debug:
                            print(f"[DEBUG] Raw API response for USDT:")
                            for key, value in item.items():
                                print(f"  {key}: {value}")
                        
                        # Parse the required fields from API response
                        available = float(item.get("available", "0"))  # Available for new trades
                        frozen = float(item.get("frozen", "0"))  # Margin locked in open orders
                        margin = float(item.get("margin", "0"))  # Position Margin
                        crossUnrealizedPNL = float(item.get("crossUnrealizedPNL", "0"))  # Unrealized PnL
                        
                        # Also check other possible fields
                        equity = float(item.get("equity", "0"))
                        accountEquity = float(item.get("accountEquity", "0"))
                        balance = float(item.get("balance", "0"))
                        
                        if debug:
                            print(f"\n[DEBUG] Parsed values:")
                            print(f"  available: {available}")
                            print(f"  frozen: {frozen}")
                            print(f"  margin: {margin}")
                            print(f"  crossUnrealizedPNL: {crossUnrealizedPNL}")
                            print(f"  equity (if exists): {equity}")
                            print(f"  accountEquity (if exists): {accountEquity}")
                            print(f"  balance (if exists): {balance}")
                        
                        # If there's a direct equity field, use it
                        if equity > 0:
                            if debug:
                                print(f"\n[DEBUG] Using direct equity field: {equity}")
                            completion(("success", equity))
                            return
                        elif accountEquity > 0:
                            if debug:
                                print(f"\n[DEBUG] Using accountEquity field: {accountEquity}")
                            completion(("success", accountEquity))
                            return
                        else:
                            # Calculate equity = available + frozen + margin + unrealizedPnL
                            # frozen = margin locked in open limit orders
                            # margin = margin used by open positions
                            total_equity = available + frozen + margin + crossUnrealizedPNL
                            if debug:
                                print(f"\n[DEBUG] Calculated equity: {total_equity}")
                                print(f"  Formula: available ({available}) + frozen ({frozen}) + margin ({margin}) + PnL ({crossUnrealizedPNL})")
                            completion(("success", total_equity))
                            return
                
                # If no USDT balance found
                completion(("success", 0.0))
            else:
                error_msg = json_data.get('msg', 'Unknown error')
                completion(("failure", Exception(f"API error {json_data.get('code')}: {error_msg}")))
                
        except Exception as e:
            completion(("failure", e))
    
    def fetchBalance(self, completion):
        """
        Fetch account balance via BitUnix REST API.
        Multiple approaches to find working endpoint and signature method.
        This requires API keys (private request).
        If no credentials, returns an empty list.
        
        completion: A callback with a Result-like signature:
                    success -> list[ExchangeBalance]
                    failure -> Exception
        """
        keys = APIKeyStorage.shared().getKeys("BitUnix")

        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            # If no keys, return an empty array
            completion(("success", []))
            return

        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]

        # Try the documented account endpoint with different signature approaches for total account value (~3280)
        balance_endpoints = [
            # Method 1: Try account endpoint with no params (got "Network Error" before)
            {
                "url": "https://fapi.bitunix.com/api/v1/futures/account",
                "queryParams": "",
                "query_string": "",
                "include_language": False,
                "special_parsing": "account_balance"
            },
            # Method 2: Try account endpoint with marginCoin parameter (BitUnix signature format)
            {
                "url": "https://fapi.bitunix.com/api/v1/futures/account",
                "queryParams": "marginCoinUSDT",  # BitUnix format: name1value1name2value2
                "query_string": "?marginCoin=USDT",
                "include_language": False,
                "special_parsing": "account_balance"
            },
            # Method 3: Try account endpoint with sorted parameters (BitUnix format)
            {
                "url": "https://fapi.bitunix.com/api/v1/futures/account",
                "queryParams": "recvWindow5000timestamp" + str(int(time.time() * 1000)),  # BitUnix format
                "query_string": "?recvWindow=5000&timestamp=" + str(int(time.time() * 1000)),
                "include_language": False,
                "special_parsing": "account_balance",
                "use_timestamp_in_params": True
            },
            # Method 4: Try account endpoint with exact documented parameters (BitUnix format)
            {
                "url": "https://fapi.bitunix.com/api/v1/futures/account",
                "queryParams": "marginCoinUSDTrecvWindow5000",  # BitUnix format: sorted by key
                "query_string": "?marginCoin=USDT&recvWindow=5000",
                "include_language": False,
                "special_parsing": "account_balance"
            },
            # Method 5: FALLBACK - extract margin from positions (this only shows ~397, not full 3280)
            {
                "url": "https://fapi.bitunix.com/api/v1/futures/position/get_pending_positions",
                "queryParams": "",
                "query_string": "",
                "include_language": False,
                "extract_balance_from_positions": True
            }
        ]

        for i, endpoint_config in enumerate(balance_endpoints):
            print(f"\n=== TRYING BALANCE METHOD {i+1} ===")
            
            # Handle special timestamp in params case
            if endpoint_config.get("use_timestamp_in_params"):
                current_timestamp = str(int(time.time() * 1000))
                # Replace the timestamp in both BitUnix format params and URL query string
                queryParams = endpoint_config["queryParams"].replace("timestamp" + str(int(time.time() * 1000)), f"timestamp{current_timestamp}")
                query_string = endpoint_config["query_string"].replace("timestamp=" + str(int(time.time() * 1000)), f"timestamp={current_timestamp}")
                url = endpoint_config["url"] + query_string
            else:
                url = endpoint_config["url"] + endpoint_config["query_string"]
                queryParams = endpoint_config["queryParams"]
            
            # Use exact same signature method as working endpoints
            nonce = str(uuid.uuid4())[:8]
            timestamp = str(int(time.time() * 1000))
            body = ""

            # Follow official documentation: nonce + timestamp + api-key + queryParams + body
            digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
            digest = self.sha256Hex(digestInput)
            signInput = f"{digest}{secretKey}"
            sign = self.sha256Hex(signInput)

            headers = {
                "api-key": apiKey,
                "nonce": nonce,
                "timestamp": timestamp,
                "sign": sign,
                "Content-Type": "application/json"
            }
            
            # Add language header only if specified
            if endpoint_config["include_language"]:
                headers["language"] = "en-US"

            print(f"DEBUG: Method {i+1} URL: {url}")
            print(f"DEBUG: Method {i+1} queryParams: '{queryParams}'")
            print(f"DEBUG: Method {i+1} digestInput: '{digestInput}'")
            print(f"DEBUG: Method {i+1} headers: {headers}")

            try:
                response = requests.get(url, headers=headers)
                print(f"DEBUG: Method {i+1} response statusCode: {response.status_code}")

                if response.status_code != 200:
                    print(f"DEBUG: Method {i+1} failed with non-200 status: {response.status_code}")
                    continue

                data = response.text
                print(f"DEBUG: Method {i+1} raw response: {data}")

                json_data = json.loads(data)
                
                # Check for API success
                if json_data.get('code', 0) == 0:
                    print(f"✅ SUCCESS with method {i+1}!")
                    
                    # Special handling for account balance parsing
                    if endpoint_config.get("special_parsing") == "account_balance":
                        print(f"  DEBUG: Using special account balance parsing")
                        data_obj = json_data.get("data", {})
                        
                        # Handle both single object and array responses
                        if isinstance(data_obj, list):
                            arr = data_obj
                        else:
                            arr = [data_obj] if data_obj else []

                        balances = []
                        for item in arr:
                            print(f"  DEBUG: Account balance item: {item}")
                            
                            marginCoin = item.get("marginCoin", "USDT")
                            
                            # Parse all balance fields from account response
                            availableStr = item.get("available", "0")
                            frozenStr = item.get("frozen", "0") 
                            marginStr = item.get("margin", "0")
                            bonusStr = item.get("bonus", "0")
                            crossUnrealizedPNLStr = item.get("crossUnrealizedPNL", "0")
                            
                            try:
                                available = float(availableStr)
                                frozen = float(frozenStr)
                                margin = float(marginStr)
                                bonus = float(bonusStr)
                                crossUnrealizedPNL = float(crossUnrealizedPNLStr)
                                
                                # Calculate total account value
                                # Total equity = available + frozen + margin + bonus + crossUnrealizedPNL
                                # 'frozen' is funds locked in orders
                                # 'margin' is funds locked in positions
                                total_balance = available + frozen + margin + bonus + crossUnrealizedPNL
                                
                                print(f"  DEBUG: Parsed balance components:")
                                print(f"    Available: {available}")
                                print(f"    Frozen (in orders): {frozen}")
                                print(f"    Margin (in positions): {margin}")
                                print(f"    Bonus: {bonus}")
                                print(f"    CrossUnrealizedPNL: {crossUnrealizedPNL}")
                                print(f"    TOTAL EQUITY: {total_balance}")
                                
                            except (ValueError, TypeError) as e:
                                print(f"  DEBUG: Error parsing balance values: {e}")
                                continue

                            if total_balance > 0:
                                balances.append(
                                    ExchangeBalance(
                                        asset=marginCoin,
                                        balance=total_balance,      # Total account equity
                                        available=available,        # Available for new trades
                                        locked=frozen + margin      # Frozen in orders + margin in positions
                                    )
                                )

                        completion(("success", balances))
                        return
                    elif endpoint_config.get("extract_balance_from_positions"):
                        # Extract comprehensive balance info from positions data
                        print(f"  DEBUG: Using positions-based balance extraction with enhanced calculation")
                        data_obj = json_data.get("data", [])
                        balances = []
                        
                        # Calculate comprehensive balance information from positions
                        total_margin = 0
                        total_unrealized_pnl = 0
                        total_entry_value = 0
                        margin_coin = "USDT"
                        
                        print(f"  DEBUG: Processing {len(data_obj)} positions for balance calculation:")
                        
                        for position in data_obj:
                            symbol = position.get("symbol", "")
                            margin_str = position.get("margin", "0")
                            unrealized_pnl_str = position.get("unrealizedPNL", "0")
                            entry_value_str = position.get("entryValue", "0")
                            
                            try:
                                margin = float(margin_str)
                                unrealized_pnl = float(unrealized_pnl_str)
                                entry_value = float(entry_value_str)
                                
                                total_margin += margin
                                total_unrealized_pnl += unrealized_pnl
                                total_entry_value += entry_value
                                
                                print(f"    {symbol}: margin={margin}, pnl={unrealized_pnl}, entry_value={entry_value}")
                                
                            except ValueError:
                                continue
                        
                        print(f"  DEBUG: Balance calculation summary:")
                        print(f"    Total margin in use: ${total_margin:.2f}")
                        print(f"    Total unrealized P&L: ${total_unrealized_pnl:.2f}")
                        print(f"    Total entry value: ${total_entry_value:.2f}")
                        
                        # Create balance entry with available information
                        # Note: This only shows margin in use, not total account balance
                        effective_balance = total_margin + total_unrealized_pnl
                        
                        print(f"    Effective balance (margin + PnL): ${effective_balance:.2f}")
                        print(f"  WARNING: This shows only futures margin usage, not total account balance (~$3280)")
                        print(f"  NOTE: Total account balance requires different API permissions or endpoint access")
                        
                        if total_margin > 0:
                            balances.append(
                                ExchangeBalance(
                                    asset=margin_coin,
                                    balance=effective_balance,  # Margin + unrealized PnL
                                    available=0,  # Cannot determine from positions
                                    locked=total_margin       # Margin locked in positions
                                )
                            )
                        
                        completion(("success", balances))
                        return
                    else:
                        # Unknown parsing method
                        print(f"  DEBUG: Unknown parsing method")
                        completion(("success", []))
                        return
                else:
                    error_msg = json_data.get('msg', 'Unknown error')
                    print(f"DEBUG: Method {i+1} failed with API error {json_data.get('code')}: {error_msg}")
                    continue

            except Exception as e:
                print(f"DEBUG: Method {i+1} failed with exception: {str(e)}")
                continue
        
        # If all methods failed
        completion(("failure", Exception("All balance endpoint methods failed")))

    def fetchOrders(self, completion):
        """
        Fetch open orders via BitUnix REST API.
        According to docs: GET /api/v1/futures/trade/get_pending_orders
        This requires API keys (private request).
        If no credentials, returns an empty list.
        
        completion: A callback with a Result-like signature:
                    success -> list[ExchangeOrder]
                    failure -> Exception
        """
        url = "https://fapi.bitunix.com/api/v1/futures/trade/get_pending_orders"
        keys = APIKeyStorage.shared().getKeys("BitUnix")

        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            # If no keys, return an empty array
            completion(("success", []))
            return

        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]

        # We'll do a GET with signing using the doc approach (Double SHA-256).
        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        queryParams = ""
        body = ""

        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)

        headers = {
            "api-key": apiKey,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": sign,
            "Content-Type": "application/json"
        }

        print(f"DEBUG: BitUnixExchange fetchOrders request URL: {url}")
        print(f"DEBUG: BitUnixExchange fetchOrders headers: {headers}")

        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: BitUnixExchange fetchOrders response statusCode: {response.status_code}")

            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}")

            data = response.text
            print(f"DEBUG: BitUnixExchange fetchOrders raw response: {data}")

            json_data = json.loads(data)
            data_obj = json_data.get("data", {})
            arr = data_obj.get("orderList", [])

            orders = []
            for item in arr:
                orderId = item.get("orderId")
                symbol = item.get("symbol")
                side = item.get("side")
                orderType = item.get("orderType")
                qtyStr = item.get("qty")
                priceStr = item.get("price")
                status = item.get("status")
                timeInForce = item.get("timeInForce", "GTC")
                createTime = item.get("createTime", 0)
                clientId = item.get("clientId")
                stopPriceStr = item.get("stopPrice")
                executedQtyStr = item.get("executedQty", "0")

                if not all([orderId, symbol, side, orderType, qtyStr, status]):
                    continue

                try:
                    qty = float(qtyStr)
                    price = float(priceStr) if priceStr else None
                    stopPrice = float(stopPriceStr) if stopPriceStr else None
                    executedQty = float(executedQtyStr)
                except ValueError:
                    continue

                orders.append(
                    ExchangeOrder(
                        orderId=orderId,
                        symbol=symbol,
                        side=side,
                        orderType=orderType,
                        qty=qty,
                        price=price,
                        status=status,
                        timeInForce=timeInForce,
                        createTime=createTime,
                        clientId=clientId,
                        executedQty=executedQty
                    )
                )

            completion(("success", orders))

        except Exception as e:
            print(f"DEBUG: BitUnixExchange fetchOrders error: {str(e)}")
            completion(("failure", e))

    def fetchHistoryOrders(self, symbol: str = None, startTime: int = None, endTime: int = None, limit: int = 50, completion=None):
        """
        Fetch order history to determine how positions were closed.
        This is crucial for detecting stop loss, take profit, or manual closures.
        
        Args:
            symbol: Trading pair (optional)
            startTime: Unix timestamp in milliseconds (optional)
            endTime: Unix timestamp in milliseconds (optional) 
            limit: Max results (default 50, max 100)
            completion: Callback function
        """
        url = "https://fapi.bitunix.com/api/v1/futures/trade/get_history_orders"
        keys = APIKeyStorage.shared().getKeys("BitUnix")

        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            completion(("failure", Exception("No API keys available")))
            return

        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]

        # Build query parameters
        params = {}
        if symbol:
            params["symbol"] = symbol
        if startTime:
            params["startTime"] = str(startTime)
        if endTime:
            params["endTime"] = str(endTime)
        if limit:
            params["limit"] = str(limit)

        # Convert params to query string for URL (standard format)
        queryString = ""
        if params:
            url_params = "&".join([f"{k}={v}" for k, v in params.items()])
            queryString = "?" + url_params

        # Convert params to signature format: sorted by key, format "name1value1name2value2"
        queryParams = ""
        if params:
            sorted_params = sorted(params.items())
            queryParams = "".join([f"{k}{v}" for k, v in sorted_params])

        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        body = ""

        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)

        headers = {
            "api-key": apiKey,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": sign,
            "Content-Type": "application/json"
        }

        full_url = url + queryString
        print(f"DEBUG: BitUnixExchange fetchHistoryOrders URL: {full_url}")
        print(f"DEBUG: BitUnixExchange fetchHistoryOrders queryParams for signature: '{queryParams}'")
        print(f"DEBUG: BitUnixExchange fetchHistoryOrders digestInput: '{digestInput}'")
        print(f"DEBUG: BitUnixExchange fetchHistoryOrders headers: {headers}")

        try:
            response = requests.get(full_url, headers=headers)
            print(f"DEBUG: BitUnixExchange fetchHistoryOrders response statusCode: {response.status_code}")
            
            responseStr = response.text
            print(f"DEBUG: BitUnixExchange fetchHistoryOrders raw response: {responseStr}")

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {responseStr}")

            json_data = json.loads(responseStr)
            if json_data.get('code', 0) != 0:
                error_msg = json_data.get('msg', 'Unknown error')
                raise Exception(f"API Error {json_data.get('code')}: {error_msg}")

            # Extract order list
            order_list = json_data.get("data", {}).get("orderList", [])
            completion(("success", order_list))

        except Exception as e:
            print(f"DEBUG: BitUnixExchange fetchHistoryOrders error: {str(e)}")
            completion(("failure", e))

    def fetchHistoryTrades(self, symbol: str = None, orderId: str = None, startTime: int = None, endTime: int = None, limit: int = 50, completion=None):
        """
        Fetch trade history to see actual order executions.
        
        Args:
            symbol: Trading pair (optional)
            orderId: Specific order ID (optional)
            startTime: Unix timestamp in milliseconds (optional)
            endTime: Unix timestamp in milliseconds (optional)
            limit: Max results (default 50, max 100)
            completion: Callback function
        """
        url = "https://fapi.bitunix.com/api/v1/futures/trade/get_history_trades"
        keys = APIKeyStorage.shared().getKeys("BitUnix")

        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            completion(("failure", Exception("No API keys available")))
            return

        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]

        # Build query parameters
        params = {}
        if symbol:
            params["symbol"] = symbol
        if orderId:
            params["orderId"] = orderId
        if startTime:
            params["startTime"] = str(startTime)
        if endTime:
            params["endTime"] = str(endTime)
        if limit:
            params["limit"] = str(limit)

        # Convert params to query string for URL (standard format)
        queryString = ""
        if params:
            url_params = "&".join([f"{k}={v}" for k, v in params.items()])
            queryString = "?" + url_params

        # Convert params to signature format: sorted by key, format "name1value1name2value2"
        queryParams = ""
        if params:
            sorted_params = sorted(params.items())
            queryParams = "".join([f"{k}{v}" for k, v in sorted_params])

        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        body = ""

        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)

        headers = {
            "api-key": apiKey,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": sign,
            "Content-Type": "application/json"
        }

        full_url = url + queryString
        print(f"DEBUG: BitUnixExchange fetchHistoryTrades URL: {full_url}")
        print(f"DEBUG: BitUnixExchange fetchHistoryTrades queryParams for signature: '{queryParams}'")
        print(f"DEBUG: BitUnixExchange fetchHistoryTrades digestInput: '{digestInput}'")
        print(f"DEBUG: BitUnixExchange fetchHistoryTrades headers: {headers}")

        try:
            response = requests.get(full_url, headers=headers)
            print(f"DEBUG: BitUnixExchange fetchHistoryTrades response statusCode: {response.status_code}")
            
            responseStr = response.text
            print(f"DEBUG: BitUnixExchange fetchHistoryTrades raw response: {responseStr}")

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {responseStr}")

            json_data = json.loads(responseStr)
            if json_data.get('code', 0) != 0:
                error_msg = json_data.get('msg', 'Unknown error')
                raise Exception(f"API Error {json_data.get('code')}: {error_msg}")

            # Extract trade list
            trade_list = json_data.get("data", {}).get("tradeList", [])
            completion(("success", trade_list))

        except Exception as e:
            print(f"DEBUG: BitUnixExchange fetchHistoryTrades error: {str(e)}")
            completion(("failure", e))

    def fetchLeverageAndMarginMode(self, symbol: str, marginCoin: str, completion):
        """
        Fetch the current leverage and margin mode for a symbol.
        This can help determine the risk tier based on leverage.
        
        completion: A callback with a Result-like signature:
                    success -> dict containing leverage and margin mode
                    failure -> Exception
        """
        url = f"https://fapi.bitunix.com/api/v1/futures/account/get_leverage_margin_mode?symbol={symbol}&marginCoin={marginCoin}"
        keys = APIKeyStorage.shared().getKeys("BitUnix")
        
        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            completion(("failure", Exception("API keys not configured")))
            return
        
        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]
        
        # Generate signature for GET request with query params
        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        queryParams = f"marginCoin{marginCoin}symbol{symbol}"  # Alphabetically sorted
        body = ""
        
        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)
        
        headers = {
            "api-key": apiKey,
            "sign": sign,
            "nonce": nonce,
            "timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        print(f"DEBUG: BitUnixExchange fetchLeverageAndMarginMode request URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: BitUnixExchange fetchLeverageAndMarginMode response statusCode: {response.status_code}")
            
            responseStr = response.text
            print(f"DEBUG: BitUnixExchange fetchLeverageAndMarginMode raw response: {responseStr}")
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {responseStr}")
            
            json_data = json.loads(responseStr)
            
            if json_data.get('code', 0) == 0:
                completion(("success", json_data.get("data", {})))
            else:
                error_msg = json_data.get('msg', 'Unknown error')
                completion(("failure", Exception(f"API Error {json_data.get('code')}: {error_msg}")))
                
        except Exception as e:
            print(f"DEBUG: BitUnixExchange fetchLeverageAndMarginMode error: {str(e)}")
            completion(("failure", e))

    def fetchAccountRiskLimit(self, symbol: str, completion):
        """
        Fetch the account's current risk limit setting for a symbol.
        This tells us which tier the account is currently configured to use.
        
        completion: A callback with a Result-like signature:
                    success -> dict containing current risk limit info
                    failure -> Exception
        """
        # First try to get pending positions which might include risk tier info
        url = "https://fapi.bitunix.com/api/v1/futures/position/get_pending_positions"
        keys = APIKeyStorage.shared().getKeys("BitUnix")
        
        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            completion(("failure", Exception("API keys not configured")))
            return
        
        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]
        
        # Generate signature for GET request (no query params for open positions)
        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        queryParams = ""  # No query params for this endpoint
        body = ""
        
        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)
        
        headers = {
            "api-key": apiKey,
            "sign": sign,
            "nonce": nonce,
            "timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        print(f"DEBUG: BitUnixExchange fetchAccountRiskLimit request URL: {url}")
        print(f"DEBUG: BitUnixExchange fetchAccountRiskLimit headers: {headers}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: BitUnixExchange fetchAccountRiskLimit response statusCode: {response.status_code}")
            
            responseStr = response.text
            print(f"DEBUG: BitUnixExchange fetchAccountRiskLimit raw response: {responseStr}")
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {responseStr}")
            
            json_data = json.loads(responseStr)
            
            # Check if we got positions data
            if json_data.get('code', 0) == 0:
                # Look for risk limit info in position data
                positions = json_data.get('data', [])
                
                # Look for the specific symbol
                symbol_risk_info = None
                for pos in positions:
                    if pos.get('symbol') == symbol:
                        # Extract any risk limit related fields
                        symbol_risk_info = {
                            'symbol': symbol,
                            'leverage': pos.get('leverage', 'Unknown'),
                            'marginMode': pos.get('marginMode', 'Unknown'),
                            'maxNotional': pos.get('maxNotional', 'Unknown'),
                            'riskLimit': pos.get('riskLimit', 'Unknown'),
                            'tier': pos.get('tier', 'Unknown'),
                            'positionValue': pos.get('entryValue', 'Unknown')
                        }
                        break
                
                # If we didn't find the symbol in open positions, try to get leverage info
                if not symbol_risk_info:
                    # Try to fetch leverage and margin mode for this symbol
                    leverage_info = None
                    leverage_error = None
                    
                    def leverage_callback(result):
                        nonlocal leverage_info, leverage_error
                        status, data = result
                        if status == "success":
                            leverage_info = data
                        else:
                            leverage_error = data
                    
                    # Assume USDT as margin coin for now
                    self.fetchLeverageAndMarginMode(symbol, "USDT", leverage_callback)
                    
                    if leverage_info and 'leverage' in leverage_info:
                        # We have leverage info, return it
                        completion(("success", {
                            'symbol': symbol,
                            'leverage': leverage_info.get('leverage'),
                            'marginMode': leverage_info.get('marginMode'),
                            'message': 'No open position, but leverage settings found',
                            'assumeTierBasedOnLeverage': True
                        }))
                    else:
                        # No position and no leverage info, assume Tier 1
                        completion(("success", {
                            'symbol': symbol, 
                            'message': 'No open position for symbol, account tier unknown',
                            'assumeTier1': True
                        }))
                else:
                    completion(("success", symbol_risk_info))
                return
            
            # API error
            error_msg = json_data.get('msg', 'Unknown error')
            completion(("failure", Exception(f"API Error {json_data.get('code')}: {error_msg}")))
            
        except Exception as e:
            print(f"DEBUG: BitUnixExchange fetchAccountRiskLimit error: {str(e)}")
            completion(("failure", e))

    def setLeverage(self, symbol: str, leverage: int, marginCoin: str = "USDT", completion=None):
        """
        Set leverage for a trading pair
        NOTE: This endpoint is not documented in public API docs
        This is a placeholder implementation based on common exchange patterns
        
        completion: A callback with a Result-like signature:
                    success -> dict containing result
                    failure -> Exception
        """
        # Based on BitUnix API patterns (change_margin_mode exists)
        # The most likely endpoint is change_leverage
        
        url = "https://fapi.bitunix.com/api/v1/futures/account/change_leverage"
        keys = APIKeyStorage.shared().getKeys("BitUnix")
        
        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            if completion:
                completion(("failure", Exception("API keys not configured")))
            return
        
        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]
        
        # Request body - try different formats
        request_body = {
            "symbol": symbol,
            "leverage": leverage,
            "marginCoin": marginCoin
        }
        
        # Alternative body format (some APIs use different parameter names)
        alt_request_body = {
            "symbol": symbol,
            "leverage": str(leverage),  # Some APIs expect string
            "marginCoin": marginCoin,
            "side": "BOTH"  # Some APIs require side specification
        }
        
        # Generate signature for POST request
        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        queryParams = ""  # No query params for POST
        body = json.dumps(request_body)
        
        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)
        
        headers = {
            "api-key": apiKey,
            "sign": sign,
            "nonce": nonce,
            "timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        print(f"DEBUG: BitUnixExchange setLeverage request URL: {url}")
        print(f"DEBUG: BitUnixExchange setLeverage body: {body}")
        
        try:
            response = requests.post(url, headers=headers, data=body)
            print(f"DEBUG: BitUnixExchange setLeverage response statusCode: {response.status_code}")
            
            responseStr = response.text
            print(f"DEBUG: BitUnixExchange setLeverage raw response: {responseStr}")
            
            # Handle common error codes
            if response.status_code == 404:
                # Try alternative endpoints based on BitUnix API patterns
                alternative_endpoints = [
                    "https://fapi.bitunix.com/api/v1/futures/account/adjust_leverage",
                    "https://fapi.bitunix.com/api/v1/futures/account/update_leverage",
                    "https://fapi.bitunix.com/api/v1/futures/account/set_leverage",
                    "https://fapi.bitunix.com/api/v1/futures/account/modify_leverage",
                    "https://fapi.bitunix.com/api/v1/futures/leverage/change",
                    "https://fapi.bitunix.com/api/v1/futures/leverage/update"
                ]
                
                print(f"DEBUG: First endpoint returned 404, trying alternatives...")
                
                # Try each alternative endpoint with different methods and body formats
                for alt_url in alternative_endpoints:
                    # Try both POST and PUT methods
                    for method in ['POST', 'PUT']:
                        # Try both body formats
                        for body_data in [body, json.dumps(alt_request_body)]:
                            print(f"DEBUG: Trying {method} {alt_url} with body: {body_data[:100]}...")
                            
                            try:
                                if method == 'POST':
                                    alt_response = requests.post(alt_url, headers=headers, data=body_data)
                                else:
                                    alt_response = requests.put(alt_url, headers=headers, data=body_data)
                                    
                                print(f"DEBUG: Response status: {alt_response.status_code}")
                                
                                if alt_response.status_code != 404:
                                    # Found a working endpoint
                                    responseStr = alt_response.text
                                    print(f"DEBUG: Response: {responseStr}")
                                    
                                    if alt_response.status_code == 200:
                                        json_data = json.loads(responseStr)
                                        if json_data.get('code', 0) == 0:
                                            print(f"DEBUG: Success with {method} {alt_url}")
                                            if completion:
                                                completion(("success", json_data.get("data", {})))
                                            return
                                        else:
                                            error_msg = json_data.get('msg', 'Unknown error')
                                            print(f"DEBUG: API Error: {error_msg}")
                                    elif alt_response.status_code == 400:
                                        # Bad request might mean wrong parameters
                                        print(f"DEBUG: Bad request - might need different parameters")
                                
                            except Exception as e:
                                print(f"DEBUG: Error trying {method} {alt_url}: {e}")
                                continue
                
                # None of the endpoints worked
                error_msg = "No working leverage endpoint found. The set leverage API may require special permissions or may not be publicly available."
                if completion:
                    completion(("failure", Exception(error_msg)))
                return
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {responseStr}")
            
            json_data = json.loads(responseStr)
            
            if json_data.get('code', 0) == 0:
                if completion:
                    completion(("success", json_data.get("data", {})))
            else:
                error_msg = json_data.get('msg', 'Unknown error')
                if completion:
                    completion(("failure", Exception(f"API Error {json_data.get('code')}: {error_msg}")))
                
        except Exception as e:
            print(f"DEBUG: BitUnixExchange setLeverage error: {str(e)}")
            if completion:
                completion(("failure", e))

    def fetchAccountFeeInfo(self, completion):
        """
        Fetch the account's VIP level and fee rates from BitUnix.
        Since BitUnix doesn't expose VIP level directly, we analyze recent trades to determine it.
        
        completion: A callback with a Result-like signature:
                    success -> dict containing VIP level and fee rates
                    failure -> Exception
        """
        keys = APIKeyStorage.shared().getKeys("BitUnix")
        
        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            # Default to standard fees if no API keys
            completion(("success", {
                "vipLevel": 0,
                "makerFee": 0.0002,  # 0.02% maker fee for futures
                "takerFee": 0.0006,  # 0.06% taker fee for futures
                "source": "default"
            }))
            return
        
        # Try to analyze recent trades to determine VIP level
        def analyze_trades_callback(result):
            status, data = result
            
            if status == "success" and isinstance(data, list):
                trades = data
                
                # BitUnix fee schedule
                fee_schedule = {
                    0: {"maker": 0.0002, "taker": 0.0006},    # 0.02% / 0.06%
                    1: {"maker": 0.00016, "taker": 0.0005},   # 0.016% / 0.05%
                    2: {"maker": 0.00014, "taker": 0.00045},  # 0.014% / 0.045%
                    3: {"maker": 0.00012, "taker": 0.0004},   # 0.012% / 0.04%
                    4: {"maker": 0.0001, "taker": 0.00035},   # 0.01% / 0.035%
                    5: {"maker": 0.00006, "taker": 0.00032},  # 0.006% / 0.032%
                    6: {"maker": 0.00004, "taker": 0.0003},   # 0.004% / 0.03%
                    7: {"maker": 0.00002, "taker": 0.00028},  # 0.002% / 0.028%
                    8: {"maker": 0.0, "taker": 0.00025},      # 0% / 0.025%
                    9: {"maker": -0.00002, "taker": 0.00022}, # -0.002% / 0.022%
                }
                
                # Analyze fees
                maker_fees = []
                taker_fees = []
                
                for trade in trades[:50]:  # Analyze up to 50 recent trades
                    qty = float(trade.get('qty', 0))
                    price = float(trade.get('price', 0))
                    fee = float(trade.get('fee', 0))
                    role_type = trade.get('roleType', 'UNKNOWN')
                    
                    if qty > 0 and price > 0 and fee > 0:
                        notional = qty * price
                        fee_rate = fee / notional  # As decimal, not percentage
                        
                        # BitUnix appears to have inverted maker/taker labels
                        # Normally: MAKER = lower fee (adds liquidity), TAKER = higher fee (removes liquidity)
                        # But BitUnix returns higher fees for "MAKER" and lower for "TAKER"
                        if role_type == 'MAKER':
                            # BitUnix "MAKER" = actual taker (higher fee)
                            taker_fees.append(fee_rate)
                        elif role_type == 'TAKER':
                            # BitUnix "TAKER" = actual maker (lower fee)
                            maker_fees.append(fee_rate)
                
                # Calculate averages
                avg_maker = sum(maker_fees) / len(maker_fees) if maker_fees else None
                avg_taker = sum(taker_fees) / len(taker_fees) if taker_fees else None
                
                # Debug output
                if maker_fees or taker_fees:
                    print(f"[FEE INFO] Analyzed {len(trades)} trades:")
                    if avg_maker:
                        print(f"[FEE INFO]   Average MAKER fee: {avg_maker:.6f} ({avg_maker*100:.4f}%) from {len(maker_fees)} trades")
                    if avg_taker:
                        print(f"[FEE INFO]   Average TAKER fee: {avg_taker:.6f} ({avg_taker*100:.4f}%) from {len(taker_fees)} trades")
                
                # Match to VIP tier
                best_match = None
                best_score = float('inf')
                
                for vip_level, fees in fee_schedule.items():
                    score = 0
                    if avg_maker is not None:
                        score += abs(fees['maker'] - avg_maker)
                    if avg_taker is not None:
                        score += abs(fees['taker'] - avg_taker)
                    
                    # Debug each VIP level scoring
                    if maker_fees or taker_fees:
                        print(f"[FEE INFO]   VIP {vip_level} score: {score:.8f} (maker diff: {abs(fees['maker'] - avg_maker) if avg_maker else 'N/A'}, taker diff: {abs(fees['taker'] - avg_taker) if avg_taker else 'N/A'})")
                    
                    if score < best_score:
                        best_score = score
                        best_match = (vip_level, fees)
                
                if best_match:
                    vip_level, fees = best_match
                    # Check if we have high confidence (very close match)
                    if best_score < 0.00005:  # Within 0.005% total deviation
                        print(f"[FEE INFO] Detected VIP Level {vip_level} from trade history (Maker: {fees['maker']:.4%}, Taker: {fees['taker']:.4%})")
                        completion(("success", {
                            "vipLevel": vip_level,
                            "makerFee": fees['maker'],
                            "takerFee": fees['taker'],
                            "source": "trade_analysis"
                        }))
                        return
                    # If we have some trades but not perfect match, still use it with warning
                    elif (maker_fees or taker_fees) and best_score < 0.0002:
                        print(f"[FEE INFO] Likely VIP Level {vip_level} from trade history (confidence: medium)")
                        print(f"[FEE INFO] Detected rates - Maker: {avg_maker:.4%}, Taker: {avg_taker:.4%}")
                        print(f"[FEE INFO] Expected rates - Maker: {fees['maker']:.4%}, Taker: {fees['taker']:.4%}")
                        completion(("success", {
                            "vipLevel": vip_level,
                            "makerFee": fees['maker'],
                            "takerFee": fees['taker'],
                            "source": "trade_analysis_medium"
                        }))
                        return
            
            # If trade analysis failed, fall back to account endpoint
            self._fetchAccountFeeInfoFallback(completion)
        
        # Get recent trades (last 7 days)
        end_time = int(time.time() * 1000)
        start_time = end_time - (7 * 24 * 60 * 60 * 1000)
        
        self.fetchHistoryTrades(
            startTime=start_time,
            endTime=end_time,
            limit=50,
            completion=analyze_trades_callback
        )
    
    def _fetchAccountFeeInfoFallback(self, completion):
        """Fallback method using account endpoint (always returns VIP 0)"""
        # Try account endpoint as fallback
        url = "https://fapi.bitunix.com/api/v1/futures/account?marginCoin=USDT"
        keys = APIKeyStorage.shared().getKeys("BitUnix")
        
        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]
        
        # Generate signature
        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        queryParams = "marginCoinUSDT"
        body = ""
        
        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)
        
        headers = {
            "api-key": apiKey,
            "sign": sign,
            "nonce": nonce,
            "timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                # Account endpoint doesn't return VIP info, default to VIP 0
                completion(("success", {
                    "vipLevel": 0,
                    "makerFee": 0.0002,
                    "takerFee": 0.0006,
                    "source": "account_api_default"
                }))
            else:
                completion(("success", {
                    "vipLevel": 0,
                    "makerFee": 0.0002,
                    "takerFee": 0.0006,
                    "source": "default_error"
                }))
                
        except Exception as e:
            print(f"DEBUG: BitUnixExchange fetchAccountFeeInfo fallback error: {str(e)}")
            completion(("success", {
                "vipLevel": 0,
                "makerFee": 0.0002,
                "takerFee": 0.0006,
                "source": "default_exception"
            }))
    
    def fetchPositionTiers(self, symbol: str, completion):
        """
        Fetch position tier information for a symbol from BitUnix.
        This shows the risk limits and max position sizes for different leverage levels.
        
        completion: A callback with a Result-like signature:
                    success -> list[dict] containing tier information
                    failure -> Exception
        """
        url = f"https://fapi.bitunix.com/api/v1/futures/position/get_position_tiers?symbol={symbol}"
        keys = APIKeyStorage.shared().getKeys("BitUnix")
        
        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            completion(("failure", Exception("API keys not configured")))
            return
        
        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]
        
        # Generate signature for GET request
        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        queryParams = f"symbol{symbol}"  # Format for signature: namevalue
        body = ""
        
        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)
        
        headers = {
            "api-key": apiKey,
            "sign": sign,
            "nonce": nonce,
            "timestamp": timestamp,
            "language": "en-US",
            "Content-Type": "application/json"
        }
        
        print(f"DEBUG: BitUnixExchange fetchPositionTiers request URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: BitUnixExchange fetchPositionTiers response statusCode: {response.status_code}")
            
            responseStr = response.text
            print(f"DEBUG: BitUnixExchange fetchPositionTiers raw response: {responseStr}")
            
            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}, response: {responseStr}")
            
            data = response.json()
            
            if data.get("code") != 0:
                error_msg = data.get("msg", "Unknown error")
                raise Exception(f"API Error {data.get('code')}: {error_msg}")
            
            tiers = data.get("data", [])
            completion(("success", tiers))
            
        except Exception as e:
            print(f"DEBUG: BitUnixExchange fetchPositionTiers error: {str(e)}")
            completion(("failure", e))

    # WebSocket Interface Methods
    def get_name(self) -> str:
        """Get the name of the exchange"""
        return "BitUnix"
    
    def get_symbol_format(self, base_symbol: str) -> str:
        """Convert a base symbol to exchange-specific format"""
        # BitUnix uses format like BTCUSDT
        return base_symbol
    
    def translate_side_to_exchange(self, side: str) -> str:
        """Translate standard side to exchange-specific format"""
        # BitUnix uses BUY/SELL
        if side == PositionSide.LONG:
            return "BUY"
        elif side == PositionSide.SHORT:
            return "SELL"
        return side
    
    def translate_side_from_exchange(self, exchange_side: str) -> str:
        """Translate exchange-specific side to standard format"""
        if exchange_side == "BUY":
            return PositionSide.LONG
        elif exchange_side == "SELL":
            return PositionSide.SHORT
        return exchange_side
    
    def fetchAccountEquity(self, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch total account equity value"""
        def balance_callback(status_data):
            status, data = status_data
            if status == "success":
                # Calculate total equity from balances
                total_equity = 0.0
                for balance in data:
                    if balance.asset == "USDT":
                        total_equity = balance.balance
                        break
                completion(("success", total_equity))
            else:
                completion(("failure", data))
        
        self.fetchBalance(balance_callback)
    
    def connectWebSocket(self, 
                        on_message: Callable[[WebSocketMessage], None],
                        on_state_change: Callable[[WebSocketState], None],
                        on_error: Callable[[Exception], None]) -> bool:
        """Connect to the exchange WebSocket"""
        # Always create WebSocket manager first
        self._ws_manager = BitUnixWebSocketManager(
            on_message=on_message,
            on_error=on_error,
            on_state_change=on_state_change
        )
        
        # For now, always use public WebSocket for market data
        # Private WebSocket can be added later for order/position updates
        return self._ws_manager.connect_public()
    
    def disconnectWebSocket(self):
        """Disconnect from the WebSocket"""
        if self._ws_manager:
            self._ws_manager.disconnect()
    
    def subscribeWebSocket(self, subscriptions: List[WebSocketSubscription]) -> bool:
        """Subscribe to WebSocket channels"""
        if not self._ws_manager:
            return False
        
        # Convert to BitUnix format
        channels = []
        for sub in subscriptions:
            if sub.channel == WebSocketChannels.TICKER and sub.symbol:
                channels.append({
                    "symbol": sub.symbol,
                    "ch": "ticker"
                })
            elif sub.channel == WebSocketChannels.ORDERBOOK and sub.symbol:
                depth = sub.params.get("depth", 20) if sub.params else 20
                channels.append({
                    "symbol": sub.symbol,
                    "ch": "depth_books",
                    "depth": depth
                })
            elif sub.channel == WebSocketChannels.TRADES and sub.symbol:
                channels.append({
                    "symbol": sub.symbol,
                    "ch": "trade"
                })
            elif sub.channel == WebSocketChannels.ORDERS:
                channels.append({"ch": "order"})
            elif sub.channel == WebSocketChannels.POSITIONS:
                channels.append({"ch": "position"})
            elif sub.channel == WebSocketChannels.BALANCE:
                channels.append({"ch": "balance"})
        
        return self._ws_manager.subscribe(channels) if channels else False
    
    def unsubscribeWebSocket(self, subscriptions: List[WebSocketSubscription]) -> bool:
        """Unsubscribe from WebSocket channels"""
        if not self._ws_manager:
            return False
        
        # Convert to BitUnix format (same as subscribe)
        channels = []
        for sub in subscriptions:
            if sub.channel == WebSocketChannels.TICKER and sub.symbol:
                channels.append({
                    "symbol": sub.symbol,
                    "ch": "ticker"
                })
            elif sub.channel == WebSocketChannels.ORDERBOOK and sub.symbol:
                channels.append({
                    "symbol": sub.symbol,
                    "ch": "depth_books"
                })
            elif sub.channel == WebSocketChannels.TRADES and sub.symbol:
                channels.append({
                    "symbol": sub.symbol,
                    "ch": "trade"
                })
            elif sub.channel == WebSocketChannels.ORDERS:
                channels.append({"ch": "order"})
            elif sub.channel == WebSocketChannels.POSITIONS:
                channels.append({"ch": "position"})
            elif sub.channel == WebSocketChannels.BALANCE:
                channels.append({"ch": "balance"})
        
        return self._ws_manager.unsubscribe(channels) if channels else False
    
    def getWebSocketState(self) -> WebSocketState:
        """Get current WebSocket connection state"""
        if self._ws_manager:
            return self._ws_manager.get_state()
        return WebSocketState.DISCONNECTED
    
    def isWebSocketConnected(self) -> bool:
        """Check if WebSocket is connected and ready"""
        return self._ws_manager.is_connected() if self._ws_manager else False
    
    # Helper for double sha256
    def sha256Hex(self, input_str: str) -> str:
        """
        Generates a SHA-256 hex digest of the input string.
        """
        return hashlib.sha256(input_str.encode('utf-8')).hexdigest()
    
    def fetchPositionMode(self, completion):
        """
        Fetch the current position mode (one-way or hedge mode).
        Since BitUnix doesn't have a dedicated endpoint, we'll infer from position data.
        
        completion: A callback with a Result-like signature:
                    success -> dict containing position mode info {"positionMode": "ONE_WAY" or "HEDGE"}
                    failure -> Exception
        """
        # Try to get position mode from account info
        url = "https://fapi.bitunix.com/api/v1/futures/account/get_single_account"
        keys = APIKeyStorage.shared().getKeys("BitUnix")
        
        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            # If no API keys, check from any open position
            def pos_callback(status_data):
                status, data = status_data
                if status == "success" and data:
                    # Get mode from first position
                    for pos in data:
                        if hasattr(pos, 'raw_response') and pos.raw_response:
                            mode = pos.raw_response.get('positionMode', 'HEDGE')
                            completion(("success", {"positionMode": mode}))
                            return
                # Default to HEDGE if no positions
                completion(("success", {"positionMode": "HEDGE", "source": "default"}))
            
            self.fetchPositions(pos_callback)
            return
        
        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]
        
        # Generate signature for GET request
        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        queryParams = ""  # No query params
        body = ""
        
        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)
        
        headers = {
            "api-key": apiKey,
            "sign": sign,
            "nonce": nonce,
            "timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers)
            responseStr = response.text
            
            if response.status_code != 200:
                # Fallback to checking positions
                def pos_callback(status_data):
                    status, data = status_data
                    if status == "success" and data:
                        # Get mode from first position
                        for pos in data:
                            if hasattr(pos, 'raw_response') and pos.raw_response:
                                mode = pos.raw_response.get('positionMode', 'HEDGE')
                                completion(("success", {"positionMode": mode, "source": "position"}))
                                return
                    # Default to HEDGE if no positions
                    completion(("success", {"positionMode": "HEDGE", "source": "default"}))
                
                self.fetchPositions(pos_callback)
                return
            
            json_data = json.loads(responseStr)
            
            if json_data.get('code', 0) == 0:
                # Extract position mode from account data
                data = json_data.get("data", {})
                position_mode = data.get("positionMode", "HEDGE")
                completion(("success", {"positionMode": position_mode, "source": "account"}))
            else:
                # Fallback to positions
                def pos_callback(status_data):
                    status, data = status_data
                    if status == "success" and data:
                        for pos in data:
                            if hasattr(pos, 'raw_response') and pos.raw_response:
                                mode = pos.raw_response.get('positionMode', 'HEDGE')
                                completion(("success", {"positionMode": mode, "source": "position"}))
                                return
                    completion(("success", {"positionMode": "HEDGE", "source": "default"}))
                
                self.fetchPositions(pos_callback)
                
        except Exception as e:
            # Fallback to positions on any error
            def pos_callback(status_data):
                status, data = status_data
                if status == "success" and data:
                    for pos in data:
                        if hasattr(pos, 'raw_response') and pos.raw_response:
                            mode = pos.raw_response.get('positionMode', 'HEDGE')
                            completion(("success", {"positionMode": mode, "source": "position"}))
                            return
                completion(("success", {"positionMode": "HEDGE", "source": "default"}))
            
            self.fetchPositions(pos_callback)
    
    def setPositionMode(self, mode: str, completion):
        """
        Set the position mode (one-way or hedge mode).
        
        Args:
            mode: "ONE_WAY" or "HEDGE"
            completion: A callback with a Result-like signature
        """
        url = "https://fapi.bitunix.com/api/v1/futures/account/change_position_mode"
        keys = APIKeyStorage.shared().getKeys("BitUnix")
        
        if not keys or not keys.get("apiKey") or not keys.get("secretKey"):
            completion(("failure", Exception("API keys not configured")))
            return
        
        apiKey = keys["apiKey"]
        secretKey = keys["secretKey"]
        
        # BitUnix expects "positionMode" parameter with "ONE_WAY" or "HEDGE" value
        body = json.dumps({
            "positionMode": mode.upper()
        })
        
        # Generate signature for POST request
        nonce = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time() * 1000))
        queryParams = ""  # No query params
        
        digestInput = f"{nonce}{timestamp}{apiKey}{queryParams}{body}"
        digest = self.sha256Hex(digestInput)
        signInput = f"{digest}{secretKey}"
        sign = self.sha256Hex(signInput)
        
        headers = {
            "api-key": apiKey,
            "sign": sign,
            "nonce": nonce,
            "timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        print(f"DEBUG: BitUnixExchange setPositionMode URL: {url}")
        print(f"DEBUG: BitUnixExchange setPositionMode body: {body}")
        
        try:
            response = requests.post(url, headers=headers, data=body)
            responseStr = response.text
            
            print(f"DEBUG: BitUnixExchange setPositionMode response statusCode: {response.status_code}")
            print(f"DEBUG: BitUnixExchange setPositionMode raw response: {responseStr}")
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {responseStr}")
            
            json_data = json.loads(responseStr)
            
            if json_data.get('code', 0) == 0:
                completion(("success", {"positionMode": mode, "message": "Position mode changed successfully"}))
            else:
                error_msg = json_data.get('msg', 'Unknown error')
                completion(("failure", Exception(f"API Error {json_data.get('code')}: {error_msg}")))
                
        except Exception as e:
            print(f"DEBUG: BitUnixExchange setPositionMode error: {str(e)}")
            completion(("failure", e))