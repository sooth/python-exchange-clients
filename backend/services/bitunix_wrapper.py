"""
Wrapper to convert BitUnix callback-based API to async/await
"""
import asyncio
from typing import Any, Callable, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor


class BitUnixWrapper:
    """Wraps BitUnix exchange to convert callbacks to async/await"""
    
    def __init__(self, exchange):
        self.exchange = exchange
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def _callback_to_async(self, method: Callable, *args) -> Any:
        """Convert a callback-based method to async/await"""
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        def callback(result):
            if result[0] == "success":
                loop.call_soon_threadsafe(future.set_result, result[1])
            else:
                loop.call_soon_threadsafe(future.set_exception, result[1] if isinstance(result[1], Exception) else Exception(str(result[1])))
        
        # Run the method in thread pool with callback
        await loop.run_in_executor(self.executor, method, *args, callback)
        
        # Wait for the callback to complete
        return await future
    
    async def fetchTickers(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fetch tickers with async/await interface"""
        return await self._callback_to_async(self.exchange.fetchTickers, symbols or [])
    
    async def fetchBalance(self) -> Dict[str, Any]:
        """Fetch balance with async/await interface"""
        return await self._callback_to_async(self.exchange.fetchBalance)
    
    async def fetchPositions(self) -> List[Any]:
        """Fetch positions with async/await interface"""
        return await self._callback_to_async(self.exchange.fetchPositions)
    
    async def fetchOrders(self, symbol: Optional[str] = None) -> List[Any]:
        """Fetch orders with async/await interface"""
        # BitUnix fetchOrders doesn't use callbacks
        return self.exchange.fetchOrders(symbol)
    
    async def fetchSymbolInfo(self, symbol: str) -> Dict[str, Any]:
        """Fetch symbol info with async/await interface"""
        return await self._callback_to_async(self.exchange.fetchSymbolInfo, symbol)
    
    async def fetchAccountEquity(self) -> float:
        """Fetch account equity with async/await interface"""
        return await self._callback_to_async(self.exchange.fetchAccountEquity)
    
    async def placeOrder(self, order_request) -> Any:
        """Place order with async/await interface"""
        return await self._callback_to_async(self.exchange.placeOrder, order_request)
    
    async def cancelOrder(self, order_id: str, symbol: Optional[str] = None) -> Any:
        """Cancel order with async/await interface"""
        return await self._callback_to_async(self.exchange.cancelOrder, order_id, symbol)
    
    def __getattr__(self, name):
        """Proxy other attributes to the underlying exchange"""
        return getattr(self.exchange, name)