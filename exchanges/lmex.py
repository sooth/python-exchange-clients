"""
This Python module provides an LMEX-specific implementation of an ExchangeProtocol,
mirroring the functionality found in BitUnix.py but adapted for LMEX exchange.

It includes:
- LMEX REST API integration for futures trading
- HMAC-SHA384 authentication as per LMEX requirements
- Methods to fetch tickers, positions, and place orders via REST API calls
- WebSocket manager placeholder for future real-time data integration

Dependencies:
- requests (for HTTP requests)
- hashlib/hmac (for HMAC-SHA384)
- json (for JSON parsing)
- python-dotenv (for environment variables)
"""

import requests
from typing import Optional, Type, Dict, Any, List
import json
import hashlib
import hmac
import time
import uuid
import threading
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import urllib.parse

# ------------------------------------------------------------------------------
# Mock definitions for the protocols and data structures referenced
# ------------------------------------------------------------------------------

class ExchangeWebSocketManagerProtocol:
    """
    A protocol defining the methods a WebSocket manager should implement.
    This is a placeholder for the Python version.
    """
    def subscribeToTicker(self, symbol: str):
        raise NotImplementedError
    
    def lastTradePrice(self, symbol: str) -> float:
        raise NotImplementedError
    
    def subscribeToOrders(self, symbols: list[str]):
        raise NotImplementedError


class LMEXWebSocketManager(ExchangeWebSocketManagerProtocol):
    """
    A mock or placeholder for LMEX WebSocket manager.
    In actual usage, you would implement real WebSocket functionalities here.
    """
    _shared_instance: Optional['LMEXWebSocketManager'] = None

    @classmethod
    def shared(cls):
        if cls._shared_instance is None:
            cls._shared_instance = cls()
        return cls._shared_instance

    def subscribeToTicker(self, symbol: str):
        print(f"DEBUG: Subscribing to ticker for {symbol} (WebSocket not actually implemented).")

    def lastTradePrice(self, symbol: str) -> float:
        """Get the last trade price for a symbol - fetch from market data."""
        # LMEX doesn't have WebSocket caching yet, so fetch from REST API
        # This is called from the main LMEX class which will handle the fetch
        return 0.0  # Return 0 to indicate no cached price

    def subscribeToOrders(self, symbols: list[str]):
        print(f"DEBUG: Subscribing to orders for symbols {symbols} (WebSocket not actually implemented).")


class ExchangeProtocol:
    """
    A protocol (or abstract base class) that an Exchange class should implement.
    """
    def subscribeToTicker(self, symbol: str):
        raise NotImplementedError
    
    def lastTradePrice(self, symbol: str) -> float:
        raise NotImplementedError

    def subscribeToOrders(self, symbols: list[str]):
        raise NotImplementedError
    
    def fetchTickers(self, completion):
        raise NotImplementedError
    
    def fetchPositions(self, completion):
        raise NotImplementedError
    
    def placeOrder(self, request, completion):
        raise NotImplementedError
    
    def fetchBalance(self, completion):
        raise NotImplementedError
    
    def createGridBot(self, symbol: str, direction: str, upper_price: float, 
                     lower_price: float, leverage: float, wallet_mode: str, 
                     grid_number: int, initial_margin: float, 
                     cancel_all_on_stop: bool, close_all_on_stop: bool, 
                     completion):
        """
        Create a new LMEX Grid bot using the Bearer token.
        
        Args:
            symbol: Trading symbol (e.g., "BTC-PERP")
            direction: "LONG" or "SHORT"
            upper_price: Upper price boundary for the grid
            lower_price: Lower price boundary for the grid
            leverage: Leverage to use
            wallet_mode: "CROSS" or "ISOLATED"
            grid_number: Number of grid levels
            initial_margin: Initial margin in USDT
            cancel_all_on_stop: Whether to cancel all orders when bot stops
            close_all_on_stop: Whether to close all positions when bot stops
            completion: Callback function with Result
        """
        try:
            # Get Bearer token from environment
            bearer_token = os.getenv("LMEX_BEARER_TOKEN", "")
            if not bearer_token:
                error = Exception("No LMEX Bearer token configured")
                completion(error, None)
                return
            
            url = "https://api.lmex.io/taskExecutor/api/v1/tradingBots"
            
            # Calculate mid price
            mid_price = (upper_price + lower_price) / 2.0
            
            # Get price precision for the symbol
            price_precision = self.precision_manager.get_price_precision(symbol)
            
            # Format prices with correct precision
            mid_price_str = f"{mid_price:.{price_precision}f}"
            upper_price_str = f"{upper_price:.{price_precision}f}"
            lower_price_str = f"{lower_price:.{price_precision}f}"
            
            # Build request body according to LMEX API format
            body = {
                "symbol": symbol,
                "marketType": "FUTURES",
                "botType": "GRID",
                "config": {
                    "tradingDirection": direction.upper(),
                    "midPrice": mid_price_str,
                    "upperPrice": upper_price_str,
                    "lowerPrice": lower_price_str,
                    "wallet": {
                        "mode": wallet_mode.upper(),
                        "leverage": str(leverage)
                    },
                    "gridNumber": grid_number,
                    "initialMargin": str(initial_margin),
                    "botStopAction": {
                        "cancelAllOrders": cancel_all_on_stop,
                        "closeAllPositions": close_all_on_stop
                    },
                    "feeType": "MAKER"
                },
                "hideCode": True
            }
            
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {bearer_token}",
                "accept": "application/json, text/plain, */*",
                "accept-language": "en",
                "lang": "en",
                "web": "true"
            }
            
            response = requests.post(url, json=body, headers=headers)
            
            print(f"DEBUG: createGridBot response => {response.text}")
            
            # Parse response
            try:
                data = response.json()
                if data.get("success"):
                    completion(None, data)
                else:
                    error_msg = data.get("msg", "Unknown error")
                    error_code = data.get("code", -1)
                    error = Exception(f"Failed to create grid bot: {error_msg} (code: {error_code})")
                    completion(error, None)
            except json.JSONDecodeError:
                error = Exception(f"Invalid JSON response: {response.text}")
                completion(error, None)
                
        except Exception as e:
            completion(e, None)
    
    def fetchGridBots(self, completion):
        """
        Fetch the list of grid bots from LMEX.
        
        Args:
            completion: Callback function with (error, bots_list)
        """
        try:
            # Try Bearer token first, then fall back to API key/secret
            bearer_token = os.getenv("LMEX_BEARER_TOKEN", "")
            api_key = os.getenv("LMEX_API_KEY", "")
            secret_key = os.getenv("LMEX_SECRET_KEY", "")
            
            path = "/taskExecutor/api/v1/tradingBots?marketType=FUTURES&botType=GRID"
            url = f"https://api.lmex.io{path}"
            
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "en"
            }
            
            if bearer_token:
                # Use Bearer token authentication
                headers["authorization"] = f"Bearer {bearer_token}"
            elif api_key and secret_key:
                # Use standard LMEX API key authentication
                nonce = str(int(time.time() * 1000))
                sign_message = path + nonce
                signature = self._generate_signature(path, nonce, "")
                
                headers["request-api"] = api_key
                headers["request-nonce"] = nonce
                headers["request-sign"] = signature
            else:
                # No credentials available
                completion(None, [])
                return
            
            response = requests.get(url, headers=headers)
            
            print(f"DEBUG: fetchGridBots raw => {response.text}")
            
            try:
                data = response.json()
                
                if not data.get("success", False):
                    error_msg = f"LMEX returned success={data.get('success')}, code={data.get('code')}, msg={data.get('msg', 'no message')}"
                    error = Exception(f"Failed to retrieve LMEX bots: {error_msg}")
                    completion(error, None)
                    return
                
                raw_bots = data.get("data", {}).get("tradingBots", [])
                
                # Convert raw bot data to simplified format
                bots = []
                for row in raw_bots:
                    direction = row.get("direction", "")
                    detail = row.get("detail", {})
                    position = detail.get("position", {})
                    
                    bot = {
                        "tradingBotId": row["tradingBotId"],
                        "symbol": row["symbol"],
                        "totalProfit": float(row.get("totalProfit", "0")),
                        "realizedProfit": float(row.get("realizedProfit", "0")),
                        "unrealizedProfit": float(row.get("unrealizedProfit", "0")),
                        "createdAt": row.get("createdAt"),
                        "totalProfitInUsdt": float(row.get("totalProfitInUsdt", "0")),
                        "direction": direction,
                        "entryPrice": position.get("entryPrice", 0.0),
                        "totalContracts": position.get("totalContracts", 0.0),
                        "upperPrice": float(detail.get("upperPrice", "0")) if detail.get("upperPrice") else None,
                        "lowerPrice": float(detail.get("lowerPrice", "0")) if detail.get("lowerPrice") else None
                    }
                    bots.append(bot)
                
                completion(None, bots)
                
            except (json.JSONDecodeError, KeyError) as e:
                error = Exception(f"Failed to parse grid bots response: {str(e)}")
                completion(error, None)
                
        except Exception as e:
            completion(e, None)
        
    def fetchOrders(self, completion):
        raise NotImplementedError


