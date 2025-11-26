"""Python Exchange Clients - Cryptocurrency exchange API clients."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Import main exchange classes
from .lmex import LMEXExchange
from .bitunix import BitUnixExchange

# Import base classes and protocols
from .base import (
    ExchangeProtocol,
    ExchangeOrderRequest,
    ExchangeOrderResponse,
    ExchangePosition,
    ExchangeTicker,
    ExchangeBalance,
    ExchangeOrder,
    PositionSide,
    TradingType,
)

# Adapters are optional and can be imported separately if needed

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",

    # Exchange classes
    "LMEXExchange",
    "BitUnixExchange",

    # Base classes
    "ExchangeProtocol",
    "ExchangeOrderRequest",
    "ExchangeOrderResponse",
    "ExchangePosition",
    "ExchangeTicker",
    "ExchangeBalance",
    "ExchangeOrder",
    "PositionSide",
    "TradingType",

]
