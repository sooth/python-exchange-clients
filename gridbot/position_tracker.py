"""Position Tracker - Tracks positions and calculates P&L"""

import time
from typing import Dict, List, Optional, Tuple
from collections import deque
import threading

from .types import GridPosition, GridOrder, GridTrade, OrderSide


class PositionTracker:
    """Tracks positions and calculates profit/loss"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.position = GridPosition(
            symbol=symbol,
            size=0,
            entry_price=0,
            current_price=0,
            unrealized_pnl=0,
            realized_pnl=0,
            total_trades=0
        )
        
        # Trade history
        self.completed_trades: List[GridTrade] = []
        self.trade_history: deque = deque(maxlen=1000)  # Keep last 1000 trades
        
        # Order pairing for grid trades
        self.pending_buys: Dict[int, GridOrder] = {}  # grid_index -> buy order
        self.pending_sells: Dict[int, GridOrder] = {}  # grid_index -> sell order
        
        # Performance metrics
        self.total_volume = 0.0
        self.total_fees = 0.0
        self.peak_position_value = 0.0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        self.lock = threading.Lock()
    
    def update_position_from_order(self, order: GridOrder, fill_price: Optional[float] = None):
        """Update position when an order is filled"""
        with self.lock:
            price = fill_price or order.price
            quantity = order.quantity
            
            if order.side == OrderSide.BUY:
                # Increase position
                new_size = self.position.size + quantity
                if self.position.size >= 0:
                    # Adding to long position
                    total_cost = (self.position.size * self.position.entry_price) + (quantity * price)
                    self.position.entry_price = total_cost / new_size if new_size > 0 else 0
                else:
                    # Reducing short position
                    if new_size >= 0:
                        # Flipped from short to long
                        realized_pnl = (self.position.entry_price - price) * abs(self.position.size)
                        self.position.realized_pnl += realized_pnl
                        self.position.entry_price = price
                self.position.size = new_size
            
            else:  # SELL
                # Decrease position
                new_size = self.position.size - quantity
                if self.position.size > 0:
                    # Reducing long position
                    if new_size <= 0:
                        # Flipped from long to short
                        realized_pnl = (price - self.position.entry_price) * self.position.size
                        self.position.realized_pnl += realized_pnl
                        self.position.entry_price = price
                    else:
                        # Partial close
                        realized_pnl = (price - self.position.entry_price) * quantity
                        self.position.realized_pnl += realized_pnl
                else:
                    # Adding to short position
                    total_cost = (abs(self.position.size) * self.position.entry_price) + (quantity * price)
                    new_size_abs = abs(new_size)
                    self.position.entry_price = total_cost / new_size_abs if new_size_abs > 0 else 0
                self.position.size = new_size
            
            # Update volume
            self.total_volume += quantity * price
            
            # Check for grid trade completion
            self._check_grid_trade_completion(order)
    
    def _check_grid_trade_completion(self, filled_order: GridOrder):
        """Check if a grid trade is completed (buy + sell pair)"""
        if filled_order.side == OrderSide.BUY:
            # Store buy order
            self.pending_buys[filled_order.grid_index] = filled_order
            
            # Check if we have a matching sell
            if filled_order.grid_index in self.pending_sells:
                sell_order = self.pending_sells[filled_order.grid_index]
                self._record_grid_trade(filled_order, sell_order)
                del self.pending_sells[filled_order.grid_index]
        
        else:  # SELL
            # Store sell order
            self.pending_sells[filled_order.grid_index] = filled_order
            
            # Check if we have a matching buy
            if filled_order.grid_index in self.pending_buys:
                buy_order = self.pending_buys[filled_order.grid_index]
                self._record_grid_trade(buy_order, filled_order)
                del self.pending_buys[filled_order.grid_index]
    
    def _record_grid_trade(self, buy_order: GridOrder, sell_order: GridOrder):
        """Record a completed grid trade"""
        # Calculate profit
        buy_cost = buy_order.fill_price * buy_order.quantity
        sell_revenue = sell_order.fill_price * sell_order.quantity
        gross_profit = sell_revenue - buy_cost
        
        # Estimate fees (should get actual fees from exchange)
        fee_rate = 0.001  # 0.1%
        fees = (buy_cost + sell_revenue) * fee_rate
        net_profit = gross_profit - fees
        
        profit_percentage = (net_profit / buy_cost) * 100 if buy_cost > 0 else 0
        
        # Create trade record
        trade = GridTrade(
            buy_order=buy_order,
            sell_order=sell_order,
            profit=net_profit,
            profit_percentage=profit_percentage,
            completed_at=time.time()
        )
        
        self.completed_trades.append(trade)
        self.trade_history.append(trade)
        self.position.total_trades += 1
        self.total_fees += fees
    
    def update_current_price(self, price: float):
        """Update current market price and recalculate unrealized P&L"""
        with self.lock:
            self.position.current_price = price
            
            if self.position.size != 0:
                if self.position.size > 0:
                    # Long position
                    self.position.unrealized_pnl = (price - self.position.entry_price) * self.position.size
                else:
                    # Short position
                    self.position.unrealized_pnl = (self.position.entry_price - price) * abs(self.position.size)
            else:
                self.position.unrealized_pnl = 0
            
            # Update drawdown
            self._update_drawdown()
    
    def _update_drawdown(self):
        """Update drawdown metrics"""
        current_value = self.position.unrealized_pnl + self.position.realized_pnl
        
        # Update peak value
        if current_value > self.peak_position_value:
            self.peak_position_value = current_value
            self.current_drawdown = 0
        else:
            # Calculate drawdown
            self.current_drawdown = self.peak_position_value - current_value
            if self.current_drawdown > self.max_drawdown:
                self.max_drawdown = self.current_drawdown
    
    def get_position_summary(self) -> dict:
        """Get current position summary"""
        with self.lock:
            total_pnl = self.position.realized_pnl + self.position.unrealized_pnl
            position_value = abs(self.position.size) * self.position.current_price
            
            return {
                'symbol': self.symbol,
                'size': self.position.size,
                'side': 'LONG' if self.position.size > 0 else 'SHORT' if self.position.size < 0 else 'FLAT',
                'entry_price': self.position.entry_price,
                'current_price': self.position.current_price,
                'position_value': position_value,
                'unrealized_pnl': self.position.unrealized_pnl,
                'realized_pnl': self.position.realized_pnl,
                'total_pnl': total_pnl,
                'pnl_percentage': self.position.pnl_percentage,
                'total_trades': self.position.total_trades,
                'total_volume': self.total_volume,
                'total_fees': self.total_fees,
                'net_profit': total_pnl - self.total_fees
            }
    
    def get_trade_statistics(self) -> dict:
        """Get detailed trade statistics"""
        with self.lock:
            if not self.completed_trades:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'average_profit': 0,
                    'best_trade': 0,
                    'worst_trade': 0,
                    'average_duration': 0,
                    'total_grid_profit': 0
                }
            
            winning_trades = [t for t in self.completed_trades if t.profit > 0]
            losing_trades = [t for t in self.completed_trades if t.profit <= 0]
            
            profits = [t.profit for t in self.completed_trades]
            best_trade = max(profits) if profits else 0
            worst_trade = min(profits) if profits else 0
            
            # Calculate average trade duration
            durations = []
            for trade in self.completed_trades:
                duration = trade.completed_at - trade.buy_order.created_at
                durations.append(duration)
            
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                'total_trades': len(self.completed_trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': (len(winning_trades) / len(self.completed_trades) * 100) if self.completed_trades else 0,
                'average_profit': sum(profits) / len(profits) if profits else 0,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'average_duration': avg_duration,
                'total_grid_profit': sum(t.profit for t in self.completed_trades)
            }
    
    def get_recent_trades(self, limit: int = 10) -> List[GridTrade]:
        """Get recent completed trades"""
        with self.lock:
            return list(self.trade_history)[-limit:]
    
    def reset_position(self):
        """Reset position tracking (use with caution)"""
        with self.lock:
            self.position.size = 0
            self.position.entry_price = 0
            self.position.unrealized_pnl = 0
            # Keep realized P&L and trade history