class ExchangeTicker:
    """
    A data structure representing an exchange ticker.
    """
    def __init__(self, symbol: str):
        self.symbol = symbol

    def __repr__(self):
        return f"ExchangeTicker(symbol='{self.symbol}')"


class ExchangePosition:
    """
    A data structure representing an exchange position.
    """
    def __init__(
        self,
        symbol: str,
        size: float,
        entryPrice: float,
        markPrice: float,
        pnl: float,
        pnlPercentage: float
    ):
        self.symbol = symbol
        self.size = size
        self.entryPrice = entryPrice
        self.markPrice = markPrice
        self.pnl = pnl
        self.pnlPercentage = pnlPercentage

    def __repr__(self):
        return (
            f"ExchangePosition(symbol='{self.symbol}', size={self.size}, "
            f"entryPrice={self.entryPrice}, markPrice={self.markPrice}, "
            f"pnl={self.pnl}, pnlPercentage={self.pnlPercentage})"
        )


class ExchangeOrderRequest:
    """
    A data structure for representing an exchange order request.
    """
    def __init__(
        self,
        symbol: str,
        side: str,
        qty: float,
        orderType: str,
        price: Optional[float] = None,
        timeInForce: str = "GTC",
        orderLinkId: Optional[str] = None,
        stopLoss: Optional[float] = None,
        takeProfit: Optional[float] = None
    ):
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.orderType = orderType
        self.price = price
        self.timeInForce = timeInForce
        self.orderLinkId = orderLinkId
        self.stopLoss = stopLoss
        self.takeProfit = takeProfit

    def __repr__(self):
        return (
            f"ExchangeOrderRequest(symbol='{self.symbol}', side='{self.side}', qty={self.qty}, "
            f"orderType='{self.orderType}', price={self.price}, timeInForce='{self.timeInForce}', "
            f"orderLinkId='{self.orderLinkId}', stopLoss={self.stopLoss}, takeProfit={self.takeProfit})"
        )


class ExchangeOrderResponse:
    """
    A data structure for representing the response to placing an order.
    """
    def __init__(self, rawResponse: str):
        try:
            # Parse the JSON response
            self.rawResponse = json.loads(rawResponse) if isinstance(rawResponse, str) else rawResponse
        except json.JSONDecodeError:
            # Fallback to raw string if parsing fails
            self.rawResponse = {"data": rawResponse}

    def __repr__(self):
        return f"ExchangeOrderResponse(rawResponse={self.rawResponse})"


class ExchangeBalance:
    """
    A data structure representing account balance information.
    """
    def __init__(
        self,
        asset: str,
        balance: float,
        available: float,
        locked: float
    ):
        self.asset = asset
        self.balance = balance
        self.available = available
        self.locked = locked

    def __repr__(self):
        return (
            f"ExchangeBalance(asset='{self.asset}', balance={self.balance}, "
            f"available={self.available}, locked={self.locked})"
        )


class ExchangeOrder:
    """
    A data structure representing an open order.
    """
    def __init__(
        self,
        orderId: str,
        symbol: str,
        side: str,
        orderType: str,
        qty: float,
        price: Optional[float],
        status: str,
        timeInForce: str,
        createTime: int,
        clientId: Optional[str] = None,
        stopPrice: Optional[float] = None,
        executedQty: float = 0.0
    ):
        self.orderId = orderId
        self.symbol = symbol
        self.side = side
        self.orderType = orderType
        self.qty = qty
        self.price = price
        self.status = status
        self.timeInForce = timeInForce
        self.createTime = createTime
        self.clientId = clientId
        self.stopPrice = stopPrice
        self.executedQty = executedQty

    def __repr__(self):
        return (
            f"ExchangeOrder(orderId='{self.orderId}', symbol='{self.symbol}', "
            f"side='{self.side}', orderType='{self.orderType}', qty={self.qty}, "
            f"price={self.price}, status='{self.status}')"
        )


