"""Rate limiter for WebSocket updates to prevent system overload"""

import asyncio
import time
from typing import Dict, Any, Callable, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class UpdateRateLimiter:
    """
    Rate limiter that ensures updates are processed at a sustainable rate.
    Prevents system overload by limiting updates per symbol per second.
    """
    
    def __init__(self, max_updates_per_second: int = 10):
        self.max_updates_per_second = max_updates_per_second
        self.min_interval = 1.0 / max_updates_per_second
        self.last_update_time: Dict[str, float] = defaultdict(float)
        self._pending_updates: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
    
    async def process_update(
        self, 
        key: str, 
        handler: Callable, 
        *args, 
        **kwargs
    ) -> bool:
        """
        Process an update with rate limiting.
        
        Args:
            key: Unique key for the update (e.g., "ticker:BTCUSDT")
            handler: The async function to call
            *args, **kwargs: Arguments to pass to the handler
            
        Returns:
            True if update was processed, False if rate limited
        """
        async with self._lock:
            current_time = time.time()
            last_time = self.last_update_time[key]
            
            # Check if we're within the rate limit
            if current_time - last_time < self.min_interval:
                # Cancel any pending update for this key
                if key in self._pending_updates:
                    self._pending_updates[key].cancel()
                
                # Schedule the update for later
                delay = self.min_interval - (current_time - last_time)
                task = asyncio.create_task(
                    self._delayed_update(key, handler, delay, *args, **kwargs)
                )
                self._pending_updates[key] = task
                return False
            
            # Process immediately
            self.last_update_time[key] = current_time
            await handler(*args, **kwargs)
            return True
    
    async def _delayed_update(
        self, 
        key: str, 
        handler: Callable, 
        delay: float, 
        *args, 
        **kwargs
    ):
        """Execute a delayed update"""
        try:
            await asyncio.sleep(delay)
            async with self._lock:
                self.last_update_time[key] = time.time()
                await handler(*args, **kwargs)
                # Remove from pending updates
                if key in self._pending_updates:
                    del self._pending_updates[key]
        except asyncio.CancelledError:
            # Update was superseded by a newer one
            pass
        except Exception as e:
            logger.error(f"Error in delayed update for {key}: {e}")
    
    async def shutdown(self):
        """Cancel all pending updates"""
        async with self._lock:
            for task in self._pending_updates.values():
                task.cancel()
            self._pending_updates.clear()