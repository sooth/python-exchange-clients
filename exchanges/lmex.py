"""LMEX Exchange Implementation"""

from .base import (
    ExchangeProtocol,
    ExchangeOrderRequest,
    ExchangeOrderResponse,
    ExchangeTicker,
    ExchangePosition,
    ExchangeBalance,
    ExchangeOrder
)
from .utils.precision import SymbolPrecisionManager
from .utils.api_keys import APIKeyStorage
from .utils.logging import ExchangeLogger

import requests
from typing import Optional, Dict
import json
import hashlib
import hmac
import time
import threading
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Module-level logger for LMEX
_logger = ExchangeLogger.get_logger("LMEX")


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
        _logger.debug(
            "Subscribing to ticker for {symbol} (WebSocket not actually implemented).")

    def lastTradePrice(self, symbol: str) -> float:
        """Get the last trade price for a symbol - fetch from market data."""
        # LMEX doesn't have WebSocket caching yet, so fetch from REST API
        # This is called from the main LMEX class which will handle the fetch
        return 0.0  # Return 0 to indicate no cached price

    def subscribeToOrders(self, symbols: list[str]):
        _logger.debug(
            "Subscribing to orders for symbols {symbols} (WebSocket not actually implemented).")


class LMEXExchange(ExchangeProtocol):
    """
    An LMEX-specific implementation of ExchangeProtocol (Python version).
    """

    def __init__(self):
        self.precision_manager = SymbolPrecisionManager.get_instance("LMEX")
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
                            if isinstance(market, dict) and market.get(
                                    'symbol') == symbol:
                                # LMEX uses 'last' field for last price
                                last_price = market.get(
                                    'last', market.get('lastPrice', 0))
                                if last_price:
                                    return float(last_price)

        # Return 0 if no price found
        _logger.warning("Could not fetch real price for {symbol}")
        return 0.0

    def subscribeToOrders(self, symbols: list[str]):
        """
        Subscribe to order updates for a list of symbols.
        """
        self.webSocketManager.subscribeToOrders(symbols)

    # MARK: - Authentication Helper
    def _generate_signature(
            self,
            path: str,
            nonce: str,
            body: str = "") -> str:
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
    def fetchOHLCV(
            self,
            symbol: str,
            timeframe: str,
            limit: int = 300,
            completion=None):
        """
        Fetch OHLCV (candlestick) data from LMEX.

        Args:
            symbol: Trading symbol (e.g., 'BTC-PERP')
            timeframe: Candle timeframe ('1m', '5m', '15m', '30m', '1h', '4h', '1d')
            limit: Number of candles to fetch (max 300)
            completion: Callback function that receives (status, data)
        """
        try:
            # Map timeframes to LMEX format (resolution)
            timeframe_map = {
                '1m': '1',
                '5m': '5',
                '15m': '15',
                '30m': '30',
                '1h': '60',
                '4h': '240',
                '1d': '1440'
            }

            if timeframe not in timeframe_map:
                completion(("failure", Exception(
                    f"Invalid timeframe: {timeframe}")))
                return

            resolution = timeframe_map[timeframe]

            # LMEX OHLCV endpoint from documentation
            path = "/api/v2.2/ohlcv"
            url = f"{self.base_url}{path}"

            # Calculate time range for the requested number of candles
            import time
            end_time = int(time.time() * 1000)  # Current time in milliseconds

            # Calculate start time based on timeframe and limit
            minutes_per_candle = int(resolution)
            start_time = end_time - (minutes_per_candle * 60 * 1000 * limit)

            params = {
                'symbol': symbol,
                'resolution': resolution,
                'start': str(start_time),
                'end': str(end_time)
            }

            _logger.debug(f"LMEXExchange fetchOHLCV request URL: {url}")
            _logger.debug(f"LMEXExchange fetchOHLCV params: {params}")

            response = requests.get(url, params=params)
            _logger.debug(
                f"LMEXExchange fetchOHLCV response statusCode: "
                f"{response.status_code}")

            if response.status_code != 200:
                raise Exception(
                    f"Failed to fetch OHLCV data: {
                        response.status_code} {
                        response.text}")

            data = response.json()
            sample = data[:2] if isinstance(data, list) and len(data) > 0 else data
            _logger.debug(f"LMEXExchange fetchOHLCV response sample: {sample}")

            # Parse the response into standard format
            # LMEX returns: [timestamp, open, high, low, close, volume]
            candles = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, list) and len(item) >= 6:
                        candles.append({
                            # LMEX returns timestamp in seconds
                            'timestamp': int(item[0]),
                            'open': float(item[1]),
                            'high': float(item[2]),
                            'low': float(item[3]),
                            'close': float(item[4]),
                            'volume': float(item[5])
                        })

            # Sort by timestamp ascending
            candles.sort(key=lambda x: x['timestamp'])

            completion(("success", candles))

        except Exception as e:
            _logger.debug(f" LMEXExchange fetchOHLCV error: {str(e)}")
            completion(("failure", e))

    def fetchSymbolInfo(self, symbol: str, completion):
        """
        Fetch detailed information for a specific symbol.

        Args:
            symbol: The trading symbol
            completion: Callback function that receives (status, data)
        """
        try:
            # First get ticker data for the symbol
            def on_tickers_result(result):
                status, data = result
                if status == "failure":
                    completion(("failure", data))
                    return

                # Find the specific symbol in tickers
                symbol_info = None
                for ticker in data:
                    if ticker.symbol == symbol:
                        symbol_info = ticker
                        break

                if not symbol_info:
                    completion(("failure", Exception(
                        f"Symbol {symbol} not found")))
                    return

                # Get precision info from precision manager
                price_precision = self.precision_manager.get_price_precision(
                    symbol)
                quantity_precision = self.precision_manager.get_quantity_precision(
                    symbol)
                min_qty = self.precision_manager.get_min_quantity(symbol)
                contract_size = self.precision_manager.get_contract_size(
                    symbol)

                # Create enhanced symbol info
                enhanced_info = {
                    "symbol": symbol_info.symbol,
                    "bid": symbol_info.bidPrice,
                    "ask": symbol_info.askPrice,
                    "last": symbol_info.lastPrice,
                    "volume": symbol_info.volume,
                    # May not have change attribute
                    "change": getattr(symbol_info, 'change', 0.0),
                    "pricePrecision": price_precision,
                    "quantityPrecision": quantity_precision,
                    "minQuantity": min_qty,
                    "contractSize": contract_size,
                    "status": "active"  # LMEX doesn't provide status, assume active
                }

                completion(("success", enhanced_info))

            # Fetch all tickers to get the specific symbol
            self.fetchTickers(on_tickers_result)

        except Exception as e:
            _logger.debug(f" LMEXExchange fetchSymbolInfo error: {str(e)}")
            completion(("failure", e))

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
        _logger.debug("LMEXExchange fetchTickers request URL: {url}")

        try:
            response = requests.get(url)
            # DEBUG: Print response info
            _logger.debug(
                "LMEXExchange fetchTickers response statusCode: {response.status_code}")

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

                        # Update precision cache with contract size (preserve existing fields like
                        # price_decimal)
                        if hasattr(
                                self, 'precision_manager') and 'contractSize' in market:
                            if symbol not in self.precision_manager.precision_cache:
                                self.precision_manager.precision_cache[symbol] = {
                                }
                            # Update specific fields without overwriting
                            # existing data
                            cache_entry = self.precision_manager.precision_cache[symbol]
                            cache_entry['contract_size'] = float(
                                market['contractSize'])
                            cache_entry['min_qty'] = float(
                                market.get('minOrderSize', 1))
                            cache_entry['max_qty'] = float(
                                market.get('maxOrderSize', 1000000))
                            cache_entry['tick_size'] = float(
                                market.get('minPriceIncrement', 0.01))

                # Save updated cache after fetching tickers
                if hasattr(self, 'precision_manager'):
                    self.precision_manager._save_cache()
                completion(("success", tickers))
            else:
                raise Exception("Unexpected response format")

        except Exception as e:
            _logger.debug("LMEXExchange fetchTickers error: {str(e)}")
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

        _logger.debug("LMEXExchange fetchPositions request URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            _logger.debug(
                "LMEXExchange fetchPositions response statusCode: {response.status_code}")

            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}")

            data = response.json()
            _logger.debug(
                "LMEXExchange fetchPositions raw response: {json.dumps(data)}")

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
                # LMEX uses 'size' field for position size (always positive)
                qty = float(item.get("size", item.get("qty", 0)))
                # For LMEX, size is always positive, side field indicates
                # direction
                side = item.get("side", "BUY").upper()
                if side == "SELL" or side == "SHORT":
                    qty = -abs(qty)  # Make negative for short positions
                elif side == "BUY" or side == "LONG":
                    qty = abs(qty)  # Keep positive for long positions

                avg_price = float(
                    item.get(
                        "entryPrice",
                        item.get(
                            "avgPrice",
                            0)))
                mark_price = float(item.get("markPrice", avg_price))
                unrealized_pnl = float(
                    item.get(
                        "unrealizedProfitLoss",
                        item.get(
                            "unrealizedPnl",
                            0)))

                if symbol and qty != 0:
                    # Calculate PnL percentage based on entry value
                    pnl_percentage = 0.0
                    if avg_price != 0 and qty != 0:
                        pnl_percentage = (
                            unrealized_pnl / (avg_price * abs(qty))) * 100

                    # Normalize side to LONG/SHORT for hedge mode
                    normalized_side = "LONG" if side in [
                        "BUY", "LONG"] else "SHORT"

                    positions.append(
                        ExchangePosition(
                            symbol=symbol,
                            size=qty,
                            # Now properly signed (negative for short)
                            entryPrice=avg_price,
                            markPrice=mark_price,
                            pnl=unrealized_pnl,
                            pnlPercentage=pnl_percentage,
                            side=normalized_side,  # Explicit side for hedge mode
                            raw_response=item  # Include raw response for debugging
                        )
                    )

            _logger.debug(
                "[LMEX] Positions response parsed {len(positions)} positions")

            completion(("success", positions))

        except Exception as e:
            _logger.debug("LMEXExchange fetchPositions error: {str(e)}")
            completion(("failure", e))

    def fetchPositionMode(self, symbol: str, completion):
        """
        Fetch current position mode for a symbol.
        GET /api/v2.2/position_mode?symbol={symbol}

        completion: A callback with a Result-like signature:
                    success -> dict with {"positionMode": "HEDGE" | "ONE_WAY" | "ISOLATED"}
                    failure -> Exception
        """
        path = f"/api/v2.2/position_mode?symbol={symbol}"
        url = f"{self.base_url}{path}"

        try:
            # For auth, use path without query params
            auth_path = "/api/v2.2/position_mode"
            headers = self._get_auth_headers(auth_path)
        except Exception as e:
            completion(("failure", e))
            return

        _logger.debug("LMEXExchange fetchPositionMode URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            _logger.debug(
                "LMEXExchange fetchPositionMode response statusCode: {response.status_code}")

            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}")

            data = response.json()
            _logger.debug(
                "LMEXExchange fetchPositionMode response: {json.dumps(data)}")

            completion(("success", data))

        except Exception as e:
            _logger.debug("LMEXExchange fetchPositionMode error: {str(e)}")
            completion(("failure", e))

    def setPositionMode(self, symbol: str, position_mode: str, completion):
        """
        Set position mode for a symbol.
        POST /api/v2.2/position_mode
        Body: {"symbol": "BTC-PERP", "positionMode": "HEDGE"}

        Args:
            symbol: Trading symbol (e.g., "BTC-PERP")
            position_mode: "ONE_WAY", "HEDGE", or "ISOLATED"
            completion: A callback with a Result-like signature:
                        success -> timestamp of mode setting
                        failure -> Exception
        """
        path = "/api/v2.2/position_mode"
        url = f"{self.base_url}{path}"

        payload = {
            "symbol": symbol,
            "positionMode": position_mode
        }

        body_str = json.dumps(payload)

        try:
            headers = self._get_auth_headers(path, body_str)
        except Exception as e:
            completion(("failure", e))
            return

        _logger.debug(
            "LMEXExchange setPositionMode: {symbol} -> {position_mode}")
        _logger.debug("LMEXExchange setPositionMode URL: {url}")
        _logger.debug("LMEXExchange setPositionMode body: {body_str}")

        try:
            response = requests.post(url, headers=headers, data=body_str)
            _logger.debug(
                "LMEXExchange setPositionMode response statusCode: {response.status_code}")

            response_str = response.text
            _logger.debug(
                "LMEXExchange setPositionMode response: {response_str}")

            if response.status_code != 200:
                try:
                    error_data = json.loads(response_str)
                    error_msg = error_data.get(
                        'message', f'HTTP {response.status_code}')
                    raise Exception(
                        f"Failed to set position mode: {error_msg}")
                except json.JSONDecodeError:
                    raise Exception(
                        f"HTTP {
                            response.status_code}: {response_str}")

            data = json.loads(response_str) if response_str else {}
            completion(("success", data))

        except Exception as e:
            _logger.debug("LMEXExchange setPositionMode error: {str(e)}")
            completion(("failure", e))

    def initializeHedgeMode(self, symbols: list = None):
        """
        Initialize HEDGE mode for trading symbols.
        This should be called on startup to ensure all symbols are set to hedge mode.

        Args:
            symbols: List of symbols to initialize (e.g., ["BTC-PERP", "ETH-PERP"])
                     If None, will use common perpetual symbols
        """
        if symbols is None:
            # Default to common perpetual symbols
            symbols = ["BTC-PERP", "ETH-PERP", "SOL-PERP"]

        _logger.debug(
            "[LMEX] Initializing HEDGE mode for {len(symbols)} symbols")

        success_count = 0
        failure_count = 0

        for symbol in symbols:
            try:
                # Use a simple synchronous approach for startup initialization
                result_container = {}

                def callback(result):
                    result_container['result'] = result

                self.setPositionMode(symbol, "HEDGE", callback)

                # Wait briefly for callback (simple blocking for startup)
                time.sleep(0.5)

                if 'result' in result_container:
                    status, data = result_container['result']
                    if status == "success":
                        _logger.debug("[LMEX] ✓ {symbol} set to HEDGE mode")
                        success_count += 1
                    else:
                        _logger.debug(
                            "[LMEX] ✗ {symbol} failed to set HEDGE mode: {data}")
                        failure_count += 1
                else:
                    _logger.debug("[LMEX] ✗ {symbol} no response received")
                    failure_count += 1

            except Exception:
                _logger.debug(f"[LMEX] ✗ {symbol} error")
                failure_count += 1

        _logger.debug(
            f"[LMEX] HEDGE mode init: {success_count} success, {failure_count} failed")
        return success_count > 0

    def placeOrder(self, request: ExchangeOrderRequest, completion):
        """
        Place an order via LMEX REST API with automatic position mode switching.
        If we get error code 133 (position mode invalid), automatically switch to the
        requested position mode and retry.

        completion: A callback with a Result-like signature:
                    success -> ExchangeOrderResponse
                    failure -> Exception
        """
        # Wrapper completion handler to catch error 133 and retry
        def completion_with_retry(result):
            status, data = result
            if status == "failure" and isinstance(data, Exception):
                error_msg = str(data)
                # Check if this is error code 133 (position mode invalid)
                if "code: 133" in error_msg or "Position mode invalid" in error_msg:
                    _logger.debug(
                        f"Position mode invalid for {request.symbol}, "
                        f"switching to {request.positionMode} mode...")

                    # Define callback for position mode setting
                    def mode_completion(mode_result):
                        mode_status, mode_data = mode_result
                        if mode_status == "success":
                            _logger.debug(
                                f"Successfully set position mode to "
                                f"{request.positionMode} for {request.symbol}")
                            # Retry the order after successfully setting
                            # position mode
                            _logger.debug(
                                "[LMEX] Retrying order placement after position mode switch...")
                            self._placeOrderInternal(request, completion)
                        else:
                            # If mode setting failed, pass through the original
                            # error
                            _logger.debug(
                                "[LMEX] Failed to set position mode: {mode_data}")
                            _logger.debug(
                                "[LMEX] Cannot retry order - position mode switch failed")
                            completion(result)

                    # Call setPositionMode asynchronously
                    self.setPositionMode(
                        request.symbol, request.positionMode, mode_completion)
                    return

            # For all other cases, pass through the result
            completion(result)

        # Place the order with the retry-enabled completion handler
        self._placeOrderInternal(request, completion_with_retry)

    def _placeOrderInternal(self, request: ExchangeOrderRequest, completion):
        """
        Internal order placement method (actual implementation).
        """
        path = "/api/v2.2/order"
        url = f"{self.base_url}{path}"

        # Get symbol precision info
        symbol = request.symbol
        price_precision = self.precision_manager.get_price_precision(symbol)
        min_qty = self.precision_manager.get_min_quantity(symbol)

        # Get contract size for this symbol
        contract_size = self.precision_manager.get_contract_size(symbol)

        # Convert asset amount to LMEX contracts
        contracts = int(request.qty / contract_size)

        # Ensure quantity meets minimum requirements
        if contracts < min_qty:
            _logger.debug(
                f"Adjusting quantity from {request.qty} units ({contracts} contracts) "
                f"to minimum {min_qty} contracts for {symbol}")
            actual_qty = min_qty
        else:
            actual_qty = contracts
            _logger.debug(
                f"Converting {request.qty} units to {contracts} contracts "
                f"for {symbol} (contract_size: {contract_size})")

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
            "positionMode": request.positionMode  # HEDGE mode support
        }

        # Add reduceOnly parameter if specified (for hedge mode position
        # reductions)
        if request.reduceOnly is not None:
            payload["reduceOnly"] = request.reduceOnly

        # Add price for limit orders
        if request.price is not None and order_type == "LIMIT":
            payload["price"] = float(round(request.price, price_precision))

        # Add client order ID if provided
        if request.orderLinkId is not None:
            payload["clOrderID"] = request.orderLinkId

        # Add Stop Loss and Take Profit parameters if provided
        if request.stopLoss is not None:
            # Ensure stopLossPrice is sent as a float/double
            payload["stopLossPrice"] = float(
                round(request.stopLoss, price_precision))
            payload["stopLossTrigger"] = "markPrice"  # Default trigger type
            _logger.debug("[LMEX] Adding Stop Loss at ${request.stopLoss}")

        if request.takeProfit is not None:
            # Ensure takeProfitPrice is sent as a float/double
            payload["takeProfitPrice"] = float(
                round(request.takeProfit, price_precision))
            payload["takeProfitTrigger"] = "markPrice"  # Default trigger type
            _logger.debug("[LMEX] Adding Take Profit at ${request.takeProfit}")

        body_str = json.dumps(payload)

        # Log the complete payload for debugging
        _logger.debug(
            "[LMEX] Complete order payload: {json.dumps(payload, indent=2)}")

        try:
            headers = self._get_auth_headers(path, body_str)
        except Exception as e:
            completion(("failure", e))
            return

        _logger.debug("LMEXExchange placeOrder URL: {url}")
        _logger.debug("LMEXExchange placeOrder headers: {headers}")
        _logger.debug("LMEXExchange placeOrder body: {body_str}")

        try:
            response = requests.post(url, headers=headers, data=body_str)
            _logger.debug(
                "LMEXExchange placeOrder response statusCode: {response.status_code}")

            response_str = response.text
            _logger.debug(
                "LMEXExchange placeOrder raw response: {response_str}")

            # Check response status
            if response.status_code != 200:
                # Parse error response
                try:
                    error_data = json.loads(response_str)
                    error_msg = error_data.get(
                        'message', f'HTTP {response.status_code}')
                    error_code = error_data.get('errorCode', 'UNKNOWN')
                    raise Exception(
                        f"Order failed: {error_msg} (code: {error_code})")
                except json.JSONDecodeError:
                    raise Exception(
                        f"HTTP {
                            response.status_code}: {response_str}")

            # Parse success response
            json_data = json.loads(response_str) if response_str else {}

            # Log the raw API response for debugging
            _logger.debug(
                "[LMEX] Order API Response: {json.dumps(json_data, indent=2)}")

            # LMEX returns a list with one order object
            if isinstance(json_data, list) and len(json_data) > 0:
                # Extract the first order from the list
                order_data = json_data[0]
            else:
                order_data = json_data

            # Check order status - status 8 means CANCELLED/REJECTED
            order_status = order_data.get('status', 0)
            if order_status == 8:
                # Order was rejected - extract error message
                error_msg = order_data.get(
                    'message', 'Order rejected by exchange')
                if isinstance(error_msg, str):
                    try:
                        # Parse JSON error message
                        error_json = json.loads(error_msg)
                        error_msg = error_json.get('default_msg', error_msg)
                    except Exception:
                        pass
                raise Exception(f"Order rejected: {error_msg}")

            orderResponse = ExchangeOrderResponse(order_data)
            completion(("success", orderResponse))
        except Exception as e:
            _logger.debug("LMEXExchange placeOrder error: {str(e)}")
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
                completion(("failure", Exception(
                    f"HTTP error: {response.status_code}")))
                return

            json_data = json.loads(response.text)

            # Extract total equity from response
            total_equity = 0.0

            # LMEX returns an array with wallet info
            if isinstance(json_data, list) and len(json_data) > 0:
                wallet_data = json_data[0]
                # Use totalValue which represents the total account value
                total_equity = float(wallet_data.get("totalValue", 0))

                _logger.debug("LMEX Account Equity: {total_equity}")
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

        _logger.debug("LMEXExchange fetchBalance request URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            _logger.debug(
                "LMEXExchange fetchBalance response statusCode: {response.status_code}")

            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}")

            data = response.json()
            _logger.debug(
                "LMEXExchange fetchBalance raw response: {json.dumps(data)}")

            balances = []

            # LMEX returns an array with wallet info
            if isinstance(data, list) and len(data) > 0:
                wallet_data = data[0]
                # Extract balance information
                available = float(wallet_data.get("availableBalance", 0))
                total_value = float(wallet_data.get("totalValue", 0))
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
            _logger.debug("LMEXExchange fetchBalance error: {str(e)}")
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

        _logger.debug("LMEXExchange fetchOrders request URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            _logger.debug(
                "LMEXExchange fetchOrders response statusCode: {response.status_code}")

            if response.status_code != 200:
                raise Exception(f"Non-200 status code: {response.status_code}")

            data = response.json()
            _logger.debug(
                "LMEXExchange fetchOrders raw response: {json.dumps(data)}")

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
                price = float(
                    item.get(
                        "price",
                        0)) if item.get("price") else None
                order_status = item.get(
                    "orderState", item.get(
                        "ordStatus", "")).upper()
                time_in_force = item.get("timeInForce", "GTC").upper()
                timestamp = int(item.get("timestamp", 0))
                cl_order_id = item.get("clOrderID")
                cum_qty = float(item.get("filledSize", item.get("cumQty", 0)))

                # Extract TP/SL specific fields
                stop_price = float(item.get("stopPx", item.get("stopPrice", 0))) if item.get(
                    "stopPx") or item.get("stopPrice") else None
                trigger_price = float(item.get("triggerPrice", 0)) if item.get(
                    "triggerPrice") else None
                reduce_only = item.get("reduceOnly", False)
                post_only = item.get("postOnly", False)

                # Parse trigger order fields
                trigger_order = item.get("triggerOrder", False)
                trigger_order_type = item.get("triggerOrderType")
                tx_type = item.get("txType")

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
                            executedQty=cum_qty,
                            stopPrice=stop_price,
                            triggerPrice=trigger_price,
                            reduceOnly=reduce_only,
                            postOnly=post_only,
                            triggerOrder=trigger_order,
                            triggerOrderType=trigger_order_type,
                            txType=tx_type,
                            rawOrderType=str(order_type_raw),
                            rawResponse=item
                        )
                    )

                # Check for nested Take Profit order
                if "takeProfitOrder" in item and item["takeProfitOrder"]:
                    tp_order = item["takeProfitOrder"]
                    tp_order_id = tp_order.get("orderId")
                    tp_trigger_price = float(
                        tp_order.get(
                            "triggerPrice",
                            0)) if tp_order.get("triggerPrice") else None
                    tp_side = tp_order.get("side", side)

                    if tp_order_id and symbol and tp_trigger_price:
                        orders.append(
                            ExchangeOrder(
                                orderId=tp_order_id,
                                symbol=symbol,
                                side=tp_side,
                                orderType="MARKET",  # TP = market when triggered
                                qty=order_qty,  # Same size as parent order
                                price=None,  # Market order, no limit price
                                status=order_status,
                                timeInForce=time_in_force,
                                createTime=timestamp,
                                clientId=None,
                                executedQty=0,
                                stopPrice=tp_trigger_price,
                                triggerOrder=True,
                                triggerOrderType=1002,  # 1002 = Take Profit
                                txType="TAKEPROFIT"
                            )
                        )

                # Check for nested Stop Loss order (only if not already the
                # main order)
                if "stopLossOrder" in item and item["stopLossOrder"]:
                    sl_order = item["stopLossOrder"]
                    sl_order_id = sl_order.get("orderId")

                    # Only add as separate order if it's different from the
                    # main order ID
                    if sl_order_id and sl_order_id != order_id and symbol:
                        sl_trigger_price = float(
                            sl_order.get(
                                "triggerPrice",
                                0)) if sl_order.get("triggerPrice") else None
                        sl_side = sl_order.get("side", side)

                        if sl_trigger_price:
                            orders.append(
                                ExchangeOrder(
                                    orderId=sl_order_id,
                                    symbol=symbol,
                                    side=sl_side,
                                    orderType="MARKET",  # SL = market when triggered
                                    qty=order_qty,  # Same size as parent order
                                    price=None,  # Market order, no limit price
                                    status=order_status,
                                    timeInForce=time_in_force,
                                    createTime=timestamp,
                                    clientId=None,
                                    executedQty=0,
                                    stopPrice=sl_trigger_price,
                                    triggerOrder=True,
                                    triggerOrderType=1001,  # 1001 = Stop Loss
                                    txType="STOP"
                                )
                            )

            completion(("success", orders))

        except Exception as e:
            _logger.debug("LMEXExchange fetchOrders error: {str(e)}")
            completion(("failure", e))

    def fetchHistoryOrders(
            self,
            symbol: str = None,
            startTime: int = None,
            endTime: int = None,
            limit: int = 50,
            completion=None):
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

        _logger.debug("LMEXExchange fetchHistoryOrders URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            _logger.debug(
                "LMEXExchange fetchHistoryOrders response statusCode: {response.status_code}")

            response_str = response.text
            _logger.debug(
                "LMEXExchange fetchHistoryOrders raw response: {response_str}")

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response_str}")

            json_data = json.loads(response_str)
            completion(("success", json_data))

        except Exception as e:
            _logger.debug("LMEXExchange fetchHistoryOrders error: {str(e)}")
            completion(("failure", e))

    def fetchHistoryTrades(
            self,
            symbol: str = None,
            orderId: str = None,
            startTime: int = None,
            endTime: int = None,
            limit: int = 50,
            completion=None):
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

        _logger.debug("LMEXExchange fetchHistoryTrades URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            _logger.debug(
                "LMEXExchange fetchHistoryTrades response statusCode: {response.status_code}")

            response_str = response.text
            _logger.debug(
                "LMEXExchange fetchHistoryTrades raw response: {response_str}")

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response_str}")

            json_data = json.loads(response_str)
            completion(("success", json_data))

        except Exception as e:
            _logger.debug("LMEXExchange fetchHistoryTrades error: {str(e)}")
            completion(("failure", e))

    def fetchLeverageAndMarginMode(
            self,
            symbol: str,
            marginCoin: str,
            completion):
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

        _logger.debug(
            "LMEXExchange fetchLeverageAndMarginMode request URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            _logger.debug(
                f"LMEXExchange fetchLeverageAndMarginMode status: {
                    response.status_code}")

            response_str = response.text
            _logger.debug(
                "LMEXExchange fetchLeverageAndMarginMode raw response: {response_str}")

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response_str}")

            json_data = json.loads(response_str)

            # LMEX returns an array with leverage info
            if isinstance(json_data, list) and len(json_data) > 0:
                leverage_info = json_data[0]
                result = {
                    "leverage": leverage_info.get(
                        "leverage", 1), "marginMode": leverage_info.get(
                        "marginMode", "CROSS").lower(), "symbol": leverage_info.get(
                        "symbol", symbol)}
            else:
                # Fallback if response format is unexpected
                result = {
                    "leverage": 1,
                    "marginMode": "cross",
                    "symbol": symbol
                }
            completion(("success", result))

        except Exception as e:
            _logger.debug(
                "LMEXExchange fetchLeverageAndMarginMode error: {str(e)}")
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

        _logger.debug("LMEXExchange fetchAccountRiskLimit request URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            _logger.debug(
                "LMEXExchange fetchAccountRiskLimit response statusCode: {response.status_code}")

            response_str = response.text
            _logger.debug(
                "LMEXExchange fetchAccountRiskLimit raw response: {response_str}")

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response_str}")

            json_data = json.loads(response_str)
            completion(("success", json_data))

        except Exception as e:
            _logger.debug("LMEXExchange fetchAccountRiskLimit error: {str(e)}")
            completion(("failure", e))

    def setLeverage(
            self,
            symbol: str,
            leverage: int,
            marginCoin: str = "USDT",
            completion=None):
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

        _logger.debug("LMEXExchange setLeverage request URL: {url}")
        _logger.debug("LMEXExchange setLeverage body: {body_str}")

        try:
            response = requests.post(url, headers=headers, data=body_str)
            _logger.debug(
                "LMEXExchange setLeverage response statusCode: {response.status_code}")

            response_str = response.text
            _logger.debug(
                "LMEXExchange setLeverage raw response: {response_str}")

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response_str}")

            json_data = json.loads(response_str) if response_str else {}

            if completion:
                completion(("success", json_data))

        except Exception as e:
            _logger.debug("LMEXExchange setLeverage error: {str(e)}")
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
        except Exception:
            # Default to standard fees if auth fails
            completion(("success", {
                "vipLevel": 0,
                "makerFee": 0.0002,  # 0.02% maker fee
                "takerFee": 0.0006,  # 0.06% taker fee
                "source": "default_auth_error"
            }))
            return

        _logger.debug("LMEXExchange fetchAccountFeeInfo request URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            _logger.debug(
                "LMEXExchange fetchAccountFeeInfo response statusCode: {response.status_code}")

            response_str = response.text
            _logger.debug(
                "LMEXExchange fetchAccountFeeInfo raw response: {response_str}")

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

        except Exception:
            _logger.debug("LMEXExchange fetchAccountFeeInfo error")
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

        _logger.debug("LMEXExchange fetchPositionTiers request URL: {url}")

        try:
            headers = self._get_auth_headers(auth_path)
        except Exception as e:
            completion(("failure", e))
            return

        try:
            response = requests.get(url, headers=headers)
            _logger.debug(
                "LMEXExchange fetchPositionTiers response statusCode: {response.status_code}")

            response_str = response.text
            _logger.debug(
                "LMEXExchange fetchPositionTiers raw response: {response_str}")

            if response.status_code != 200:
                raise Exception(
                    f"Non-200 status code: {response.status_code}, response: {response_str}")

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
                risk_limit = data.get(
                    "riskLimit", 3000000) if isinstance(
                    data, dict) else 3000000

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
            _logger.debug("LMEXExchange fetchPositionTiers error: {str(e)}")
            completion(("failure", e))

    def cancelOrder(
            self,
            orderID: str = None,
            clOrderID: str = None,
            symbol: str = None,
            completion=None):
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
                completion(("failure", Exception(
                    "symbol is required for cancel order")))
            return

        # Build query parameters
        params = [f"symbol={symbol}"]
        if orderID:
            params.append(f"orderID={orderID}")
        elif clOrderID:
            params.append(f"clOrderID={clOrderID}")
        else:
            if completion:
                completion(("failure", Exception(
                    "Either orderID or clOrderID must be provided")))
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

        _logger.debug("LMEXExchange cancelOrder URL: {url}")

        try:
            # LMEX uses DELETE method for canceling orders
            response = requests.delete(url, headers=headers)
            _logger.debug(
                "LMEXExchange cancelOrder response statusCode: {response.status_code}")

            response_str = response.text
            _logger.debug(
                "LMEXExchange cancelOrder raw response: {response_str}")

            if response.status_code == 200:
                json_data = json.loads(response_str) if response_str else {}
                if completion:
                    completion(("success", json_data))
            else:
                if completion:
                    completion(("failure", Exception(
                        f"HTTP {response.status_code}: {response_str}")))

        except Exception as e:
            _logger.debug("LMEXExchange cancelOrder error: {str(e)}")
            if completion:
                completion(("failure", e))

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
            price_precision = self.precision_manager.get_price_precision(
                symbol)

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

            _logger.debug("createGridBot response => {response.text}")

            # Parse response
            try:
                data = response.json()
                if data.get("success"):
                    completion(None, data)
                else:
                    error_msg = data.get("msg", "Unknown error")
                    error_code = data.get("code", -1)
                    error = Exception(
                        f"Failed to create grid bot: {error_msg} (code: {error_code})")
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
                signature = self._generate_signature(path, nonce, "")

                headers["request-api"] = api_key
                headers["request-nonce"] = nonce
                headers["request-sign"] = signature
            else:
                # No credentials available
                completion(None, [])
                return

            response = requests.get(url, headers=headers)

            _logger.debug("fetchGridBots raw => {response.text}")

            try:
                data = response.json()

                if not data.get("success", False):
                    error_msg = f"LMEX returned success={
                        data.get('success')}, code={
                        data.get('code')}, msg={
                        data.get(
                            'msg',
                            'no message')}"
                    error = Exception(
                        f"Failed to retrieve LMEX bots: {error_msg}")
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
                        "upperPrice": (float(detail.get("upperPrice", "0"))
                                       if detail.get("upperPrice") else None),
                        "lowerPrice": (float(detail.get("lowerPrice", "0"))
                                       if detail.get("lowerPrice") else None)
                    }
                    bots.append(bot)

                completion(None, bots)

            except (json.JSONDecodeError, KeyError) as e:
                error = Exception(
                    f"Failed to parse grid bots response: {
                        str(e)}")
                completion(error, None)

        except Exception as e:
            completion(e, None)
