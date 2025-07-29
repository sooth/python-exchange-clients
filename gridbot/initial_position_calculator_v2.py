"""Initial Position Calculator V2 - Fixed for proper position sizing"""

from typing import List, Tuple, Optional
from .types import GridLevel, OrderSide, GridConfig, PositionDirection


class InitialPositionCalculatorV2:
    """
    Calculates the initial position needed when starting a grid bot.
    
    Key principle: The initial position should equal the sum of all exit orders
    to ensure the position is completely closed when all exit orders are filled.
    """
    
    def __init__(self, config: GridConfig):
        self.config = config
    
    def calculate_initial_position(self, grid_levels: List[GridLevel], current_price: float) -> Tuple[float, OrderSide, List[int]]:
        """
        Calculate the initial position to open when starting the grid bot.
        
        FIXED LOGIC:
        For LONG grids:
        - Open a LONG position equal to the sum of all SELL orders
        - This ensures when all SELL orders execute, position is fully closed
        
        For SHORT grids:
        - Open a SHORT position equal to the sum of all BUY orders  
        - This ensures when all BUY orders execute, position is fully closed
        
        For NEUTRAL grids:
        - Calculate net exposure needed based on grid distribution
        
        Args:
            grid_levels: List of all grid levels with assigned sides
            current_price: Current market price
            
        Returns:
            Tuple of (total_quantity, side, affected_grid_indices)
        """
        total_quantity = 0.0
        affected_indices = []
        
        if self.config.position_direction == PositionDirection.LONG:
            # LONG: Initial position = (Leverage × Margin)/Price - Sum of BUY orders
            # This ensures: Initial + BUYs = Total Capital and SELLs = Initial (closes at top)
            side = OrderSide.BUY
            
            # Calculate total capital in base currency
            total_capital_usd = self.config.total_investment * self.config.leverage
            total_capital_btc = total_capital_usd / current_price
            
            # Sum of all BUY orders
            buy_total = sum(level.quantity for level in grid_levels if level.side == OrderSide.BUY)
            
            # Initial position = Total capital - BUY orders
            total_quantity = total_capital_btc - buy_total
            
            # All SELL orders will be used to close the position
            for level in grid_levels:
                if level.side == OrderSide.SELL:
                    affected_indices.append(level.index)
                    
        elif self.config.position_direction == PositionDirection.SHORT:
            # SHORT: Initial position = (Leverage × Margin)/Price - Sum of SELL orders
            # This ensures: Initial + SELLs = Total Capital and BUYs = Initial (closes at bottom)
            side = OrderSide.SELL
            
            # Calculate total capital in base currency
            total_capital_usd = self.config.total_investment * self.config.leverage
            total_capital_btc = total_capital_usd / current_price
            
            # Sum of all SELL orders
            sell_total = sum(level.quantity for level in grid_levels if level.side == OrderSide.SELL)
            
            # Initial position = Total capital - SELL orders
            total_quantity = total_capital_btc - sell_total
            
            # All BUY orders will be used to close the position
            for level in grid_levels:
                if level.side == OrderSide.BUY:
                    affected_indices.append(level.index)
                    
        else:  # NEUTRAL
            # For neutral, calculate net position needed
            buy_total = sum(level.quantity for level in grid_levels if level.side == OrderSide.BUY)
            sell_total = sum(level.quantity for level in grid_levels if level.side == OrderSide.SELL)
            
            if sell_total > buy_total:
                # Need to buy the difference to balance
                side = OrderSide.BUY
                total_quantity = sell_total - buy_total
                # Affected indices are the excess SELL orders
                sell_count = sum(1 for level in grid_levels if level.side == OrderSide.SELL)
                buy_count = sum(1 for level in grid_levels if level.side == OrderSide.BUY)
                excess_sells = sell_count - buy_count
                for level in grid_levels:
                    if level.side == OrderSide.SELL and len(affected_indices) < excess_sells:
                        affected_indices.append(level.index)
            else:
                # Need to sell the difference to balance
                side = OrderSide.SELL
                total_quantity = buy_total - sell_total
                # Affected indices are the excess BUY orders
                buy_count = sum(1 for level in grid_levels if level.side == OrderSide.BUY)
                sell_count = sum(1 for level in grid_levels if level.side == OrderSide.SELL)
                excess_buys = buy_count - sell_count
                for level in grid_levels:
                    if level.side == OrderSide.BUY and len(affected_indices) < excess_buys:
                        affected_indices.append(level.index)
        
        return total_quantity, side, affected_indices
    
    def adjust_grid_quantities_for_balance(self, grid_levels: List[GridLevel], current_price: float) -> List[GridLevel]:
        """
        Adjust grid quantities to ensure proper balance.
        For LONG: SELL quantities should sum to initial position
        For SHORT: BUY quantities should sum to initial position
        """
        # First calculate initial position
        initial_qty, side, _ = self.calculate_initial_position(grid_levels, current_price)
        
        if self.config.position_direction == PositionDirection.LONG:
            # Adjust SELL orders to sum to initial position
            sell_orders = [l for l in grid_levels if l.side == OrderSide.SELL]
            if sell_orders and initial_qty > 0:
                # Distribute initial position across SELL orders
                # Use a minimum quantity of 0.001 for BitUnix
                min_qty = 0.001
                qty_per_sell = max(initial_qty / len(sell_orders), min_qty)
                
                # Assign quantities, handling rounding
                remaining = initial_qty
                for i, level in enumerate(sell_orders):
                    if i < len(sell_orders) - 1:
                        level.quantity = round(qty_per_sell, self._get_quantity_precision())
                        remaining -= level.quantity
                    else:
                        # Last order gets the remainder to ensure exact sum
                        level.quantity = round(remaining, self._get_quantity_precision())
        
        elif self.config.position_direction == PositionDirection.SHORT:
            # Adjust BUY orders to sum to initial position
            buy_orders = [l for l in grid_levels if l.side == OrderSide.BUY]
            if buy_orders and initial_qty > 0:
                # Distribute initial position across BUY orders
                # Use a minimum quantity of 0.001 for BitUnix
                min_qty = 0.001
                qty_per_buy = max(initial_qty / len(buy_orders), min_qty)
                
                # Assign quantities, handling rounding
                remaining = initial_qty
                for i, level in enumerate(buy_orders):
                    if i < len(buy_orders) - 1:
                        level.quantity = round(qty_per_buy, self._get_quantity_precision())
                        remaining -= level.quantity
                    else:
                        # Last order gets the remainder to ensure exact sum
                        level.quantity = round(remaining, self._get_quantity_precision())
        
        return grid_levels
    
    def _get_quantity_precision(self) -> int:
        """Get quantity precision (default to 4 decimal places)"""
        return 4
    
    def verify_position_closure(self, grid_levels: List[GridLevel], initial_quantity: float, initial_side: OrderSide, current_price: float) -> dict:
        """
        Verify that the initial position will be completely closed when all orders execute.
        
        Args:
            grid_levels: List of all grid levels
            initial_quantity: Initial position quantity
            initial_side: Initial position side (BUY or SELL)
            
        Returns:
            Dictionary with verification results
        """
        # Calculate total quantities by side
        total_buy_orders = sum(level.quantity for level in grid_levels if level.side == OrderSide.BUY)
        total_sell_orders = sum(level.quantity for level in grid_levels if level.side == OrderSide.SELL)
        
        # Add initial position to appropriate side
        if initial_side == OrderSide.BUY:
            total_buy_quantity = initial_quantity + total_buy_orders
            total_sell_quantity = total_sell_orders
        else:
            total_buy_quantity = total_buy_orders
            total_sell_quantity = initial_quantity + total_sell_orders
        
        # Calculate expected totals based on formula
        total_capital_usd = self.config.total_investment * self.config.leverage
        total_capital_btc = total_capital_usd / current_price
        
        # Check different balances
        if self.config.position_direction == PositionDirection.LONG:
            # For LONG: Initial + BUYs should equal total capital
            capital_balance = abs((initial_quantity + total_buy_orders) - total_capital_btc) < 0.0001
            # SELLs should equal initial position
            exit_balance = abs(total_sell_orders - initial_quantity) < 0.0001
            is_balanced = capital_balance and exit_balance
            net_position = initial_quantity + total_buy_orders - total_sell_orders
        else:
            # For SHORT: Initial + SELLs should equal total capital
            capital_balance = abs((initial_quantity + total_sell_orders) - total_capital_btc) < 0.0001
            # BUYs should equal initial position
            exit_balance = abs(total_buy_orders - initial_quantity) < 0.0001
            is_balanced = capital_balance and exit_balance
            net_position = total_sell_orders - initial_quantity - total_buy_orders
        
        return {
            'initial_position': {
                'side': initial_side.value,
                'quantity': initial_quantity
            },
            'grid_orders': {
                'total_buy_orders': total_buy_orders,
                'total_sell_orders': total_sell_orders
            },
            'final_totals': {
                'total_buy_quantity': total_buy_quantity,
                'total_sell_quantity': total_sell_quantity
            },
            'capital_deployment': {
                'total_capital_usd': total_capital_usd,
                'total_capital_btc': total_capital_btc,
                'capital_balance': capital_balance,
                'exit_balance': exit_balance
            },
            'net_position': net_position,
            'is_balanced': is_balanced,
            'explanation': self._get_verification_explanation(is_balanced, net_position, self.config.position_direction)
        }
    
    def _get_verification_explanation(self, is_balanced: bool, net_position: float, direction: PositionDirection) -> str:
        """Generate explanation of position verification"""
        if is_balanced:
            if direction == PositionDirection.LONG:
                return "✅ Position correctly sized: Initial + BUYs = Total Capital, SELLs = Initial Position"
            elif direction == PositionDirection.SHORT:
                return "✅ Position correctly sized: Initial + SELLs = Total Capital, BUYs = Initial Position"
            else:
                return "✅ Position correctly sized: Grid is balanced for NEUTRAL trading"
        else:
            if net_position > 0:
                return f"⚠️ Position imbalanced: {net_position:.4f} units LONG exposure will remain"
            else:
                return f"⚠️ Position imbalanced: {abs(net_position):.4f} units SHORT exposure will remain"
    
    def get_initial_position_summary(self, grid_levels: List[GridLevel], current_price: float) -> dict:
        """
        Get a detailed summary of the initial position calculation.
        
        Args:
            grid_levels: List of all grid levels
            current_price: Current market price
            
        Returns:
            Dictionary with position details
        """
        quantity, side, indices = self.calculate_initial_position(grid_levels, current_price)
        verification = self.verify_position_closure(grid_levels, quantity, side, current_price)
        
        # Calculate position value
        investment = quantity * current_price
        
        # Calculate where price is in the range
        price_range = self.config.upper_price - self.config.lower_price
        price_location = ((current_price - self.config.lower_price) / price_range) * 100
        
        # Count orders by type
        buy_orders_count = sum(1 for level in grid_levels if level.side == OrderSide.BUY)
        sell_orders_count = sum(1 for level in grid_levels if level.side == OrderSide.SELL)
        
        return {
            'position_direction': self.config.position_direction.value,
            'current_price': current_price,
            'price_location_pct': price_location,
            'initial_position': {
                'side': side.value,
                'quantity': quantity,
                'value_usd': investment,
                'explanation': self._get_explanation(side, quantity, buy_orders_count, sell_orders_count)
            },
            'grid_distribution': {
                'buy_orders': buy_orders_count,
                'sell_orders': sell_orders_count,
                'total_orders': len(grid_levels)
            },
            'verification': verification
        }
    
    def _get_explanation(self, side: OrderSide, quantity: float, buy_count: int, sell_count: int) -> str:
        """Generate human-readable explanation of the initial position"""
        direction = self.config.position_direction.value
        
        if direction == "LONG":
            if quantity == 0:
                return "No initial position needed - grid is already balanced"
            return f"Opening LONG by buying {quantity:.4f} units to match {sell_count} SELL orders that will close the position"
        elif direction == "SHORT":
            if quantity == 0:
                return f"No initial SHORT position - grid has more BUY orders ({buy_count}) than SELL orders ({sell_count})"
            elif buy_count < sell_count:
                return f"Opening SHORT by selling {quantity:.4f} units to match {buy_count} BUY orders (partial grid due to price location)"
            else:
                return f"Opening SHORT by selling {quantity:.4f} units to match {buy_count} BUY orders that will close the position"
        else:
            if side == OrderSide.BUY:
                return f"Buying {quantity:.4f} units to balance {sell_count} SELL orders vs {buy_count} BUY orders"
            else:
                return f"Selling {quantity:.4f} units to balance {buy_count} BUY orders vs {sell_count} SELL orders"