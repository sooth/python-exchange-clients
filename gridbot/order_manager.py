"""Order Manager - Handles order placement, tracking, and management"""

import time
import uuid
from typing import List, Dict, Optional, Callable, Tuple
from collections import defaultdict
import threading

from exchanges.base import ExchangeInterface, ExchangeOrderRequest
from .types import GridLevel, GridOrder, OrderSide, GridConfig


class OrderManager:
    """Manages orders for the grid bot"""
    
    def __init__(self, exchange: ExchangeInterface, config: GridConfig, position_tracker=None):
        self.exchange = exchange
        self.config = config
        self.position_tracker = position_tracker
        self.active_orders: Dict[str, GridOrder] = {}  # order_id -> GridOrder
        self.grid_orders: Dict[int, str] = {}  # grid_index -> order_id
        self.order_callbacks: Dict[str, Callable] = {}
        self.lock = threading.Lock()
        
        # Rate limiting
        self.last_order_time = 0
        self.min_order_interval = 0.1  # 100ms between orders
    
    def set_position_tracker(self, position_tracker):
        """Set the position tracker (for circular dependency resolution)"""
        self.position_tracker = position_tracker
        
    def place_initial_orders(self, levels: List[GridLevel], callback: Optional[Callable] = None) -> List[str]:
        """
        Place initial grid orders
        
        Args:
            levels: Grid levels to place orders for
            callback: Optional callback for order placement results
            
        Returns:
            List of order IDs
        """
        order_ids = []
        errors = []
        
        # Batch orders if possible
        batch_size = 10  # Place 10 orders at a time
        
        for i in range(0, len(levels), batch_size):
            batch = levels[i:i + batch_size]
            
            for level in batch:
                try:
                    order_id = self._place_grid_order(level)
                    if order_id:
                        order_ids.append(order_id)
                except Exception as e:
                    errors.append(f"Failed to place order at level {level.index}: {e}")
            
            # Rate limiting between batches
            time.sleep(0.5)
        
        if callback:
            callback(order_ids, errors)
        
        return order_ids
    
    def _place_grid_order(self, level: GridLevel) -> Optional[str]:
        """Place a single grid order"""
        # Generate client order ID
        client_order_id = f"grid_{self.config.symbol}_{level.index}_{uuid.uuid4().hex[:8]}"
        
        # Determine if this order should be reduce-only
        # Get current position from position tracker if available
        reduce_only = False
        if hasattr(self, 'position_tracker') and self.position_tracker:
            current_position = self.position_tracker.position.size
            # If we have a LONG position and placing a SELL order, it should reduce
            # If we have a SHORT position and placing a BUY order, it should reduce
            if (current_position > 0 and level.side == OrderSide.SELL) or \
               (current_position < 0 and level.side == OrderSide.BUY):
                reduce_only = True
        
        # Create order request
        order_request = ExchangeOrderRequest(
            symbol=self.config.symbol,
            side="BUY" if level.side == OrderSide.BUY else "SELL",
            orderType=self.config.order_type,
            qty=level.quantity,
            price=level.price,
            orderLinkId=client_order_id,
            timeInForce=self.config.time_in_force,
            reduceOnly=reduce_only
        )
        
        # Add post-only flag if enabled
        if self.config.post_only:
            order_request.timeInForce = "PO"  # Post-only
        
        # Rate limiting
        self._apply_rate_limit()
        
        # Place order
        result = {"order_id": None, "error": None, "completed": False}
        
        def order_callback(status_data):
            status, data = status_data
            result["completed"] = True
            if status == "success":
                result["order_id"] = data.orderId
            else:
                result["error"] = data
        
        self.exchange.placeOrder(order_request, order_callback)
        
        # Wait for completion
        timeout = 5
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.01)
        
        if result["error"]:
            raise Exception(result["error"])
        
        if result["order_id"]:
            # Track the order
            grid_order = GridOrder(
                grid_index=level.index,
                order_id=result["order_id"],
                client_order_id=client_order_id,
                symbol=self.config.symbol,
                side=level.side,
                price=level.price,
                quantity=level.quantity,
                status="placed",
                created_at=time.time()
            )
            
            with self.lock:
                self.active_orders[result["order_id"]] = grid_order
                self.grid_orders[level.index] = result["order_id"]
                level.order_id = result["order_id"]
                level.status = "placed"
            
            return result["order_id"]
        
        return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a specific order"""
        result = {"success": False, "completed": False}
        
        def cancel_callback(status_data):
            status, data = status_data
            result["completed"] = True
            result["success"] = status == "success"
        
        self.exchange.cancelOrder(orderID=order_id, symbol=self.config.symbol, completion=cancel_callback)
        
        # Wait for completion
        timeout = 5
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.01)
        
        if result["success"]:
            with self.lock:
                # Remove from tracking
                if order_id in self.active_orders:
                    grid_order = self.active_orders[order_id]
                    del self.active_orders[order_id]
                    if grid_order.grid_index in self.grid_orders:
                        del self.grid_orders[grid_order.grid_index]
        
        return result["success"]
    
    def cancel_all_orders(self) -> Tuple[int, int]:
        """
        Cancel all active orders
        
        Returns:
            Tuple of (successful_cancels, failed_cancels)
        """
        order_ids = list(self.active_orders.keys())
        successful = 0
        failed = 0
        
        for order_id in order_ids:
            if self.cancel_order(order_id):
                successful += 1
            else:
                failed += 1
            
            # Rate limiting
            time.sleep(0.1)
        
        return successful, failed
    
    def update_order_status(self, order_id: str, status: str, fill_price: Optional[float] = None):
        """Update order status (called by websocket or polling)"""
        with self.lock:
            if order_id in self.active_orders:
                order = self.active_orders[order_id]
                order.status = status
                
                if status == "filled":
                    order.filled_at = time.time()
                    if fill_price:
                        order.fill_price = fill_price
                    
                    # Trigger fill callback if registered
                    if order_id in self.order_callbacks:
                        self.order_callbacks[order_id](order)
    
    def on_order_filled(self, order_id: str, callback: Callable):
        """Register callback for when an order is filled"""
        self.order_callbacks[order_id] = callback
    
    def get_active_orders(self) -> List[GridOrder]:
        """Get all active orders"""
        with self.lock:
            return list(self.active_orders.values())
    
    def get_order_by_grid_index(self, grid_index: int) -> Optional[GridOrder]:
        """Get order by grid index"""
        with self.lock:
            order_id = self.grid_orders.get(grid_index)
            if order_id:
                return self.active_orders.get(order_id)
        return None
    
    def replace_order(self, grid_level: GridLevel, new_price: Optional[float] = None) -> Optional[str]:
        """
        Replace an order at a grid level
        
        Args:
            grid_level: Grid level to replace order for
            new_price: Optional new price (uses level price if not specified)
            
        Returns:
            New order ID if successful
        """
        # Cancel existing order if any
        if grid_level.order_id:
            self.cancel_order(grid_level.order_id)
        
        # Update price if specified
        if new_price:
            grid_level.price = new_price
        
        # Place new order
        return self._place_grid_order(grid_level)
    
    def get_order_summary(self) -> dict:
        """Get summary of current orders"""
        with self.lock:
            buy_orders = [o for o in self.active_orders.values() if o.side == OrderSide.BUY]
            sell_orders = [o for o in self.active_orders.values() if o.side == OrderSide.SELL]
            
            return {
                'total_orders': len(self.active_orders),
                'buy_orders': len(buy_orders),
                'sell_orders': len(sell_orders),
                'buy_value': sum(o.price * o.quantity for o in buy_orders),
                'sell_value': sum(o.price * o.quantity for o in sell_orders)
            }
    
    def _apply_rate_limit(self):
        """Apply rate limiting between orders"""
        current_time = time.time()
        time_since_last = current_time - self.last_order_time
        
        if time_since_last < self.min_order_interval:
            time.sleep(self.min_order_interval - time_since_last)
        
        self.last_order_time = time.time()