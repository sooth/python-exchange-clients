"""Initial Position Calculator V3 - Proper leverage-based calculation"""

from typing import List, Tuple, Optional
from .types import GridLevel, OrderSide, GridConfig, PositionDirection


class InitialPositionCalculatorV3:
    """
    Calculates initial position and grid quantities for leveraged trading.
    
    Key principle: Deploy all available capital (margin × leverage) across the grid
    while ensuring the position closes to 0 when all orders execute.
    """
    
    def __init__(self, config: GridConfig):
        self.config = config
    
    def calculate_grid_with_leverage(self, grid_levels: List[GridLevel], current_price: float) -> Tuple[float, List[GridLevel]]:
        """
        Calculate initial position and adjust all grid quantities to use full leveraged capital.
        
        For LONG positions:
        - Scale all order quantities proportionally to use full capital
        - Initial position ensures total deployment = margin × leverage
        
        Returns:
            Tuple of (initial_position_quantity, updated_grid_levels)
        """
        # Calculate total leveraged capital
        total_capital_usd = self.config.total_investment * self.config.leverage
        total_capital_btc = total_capital_usd / current_price
        
        # Count orders by side
        buy_orders = [l for l in grid_levels if l.side == OrderSide.BUY]
        sell_orders = [l for l in grid_levels if l.side == OrderSide.SELL]
        
        if self.config.position_direction == PositionDirection.LONG:
            # For LONG: We want Initial + BUYs = SELLs (so position closes to 0)
            # And: Initial + BUYs = Total Capital (to use all leverage)
            # Therefore: SELLs = Total Capital
            
            # If grid is balanced (equal BUYs and SELLs)
            if len(buy_orders) == len(sell_orders):
                # Each SELL order quantity
                qty_per_sell = total_capital_btc / len(sell_orders)
                # Each BUY order quantity (same as SELL for balanced grid)
                qty_per_buy = qty_per_sell
                # No initial position needed for balanced grid
                initial_position = 0.0
                initial_side = OrderSide.BUY
            else:
                # Handle imbalanced grids
                # We need: Initial + sum(BUYs) = sum(SELLs)
                # And: Initial + sum(BUYs) = Total Capital
                # So: sum(SELLs) = Total Capital
                
                qty_per_sell = total_capital_btc / len(sell_orders) if sell_orders else 0
                
                # Now calculate BUY quantities and initial position
                if buy_orders:
                    # We want: Initial + sum(BUYs) = sum(SELLs)
                    total_sells = qty_per_sell * len(sell_orders)
                    # Distribute the sells amount across initial + buys
                    # Let's use equal quantities for BUYs
                    qty_per_buy = min(total_sells / (len(buy_orders) + 1), total_capital_btc / len(buy_orders))
                    total_buys = qty_per_buy * len(buy_orders)
                    initial_position = total_sells - total_buys
                else:
                    qty_per_buy = 0
                    initial_position = total_capital_btc
                
                initial_side = OrderSide.BUY
            
            # Update grid quantities
            for level in buy_orders:
                level.quantity = round(max(qty_per_buy, 0.001), 4)
            for level in sell_orders:
                level.quantity = round(max(qty_per_sell, 0.001), 4)
                
        elif self.config.position_direction == PositionDirection.SHORT:
            # For SHORT: We want Initial + SELLs = BUYs (so position closes to 0)
            # And: Initial + SELLs = Total Capital (to use all leverage)
            # Therefore: BUYs = Total Capital
            
            if len(buy_orders) == len(sell_orders):
                # Balanced grid
                qty_per_buy = total_capital_btc / len(buy_orders)
                qty_per_sell = qty_per_buy
                initial_position = 0.0
                initial_side = OrderSide.SELL
            else:
                # Imbalanced grid
                qty_per_buy = total_capital_btc / len(buy_orders) if buy_orders else 0
                
                if sell_orders:
                    total_buys = qty_per_buy * len(buy_orders)
                    qty_per_sell = min(total_buys / (len(sell_orders) + 1), total_capital_btc / len(sell_orders))
                    total_sells = qty_per_sell * len(sell_orders)
                    initial_position = total_buys - total_sells
                else:
                    qty_per_sell = 0
                    initial_position = total_capital_btc
                
                initial_side = OrderSide.SELL
            
            # Update grid quantities
            for level in buy_orders:
                level.quantity = round(max(qty_per_buy, 0.001), 4)
            for level in sell_orders:
                level.quantity = round(max(qty_per_sell, 0.001), 4)
                
        else:  # NEUTRAL
            # For neutral grids, distribute capital equally
            total_orders = len(grid_levels)
            qty_per_order = total_capital_btc / total_orders if total_orders else 0
            
            for level in grid_levels:
                level.quantity = round(max(qty_per_order, 0.001), 4)
            
            # Calculate net position needed
            buy_total = sum(l.quantity for l in buy_orders)
            sell_total = sum(l.quantity for l in sell_orders)
            
            if sell_total > buy_total:
                initial_position = sell_total - buy_total
                initial_side = OrderSide.BUY
            else:
                initial_position = buy_total - sell_total
                initial_side = OrderSide.SELL
        
        return (initial_position, initial_side), grid_levels
    
    def verify_calculations(self, grid_levels: List[GridLevel], initial_qty: float, initial_side: OrderSide, current_price: float) -> dict:
        """Verify the calculations are correct"""
        buy_orders = [l for l in grid_levels if l.side == OrderSide.BUY]
        sell_orders = [l for l in grid_levels if l.side == OrderSide.SELL]
        
        buy_total = sum(l.quantity for l in buy_orders)
        sell_total = sum(l.quantity for l in sell_orders)
        
        total_capital_usd = self.config.total_investment * self.config.leverage
        total_capital_btc = total_capital_usd / current_price
        
        if self.config.position_direction == PositionDirection.LONG:
            capital_deployed = initial_qty + buy_total
            will_close_to_zero = abs((initial_qty + buy_total) - sell_total) < 0.0001
        else:
            capital_deployed = initial_qty + sell_total
            will_close_to_zero = abs((initial_qty + sell_total) - buy_total) < 0.0001
        
        return {
            'total_capital_usd': total_capital_usd,
            'total_capital_btc': total_capital_btc,
            'initial_position': {
                'side': initial_side.value,
                'quantity': initial_qty
            },
            'grid_totals': {
                'buy_total': buy_total,
                'sell_total': sell_total,
                'total_orders': len(grid_levels)
            },
            'capital_deployed': capital_deployed,
            'capital_utilization': (capital_deployed / total_capital_btc * 100) if total_capital_btc > 0 else 0,
            'will_close_to_zero': will_close_to_zero,
            'final_position': initial_qty + buy_total - sell_total if self.config.position_direction == PositionDirection.LONG else sell_total - buy_total - initial_qty
        }