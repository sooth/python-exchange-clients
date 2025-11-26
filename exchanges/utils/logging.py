"""
Exchange-specific logging configuration for the abstraction layer
"""

import logging
import os
from datetime import datetime
from typing import Optional


class ExchangeLogger:
    """Manages exchange-specific logging with both console and file output"""

    _loggers = {}  # Cache for exchange loggers

    @classmethod
    def get_logger(cls, exchange_name: str, log_dir: str = "exchange_logs") -> logging.Logger:
        """
        Get or create a logger for a specific exchange

        Args:
            exchange_name: Name of the exchange (e.g., 'bitunix', 'lmex')
            log_dir: Directory to store log files

        Returns:
            Configured logger instance
        """
        logger_name = f"exchange.{exchange_name.lower()}"

        # Return cached logger if exists
        if logger_name in cls._loggers:
            return cls._loggers[logger_name]

        # Create new logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

        # Remove any existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # File handler - separate file per exchange
        timestamp = datetime.now().strftime("%Y%m%d")
        log_filename = os.path.join(log_dir, f"{exchange_name.lower()}_{timestamp}.log")
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Create formatters with custom millisecond formatter
        class MillisecondFormatter(logging.Formatter):
            def formatTime(self, record, datefmt=None):
                # Get current time with milliseconds
                dt = datetime.fromtimestamp(record.created)
                # Format as HH:MM:SSS (hour:minute:millisecond)
                return dt.strftime('%H:%M:%S.%f')[
                    :-3]  # Remove microseconds, keep only milliseconds

        # File format includes timestamp
        file_formatter = MillisecondFormatter(
            '%(asctime)s - [%(exchange)s] - %(levelname)s - %(funcName)s - %(message)s'
        )

        # Console format with timestamp
        console_formatter = MillisecondFormatter(
            '%(asctime)s [%(exchange)s] %(levelname)s: %(message)s'
        )

        # Apply formatters
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # Add exchange name to all log records
        class ExchangeFilter(logging.Filter):
            def __init__(self, exchange_name):
                self.exchange_name = exchange_name.upper()

            def filter(self, record):
                record.exchange = self.exchange_name
                return True

        logger.addFilter(ExchangeFilter(exchange_name))

        # Cache the logger
        cls._loggers[logger_name] = logger

        # Log initialization
        logger.info(f"Logger initialized for {exchange_name.upper()}")
        logger.debug(f"Log file: {log_filename}")

        return logger

    @classmethod
    def log_api_request(cls, logger: logging.Logger, method: str, url: str,
                        headers: Optional[dict] = None, body: Optional[str] = None):
        """Log API request details"""
        logger.debug(f"API Request: {method} {url}")
        if headers:
            # Sanitize sensitive headers
            safe_headers = headers.copy()
            if 'api-key' in safe_headers:
                safe_headers['api-key'] = safe_headers['api-key'][:8] + '...'
            if 'sign' in safe_headers:
                safe_headers['sign'] = safe_headers['sign'][:16] + '...'
            if 'request-api' in safe_headers:
                safe_headers['request-api'] = safe_headers['request-api'][:16] + '...'
            if 'request-sign' in safe_headers:
                safe_headers['request-sign'] = safe_headers['request-sign'][:16] + '...'
            logger.debug(f"Headers: {safe_headers}")
        if body:
            logger.debug(f"Body: {body}")

    @classmethod
    def log_api_response(cls, logger: logging.Logger, status_code: int, response: str):
        """Log API response details"""
        logger.debug(f"API Response: Status {status_code}")
        if len(response) > 1000:
            logger.debug(f"Response (truncated): {response[:1000]}...")
        else:
            logger.debug(f"Response: {response}")

    @classmethod
    def log_order_placement(cls, logger: logging.Logger, order_request: dict,
                            success: bool, response: Optional[dict] = None):
        """Log order placement with consistent format"""
        if success:
            order_id = None
            if response and isinstance(response, dict):
                # Try different response formats
                if 'data' in response:
                    order_id = response['data'].get('orderId') or response['data'].get('orderID')
                elif 'orderID' in response:
                    order_id = response['orderID']
                elif isinstance(response.get('rawResponse'), dict):
                    raw = response['rawResponse']
                    if 'data' in raw:
                        order_id = raw['data'].get('orderId')

            logger.info(
                f"✅ Order placed - Symbol: {order_request.get('symbol')}, "
                f"Side: {order_request.get('side')}, "
                f"Qty: {order_request.get('qty')}, "
                f"Price: {order_request.get('price')}, "
                f"OrderID: {order_id or 'N/A'}"
            )
        else:
            logger.error(
                f"❌ Order failed - Symbol: {order_request.get('symbol')}, "
                f"Side: {order_request.get('side')}, "
                f"Error: {response}"
            )

    @classmethod
    def log_order_cancellation(cls, logger: logging.Logger, order_id: str,
                               symbol: str, success: bool, response: Optional[dict] = None):
        """Log order cancellation with consistent format"""
        if success:
            logger.info(f"✅ Order cancelled - OrderID: {order_id}, Symbol: {symbol}")
        else:
            logger.error(
                f"❌ Cancel failed - OrderID: {order_id}, Symbol: {symbol}, "
                f"Error: {response}"
            )

    @classmethod
    def log_balance_fetch(cls, logger: logging.Logger, success: bool,
                          balances: Optional[list] = None, error: Optional[str] = None):
        """Log balance fetch operation"""
        if success and balances:
            total_usdt = sum(b.balance for b in balances if b.asset == 'USDT')
            logger.info(f"✅ Balance fetched - Total USDT: ${total_usdt:,.2f}")
            for balance in balances:
                if balance.balance > 0:
                    logger.debug(
                        f"  {balance.asset}: {balance.balance:,.8f} "
                        f"(Available: {balance.available:,.8f})"
                    )
        else:
            logger.error(f"❌ Balance fetch failed - Error: {error}")

    @classmethod
    def log_position_fetch(cls, logger: logging.Logger, success: bool,
                           positions: Optional[list] = None, error: Optional[str] = None):
        """Log position fetch operation"""
        if success:
            if positions:
                logger.info(f"✅ Positions fetched - Count: {len(positions)}")
                for pos in positions:
                    logger.debug(
                        f"  {pos.symbol}: Size={pos.size}, "
                        f"Entry=${pos.entryPrice}, PnL={pos.pnlPercentage:.2f}%"
                    )
            else:
                logger.info("✅ Positions fetched - No open positions")
        else:
            logger.error(f"❌ Position fetch failed - Error: {error}")