class SymbolPrecisionManager:
    """
    Manages symbol precision data from LMEX API to ensure accurate order formatting
    """
    _instance = None
    CACHE_FILE = "lmex_precision_cache.json"
    
    def __init__(self):
        self.precision_cache: Dict[str, Dict[str, Any]] = {}
        self.last_update: Optional[datetime] = None
        self.cache_duration_hours = 24
        # Load cached data on initialization
        self._load_cache()
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol info including precision data"""
        if self._needs_refresh():
            self._fetch_all_symbols()
        
        # Return cached data or sensible defaults
        return self.precision_cache.get(symbol, {
            "price_decimal": 2,
            "qty_decimal": 4,
            "min_qty": 0.0001,
            "tick_size": 0.01,
            "step_size": 0.0001
        })
    
    def get_price_precision(self, symbol: str) -> int:
        """Get price precision (decimal places) for a symbol"""
        symbol_info = self.get_symbol_info(symbol)
        return symbol_info.get("price_decimal", 2)
    
    def get_quantity_precision(self, symbol: str) -> int:
        """Get quantity precision (decimal places) for a symbol"""
        symbol_info = self.get_symbol_info(symbol)
        return symbol_info.get("qty_decimal", 4)
    
    def get_min_quantity(self, symbol: str) -> float:
        """Get minimum trade quantity for a symbol"""
        symbol_info = self.get_symbol_info(symbol)
        return float(symbol_info.get("min_qty", 0.0001))
    
    def has_symbol(self, symbol: str) -> bool:
        """Check if a symbol is supported"""
        if self._needs_refresh():
            self._fetch_all_symbols()
        return symbol in self.precision_cache
    
    def get_contract_size(self, symbol: str) -> float:
        """Get contract size for a symbol"""
        symbol_info = self.get_symbol_info(symbol)
        contract_size = symbol_info.get("contract_size")
        
        if contract_size is None:
            raise ValueError(f"Contract size not found for {symbol}. Please ensure fetchTickers() has been called to populate symbol data.")
        
        return float(contract_size)
    
    def _needs_refresh(self) -> bool:
        """Check if cache needs refreshing - only on first init when cache is empty"""
        # Only fetch fresh data if we have no cached data at all
        return len(self.precision_cache) == 0
    
    def _fetch_all_symbols(self):
        """Fetch all symbol precision data from LMEX API"""
        try:
            print("DEBUG: Fetching symbol precision data from LMEX API...")
            # First try to get ticker data which has actual prices
            # We'll use this to infer precision
            exchange = LMEXExchange()
            tickers_received = threading.Event()
            ticker_data = None
            
            def ticker_callback(result):
                nonlocal ticker_data
                status, data = result
                if status == "success":
                    ticker_data = data
                tickers_received.set()
            
            exchange.fetchTickers(ticker_callback)
            
            if tickers_received.wait(timeout=10) and ticker_data:
                # Clear cache and update with fresh data
                self.precision_cache.clear()
                
                for ticker in ticker_data:
                    symbol = ticker.symbol
                    last_price = ticker.lastPrice
                    
                    # Detect decimal precision from actual price
                    price_decimals = self._detect_decimal_places(last_price)
                    
                    # Store precision data
                    self.precision_cache[symbol] = {
                        "price_decimal": price_decimals,
                        "qty_decimal": 0,  # LMEX uses integer contracts
                        "min_qty": 1,      # Min 1 contract
                        "tick_size": 10 ** (-price_decimals) if price_decimals > 0 else 1,
                        "step_size": 1,    # Step size is 1 contract
                        "max_leverage": 100,
                        "maintenance_margin_rate": 0.005
                    }
                
                self.last_update = datetime.now()
                print(f"DEBUG: Cached precision data for {len(self.precision_cache)} symbols")
                
                # Show some examples
                examples = list(self.precision_cache.items())[:5]
                for symbol, info in examples:
                    print(f"  {symbol}: {info['price_decimal']} decimals")
                
                # Save to cache file
                self._save_cache()
                
        except Exception as e:
            print(f"WARNING: Failed to fetch symbol precision data: {e}")
            print("DEBUG: Using fallback precision defaults")
    
    def _detect_decimal_places(self, price: float) -> int:
        """Detect the number of decimal places in a price"""
        if price == 0:
            return 2  # Default
        
        # Convert to string and analyze
        price_str = f"{price:.10f}".rstrip('0')
        if '.' in price_str:
            decimal_part = price_str.split('.')[1]
            return len(decimal_part) if decimal_part else 0
        return 0
    
    def _load_cache(self):
        """Load cached precision data from file"""
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r') as f:
                    cache_data = json.load(f)
                    self.precision_cache = cache_data.get('precision_cache', {})
                    # Convert timestamp string back to datetime
                    if cache_data.get('last_update'):
                        self.last_update = datetime.fromisoformat(cache_data['last_update'])
                    print(f"DEBUG: Loaded precision cache with {len(self.precision_cache)} symbols from {self.CACHE_FILE}")
            else:
                print(f"DEBUG: No cache file found at {self.CACHE_FILE}, will fetch fresh data")
        except Exception as e:
            print(f"WARNING: Failed to load precision cache: {e}")
            self.precision_cache = {}
            self.last_update = None
    
    def _save_cache(self):
        """Save precision data to cache file"""
        try:
            cache_data = {
                'precision_cache': self.precision_cache,
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'version': '1.0'
            }
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"DEBUG: Saved precision cache with {len(self.precision_cache)} symbols to {self.CACHE_FILE}")
        except Exception as e:
            print(f"WARNING: Failed to save precision cache: {e}")


class APIKeyStorage:
    """
    A storage mechanism that retrieves API keys from environment variables.
    """
    _shared_instance: Optional['APIKeyStorage'] = None

    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get API keys from environment variables
        self._keys = {
            "LMEX": {
                "apiKey": os.getenv("LMEX_API_KEY", ""),
                "secretKey": os.getenv("LMEX_SECRET_KEY", "")
            }
        }

    @classmethod
    def shared(cls):
        if cls._shared_instance is None:
            cls._shared_instance = cls()
        return cls._shared_instance

    def getKeys(self, for_exchange: str):
        # Returns a dictionary with 'apiKey' and 'secretKey'
        return self._keys.get(for_exchange, {"apiKey": "", "secretKey": ""})


# ----------------------------------------------------------------------
# Python version of LMEXExchange, mirroring BitUnixExchange implementation
# ----------------------------------------------------------------------
class LMEXExchange(ExchangeProtocol):
    """
    An LMEX-specific implementation of ExchangeProtocol (Python version).
    """
    
    def __init__(self):
        self.precision_manager = SymbolPrecisionManager.get_instance()
        self.base_url = "https://api.lmex.io/futures"

    @property
    def webSocketManager(self) -> ExchangeWebSocketManagerProtocol:
        """
        Provide a reference to the exchange's WebSocket manager
        so UI layers can subscribe to real-time data.
        """
        return LMEXWebSocketManager.shared()

    # MARK: - WebSocket Support
    def subscribeToTicker(self, symbol: str):
        """
        Subscribe to ticker updates for a given symbol.
        """
        self.webSocketManager.subscribeToTicker(symbol)

    def lastTradePrice(self, symbol: str) -> float:
        """
        Retrieve the last trade price for a given symbol.
        """
        # First check WebSocket manager cache
        cached_price = self.webSocketManager.lastTradePrice(symbol)
        if cached_price > 0:
            return cached_price
        
        # If no cached price, fetch from market summary
        market_data = None
        data_received = threading.Event()
        
        def market_callback(result):
            nonlocal market_data
            status, data = result
            if status == "success":
                market_data = data
            data_received.set()
        
        # Fetch market summary which includes all symbols
        self.fetchTickers(market_callback)
        
        if data_received.wait(timeout=5):
            if market_data and isinstance(market_data, list):
                for ticker in market_data:
                    if ticker.symbol == symbol:
                        # Try to get last price from ticker data
                        # LMEX market summary might have different field names
                        if hasattr(ticker, 'lastPrice'):
                            return float(ticker.lastPrice)
                        # Check the raw market data
                        for market in market_data:
                            if isinstance(market, dict) and market.get('symbol') == symbol:
                                # LMEX uses 'last' field for last price
                                last_price = market.get('last', market.get('lastPrice', 0))
                                if last_price:
                                    return float(last_price)
        
        # Return 0 if no price found
        print(f"WARNING: Could not fetch real price for {symbol}")
        return 0.0

    def subscribeToOrders(self, symbols: list[str]):
        """
        Subscribe to order updates for a list of symbols.
        """
        self.webSocketManager.subscribeToOrders(symbols)

    # MARK: - Authentication Helper
    def _generate_signature(self, path: str, nonce: str, body: str = "") -> str:
        """
        Generate HMAC-SHA384 signature for LMEX API
        Signature = HMAC.Sha384(secretKey, (path + request-nonce + body))
        """
        keys = APIKeyStorage.shared().getKeys("LMEX")
        secret_key = keys.get("secretKey", "")
        
        if not secret_key:
            raise Exception("LMEX secret key not found")
        
        # Construct the message to sign
        message = f"{path}{nonce}{body}"
        
        # Generate HMAC-SHA384
        signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha384
        ).hexdigest()
        
        return signature

    def _get_auth_headers(self, path: str, body: str = "") -> Dict[str, str]:
        """
        Generate authentication headers for LMEX API requests
        """
        keys = APIKeyStorage.shared().getKeys("LMEX")
        api_key = keys.get("apiKey", "")
        
        if not api_key:
            raise Exception("LMEX API key not found")
        
        # Generate nonce (timestamp in milliseconds)
        nonce = str(int(time.time() * 1000))
        
        # Generate signature
        signature = self._generate_signature(path, nonce, body)
        
        return {
            "request-api": api_key,
            "request-nonce": nonce,
            "request-sign": signature,
            "Content-Type": "application/json"
        }

    # MARK: - REST API Calls
    def fetchTickers(self, completion):
        """
        Fetch ticker information from LMEX via REST API.
        
        completion: A callback with a Result-like signature:
                    success -> list[ExchangeTicker]
                    failure -> Exception
        """
        path = "/api/v2.2/market_summary?listFullAttributes=true"
        url = f"{self.base_url}{path}"

        # DEBUG: Print request info
        print(f"DEBUG: LMEXExchange fetchTickers request URL: {url}")

        try:
            response = requests.get(url)
            # DEBUG: Print response info
            print(f"DEBUG: LMEXExchange fetchTickers response statusCode: {response.status_code}")

            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}")

            data = response.json()
            # LMEX v2.2 returns array directly
            if isinstance(data, list):
                tickers = []
                for market in data:
                    symbol = market.get("symbol")
                    if symbol:
                        ticker = ExchangeTicker(symbol)
                        # LMEX uses 'last' field for last price
                        ticker.lastPrice = float(market.get("last", 0))
                        ticker.bidPrice = float(market.get("bid", 0))
                        ticker.askPrice = float(market.get("ask", 0))
                        ticker.volume = float(market.get("volume", 0))
                        ticker.price = float(market.get("last", 0))  # Alias
                        tickers.append(ticker)
                        
                        # Update precision cache with contract size
                        if hasattr(self, 'precision_manager') and 'contractSize' in market:
                            if symbol not in self.precision_manager.precision_cache:
                                self.precision_manager.precision_cache[symbol] = {}
                            self.precision_manager.precision_cache[symbol]['contract_size'] = float(market['contractSize'])
                            self.precision_manager.precision_cache[symbol]['min_qty'] = float(market.get('minOrderSize', 1))
                            self.precision_manager.precision_cache[symbol]['max_qty'] = float(market.get('maxOrderSize', 1000000))
                            self.precision_manager.precision_cache[symbol]['tick_size'] = float(market.get('minPriceIncrement', 0.01))
                            
                # Save updated cache after fetching tickers
                if hasattr(self, 'precision_manager'):
                    self.precision_manager._save_cache()
                completion(("success", tickers))
            else:
                raise Exception(f"Unexpected response format")

        except Exception as e:
            print(f"DEBUG: LMEXExchange fetchTickers error: {str(e)}")
            completion(("failure", e))

    def fetchPositions(self, completion):
        """
        Fetch open positions via LMEX REST API.
        
        completion: A callback with a Result-like signature:
                    success -> list[ExchangePosition]
                    failure -> Exception
        """
        path = "/api/v2.2/user/positions"
        url = f"{self.base_url}{path}"
        
        try:
            headers = self._get_auth_headers(path)
        except Exception as e:
            completion(("failure", e))
            return

        print(f"DEBUG: LMEXExchange fetchPositions request URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: LMEXExchange fetchPositions response statusCode: {response.status_code}")

            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}")

            data = response.json()
            print(f"DEBUG: LMEXExchange fetchPositions raw response: {json.dumps(data)}")

            positions = []
            
            # Handle both array and object response formats
            if isinstance(data, list):
                positions_data = data
            elif isinstance(data, dict) and "positions" in data:
                positions_data = data["positions"]
            else:
                positions_data = []
            
            for item in positions_data:
                symbol = item.get("symbol")
                # qty is the position size (positive for long, negative for short)
                qty = float(item.get("qty", 0))
                avg_price = float(item.get("avgPrice", 0))
                mark_price = float(item.get("markPrice", avg_price))
                unrealized_pnl = float(item.get("unrealizedPnl", 0))
                
                if symbol and qty != 0:
                    # Calculate PnL percentage
                    pnl_percentage = 0.0
                    if avg_price != 0 and qty != 0:
                        pnl_percentage = (unrealized_pnl / (avg_price * abs(qty))) * 100

                    positions.append(
                        ExchangePosition(
                            symbol=symbol,
                            size=qty,  # Already signed (negative for short)
                            entryPrice=avg_price,
                            markPrice=mark_price,
                            pnl=unrealized_pnl,
                            pnlPercentage=pnl_percentage
                        )
                    )

            completion(("success", positions))

        except Exception as e:
            print(f"DEBUG: LMEXExchange fetchPositions error: {str(e)}")
            completion(("failure", e))

    def placeOrder(self, request: ExchangeOrderRequest, completion):
        """
        Place an order via LMEX REST API.
        
        completion: A callback with a Result-like signature:
                    success -> ExchangeOrderResponse
                    failure -> Exception
        """
        path = "/api/v2.2/order"
        url = f"{self.base_url}{path}"

        # Get symbol precision info
        symbol = request.symbol
        price_precision = self.precision_manager.get_price_precision(symbol)
        quantity_precision = self.precision_manager.get_quantity_precision(symbol)
        min_qty = self.precision_manager.get_min_quantity(symbol)
        
        # Get contract size for this symbol
        contract_size = self.precision_manager.get_contract_size(symbol)
        
        # Convert asset amount to LMEX contracts
        contracts = int(request.qty / contract_size)
        
        # Ensure quantity meets minimum requirements
        if contracts < min_qty:
            print(f"DEBUG: Adjusting quantity from {request.qty} units ({contracts} contracts) to minimum {min_qty} contracts for {symbol}")
            actual_qty = min_qty
        else:
            actual_qty = contracts
            print(f"DEBUG: Converting {request.qty} units to {contracts} contracts for {symbol} (contract_size: {contract_size})")

        # Map order side to LMEX format
        side = request.side.upper()
        if side == "LONG":
            side = "BUY"
        elif side == "SHORT":
            side = "SELL"

        # Map order types
        order_type = request.orderType.upper()

        payload = {
            "symbol": symbol,
            "side": side,
            "size": int(actual_qty),  # LMEX uses integer for contract size
            "type": order_type,
            "time_in_force": request.timeInForce,
            "postOnly": False,
            "trailValue": 0
        }
        
        # Add price for limit orders
        if request.price is not None and order_type == "LIMIT":
            payload["price"] = round(request.price, price_precision)
        
        # Add client order ID if provided
        if request.orderLinkId is not None:
            payload["clOrderID"] = request.orderLinkId
        
        body_str = json.dumps(payload)
        
        try:
            headers = self._get_auth_headers(path, body_str)
        except Exception as e:
            completion(("failure", e))
            return

        print(f"DEBUG: LMEXExchange placeOrder URL: {url}")
        print(f"DEBUG: LMEXExchange placeOrder headers: {headers}")
        print(f"DEBUG: LMEXExchange placeOrder body: {body_str}")

        try:
            response = requests.post(url, headers=headers, data=body_str)
            print(f"DEBUG: LMEXExchange placeOrder response statusCode: {response.status_code}")
            
            response_str = response.text
            print(f"DEBUG: LMEXExchange placeOrder raw response: {response_str}")

            # Check response status
            if response.status_code != 200:
                # Parse error response
                try:
                    error_data = json.loads(response_str)
                    error_msg = error_data.get('message', f'HTTP {response.status_code}')
                    error_code = error_data.get('errorCode', 'UNKNOWN')
                    raise Exception(f"Order failed: {error_msg} (code: {error_code})")
                except json.JSONDecodeError:
                    raise Exception(f"HTTP {response.status_code}: {response_str}")
            
            # Parse success response
            json_data = json.loads(response_str) if response_str else {}
            
            # LMEX returns a list with one order object
            if isinstance(json_data, list) and len(json_data) > 0:
                # Extract the first order from the list
                order_data = json_data[0]
            else:
                order_data = json_data
            
            orderResponse = ExchangeOrderResponse(order_data)
            completion(("success", orderResponse))
        except Exception as e:
            print(f"DEBUG: LMEXExchange placeOrder error: {str(e)}")
            completion(("failure", e))

    def fetchAccountEquity(self, completion):
        """
        Fetch the actual account equity from LMEX.
        
        completion: A callback with a Result-like signature:
                    success -> float (total equity in USDT)
                    failure -> Exception
        """
        # For auth, use path without query params
        auth_path = "/api/v2.2/user/wallet"
        query_string = "?wallet=CROSS@"
        url = f"{self.base_url}{auth_path}{query_string}"
        
        try:
            headers = self._get_auth_headers(auth_path)
        except Exception as e:
            completion(("failure", e))
            return

        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                completion(("failure", Exception(f"HTTP error: {response.status_code}")))
                return

            json_data = json.loads(response.text)
            
            # Extract total equity from response
            total_equity = 0.0
            
            # LMEX returns an array with wallet info
            if isinstance(json_data, list) and len(json_data) > 0:
                wallet_data = json_data[0]
                # Use totalValue which represents the total account value
                total_equity = float(wallet_data.get("totalValue", 0))
                
                print(f"DEBUG: LMEX Account Equity: {total_equity}")
            elif isinstance(json_data, dict):
                # Fallback for dict format
                total_equity = float(json_data.get("totalEquity", 0))
                
            completion(("success", total_equity))
                
        except Exception as e:
            completion(("failure", e))
    
    def fetchBalance(self, completion):
        """
        Fetch account balance via LMEX REST API.
        
        completion: A callback with a Result-like signature:
                    success -> list[ExchangeBalance]
                    failure -> Exception
        """
        # For auth, use path without query params
        auth_path = "/api/v2.2/user/wallet"
        query_string = "?wallet=CROSS@"
        url = f"{self.base_url}{auth_path}{query_string}"
        
        try:
            headers = self._get_auth_headers(auth_path)
        except Exception as e:
            completion(("failure", e))
            return

        print(f"DEBUG: LMEXExchange fetchBalance request URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: LMEXExchange fetchBalance response statusCode: {response.status_code}")

            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}")

            data = response.json()
            print(f"DEBUG: LMEXExchange fetchBalance raw response: {json.dumps(data)}")

            balances = []
            
            # LMEX returns an array with wallet info
            if isinstance(data, list) and len(data) > 0:
                wallet_data = data[0]
                # Extract balance information
                available = float(wallet_data.get("availableBalance", 0))
                total_value = float(wallet_data.get("totalValue", 0))
                margin_balance = float(wallet_data.get("marginBalance", 0))
                open_margin = float(wallet_data.get("openMargin", 0))
                
                # Calculate locked amount (open positions margin)
                locked = open_margin
                
                if total_value > 0:
                    balances.append(
                        ExchangeBalance(
                            asset="USDT",
                            balance=total_value,
                            available=available,
                            locked=locked
                        )
                    )
            elif isinstance(data, dict):
                # Fallback for dict format (if API changes)
                available = float(data.get("availableBalance", 0))
                wallet_balance = float(data.get("walletBalance", 0))
                margin_balance = float(data.get("marginBalance", 0))
                position_margin = float(data.get("positionMargin", 0))
                order_margin = float(data.get("orderMargin", 0))
                
                # Calculate locked amount
                locked = position_margin + order_margin
                
                if wallet_balance > 0:
                    balances.append(
                        ExchangeBalance(
                            asset="USDT",
                            balance=wallet_balance,
                            available=available,
                            locked=locked
                        )
                    )

            completion(("success", balances))

        except Exception as e:
            print(f"DEBUG: LMEXExchange fetchBalance error: {str(e)}")
            completion(("failure", e))

    def fetchOrders(self, completion):
        """
        Fetch open orders via LMEX REST API.
        
        completion: A callback with a Result-like signature:
                    success -> list[ExchangeOrder]
                    failure -> Exception
        """
        path = "/api/v2.2/user/open_orders"
        url = f"{self.base_url}{path}"
        
        try:
            headers = self._get_auth_headers(path)
        except Exception as e:
            completion(("failure", e))
            return

        print(f"DEBUG: LMEXExchange fetchOrders request URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: LMEXExchange fetchOrders response statusCode: {response.status_code}")

            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}")

            data = response.json()
            print(f"DEBUG: LMEXExchange fetchOrders raw response: {json.dumps(data)}")

            orders = []
            
            # Handle both array and object response formats
            if isinstance(data, list):
                orders_data = data
            elif isinstance(data, dict) and "orders" in data:
                orders_data = data["orders"]
            else:
                orders_data = []
            
            for item in orders_data:
                order_id = item.get("orderID")
                symbol = item.get("symbol")
                side = item.get("side", "").upper()
                order_type_raw = item.get("orderType", "")
                # Handle numeric order types
                if isinstance(order_type_raw, int):
                    # Map numeric order types to string
                    order_type_map = {76: "LIMIT", 77: "MARKET", 80: "PEG"}
                    order_type = order_type_map.get(order_type_raw, "LIMIT")
                else:
                    order_type = str(order_type_raw).upper()
                order_qty = float(item.get("size", item.get("orderQty", 0)))
                price = float(item.get("price", 0)) if item.get("price") else None
                order_status = item.get("orderState", item.get("ordStatus", "")).upper()
                time_in_force = item.get("timeInForce", "GTC").upper()
                timestamp = int(item.get("timestamp", 0))
                cl_order_id = item.get("clOrderID")
                cum_qty = float(item.get("filledSize", item.get("cumQty", 0)))
                
                if order_id and symbol:
                    orders.append(
                        ExchangeOrder(
                            orderId=order_id,
                            symbol=symbol,
                            side=side,
                            orderType=order_type,
                            qty=order_qty,
                            price=price,
                            status=order_status,
                            timeInForce=time_in_force,
                            createTime=timestamp,
                            clientId=cl_order_id,
                            executedQty=cum_qty
                        )
                    )

            completion(("success", orders))

        except Exception as e:
            print(f"DEBUG: LMEXExchange fetchOrders error: {str(e)}")
            completion(("failure", e))


    def fetchHistoryOrders(self, symbol: str = None, startTime: int = None, endTime: int = None, limit: int = 50, completion=None):
        """
        Fetch order history to determine how positions were closed.
        
        Args:
            symbol: Trading pair (optional)
            startTime: Unix timestamp in milliseconds (optional)
            endTime: Unix timestamp in milliseconds (optional) 
            limit: Max results (default 50, max 100)
            completion: Callback function
        """
        # LMEX doesn't have a direct order history endpoint in v2.2
        # We'll use trade history instead
        # For auth, use path without query params
        auth_path = "/api/v2.2/user/trade_history"
        
        # Build query parameters
        params = []
        if symbol:
            params.append(f"symbol={symbol}")
        if startTime:
            params.append(f"startTime={startTime}")
        if endTime:
            params.append(f"endTime={endTime}")
        if limit:
            params.append(f"count={limit}")
        
        query_string = f"?{'&'.join(params)}" if params else ""
        url = f"{self.base_url}{auth_path}{query_string}"
        
        try:
            headers = self._get_auth_headers(auth_path)
        except Exception as e:
            completion(("failure", e))
            return

        print(f"DEBUG: LMEXExchange fetchHistoryOrders URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: LMEXExchange fetchHistoryOrders response statusCode: {response.status_code}")
            
            response_str = response.text
            print(f"DEBUG: LMEXExchange fetchHistoryOrders raw response: {response_str}")

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response_str}")

            json_data = json.loads(response_str)
            completion(("success", json_data))

        except Exception as e:
            print(f"DEBUG: LMEXExchange fetchHistoryOrders error: {str(e)}")
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
        # For auth, use path without query params
        auth_path = "/api/v2.2/user/trade_history"
        
        # Build query parameters
        params = []
        if symbol:
            params.append(f"symbol={symbol}")
        if startTime:
            params.append(f"startTime={startTime}")
        if endTime:
            params.append(f"endTime={endTime}")
        if limit:
            params.append(f"count={limit}")
        
        query_string = f"?{'&'.join(params)}" if params else ""
        url = f"{self.base_url}{auth_path}{query_string}"
        
        try:
            headers = self._get_auth_headers(auth_path)
        except Exception as e:
            completion(("failure", e))
            return

        print(f"DEBUG: LMEXExchange fetchHistoryTrades URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: LMEXExchange fetchHistoryTrades response statusCode: {response.status_code}")
            
            response_str = response.text
            print(f"DEBUG: LMEXExchange fetchHistoryTrades raw response: {response_str}")

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response_str}")

            json_data = json.loads(response_str)
            completion(("success", json_data))

        except Exception as e:
            print(f"DEBUG: LMEXExchange fetchHistoryTrades error: {str(e)}")
            completion(("failure", e))

    def fetchLeverageAndMarginMode(self, symbol: str, marginCoin: str, completion):
        """
        Fetch the current leverage and margin mode for a symbol.
        
        completion: A callback with a Result-like signature:
                    success -> dict containing leverage and margin mode
                    failure -> Exception
        """
        # For auth, use path without query params
        auth_path = "/api/v2.2/leverage"
        query_string = f"?symbol={symbol}"
        url = f"{self.base_url}{auth_path}{query_string}"
        
        try:
            headers = self._get_auth_headers(auth_path)
        except Exception as e:
            completion(("failure", e))
            return
        
        print(f"DEBUG: LMEXExchange fetchLeverageAndMarginMode request URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: LMEXExchange fetchLeverageAndMarginMode response statusCode: {response.status_code}")
            
            response_str = response.text
            print(f"DEBUG: LMEXExchange fetchLeverageAndMarginMode raw response: {response_str}")
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response_str}")
            
            json_data = json.loads(response_str)
            
            # LMEX returns an array with leverage info
            if isinstance(json_data, list) and len(json_data) > 0:
                leverage_info = json_data[0]
                result = {
                    "leverage": leverage_info.get("leverage", 1),
                    "marginMode": leverage_info.get("marginMode", "CROSS").lower(),
                    "symbol": leverage_info.get("symbol", symbol)
                }
            else:
                # Fallback if response format is unexpected
                result = {
                    "leverage": 1,
                    "marginMode": "cross",
                    "symbol": symbol
                }
            completion(("success", result))
                
        except Exception as e:
            print(f"DEBUG: LMEXExchange fetchLeverageAndMarginMode error: {str(e)}")
            completion(("failure", e))

    def fetchAccountRiskLimit(self, symbol: str, completion):
        """
        Fetch the account's current risk limit setting for a symbol.
        
        completion: A callback with a Result-like signature:
                    success -> dict containing current risk limit info
                    failure -> Exception
        """
        # For auth, use path without query params
        auth_path = "/api/v2.2/risk_limit"
        query_string = f"?symbol={symbol}"
        url = f"{self.base_url}{auth_path}{query_string}"
        
        try:
            headers = self._get_auth_headers(auth_path)
        except Exception as e:
            completion(("failure", e))
            return
        
        print(f"DEBUG: LMEXExchange fetchAccountRiskLimit request URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: LMEXExchange fetchAccountRiskLimit response statusCode: {response.status_code}")
            
            response_str = response.text
            print(f"DEBUG: LMEXExchange fetchAccountRiskLimit raw response: {response_str}")
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response_str}")
            
            json_data = json.loads(response_str)
            completion(("success", json_data))
            
        except Exception as e:
            print(f"DEBUG: LMEXExchange fetchAccountRiskLimit error: {str(e)}")
            completion(("failure", e))

    def setLeverage(self, symbol: str, leverage: int, marginCoin: str = "USDT", completion=None):
        """
        Set leverage for a trading pair
        
        completion: A callback with a Result-like signature:
                    success -> dict containing result
                    failure -> Exception
        """
        path = "/api/v2.2/leverage"
        url = f"{self.base_url}{path}"
        
        # Request body
        request_body = {
            "symbol": symbol,
            "leverage": leverage
        }
        
        body_str = json.dumps(request_body)
        
        try:
            headers = self._get_auth_headers(path, body_str)
        except Exception as e:
            if completion:
                completion(("failure", e))
            return
        
        print(f"DEBUG: LMEXExchange setLeverage request URL: {url}")
        print(f"DEBUG: LMEXExchange setLeverage body: {body_str}")
        
        try:
            response = requests.post(url, headers=headers, data=body_str)
            print(f"DEBUG: LMEXExchange setLeverage response statusCode: {response.status_code}")
            
            response_str = response.text
            print(f"DEBUG: LMEXExchange setLeverage raw response: {response_str}")
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response_str}")
            
            json_data = json.loads(response_str) if response_str else {}
            
            if completion:
                completion(("success", json_data))
                
        except Exception as e:
            print(f"DEBUG: LMEXExchange setLeverage error: {str(e)}")
            if completion:
                completion(("failure", e))

    def fetchAccountFeeInfo(self, completion):
        """
        Fetch the account's fee rates from LMEX.
        
        completion: A callback with a Result-like signature:
                    success -> dict containing fee rates
                    failure -> Exception
        """
        path = "/api/v2.2/user/fees"
        url = f"{self.base_url}{path}"
        
        try:
            headers = self._get_auth_headers(path)
        except Exception as e:
            # Default to standard fees if auth fails
            completion(("success", {
                "vipLevel": 0,
                "makerFee": 0.0002,  # 0.02% maker fee
                "takerFee": 0.0006,  # 0.06% taker fee  
                "source": "default_auth_error"
            }))
            return
        
        print(f"DEBUG: LMEXExchange fetchAccountFeeInfo request URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: LMEXExchange fetchAccountFeeInfo response statusCode: {response.status_code}")
            
            response_str = response.text
            print(f"DEBUG: LMEXExchange fetchAccountFeeInfo raw response: {response_str}")
            
            if response.status_code != 200:
                # Default fees on error
                completion(("success", {
                    "vipLevel": 0,
                    "makerFee": 0.0002,
                    "takerFee": 0.0006,
                    "source": "default_http_error"
                }))
                return
            
            json_data = json.loads(response_str)
            
            # LMEX returns array of fees per symbol
            # Find BTC-PERP or use first one
            maker_fee = 0.0002
            taker_fee = 0.0006
            
            if isinstance(json_data, list) and len(json_data) > 0:
                # Look for BTC-PERP
                btc_fee = None
                for fee_info in json_data:
                    if fee_info.get("symbol") == "BTC-PERP":
                        btc_fee = fee_info
                        break
                
                # Use BTC-PERP fees or first symbol's fees
                fee_data = btc_fee if btc_fee else json_data[0]
                maker_fee = float(fee_data.get("makerFee", 0.0002))
                taker_fee = float(fee_data.get("takerFee", 0.0006))
            
            completion(("success", {
                "vipLevel": 0,
                "makerFee": maker_fee,
                "takerFee": taker_fee,
                "source": "api"
            }))
                
        except Exception as e:
            print(f"DEBUG: LMEXExchange fetchAccountFeeInfo error: {str(e)}")
            completion(("success", {
                "vipLevel": 0,
                "makerFee": 0.0002,
                "takerFee": 0.0006,
                "source": "default_exception"
            }))
    
    def fetchPositionTiers(self, symbol: str, completion):
        """
        Fetch position tier information for a symbol from LMEX.
        
        completion: A callback with a Result-like signature:
                    success -> list[dict] containing tier information
                    failure -> Exception
        """
        # Use risk limit endpoint to get position tiers
        auth_path = "/api/v2.2/risk_limit"
        query_string = f"?symbol={symbol}"
        url = f"{self.base_url}{auth_path}{query_string}"
        
        print(f"DEBUG: LMEXExchange fetchPositionTiers request URL: {url}")
        
        try:
            headers = self._get_auth_headers(auth_path)
        except Exception as e:
            completion(("failure", e))
            return
        
        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: LMEXExchange fetchPositionTiers response statusCode: {response.status_code}")
            
            response_str = response.text
            print(f"DEBUG: LMEXExchange fetchPositionTiers raw response: {response_str}")
            
            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}, response: {response_str}")
            
            data = response.json()
            
            # LMEX returns risk limit tiers
            if isinstance(data, list):
                tiers = []
                for tier in data:
                    tiers.append({
                        "tier": tier.get("level", 1),
                        "leverage": tier.get("maxLeverage", 100),
                        "max_position": tier.get("limit", 1000000),
                        "maintenance_margin_rate": tier.get("maintMargin", 0.005),
                        "initial_margin_rate": tier.get("initialMargin", 0.01)
                    })
                completion(("success", tiers))
            else:
                # LMEX returns a single risk limit value, not tiers
                # Use the risk limit from the response if available
                risk_limit = data.get("riskLimit", 3000000) if isinstance(data, dict) else 3000000
                
                # Return a single tier with the risk limit in BitUnix format
                tiers = [{
                    "level": 1,  # BitUnix uses "level" not "tier"
                    "leverage": 100,  # LMEX typically allows up to 100x
                    "endValue": risk_limit,  # BitUnix uses "endValue" for max position
                    "max_position": risk_limit,  # Keep this for compatibility
                    "maintainMarginRate": 0.005,
                    "initialMarginRate": 0.01
                }]
                
                completion(("success", tiers))
            
        except Exception as e:
            print(f"DEBUG: LMEXExchange fetchPositionTiers error: {str(e)}")
            completion(("failure", e))

    def cancelOrder(self, orderID: str = None, clOrderID: str = None, symbol: str = None, completion=None):
        """
        Cancel an order by orderID or clOrderID
        
        Args:
            orderID: Server-assigned order ID
            clOrderID: Client-assigned order ID
            symbol: Trading symbol (required)
            completion: Callback function
        """
        if not symbol:
            if completion:
                completion(("failure", Exception("symbol is required for cancel order")))
            return
            
        # Build query parameters
        params = [f"symbol={symbol}"]
        if orderID:
            params.append(f"orderID={orderID}")
        elif clOrderID:
            params.append(f"clOrderID={clOrderID}")
        else:
            if completion:
                completion(("failure", Exception("Either orderID or clOrderID must be provided")))
            return
        
        query_string = f"?{'&'.join(params)}"
        # For auth, use path without query params as per LMEX docs
        auth_path = "/api/v2.2/order"
        # Full URL includes query params
        url = f"{self.base_url}{auth_path}{query_string}"
        
        try:
            # For DELETE with query params, no body
            headers = self._get_auth_headers(auth_path)
        except Exception as e:
            if completion:
                completion(("failure", e))
            return
        
        print(f"DEBUG: LMEXExchange cancelOrder URL: {url}")
        
        try:
            # LMEX uses DELETE method for canceling orders
            response = requests.delete(url, headers=headers)
            print(f"DEBUG: LMEXExchange cancelOrder response statusCode: {response.status_code}")
            
            response_str = response.text
            print(f"DEBUG: LMEXExchange cancelOrder raw response: {response_str}")
            
            if response.status_code == 200:
                json_data = json.loads(response_str) if response_str else {}
                if completion:
                    completion(("success", json_data))
            else:
                if completion:
                    completion(("failure", Exception(f"HTTP {response.status_code}: {response_str}")))
                    
        except Exception as e:
            print(f"DEBUG: LMEXExchange cancelOrder error: {str(e)}")
            if completion:
                completion(("failure", e))