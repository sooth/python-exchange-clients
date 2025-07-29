"""Core Grid Bot Implementation"""

import time
import threading
import os
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime

from exchanges.base import ExchangeInterface, ExchangeOrderRequest, WebSocketSubscription, WebSocketMessage, WebSocketState, WebSocketChannels
from .types import GridConfig, GridState, GridLevel, GridStats, OrderSide, PositionDirection
from .calculator import GridCalculator
from .order_manager import OrderManager
from .position_tracker import PositionTracker
from .risk_manager import RiskManager
from .persistence import GridBotPersistence
from .initial_position_calculator_v3 import InitialPositionCalculatorV3
from .safety_checker import GridBotSafetyChecker


class GridBot:
    """Main Grid Bot orchestrator"""
    
    def __init__(self, exchange: ExchangeInterface, config: GridConfig, persistence_path: Optional[str] = None):
        self.exchange = exchange
        self.config = config
        
        # Core components
        self.calculator = GridCalculator(config)
        self.position_tracker = PositionTracker(config.symbol)
        self.order_manager = OrderManager(exchange, config)
        self.order_manager.set_position_tracker(self.position_tracker)
        self.risk_manager = RiskManager(config)
        self.initial_position_calculator = InitialPositionCalculatorV3(config)
        self.safety_checker = GridBotSafetyChecker()
        
        # State
        self.state = GridState.INITIALIZED
        self.grid_levels: List[GridLevel] = []
        self.stats = GridStats()
        self.start_time = 0
        
        # Persistence
        self.persistence = GridBotPersistence(persistence_path) if persistence_path else None
        
        # Monitoring
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_interval = 1.0  # seconds
        self.running = False
        
        # WebSocket support
        self.use_websocket = True  # Enable WebSocket by default
        self.websocket_connected = False
        self.last_websocket_price: Optional[float] = None
        self.websocket_orders: Dict[str, Any] = {}
        self.websocket_positions: Dict[str, Any] = {}
        
        # Callbacks
        self.on_grid_trade: Optional[Callable] = None
        self.on_state_change: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Initialize
        self._initialize()
        
        # Risk acceptance flag
        self._accept_high_risk = False
    
    def _initialize(self):
        """Initialize the grid bot"""
        # Validate configuration
        errors = self.config.validate()
        if errors:
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")
        
        # Load persisted state if available
        if self.persistence:
            saved_state = self.persistence.load_state()
            if saved_state:
                self._restore_state(saved_state)
                return
        
        # Calculate initial grid levels
        self._update_grid_levels()
    
    def _update_grid_levels(self):
        """Update grid levels based on current configuration"""
        # Get current price
        current_price = self._get_current_price()
        
        # Calculate grid levels
        self.grid_levels = self.calculator.calculate_grid_levels(current_price)
        
        # Apply V3 calculator to adjust quantities and get initial position
        (initial_qty, initial_side), self.grid_levels = self.initial_position_calculator.calculate_grid_with_leverage(
            self.grid_levels, current_price
        )
        self._initial_position_info = (initial_qty, initial_side)
        
        print(f"Calculated {len(self.grid_levels)} grid levels")
        print(f"Price range: ${self.config.lower_price} - ${self.config.upper_price}")
        print(f"Current price: ${current_price}")
    
    def _ensure_one_way_mode(self) -> bool:
        """Ensure BitUnix is in one-way mode for proper position management"""
        # Check if exchange supports position mode management
        if not hasattr(self.exchange, 'fetchPositionMode'):
            return True
            
        result = {"completed": False, "success": False, "mode": None, "error": None}
        
        def mode_callback(status_data):
            status, data = status_data
            result["completed"] = True
            if status == "success":
                result["mode"] = data.get("positionMode")
            else:
                result["error"] = str(data)
        
        # Check current position mode
        print("Checking position mode...")
        self.exchange.fetchPositionMode(mode_callback)
        
        # Wait for completion
        timeout = 5
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.01)
        
        if result["error"]:
            print(f"⚠️ Warning: Could not check position mode: {result['error']}")
            print("Assuming HEDGE mode is active - this may cause issues with reduce-only orders.")
            # Try to continue but warn about potential issues
            return True
        
        current_mode = result["mode"]
        print(f"Current position mode: {current_mode}")
        
        if current_mode == "HEDGE":
            print("Switching to ONE_WAY mode for proper reduce-only order support...")
            
            # Reset result
            result = {"completed": False, "success": False, "error": None}
            
            def set_mode_callback(status_data):
                status, data = status_data
                result["completed"] = True
                result["success"] = status == "success"
                if status == "failure":
                    result["error"] = str(data)
            
            self.exchange.setPositionMode("ONE_WAY", set_mode_callback)
            
            # Wait for completion
            start_time = time.time()
            while not result["completed"] and (time.time() - start_time) < timeout:
                time.sleep(0.01)
            
            if result["error"]:
                print(f"❌ Error: Could not set position mode to ONE_WAY: {result['error']}")
                print("\nIMPORTANT: Grid bot requires ONE_WAY position mode to function properly.")
                print("Reduce-only orders will not work correctly in HEDGE mode.")
                print("\nTo fix this issue:")
                print("1. Close all open positions for this exchange")
                print("2. Cancel all open orders")
                print("3. Try starting the grid bot again")
                return False
            
            print("✅ Successfully switched to ONE_WAY mode")
        
        return True
    
    def start(self):
        """Start the grid bot"""
        if self.state == GridState.RUNNING:
            print("Grid bot is already running")
            return
        
        print(f"\n=== Starting Grid Bot for {self.config.symbol} ===")
        
        # Get current price for safety checks
        current_price = self._get_current_price()
        if not current_price:
            print("Failed to get current price")
            return
        
        # Perform comprehensive safety check
        print("\n🔍 Performing safety checks...")
        safety_result = self.safety_checker.check_configuration(
            self.config, current_price, exchange=self.exchange
        )
        
        # Display safety report
        safety_report = self.safety_checker.format_safety_report(
            safety_result, current_price
        )
        print(safety_report)
        
        # Handle safety check results
        if not safety_result.passed:
            # Check if user has accepted high risk
            if hasattr(self, '_accept_high_risk') and self._accept_high_risk:
                print("\n⚠️  CRITICAL SAFETY ISSUES DETECTED!")
                print("However, HIGH RISK MODE is enabled - proceeding anyway.")
                print("⚠️  YOU MAY LOSE YOUR ENTIRE INVESTMENT!")
            else:
                print("\n❌ Safety check FAILED! Grid bot cannot start with this configuration.")
                print("Please fix the critical issues and try again.")
                print("Or use bot.accept_high_risk() to override safety checks.")
                return
        elif safety_result.risk_score > 50:
            print("\n⚠️  HIGH RISK CONFIGURATION DETECTED!")
            print("Are you sure you want to proceed with this risky configuration?")
            
            # In production, this would prompt for user confirmation
            # For now, we'll require explicit acceptance
            if hasattr(self, '_accept_high_risk') and self._accept_high_risk:
                print("High risk accepted by user.")
            else:
                print("Start cancelled due to high risk. Set bot._accept_high_risk = True to override.")
                return
        
        # Ensure proper position mode for BitUnix
        if not self._ensure_one_way_mode():
            print("Failed to set position mode to ONE_WAY. Grid bot cannot start.")
            return
        
        # Check risk conditions
        allowed, reason = self.risk_manager.check_order_placement_allowed()
        if not allowed:
            print(f"Cannot start: {reason}")
            return
        
        # Update state
        self.state = GridState.RUNNING
        self.running = True
        self.start_time = time.time()
        self._trigger_state_change()
        
        # Check for existing position first
        print("\nChecking for existing position...")
        existing_position = self._check_existing_position()
        
        if existing_position and abs(existing_position['size']) > 0:
            print(f"\n⚠️  WARNING: Found existing position!")
            print(f"Position: {existing_position['size']} @ ${existing_position['entry_price']:.2f}")
            print(f"Current P&L: ${existing_position['unrealized_pnl']:.2f}")
            
            # Ask user what to do
            print("\nOptions:")
            print("1. Resume with existing position (recommended)")
            print("2. Close existing position and start fresh")
            print("3. Cancel and exit")
            
            # For automated testing, default to option 1
            if os.environ.get('GRIDBOT_AUTO_RESUME', '').lower() == 'true':
                choice = "1"
                print("\nAuto-selecting option 1: Resume with existing position")
            else:
                choice = input("\nEnter choice (1/2/3): ").strip()
            
            if choice == "2":
                print("Closing existing position...")
                self._close_position()
                time.sleep(2)
            elif choice == "3":
                print("Cancelled. Exiting...")
                self.state = GridState.STOPPED
                return
            else:
                print("Resuming with existing position...")
                # Sync position tracker with exchange position
                self.position_tracker.position.size = existing_position['size']
                self.position_tracker.position.entry_price = existing_position['entry_price']
                self.position_tracker.position.current_price = existing_position.get('mark_price', current_price)
                self.position_tracker.position.unrealized_pnl = existing_position['unrealized_pnl']
        
        # Calculate and place initial position ONLY if no existing position
        if not existing_position or abs(existing_position.get('size', 0)) == 0:
            print("\nCalculating initial position...")
            # Use the pre-calculated initial position info
            initial_qty, initial_side = self._initial_position_info
            
            # Calculate price location
            price_range = self.config.upper_price - self.config.lower_price
            price_location = ((current_price - self.config.lower_price) / price_range) * 100
            
            print(f"Price Location: {price_location:.1f}% of range")
            print(f"Initial Action: {initial_side.value} {initial_qty:.3f} units")
            
            # Place initial position if needed
            if initial_qty > 0:
                print("\nPlacing initial position order...")
                success = self._place_initial_position(
                    initial_qty,
                    initial_side.value
                )
                if not success:
                    print("\n❌ CRITICAL: Failed to establish initial position!")
                    print("Grid bot CANNOT continue without a position.")
                    print("\nPossible reasons:")
                    print("1. Order size too small for exchange minimum")
                    print("2. Insufficient balance")
                    print("3. Exchange rejected the order")
                    print("\nPlease check your configuration and try again.")
                    
                    # Update state to stopped
                    self.state = GridState.STOPPED
                    self._trigger_state_change()
                    return
                else:
                    print("✅ Initial position established and verified successfully")
                    # Give it a moment to settle
                    time.sleep(2)
        else:
            print("\nUsing existing position, skipping initial position placement.")
        
        # Check for existing orders
        print("\nChecking for existing grid orders...")
        existing_orders = self._check_existing_orders()
        
        if existing_orders and len(existing_orders) > 0:
            print(f"\n⚠️  WARNING: Found {len(existing_orders)} existing orders!")
            grid_orders = [o for o in existing_orders if o.clientId and 'grid_' in o.clientId]
            print(f"Grid orders: {len(grid_orders)}")
            
            if len(grid_orders) > 0:
                print("\nOptions:")
                print("1. Keep existing orders and continue")
                print("2. Cancel existing orders and place new ones")
                print("3. Cancel and exit")
                
                # For automated testing, default to option 1
                if os.environ.get('GRIDBOT_AUTO_RESUME', '').lower() == 'true':
                    choice = "1"
                    print("\nAuto-selecting option 1: Keep existing orders")
                else:
                    choice = input("\nEnter choice (1/2/3): ").strip()
                
                if choice == "2":
                    print("Cancelling existing orders...")
                    for order in grid_orders:
                        self.order_manager.cancel_order(order.orderId)
                    time.sleep(2)
                elif choice == "3":
                    print("Cancelled. Exiting...")
                    self.state = GridState.STOPPED
                    return
                else:
                    print("Keeping existing orders...")
                    # Map existing orders to grid levels
                    self._map_existing_orders_to_grid(grid_orders)
                    # Still need to set up monitoring and callbacks
                    self._setup_order_monitoring()
                    # Skip new order placement - we're using existing orders
                    print("\nGrid bot started successfully with existing orders!")
                    # Jump to WebSocket setup
                    self._start_websocket_and_monitoring()
                    return
        
        # Place grid orders (only if we don't have existing orders)
        print("\nPlacing grid orders...")
        initial_orders = self.calculator.get_initial_orders(self.grid_levels, current_price)
        
        def order_callback(order_ids, errors):
            print(f"Placed {len(order_ids)} orders successfully")
            if errors:
                print(f"Errors: {errors}")
        
        self.order_manager.place_initial_orders(initial_orders, order_callback)
        
        # Set up order monitoring
        self._setup_order_monitoring()
        
        # Start WebSocket and monitoring
        self._start_websocket_and_monitoring()
    
    def _start_websocket_and_monitoring(self):
        """Start WebSocket connection and monitoring"""
        # Start WebSocket connection if enabled
        if self.use_websocket:
            print("\nConnecting to WebSocket for real-time updates...")
            if self._connect_websocket():
                print("WebSocket connected successfully!")
            else:
                print("WebSocket connection failed, falling back to REST API polling")
                self.use_websocket = False
        
        # Start monitoring
        self._start_monitoring()
        
        # Start risk monitoring
        self.risk_manager.start_monitoring(self.position_tracker, self.stats)
        
        print("\nGrid bot started successfully!")
    
    def accept_high_risk(self, accept: bool = True):
        """
        Accept high risk configurations.
        
        Args:
            accept: Whether to accept high risk (default True)
        """
        self._accept_high_risk = accept
        if accept:
            print("⚠️  HIGH RISK MODE ENABLED - Proceed with extreme caution!")
        else:
            print("✅ High risk mode disabled - Safety checks enforced")
    
    def stop(self):
        """Stop the grid bot"""
        if self.state != GridState.RUNNING:
            print("Grid bot is not running")
            return
        
        print("\n=== Stopping Grid Bot ===")
        
        # Update state
        self.state = GridState.STOPPED
        self.running = False
        self._trigger_state_change()
        
        # Stop monitoring
        self._stop_monitoring()
        self.risk_manager.stop_monitoring()
        
        # Disconnect WebSocket
        if self.websocket_connected:
            self.exchange.disconnectWebSocket()
            self.websocket_connected = False
        
        # Cancel orders if configured
        if self.config.cancel_orders_on_stop:
            print("Cancelling all orders...")
            successful, failed = self.order_manager.cancel_all_orders()
            print(f"Cancelled {successful} orders, {failed} failed")
        
        # Close position if configured
        if self.config.close_position_on_stop:
            self._close_position()
        
        # Save state
        if self.persistence:
            self.persistence.save_state(self._get_state())
        
        # Print final statistics
        self._print_statistics()
        
        print("\nGrid bot stopped")
    
    def pause(self):
        """Pause the grid bot (keeps orders but stops placing new ones)"""
        if self.state != GridState.RUNNING:
            print("Grid bot is not running")
            return
        
        self.state = GridState.PAUSED
        self._trigger_state_change()
        print("Grid bot paused")
    
    def resume(self):
        """Resume the grid bot from pause"""
        if self.state != GridState.PAUSED:
            print("Grid bot is not paused")
            return
        
        self.state = GridState.RUNNING
        self._trigger_state_change()
        print("Grid bot resumed")
    
    def _start_monitoring(self):
        """Start the monitoring thread"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def _stop_monitoring(self):
        """Stop the monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Get current price (prefer WebSocket data)
                current_price = None
                if self.use_websocket and self.last_websocket_price:
                    current_price = self.last_websocket_price
                else:
                    # Fall back to REST API
                    current_price = self._get_current_price()
                
                if current_price:
                    self.position_tracker.update_current_price(current_price)
                
                # Check for filled orders (if not using WebSocket)
                if not self.use_websocket:
                    self._check_order_status()
                
                # Update statistics
                self._update_statistics()
                
                # Check if grid adjustment needed
                if self.state == GridState.RUNNING and current_price:
                    self._check_grid_adjustment(current_price)
                
                # Save state periodically
                if self.persistence and int(time.time()) % 60 == 0:
                    self.persistence.save_state(self._get_state())
                
                # Show WebSocket status
                if self.use_websocket and int(time.time()) % 10 == 0:
                    ws_state = self.exchange.getWebSocketState()
                    print(f"\r📡 WebSocket: {ws_state} | Price: ${current_price:.2f} | Orders: {len(self.order_manager.active_orders)} active", end="", flush=True)
                
            except Exception as e:
                print(f"\nMonitor error: {e}")
                if self.on_error:
                    self.on_error(e)
            
            time.sleep(self.monitor_interval)
    
    def _handle_order_fill(self, order):
        """Handle when an order is filled"""
        print(f"Order filled: {order.side.value} {order.quantity} @ ${order.fill_price}")
        
        # Update position
        self.position_tracker.update_position_from_order(order)
        
        # Record trade result for risk management
        if order.side == OrderSide.SELL:
            # Calculate approximate profit (simplified)
            profit = (order.fill_price - order.price) * order.quantity * 0.999  # Account for fees
            self.risk_manager.record_trade_result(profit)
        
        # Find the grid level
        grid_level = None
        for level in self.grid_levels:
            if level.order_id == order.order_id:
                grid_level = level
                break
        
        if not grid_level:
            return
        
        # Update grid level status
        grid_level.status = "filled"
        grid_level.filled_at = time.time()
        
        # Place opposite order if in running state
        if self.state == GridState.RUNNING:
            self._place_opposite_order(grid_level, order)
        
        # Trigger callback
        if self.on_grid_trade:
            self.on_grid_trade(order)
    
    def _place_opposite_order(self, filled_level: GridLevel, filled_order):
        """Place opposite order after a fill"""
        # Determine new side
        new_side = OrderSide.SELL if filled_order.side == OrderSide.BUY else OrderSide.BUY
        
        # Find appropriate grid level for opposite order
        if new_side == OrderSide.SELL:
            # Place sell order at higher level
            target_index = filled_level.index + 1
        else:
            # Place buy order at lower level
            target_index = filled_level.index - 1
        
        # Check bounds
        if target_index < 0 or target_index >= len(self.grid_levels):
            return
        
        target_level = self.grid_levels[target_index]
        
        # Skip if already has active order
        if target_level.is_active():
            return
        
        # Place new order
        target_level.side = new_side
        order_id = self.order_manager._place_grid_order(target_level)
        
        if order_id:
            self.order_manager.on_order_filled(order_id, self._handle_order_fill)
    
    def _check_order_status(self):
        """Check status of all orders"""
        # This would typically use WebSocket for real-time updates
        # For now, we'll use polling
        
        result = {"orders": None, "error": None, "completed": False}
        
        def orders_callback(status_data):
            status, data = status_data
            result["completed"] = True
            if status == "success":
                result["orders"] = data
            else:
                result["error"] = data
        
        self.exchange.fetchOrders(orders_callback)
        
        # Wait for completion
        timeout = 2
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.01)
        
        if result["orders"]:
            # Update order statuses
            for order in result["orders"]:
                self.order_manager.update_order_status(
                    order.orderId,
                    order.status,
                    order.price
                )
    
    def _check_grid_adjustment(self, current_price: float):
        """Check if grid needs adjustment"""
        new_levels = self.calculator.recalculate_grid_on_price_move(self.grid_levels, current_price)
        
        if new_levels:
            print(f"Adjusting grid due to price movement to ${current_price}")
            
            # Cancel existing orders
            self.order_manager.cancel_all_orders()
            
            # Update grid levels
            self.grid_levels = new_levels
            
            # Place new orders
            initial_orders = self.calculator.get_initial_orders(self.grid_levels, current_price)
            self.order_manager.place_initial_orders(initial_orders)
    
    def _get_current_price(self) -> Optional[float]:
        """Get current market price"""
        result = {"price": None, "completed": False}
        
        def ticker_callback(status_data):
            status, data = status_data
            result["completed"] = True
            if status == "success" and data:
                for ticker in data:
                    if ticker.symbol == self.config.symbol:
                        result["price"] = ticker.lastPrice
                        break
        
        self.exchange.fetchTickers(ticker_callback)
        
        # Wait for completion
        timeout = 2
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.01)
        
        return result["price"]
    
    def _check_existing_position(self) -> Optional[dict]:
        """Check for existing position on the exchange"""
        result = {"position": None, "completed": False}
        
        def position_callback(status_data):
            status, data = status_data
            result["completed"] = True
            if status == "success" and data:
                # Find position for our symbol
                for pos in data:
                    if pos.symbol == self.config.symbol:
                        result["position"] = {
                            'size': pos.size,
                            'entry_price': pos.entryPrice,
                            'unrealized_pnl': pos.pnl,
                            'mark_price': pos.markPrice
                        }
                        break
        
        self.exchange.fetchPositions(position_callback)
        
        # Wait for completion
        timeout = 5
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.01)
        
        return result["position"]
    
    def _check_existing_orders(self) -> Optional[List]:
        """Check for existing orders on the exchange"""
        result = {"orders": None, "completed": False}
        
        def orders_callback(status_data):
            status, data = status_data
            result["completed"] = True
            if status == "success":
                result["orders"] = data
        
        self.exchange.fetchOrders(orders_callback)
        
        # Wait for completion
        timeout = 5
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.01)
        
        return result["orders"]
    
    def _close_position(self):
        """Close current position at market price"""
        # Get actual position from exchange
        existing_position = self._check_existing_position()
        
        if not existing_position or existing_position['size'] == 0:
            print("No position to close")
            return
        
        # Determine close side
        close_side = "BUY" if existing_position['size'] < 0 else "SELL"
        close_qty = abs(existing_position['size'])
        
        print(f"Closing position: {close_side} {close_qty} @ market")
        
        # Place market order to close
        order_request = ExchangeOrderRequest(
            symbol=self.config.symbol,
            side=close_side,
            orderType="MARKET",
            qty=close_qty,
            orderLinkId=f"grid_close_{self.config.symbol}_{int(time.time())}",
            tradingType="PERP",
            reduceOnly=True  # Important: this is a close order
        )
        
        result = {"success": False, "completed": False}
        
        def close_callback(status_data):
            status, data = status_data
            result["completed"] = True
            result["success"] = status == "success"
        
        self.exchange.placeOrder(order_request, close_callback)
        
        # Wait for completion
        timeout = 5
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.01)
        
        if result["success"]:
            print("Position closed successfully")
        else:
            print("Failed to close position")
    
    def _place_initial_position(self, quantity: float, side: str) -> bool:
        """
        Place initial position order at market price
        
        Args:
            quantity: Amount to buy/sell
            side: "BUY" or "SELL"
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Pre-check: Verify quantity meets minimum requirements
            min_qty = self._get_minimum_order_size()
            if quantity < min_qty:
                print(f"\n❌ CRITICAL ERROR: Initial position size {quantity:.6f} is below minimum {min_qty}")
                print(f"Cannot establish position. Grid bot cannot start!")
                return False
            # Create market order request
            order_request = ExchangeOrderRequest(
                symbol=self.config.symbol,
                side=side,
                orderType="MARKET",
                qty=quantity,
                orderLinkId=f"grid_init_{self.config.symbol}_{int(time.time())}",
                tradingType="PERP"
            )
            
            # Place order
            result = {"success": False, "completed": False, "order": None, "error": None}
            
            def init_callback(status_data):
                status, data = status_data
                result["completed"] = True
                result["success"] = status == "success"
                if status == "success":
                    result["order"] = data
                else:
                    result["error"] = data
            
            self.exchange.placeOrder(order_request, init_callback)
            
            # Wait for completion
            timeout = 5
            start_time = time.time()
            while not result["completed"] and (time.time() - start_time) < timeout:
                time.sleep(0.01)
            
            if result["success"]:
                print(f"Initial position order placed: {side} {quantity:.3f} @ MARKET")
                
                # CRITICAL: Verify position was actually established
                print("\n🔍 Verifying position establishment...")
                verified = self._verify_position_established(quantity, side, max_attempts=3)
                
                if not verified:
                    print("\n❌ CRITICAL ERROR: Position verification failed!")
                    print("The order was placed but no position was established.")
                    print("Grid bot cannot continue without a confirmed position.")
                    return False
                
                print("✅ Position verified successfully!")
                return True
            else:
                print(f"\n❌ Failed to place initial position order")
                if 'error' in result:
                    print(f"Error details: {result['error']}")
                return False
                
        except Exception as e:
            print(f"Error placing initial position: {e}")
            return False
    
    def _update_statistics(self):
        """Update bot statistics"""
        # Get position summary
        position = self.position_tracker.get_position_summary()
        trade_stats = self.position_tracker.get_trade_statistics()
        
        # Update stats
        self.stats.total_trades = trade_stats['total_trades']
        self.stats.winning_trades = trade_stats['winning_trades']
        self.stats.losing_trades = trade_stats['losing_trades']
        self.stats.grid_profit = trade_stats['total_grid_profit']
        self.stats.position_profit = position['unrealized_pnl']
        self.stats.fees_paid = position['total_fees']
        self.stats.total_volume = position['total_volume']
        
        if self.start_time > 0:
            self.stats.uptime_seconds = time.time() - self.start_time
        
        self.stats.update_metrics()
    
    def _print_statistics(self):
        """Print current statistics"""
        print("\n=== Grid Bot Statistics ===")
        print(f"State: {self.state.value}")
        print(f"Uptime: {self.stats.uptime_seconds / 3600:.1f} hours")
        print(f"\nTrades:")
        print(f"  Total: {self.stats.total_trades}")
        print(f"  Winning: {self.stats.winning_trades}")
        print(f"  Losing: {self.stats.losing_trades}")
        print(f"  Win Rate: {self.stats.win_rate:.1f}%")
        print(f"\nProfit:")
        print(f"  Grid Profit: ${self.stats.grid_profit:.2f}")
        print(f"  Position Profit: ${self.stats.position_profit:.2f}")
        print(f"  Total Profit: ${self.stats.total_profit:.2f}")
        print(f"  Fees Paid: ${self.stats.fees_paid:.2f}")
        print(f"  Net Profit: ${self.stats.total_profit - self.stats.fees_paid:.2f}")
        print(f"\nVolume: ${self.stats.total_volume:,.2f}")
        
        position = self.position_tracker.get_position_summary()
        print(f"\nPosition:")
        print(f"  Size: {position['size']}")
        print(f"  Entry: ${position['entry_price']:.2f}")
        print(f"  Current: ${position['current_price']:.2f}")
        print(f"  PnL: ${position['unrealized_pnl']:.2f} ({position['pnl_percentage']:.2f}%)")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        position = self.position_tracker.get_position_summary()
        order_summary = self.order_manager.get_order_summary()
        risk_status = self.risk_manager.get_risk_status()
        
        return {
            'state': self.state.value,
            'config': {
                'symbol': self.config.symbol,
                'range': f"${self.config.lower_price} - ${self.config.upper_price}",
                'grids': self.config.grid_count,
                'investment': self.config.total_investment
            },
            'position': position,
            'orders': order_summary,
            'statistics': {
                'trades': self.stats.total_trades,
                'win_rate': self.stats.win_rate,
                'total_profit': self.stats.total_profit,
                'uptime_hours': self.stats.uptime_seconds / 3600
            },
            'risk': risk_status
        }
    
    def _get_state(self) -> Dict[str, Any]:
        """Get current state for persistence"""
        return {
            'config': self.config,
            'state': self.state,
            'grid_levels': self.grid_levels,
            'stats': self.stats,
            'position': self.position_tracker.position,
            'start_time': self.start_time
        }
    
    def _restore_state(self, saved_state: Dict[str, Any]):
        """Restore from saved state"""
        self.config = saved_state['config']
        self.state = saved_state['state']
        self.grid_levels = saved_state['grid_levels']
        self.stats = saved_state['stats']
        self.position_tracker.position = saved_state['position']
        self.start_time = saved_state['start_time']
    
    def _trigger_state_change(self):
        """Trigger state change callback"""
        if self.on_state_change:
            self.on_state_change(self.state)
    
    def _connect_websocket(self) -> bool:
        """Connect to exchange WebSocket for real-time updates"""
        try:
            # Connect to WebSocket
            success = self.exchange.connectWebSocket(
                on_message=self._handle_websocket_message,
                on_state_change=self._handle_websocket_state,
                on_error=self._handle_websocket_error
            )
            
            if success:
                # Wait for connection to establish
                time.sleep(2)
                
                # Subscribe to required channels
                subscriptions = [
                    WebSocketSubscription(channel=WebSocketChannels.TICKER, symbol=self.config.symbol),
                    WebSocketSubscription(channel=WebSocketChannels.ORDERS),
                    WebSocketSubscription(channel=WebSocketChannels.POSITIONS)
                ]
                
                if self.exchange.subscribeWebSocket(subscriptions):
                    self.websocket_connected = True
                    return True
            
            return False
            
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            return False
    
    def _handle_websocket_message(self, message: WebSocketMessage):
        """Handle incoming WebSocket messages"""
        try:
            if message.channel == WebSocketChannels.TICKER and message.symbol == self.config.symbol:
                # Update last price from ticker
                if hasattr(message.data, 'lastPrice'):
                    self.last_websocket_price = message.data.lastPrice
                
            elif message.channel == WebSocketChannels.ORDERS:
                # Handle order update
                # BitUnix may send different formats, check multiple fields
                order_id = getattr(message.data, 'orderId', None) or getattr(message.data, 'order_id', None)
                status = getattr(message.data, 'status', None) or getattr(message.data, 'orderStatus', None)
                
                if order_id and status:
                    # Log order update for debugging
                    print(f"\\n📦 Order Update: {order_id} -> {status}")
                    
                    # Check if this is one of our grid orders
                    if order_id in self.order_manager.active_orders:
                        # BitUnix uses different status names
                        if status in ["FILLED", "FULL_FILLED", "Filled"]:
                            # Process fill
                            fill_price = getattr(message.data, 'avgPrice', None) or \
                                       getattr(message.data, 'price', None) or \
                                       getattr(message.data, 'fillPrice', None)
                            self.order_manager.update_order_status(order_id, "filled", fill_price)
                            
                            # Find corresponding grid order
                            for level in self.grid_levels:
                                if level.order_id == order_id:
                                    # Create order object for handler
                                    from .types import GridOrder
                                    order = GridOrder(
                                        grid_index=level.index,
                                        order_id=order_id,
                                        client_order_id=message.data.clientId if hasattr(message.data, 'clientId') else None,
                                        symbol=self.config.symbol,
                                        side=level.side,
                                        price=level.price,
                                        quantity=level.quantity,
                                        status="filled",
                                        created_at=level.created_at,
                                        filled_at=time.time(),
                                        fill_price=fill_price or level.price
                                    )
                                    self._handle_order_fill(order)
                                    break
                        else:
                            # Update order status
                            self.order_manager.update_order_status(order_id, status)
            
            elif message.channel == WebSocketChannels.POSITIONS and message.symbol == self.config.symbol:
                # Update position information
                if hasattr(message.data, 'size'):
                    self.websocket_positions[message.symbol] = {
                        'size': message.data.size,
                        'entryPrice': message.data.entryPrice if hasattr(message.data, 'entryPrice') else 0,
                        'markPrice': message.data.markPrice if hasattr(message.data, 'markPrice') else 0,
                        'pnl': message.data.pnl if hasattr(message.data, 'pnl') else 0
                    }
                    
                    # Update position tracker
                    self.position_tracker.position.size = message.data.size
                    if hasattr(message.data, 'entryPrice'):
                        self.position_tracker.position.entry_price = message.data.entryPrice
                    if hasattr(message.data, 'pnl'):
                        self.position_tracker.position.unrealized_pnl = message.data.pnl
        
        except Exception as e:
            print(f"\nWebSocket message processing error: {e}")
            if self.on_error:
                self.on_error(e)
    
    def _handle_websocket_state(self, state: WebSocketState):
        """Handle WebSocket state changes"""
        if state == WebSocketState.DISCONNECTED:
            print(f"\n⚠️  WebSocket disconnected")
            self.websocket_connected = False
        elif state == WebSocketState.CONNECTED:
            print(f"\n✅ WebSocket connected")
        elif state == WebSocketState.AUTHENTICATED:
            print(f"\n✅ WebSocket authenticated")
        elif state == WebSocketState.RECONNECTING:
            print(f"\n🔄 WebSocket reconnecting...")
        elif state == WebSocketState.ERROR:
            print(f"\n❌ WebSocket error")
            self.websocket_connected = False
    
    def _handle_websocket_error(self, error: Exception):
        """Handle WebSocket errors"""
        print(f"\nWebSocket error: {error}")
        if self.on_error:
            self.on_error(error)
    
    def _get_minimum_order_size(self) -> float:
        """Get minimum order size for the symbol"""
        try:
            from exchanges.utils.precision import PrecisionManager
            precision_manager = PrecisionManager(self.exchange.exchange_name)
            symbol_info = precision_manager.get_symbol_info(self.config.symbol)
            
            if symbol_info:
                return symbol_info.get('minTradeVolume', 0.0001)
            else:
                # Default minimum for BTC
                if 'BTC' in self.config.symbol:
                    return 0.0001
                else:
                    return 1.0  # Default for other assets
        except Exception as e:
            print(f"Warning: Could not get minimum order size: {e}")
            return 0.0001 if 'BTC' in self.config.symbol else 1.0
    
    def _map_existing_orders_to_grid(self, existing_orders):
        """Map existing orders to grid levels"""
        print("\\nMapping existing orders to grid levels...")
        
        # Get current price first
        current_price = self._get_current_price()
        
        # Re-assign sides based on current price to ensure proper coverage
        self.grid_levels = self.calculator._assign_order_sides(self.grid_levels, current_price)
        
        mapped_count = 0
        unmapped_orders = []
        orders_by_price = {}  # Track orders by price to avoid duplicates
        
        # First, clear any existing order IDs in grid levels
        for level in self.grid_levels:
            level.order_id = None
            level.status = "pending"
        
        # Group orders by price to handle duplicates
        for order in existing_orders:
            price_key = f"{order.side}_{order.price:.2f}"
            if price_key not in orders_by_price:
                orders_by_price[price_key] = []
            orders_by_price[price_key].append(order)
        
        # Map each unique price to its closest grid level
        for price_key, orders in orders_by_price.items():
            # Use the first order at this price (others are duplicates)
            order = orders[0]
            
            # Find the closest grid level
            closest_level = None
            min_diff = float('inf')
            
            for level in self.grid_levels:
                # Skip if this level already has an order
                if level.order_id:
                    continue
                    
                # Check if sides match
                if level.side.value != order.side:
                    continue
                
                # Calculate price difference
                price_diff = abs(level.price - order.price)
                
                # Find closest match within 0.1% tolerance
                if price_diff < min_diff and price_diff / level.price < 0.001:
                    min_diff = price_diff
                    closest_level = level
            
            if closest_level:
                # Map the order to this grid level
                closest_level.order_id = order.orderId
                closest_level.status = "active"
                self.order_manager.active_orders[order.orderId] = order
                mapped_count += 1
                print(f"Mapped {order.side} order at ${order.price:.2f} to grid level {closest_level.index}")
                
                # Cancel duplicate orders at the same price
                for dup_order in orders[1:]:
                    print(f"Cancelling duplicate {dup_order.side} order at ${dup_order.price:.2f}")
                    self.order_manager.cancel_order(dup_order.orderId)
            else:
                unmapped_orders.extend(orders)
                print(f"Warning: Could not map {order.side} order at ${order.price:.2f} to any grid level")
        
        print(f"\\nMapped {mapped_count} orders to grid levels")
        if unmapped_orders:
            print(f"Warning: {len(unmapped_orders)} orders could not be mapped")
            
        # Check for missing orders around current price and place them
        self._fill_missing_orders_around_price(current_price)
    
    def _fill_missing_orders_around_price(self, current_price: float):
        """Fill any gaps in orders around the current price"""
        print(f"\\nChecking for missing orders around current price ${current_price:.2f}...")
        
        # Find levels that should have orders but don't
        missing_levels = []
        
        for level in self.grid_levels:
            # Skip levels that already have orders
            if level.order_id:
                continue
            
            # For LONG positions:
            # - BUY orders should be below current price
            # - SELL orders should be above current price
            if self.config.position_direction == PositionDirection.LONG:
                if (level.side == OrderSide.BUY and level.price < current_price) or \
                   (level.side == OrderSide.SELL and level.price > current_price):
                    # Check distance from current price
                    price_diff_pct = abs(level.price - current_price) / current_price
                    # Skip if too close (would likely execute immediately)
                    if price_diff_pct > 0.0005:  # 0.05% minimum distance
                        missing_levels.append(level)
        
        if missing_levels:
            print(f"Found {len(missing_levels)} missing orders to place:")
            for level in missing_levels[:10]:  # Show first 10
                print(f"  Level {level.index}: {level.side.value} @ ${level.price:.2f}")
            
            # Place the missing orders
            def order_callback(order_ids, errors):
                print(f"Placed {len(order_ids)} missing orders successfully")
                if errors:
                    print(f"Errors placing missing orders: {errors}")
            
            self.order_manager.place_initial_orders(missing_levels, order_callback)
        else:
            print("No missing orders found - grid coverage is complete")
    
    def _setup_order_monitoring(self):
        """Set up monitoring for order fills"""
        print("\\nSetting up order monitoring...")
        
        # For WebSocket mode, we rely on real-time updates
        if self.use_websocket:
            print("Using WebSocket for real-time order updates")
        else:
            print("Using REST API polling for order updates")
        
        # Track all active orders
        active_count = 0
        for level in self.grid_levels:
            if level.order_id:
                active_count += 1
        
        print(f"Monitoring {active_count} active grid orders")
    
    def _verify_position_established(self, expected_size: float, expected_side: str, 
                                    max_attempts: int = 3) -> bool:
        """
        Verify that a position has been established on the exchange.
        
        Args:
            expected_size: Expected position size
            expected_side: Expected position side (BUY/SELL)
            max_attempts: Maximum verification attempts
            
        Returns:
            True if position verified, False otherwise
        """
        for attempt in range(max_attempts):
            if attempt > 0:
                print(f"Retry {attempt}/{max_attempts - 1}...")
                time.sleep(2)  # Wait before retry
            
            # Check position on exchange
            position = self._check_existing_position()
            
            if position and abs(position['size']) > 0:
                actual_size = abs(position['size'])
                actual_side = "BUY" if position['size'] > 0 else "SELL"
                
                print(f"\n📊 Position found:")
                print(f"   Size: {actual_size:.6f} (expected: {expected_size:.6f})")
                print(f"   Side: {actual_side} (expected: {expected_side})")
                print(f"   Entry Price: ${position['entry_price']:,.2f}")
                
                # For LONG positions, we expect positive size
                # For SHORT positions, we expect negative size
                side_matches = (expected_side == "BUY" and position['size'] > 0) or \
                              (expected_side == "SELL" and position['size'] < 0)
                
                # Allow for small differences due to fees/slippage
                size_tolerance = 0.1  # 10% tolerance
                size_matches = abs(actual_size - expected_size) / expected_size <= size_tolerance
                
                if side_matches:
                    if not size_matches:
                        print(f"⚠️  Warning: Position size differs from expected by more than {size_tolerance*100}%")
                    
                    # Update position tracker with actual values
                    self.position_tracker.position.size = position['size']
                    self.position_tracker.position.entry_price = position['entry_price']
                    self.position_tracker.position.unrealized_pnl = position.get('unrealized_pnl', 0)
                    
                    return True
                else:
                    print(f"❌ Position side mismatch! Expected {expected_side} but found {actual_side}")
            else:
                print(f"❌ No position found on exchange (attempt {attempt + 1}/{max_attempts})")
        
        return False