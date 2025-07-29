"""Risk Manager - Handles risk management and safety controls"""

import time
from typing import Optional, Callable, List
import threading

from .types import GridConfig, GridPosition, GridStats


class RiskManager:
    """Manages risk controls for the grid bot"""
    
    def __init__(self, config: GridConfig):
        self.config = config
        self.risk_triggered = False
        self.risk_reason = ""
        
        # Risk callbacks
        self.stop_loss_callback: Optional[Callable] = None
        self.take_profit_callback: Optional[Callable] = None
        self.drawdown_callback: Optional[Callable] = None
        
        # Risk monitoring
        self.monitoring_active = True
        self.check_interval = 1.0  # Check every second
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Risk limits
        self.consecutive_losses = 0
        self.max_consecutive_losses = 5
        
        # Circuit breakers
        self.circuit_breaker_triggered = False
        self.circuit_breaker_cooldown = 300  # 5 minutes
        self.circuit_breaker_trigger_time = 0
    
    def start_monitoring(self, position_tracker, stats: GridStats):
        """Start risk monitoring thread"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(position_tracker, stats),
            daemon=True
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop risk monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self, position_tracker, stats: GridStats):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Get current position
                position_summary = position_tracker.get_position_summary()
                
                # Check various risk conditions
                self._check_stop_loss(position_summary)
                self._check_take_profit(position_summary)
                self._check_drawdown(stats)
                self._check_position_size(position_summary)
                self._check_circuit_breaker()
                
            except Exception as e:
                print(f"Risk monitor error: {e}")
            
            time.sleep(self.check_interval)
    
    def _check_stop_loss(self, position_summary: dict):
        """Check if stop loss is triggered"""
        if not self.config.stop_loss or self.risk_triggered:
            return
        
        current_price = position_summary['current_price']
        position_size = position_summary['size']
        
        if position_size > 0 and current_price <= self.config.stop_loss:
            # Long position hit stop loss
            self.risk_triggered = True
            self.risk_reason = f"Stop loss triggered at {current_price}"
            if self.stop_loss_callback:
                self.stop_loss_callback(current_price)
        
        elif position_size < 0 and current_price >= self.config.stop_loss:
            # Short position hit stop loss
            self.risk_triggered = True
            self.risk_reason = f"Stop loss triggered at {current_price}"
            if self.stop_loss_callback:
                self.stop_loss_callback(current_price)
    
    def _check_take_profit(self, position_summary: dict):
        """Check if take profit is triggered"""
        if not self.config.take_profit or self.risk_triggered:
            return
        
        total_pnl = position_summary['total_pnl']
        position_value = position_summary['position_value']
        
        if position_value > 0:
            pnl_percentage = (total_pnl / position_value) * 100
            
            if pnl_percentage >= self.config.take_profit:
                self.risk_triggered = True
                self.risk_reason = f"Take profit triggered at {pnl_percentage:.2f}%"
                if self.take_profit_callback:
                    self.take_profit_callback(pnl_percentage)
    
    def _check_drawdown(self, stats: GridStats):
        """Check if maximum drawdown is exceeded"""
        if not self.config.max_drawdown_percentage or self.risk_triggered:
            return
        
        if stats.total_profit < 0:
            drawdown_pct = abs(stats.current_drawdown / stats.total_profit) * 100
            
            if drawdown_pct >= self.config.max_drawdown_percentage:
                self.risk_triggered = True
                self.risk_reason = f"Maximum drawdown exceeded: {drawdown_pct:.2f}%"
                if self.drawdown_callback:
                    self.drawdown_callback(drawdown_pct)
    
    def _check_position_size(self, position_summary: dict):
        """Check if position size exceeds maximum"""
        if not self.config.max_position_size:
            return
        
        position_value = position_summary['position_value']
        
        if position_value > self.config.max_position_size:
            # This doesn't stop the bot but could trigger position reduction
            print(f"Warning: Position size ${position_value:.2f} exceeds maximum ${self.config.max_position_size}")
    
    def _check_circuit_breaker(self):
        """Check if circuit breaker should be reset"""
        if self.circuit_breaker_triggered:
            time_since_trigger = time.time() - self.circuit_breaker_trigger_time
            if time_since_trigger >= self.circuit_breaker_cooldown:
                self.circuit_breaker_triggered = False
                self.consecutive_losses = 0
    
    def record_trade_result(self, profit: float):
        """Record trade result for risk tracking"""
        if profit < 0:
            self.consecutive_losses += 1
            
            if self.consecutive_losses >= self.max_consecutive_losses:
                self.trigger_circuit_breaker("Maximum consecutive losses reached")
        else:
            self.consecutive_losses = 0
    
    def trigger_circuit_breaker(self, reason: str):
        """Trigger circuit breaker to pause trading"""
        self.circuit_breaker_triggered = True
        self.circuit_breaker_trigger_time = time.time()
        self.risk_reason = f"Circuit breaker: {reason}"
        print(f"Circuit breaker triggered: {reason}")
    
    def check_order_placement_allowed(self) -> tuple[bool, str]:
        """
        Check if new orders can be placed
        
        Returns:
            Tuple of (allowed, reason)
        """
        if self.risk_triggered:
            return False, f"Risk triggered: {self.risk_reason}"
        
        if self.circuit_breaker_triggered:
            return False, f"Circuit breaker active: {self.risk_reason}"
        
        return True, ""
    
    def check_market_conditions(self, volatility: float, volume: float) -> tuple[bool, str]:
        """
        Check if market conditions are suitable for trading
        
        Args:
            volatility: Current market volatility
            volume: Current trading volume
            
        Returns:
            Tuple of (suitable, reason)
        """
        # Check volatility
        if volatility > 50:  # 50% daily volatility
            return False, "Market too volatile"
        
        if volatility < 0.5:  # 0.5% daily volatility
            return False, "Market too quiet"
        
        # Check volume (example threshold)
        min_volume = 100000  # $100k daily volume
        if volume < min_volume:
            return False, f"Insufficient volume: ${volume:.0f}"
        
        return True, ""
    
    def calculate_position_sizing(self, account_balance: float, current_risk: float) -> float:
        """
        Calculate safe position size based on risk parameters
        
        Args:
            account_balance: Total account balance
            current_risk: Current risk level (0-1)
            
        Returns:
            Recommended position size
        """
        # Base position size is total investment from config
        base_size = self.config.total_investment
        
        # Apply risk-based scaling
        if current_risk > 0.8:
            # High risk - reduce position
            position_size = base_size * 0.5
        elif current_risk > 0.6:
            # Medium risk - slightly reduce
            position_size = base_size * 0.75
        else:
            # Normal risk
            position_size = base_size
        
        # Never exceed account balance
        max_allowed = account_balance * 0.9  # Keep 10% reserve
        position_size = min(position_size, max_allowed)
        
        # Apply maximum position size limit
        if self.config.max_position_size:
            position_size = min(position_size, self.config.max_position_size)
        
        return position_size
    
    def get_risk_status(self) -> dict:
        """Get current risk status"""
        return {
            'risk_triggered': self.risk_triggered,
            'risk_reason': self.risk_reason,
            'circuit_breaker_active': self.circuit_breaker_triggered,
            'consecutive_losses': self.consecutive_losses,
            'monitoring_active': self.monitoring_active
        }
    
    def reset_risk_triggers(self):
        """Reset risk triggers (use with caution)"""
        self.risk_triggered = False
        self.risk_reason = ""
        self.circuit_breaker_triggered = False
        self.consecutive_losses = 0