"""
LMEX Adapter - Implements ExchangeInterface for LMEX exchange

This adapter wraps the existing LMEXExchange class to provide
a unified interface that conforms to ExchangeInterface.
"""

import threading
from typing import List, Any, Callable, Tuple
from ..base import ExchangeInterface, PositionSide, ExchangeOrderRequest
from ..utils.logging import ExchangeLogger
from ..lmex import LMEXExchange


# Module-level logger for LMEX adapter
_logger = ExchangeLogger.get_logger("LMEX")


class LMEXAdapter(ExchangeInterface):
    """
    Adapter class that wraps LMEXExchange to implement ExchangeInterface.

    This adapter:
    - Delegates all calls to the underlying LMEXExchange instance
    - Handles any necessary data transformations
    - Provides exchange-specific configurations
    """

    def __init__(self):
        """Initialize the adapter with an LMEXExchange instance."""
        super().__init__()
        self._exchange = LMEXExchange()
        self._init_logger()

    def get_name(self) -> str:
        """Get the name of the exchange."""
        return "LMEX"

    def get_symbol_format(self, base_symbol: str) -> str:
        """
        Convert a base symbol to LMEX format.
        E.g., 'BTC' -> 'BTC-PERP'
        """
        # LMEX uses hyphenated format like BTC-PERP
        if '-PERP' in base_symbol:
            return base_symbol
        # Remove USDT if present (from BitUnix format)
        if base_symbol.endswith('USDT'):
            base_symbol = base_symbol[:-4]
        return f"{base_symbol}-PERP"

    def translate_side_to_exchange(self, side: str) -> str:
        """
        Translate standard side to LMEX format.
        LMEX uses 'BUY' for long and 'SELL' for short.
        """
        if side == PositionSide.LONG:
            return "BUY"
        elif side == PositionSide.SHORT:
            return "SELL"
        else:
            # If already in LMEX format, return as-is
            return side

    def translate_side_from_exchange(self, exchange_side: str) -> str:
        """
        Translate LMEX side to standard format.
        """
        if exchange_side.upper() == "BUY":
            return PositionSide.LONG
        elif exchange_side.upper() == "SELL":
            return PositionSide.SHORT
        else:
            # Default to original if unknown
            return exchange_side

    # Market Data Methods
    def fetchTickers(self, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch all available tickers from LMEX."""
        self._exchange.fetchTickers(completion)

    def subscribeToTicker(self, symbol: str):
        """Subscribe to real-time ticker updates for a symbol."""
        self._exchange.subscribeToTicker(symbol)

    def lastTradePrice(self, symbol: str) -> float:
        """Get the last trade price for a symbol."""
        return self._exchange.lastTradePrice(symbol)

    # Account Methods
    def fetchBalance(self, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch account balances from LMEX."""
        self.logger.info("Fetching account balance")

        # Wrap completion to add logging
        def logged_completion(result):
            status, data = result
            if status == "success":
                ExchangeLogger.log_balance_fetch(self.logger, True, data)
            else:
                ExchangeLogger.log_balance_fetch(self.logger, False, None, str(data))
            completion(result)

        self._exchange.fetchBalance(logged_completion)

    def fetchAccountEquity(self, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch total account equity value from LMEX."""
        self._exchange.fetchAccountEquity(completion)

    def fetchAccountFeeInfo(self, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch account fee information including VIP level from LMEX."""
        self._exchange.fetchAccountFeeInfo(completion)

    # Position Methods
    def fetchPositions(self, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch all open positions from LMEX."""
        self.logger.info("Fetching open positions")

        # Wrap completion to add logging
        def logged_completion(result):
            status, data = result
            if status == "success":
                ExchangeLogger.log_position_fetch(self.logger, True, data)
            else:
                ExchangeLogger.log_position_fetch(self.logger, False, None, str(data))
            completion(result)

        self._exchange.fetchPositions(logged_completion)

    def fetchPositionTiers(self, symbol: str, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch position tier/risk limit information for a symbol from LMEX."""
        self._exchange.fetchPositionTiers(symbol, completion)

    def fetchAccountRiskLimit(self, symbol: str, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch account's current risk limit/tier for a symbol from LMEX."""
        self._exchange.fetchAccountRiskLimit(symbol, completion)

    # Order Methods
    def placeOrder(self, request: ExchangeOrderRequest,
                   completion: Callable[[Tuple[str, Any]], None]):
        """Place a new order on LMEX."""
        # Check if symbol is supported before proceeding
        if not self.is_symbol_supported(request.symbol):
            error_msg = f"Symbol {request.symbol} is not supported by {self.get_name()}"
            self.logger.error(f"[SYMBOL CHECK] ❌ {error_msg}")
            completion(("failure", Exception(error_msg)))
            return

        # Log order request
        self.logger.info(
            f"Placing order - Symbol: {
                request.symbol}, Side: {
                request.side}, Qty: {
                request.qty}, Type: {
                    request.orderType}")
        self.logger.debug(
            f"Order details - Price: {
                request.price}, StopLoss: {
                request.stopLoss}, TakeProfit: {
                request.takeProfit}")

        # Translate side if it's using standard format
        if hasattr(request, 'side') and request.side in [PositionSide.LONG, PositionSide.SHORT]:
            original_side = request.side
            request.side = self.translate_side_to_exchange(request.side)
            self.logger.debug(f"Translated side: {original_side} -> {request.side}")

        # Wrap completion to add logging
        def logged_completion(result):
            status, data = result
            if status == "success":
                ExchangeLogger.log_order_placement(
                    self.logger, request.__dict__, True, data.rawResponse if hasattr(
                        data, 'rawResponse') else data)
            else:
                ExchangeLogger.log_order_placement(self.logger, request.__dict__, False, str(data))
            completion(result)

        self._exchange.placeOrder(request, logged_completion)

    def cancelOrder(self, orderID: str = None, clOrderID: str = None, symbol: str = None,
                    completion: Callable[[Tuple[str, Any]], None] = None):
        """Cancel an existing order on LMEX."""
        self.logger.info(
            f"Cancelling order - OrderID: {orderID}, ClientID: {clOrderID}, Symbol: {symbol}")

        # Wrap completion to add logging
        def logged_completion(result):
            status, data = result
            ExchangeLogger.log_order_cancellation(
                self.logger, orderID or clOrderID, symbol, status == "success", data)
            if completion:
                completion(result)

        self._exchange.cancelOrder(orderID, clOrderID, symbol, logged_completion)

    def fetchOrders(self, completion: Callable[[Tuple[str, Any]], None]):
        """Fetch all open orders from LMEX."""
        self._exchange.fetchOrders(completion)

    def fetchHistoryOrders(self, start_time: int = None, end_time: int = None,
                           symbol: str = None, limit: int = 50,
                           completion: Callable[[Tuple[str, Any]], None] = None):
        """Fetch order history from LMEX."""
        # LMEX's fetchHistoryOrders has parameters: symbol, startTime, endTime, limit, completion
        if completion:
            self._exchange.fetchHistoryOrders(
                symbol=symbol,
                startTime=start_time,
                endTime=end_time,
                limit=limit,
                completion=completion
            )

    def fetchHistoryTrades(self, start_time: int = None, end_time: int = None,
                           symbol: str = None, orderId: str = None, limit: int = 50,
                           completion: Callable[[Tuple[str, Any]], None] = None):
        """Fetch trade history from LMEX."""
        # LMEX's fetchHistoryTrades supports orderId parameter
        if completion:
            self._exchange.fetchHistoryTrades(
                symbol=symbol,
                orderId=orderId,
                startTime=start_time,
                endTime=end_time,
                limit=limit,
                completion=completion
            )

    # Leverage Methods
    def fetchLeverageAndMarginMode(self, symbol: str, marginCoin: str = "USDT",
                                   completion: Callable[[Tuple[str, Any]], None] = None):
        """Fetch current leverage and margin mode settings from LMEX."""
        # LMEX doesn't use marginCoin parameter
        if completion:
            self._exchange.fetchLeverageAndMarginMode(symbol, marginCoin, completion)

    def setLeverage(self, symbol: str, leverage: int, marginCoin: str = "USDT",
                    completion: Callable[[Tuple[str, Any]], None] = None):
        """Set leverage for a symbol on LMEX."""
        # LMEX doesn't use marginCoin parameter
        if completion:
            self._exchange.setLeverage(symbol, leverage, marginCoin, completion)

    # Utility Methods
    def get_min_trade_volume(self, symbol: str) -> float:
        """Get minimum trade volume for a symbol from LMEX."""
        # LMEX uses get_min_quantity instead of get_min_trade_volume
        return self._exchange.precision_manager.get_min_quantity(symbol)

    def is_symbol_supported(self, symbol: str) -> bool:
        """Check if a symbol is supported by LMEX."""
        # Check if symbol exists in precision cache
        return self._exchange.precision_manager.has_symbol(symbol)

    def get_price_precision(self, symbol: str) -> int:
        """Get price decimal precision for a symbol from LMEX."""
        return self._exchange.precision_manager.get_price_precision(symbol)

    def get_quantity_precision(self, symbol: str) -> int:
        """Get quantity decimal precision for a symbol from LMEX."""
        return self._exchange.precision_manager.get_quantity_precision(symbol)

    # Price Management Methods
    def getCurrentPrice(self, symbol: str) -> float:
        """Get current market price for symbol in USD/USDT."""
        price = self._exchange.lastTradePrice(symbol)
        if price <= 0:
            # Fallback: try to get from tickers
            tickers_result = None
            tickers_event = threading.Event()

            def callback(result):
                nonlocal tickers_result
                tickers_result = result
                tickers_event.set()

            self._exchange.fetchTickers(callback)

            if tickers_event.wait(timeout=5):
                status, data = tickers_result
                if status == "success" and isinstance(data, list):
                    for ticker in data:
                        if ticker.symbol == symbol:
                            # Try getting cached price again
                            price = self._exchange.lastTradePrice(symbol)
                            break

        # If still no price, return a reasonable default for BTC
        if price <= 0 and 'BTC' in symbol:
            price = 100000.0

        return price

    def validateAndAdjustPrice(self, symbol: str, price: float, side: str) -> float:
        """Validate and adjust price to meet LMEX requirements."""
        # LMEX typically has more relaxed price requirements
        # Just ensure price is positive and properly rounded
        if price <= 0:
            current_price = self.getCurrentPrice(symbol)
            _logger.debug(f"Invalid price {price}, using 10% below current ${current_price:.2f}")
            price = current_price * 0.9

        # Round to the proper precision for this symbol
        precision = self.get_price_precision(symbol)
        return round(price, precision)

    # Quantity Management Methods
    def normalizeQuantity(self, symbol: str, qty: float, price: float) -> float:
        """Convert asset amount to LMEX contracts."""
        # LMEX uses contracts, not asset amount
        # Get dynamic contract size for this symbol
        contract_size = self._exchange.precision_manager.get_contract_size(symbol)

        # Convert asset amount to contracts
        contracts = qty / contract_size

        # Ensure minimum of 1 contract
        if contracts < 1:
            contracts = 1

        # Round to integer (LMEX uses integer contracts)
        return int(contracts)

    def getMinimumOrderSize(self, symbol: str, price: float) -> float:
        """Get minimum order size in asset amount."""
        # LMEX minimum is usually 1 contract
        # Get dynamic contract size for this symbol
        contract_size = self._exchange.precision_manager.get_contract_size(symbol)
        min_contracts = self._exchange.precision_manager.get_min_quantity(symbol)

        # Convert contracts back to asset amount
        return min_contracts * contract_size

    # WebSocket Methods
    def subscribeToOrders(self, symbols: List[str]):
        """Subscribe to real-time order updates for multiple symbols on LMEX."""
        self._exchange.subscribeToOrders(symbols)
