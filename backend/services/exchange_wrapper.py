"""
Wrapper to convert callback-based ExchangeInterface to async/await for backend services
"""
import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from exchanges.base import ExchangeInterface, ExchangeOrderRequest


class ExchangeAsyncWrapper:
    """Wraps ExchangeInterface to provide async/await API"""
    
    def __init__(self, exchange: ExchangeInterface):
        self.exchange = exchange
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def _callback_to_async(self, method: Callable, *args) -> Any:
        """Convert a callback-based method to async/await"""
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        def callback(result: Tuple[str, Any]):
            status, data = result
            if status == "success":
                loop.call_soon_threadsafe(future.set_result, data)
            else:
                # data is exception on failure
                loop.call_soon_threadsafe(
                    future.set_exception, 
                    data if isinstance(data, Exception) else Exception(str(data))
                )
        
        # Run the method in thread pool with callback
        await loop.run_in_executor(self.executor, method, *args, callback)
        
        # Wait for the callback to complete
        return await future
    
    async def fetchTickers(self) -> List[Any]:
        """Fetch all tickers"""
        return await self._callback_to_async(self.exchange.fetchTickers)
    
    async def fetchSymbolInfo(self, symbol: str) -> Dict[str, Any]:
        """Fetch symbol information"""
        return await self._callback_to_async(self.exchange.fetchSymbolInfo, symbol)
    
    async def fetchBalance(self) -> Dict[str, Any]:
        """Fetch account balance"""
        return await self._callback_to_async(self.exchange.fetchBalance)
    
    async def fetchPositions(self) -> List[Any]:
        """Fetch open positions"""
        return await self._callback_to_async(self.exchange.fetchPositions)
    
    async def fetchOrders(self) -> List[Any]:
        """Fetch open orders"""
        return await self._callback_to_async(self.exchange.fetchOrders)
    
    async def placeOrder(self, request: ExchangeOrderRequest) -> Any:
        """Place an order"""
        return await self._callback_to_async(self.exchange.placeOrder, request)
    
    async def cancelOrder(self, orderID: Optional[str] = None, 
                         clOrderID: Optional[str] = None,
                         symbol: Optional[str] = None) -> Any:
        """Cancel an order"""
        return await self._callback_to_async(
            self.exchange.cancelOrder, orderID, clOrderID, symbol
        )
    
    async def fetchAccountEquity(self) -> float:
        """Fetch account equity"""
        return await self._callback_to_async(self.exchange.fetchAccountEquity)
    
    def get_name(self) -> str:
        """Get exchange name"""
        return self.exchange.get_name()
    
    def get_symbol_format(self, base_symbol: str) -> str:
        """Get symbol format for exchange"""
        return self.exchange.get_symbol_format(base_symbol)
    
    def translate_side_to_exchange(self, side: str) -> str:
        """Translate side to exchange format"""
        return self.exchange.translate_side_to_exchange(side)
    
    def translate_side_from_exchange(self, exchange_side: str) -> str:
        """Translate side from exchange format"""
        return self.exchange.translate_side_from_exchange(exchange_side)
    
    async def fetchOHLCV(self, symbol: str, timeframe: str, limit: int = 100) -> List[Any]:
        """Fetch OHLCV data"""
        return await self._callback_to_async(self.exchange.fetchOHLCV, symbol, timeframe, limit)