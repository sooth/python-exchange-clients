"""Grid Bot Safety Checker Module"""

from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from .types import GridConfig, PositionDirection


@dataclass
class SafetyCheckResult:
    """Result of safety check"""
    passed: bool
    warnings: list[str]
    errors: list[str]
    risk_score: float  # 0-100, higher is riskier
    liquidation_price: Optional[float] = None
    max_loss_usd: Optional[float] = None
    recommended_changes: Optional[Dict[str, Any]] = None


class GridBotSafetyChecker:
    """
    Comprehensive safety checker for grid bot configurations.
    
    Checks for:
    - Leverage risks and liquidation prices
    - Position size relative to account
    - Grid spacing appropriateness
    - Stop loss effectiveness
    - Market volatility alignment
    """
    
    # Risk thresholds
    MAX_SAFE_LEVERAGE = 20
    WARNING_LEVERAGE = 10
    MIN_GRID_SPACING_PCT = 0.1  # 0.1% minimum spacing
    MAX_POSITION_PCT_OF_EQUITY = 50  # Max 50% of account
    MIN_LIQUIDATION_DISTANCE_PCT = 5  # 5% minimum distance to liquidation
    
    def __init__(self):
        self.maintenance_margin_rates = {
            "BTCUSDT": 0.005,  # 0.5%
            "ETHUSDT": 0.01,   # 1%
            "default": 0.02    # 2% for others
        }
    
    def check_configuration(self, config: GridConfig, current_price: float, 
                          account_equity: float = None, exchange=None) -> SafetyCheckResult:
        """
        Perform comprehensive safety check on grid configuration.
        
        Args:
            config: Grid bot configuration
            current_price: Current market price
            account_equity: Total account equity (optional)
            
        Returns:
            SafetyCheckResult with warnings, errors, and recommendations
        """
        warnings = []
        errors = []
        risk_score = 0.0
        
        # 1. Check leverage
        leverage_check = self._check_leverage(config)
        warnings.extend(leverage_check["warnings"])
        errors.extend(leverage_check["errors"])
        risk_score += leverage_check["risk_score"]
        
        # 2. Calculate liquidation price
        liquidation_price = self._calculate_liquidation_price(
            config, current_price
        )
        
        # 3. Check liquidation distance
        liq_check = self._check_liquidation_distance(
            config, current_price, liquidation_price
        )
        warnings.extend(liq_check["warnings"])
        errors.extend(liq_check["errors"])
        risk_score += liq_check["risk_score"]
        
        # 4. Check grid spacing
        spacing_check = self._check_grid_spacing(config)
        warnings.extend(spacing_check["warnings"])
        errors.extend(spacing_check["errors"])
        risk_score += spacing_check["risk_score"]
        
        # 5. Check position size (if account equity provided)
        if account_equity:
            position_check = self._check_position_size(config, account_equity)
            warnings.extend(position_check["warnings"])
            errors.extend(position_check["errors"])
            risk_score += position_check["risk_score"]
        
        # 6. Check stop loss effectiveness
        sl_check = self._check_stop_loss(config, liquidation_price)
        warnings.extend(sl_check["warnings"])
        errors.extend(sl_check["errors"])
        risk_score += sl_check["risk_score"]
        
        # 7. Calculate maximum loss
        max_loss_usd = self._calculate_max_loss(config, current_price)
        
        # 8. Check minimum order sizes
        if exchange:
            min_order_check = self._check_minimum_order_sizes(
                config, current_price, exchange
            )
            warnings.extend(min_order_check["warnings"])
            errors.extend(min_order_check["errors"])
            risk_score += min_order_check["risk_score"]
        
        # 9. Generate recommendations
        recommendations = self._generate_recommendations(
            config, warnings, errors, risk_score
        )
        
        # Normalize risk score to 0-100
        risk_score = min(risk_score, 100)
        
        return SafetyCheckResult(
            passed=len(errors) == 0,
            warnings=warnings,
            errors=errors,
            risk_score=risk_score,
            liquidation_price=liquidation_price,
            max_loss_usd=max_loss_usd,
            recommended_changes=recommendations
        )
    
    def _check_leverage(self, config: GridConfig) -> Dict[str, Any]:
        """Check leverage safety"""
        warnings = []
        errors = []
        risk_score = 0
        
        if config.leverage > self.MAX_SAFE_LEVERAGE:
            errors.append(
                f"Leverage {config.leverage}x exceeds maximum safe level ({self.MAX_SAFE_LEVERAGE}x). "
                f"Risk of immediate liquidation!"
            )
            risk_score += 40
        elif config.leverage > self.WARNING_LEVERAGE:
            warnings.append(
                f"High leverage ({config.leverage}x) increases liquidation risk. "
                f"Consider reducing to {self.WARNING_LEVERAGE}x or below."
            )
            risk_score += 20
        
        # Additional penalty for extreme leverage
        if config.leverage >= 50:
            risk_score += (config.leverage - 50) * 0.5
        
        return {
            "warnings": warnings,
            "errors": errors,
            "risk_score": risk_score
        }
    
    def _calculate_liquidation_price(self, config: GridConfig, 
                                   current_price: float) -> float:
        """Calculate estimated liquidation price"""
        # Get maintenance margin rate
        mm_rate = self.maintenance_margin_rates.get(
            config.symbol, 
            self.maintenance_margin_rates["default"]
        )
        
        # Liquidation distance as percentage
        # Formula: (100% - maintenance_margin%) / leverage
        liquidation_distance_pct = (100 - mm_rate * 100) / config.leverage
        
        if config.position_direction == PositionDirection.LONG:
            # For long positions, liquidation is below entry
            liquidation_price = current_price * (1 - liquidation_distance_pct / 100)
        else:
            # For short positions, liquidation is above entry
            liquidation_price = current_price * (1 + liquidation_distance_pct / 100)
        
        return liquidation_price
    
    def _check_liquidation_distance(self, config: GridConfig, 
                                  current_price: float,
                                  liquidation_price: float) -> Dict[str, Any]:
        """Check if liquidation price is safely distant"""
        warnings = []
        errors = []
        risk_score = 0
        
        # Calculate distance percentage
        if config.position_direction == PositionDirection.LONG:
            distance_pct = ((current_price - liquidation_price) / current_price) * 100
            
            # Check if liquidation is above lower grid bound
            if liquidation_price > config.lower_price:
                errors.append(
                    f"Liquidation price ${liquidation_price:.2f} is above lower grid bound "
                    f"${config.lower_price:.2f}. Grid trading will likely fail!"
                )
                risk_score += 50
        else:
            distance_pct = ((liquidation_price - current_price) / current_price) * 100
            
            # Check if liquidation is below upper grid bound
            if liquidation_price < config.upper_price:
                errors.append(
                    f"Liquidation price ${liquidation_price:.2f} is below upper grid bound "
                    f"${config.upper_price:.2f}. Grid trading will likely fail!"
                )
                risk_score += 50
        
        # Check minimum distance
        if distance_pct < self.MIN_LIQUIDATION_DISTANCE_PCT:
            warnings.append(
                f"Liquidation distance ({distance_pct:.2f}%) is very small. "
                f"Consider reducing leverage to increase safety margin."
            )
            risk_score += 20
        
        return {
            "warnings": warnings,
            "errors": errors,
            "risk_score": risk_score
        }
    
    def _check_grid_spacing(self, config: GridConfig) -> Dict[str, Any]:
        """Check if grid spacing is appropriate"""
        warnings = []
        errors = []
        risk_score = 0
        
        # Calculate spacing percentage
        range_size = config.upper_price - config.lower_price
        grid_spacing = range_size / config.grid_count
        spacing_pct = (grid_spacing / config.lower_price) * 100
        
        if spacing_pct < self.MIN_GRID_SPACING_PCT:
            warnings.append(
                f"Grid spacing ({spacing_pct:.3f}%) is very small. "
                f"This may result in excessive trading fees. "
                f"Consider reducing grid count or widening range."
            )
            risk_score += 10
        
        # Check if too many grids
        if config.grid_count > 100:
            warnings.append(
                f"High grid count ({config.grid_count}) may be difficult to manage "
                f"and could result in many small, unprofitable trades."
            )
            risk_score += 5
        
        return {
            "warnings": warnings,
            "errors": errors,
            "risk_score": risk_score
        }
    
    def _check_position_size(self, config: GridConfig, 
                           account_equity: float) -> Dict[str, Any]:
        """Check if position size is appropriate for account"""
        warnings = []
        errors = []
        risk_score = 0
        
        # Calculate maximum position value
        max_position_value = config.total_investment * config.leverage
        position_pct = (max_position_value / account_equity) * 100
        
        if position_pct > self.MAX_POSITION_PCT_OF_EQUITY:
            warnings.append(
                f"Maximum position size (${max_position_value:.2f}) is "
                f"{position_pct:.1f}% of account equity. "
                f"Consider reducing investment or leverage."
            )
            risk_score += 15
        
        if position_pct > 80:
            errors.append(
                f"Position size is {position_pct:.1f}% of account equity. "
                f"This leaves no room for other positions or drawdown!"
            )
            risk_score += 30
        
        return {
            "warnings": warnings,
            "errors": errors,
            "risk_score": risk_score
        }
    
    def _check_stop_loss(self, config: GridConfig, 
                        liquidation_price: float) -> Dict[str, Any]:
        """Check stop loss effectiveness"""
        warnings = []
        errors = []
        risk_score = 0
        
        if not config.stop_loss:
            warnings.append(
                "No stop loss set. Consider adding one to limit maximum loss."
            )
            risk_score += 10
        else:
            # Check if stop loss protects from liquidation
            if config.position_direction == PositionDirection.LONG:
                if config.stop_loss <= liquidation_price:
                    errors.append(
                        f"Stop loss ${config.stop_loss:.2f} is at or below "
                        f"liquidation price ${liquidation_price:.2f}. "
                        f"Stop loss won't protect from liquidation!"
                    )
                    risk_score += 25
            else:  # SHORT
                if config.stop_loss >= liquidation_price:
                    errors.append(
                        f"Stop loss ${config.stop_loss:.2f} is at or above "
                        f"liquidation price ${liquidation_price:.2f}. "
                        f"Stop loss won't protect from liquidation!"
                    )
                    risk_score += 25
        
        return {
            "warnings": warnings,
            "errors": errors,
            "risk_score": risk_score
        }
    
    def _calculate_max_loss(self, config: GridConfig, 
                          current_price: float) -> float:
        """Calculate maximum potential loss"""
        if not config.stop_loss:
            # If no stop loss, max loss is total investment
            return config.total_investment
        
        # Calculate loss percentage at stop loss
        if config.position_direction == PositionDirection.LONG:
            loss_pct = ((current_price - config.stop_loss) / current_price) * 100
        else:
            loss_pct = ((config.stop_loss - current_price) / current_price) * 100
        
        # Maximum loss is the leveraged loss
        max_loss = config.total_investment * (loss_pct / 100) * config.leverage
        
        # Cap at total investment (can't lose more than invested)
        return min(abs(max_loss), config.total_investment)
    
    def _generate_recommendations(self, config: GridConfig, 
                                warnings: list, errors: list,
                                risk_score: float) -> Dict[str, Any]:
        """Generate recommended configuration changes"""
        recommendations = {}
        
        # High leverage recommendation
        if config.leverage > self.MAX_SAFE_LEVERAGE:
            recommendations["leverage"] = min(self.MAX_SAFE_LEVERAGE, 10)
        
        # Grid count recommendation
        if config.grid_count > 100:
            recommendations["grid_count"] = 50
        
        # Stop loss recommendation
        if not config.stop_loss:
            if config.position_direction == PositionDirection.LONG:
                recommendations["stop_loss"] = config.lower_price * 0.95
            else:
                recommendations["stop_loss"] = config.upper_price * 1.05
        
        # Risk score based recommendations
        if risk_score > 70:
            recommendations["action"] = "DO_NOT_START"
            recommendations["reason"] = "Configuration is extremely risky"
        elif risk_score > 50:
            recommendations["action"] = "MODIFY_REQUIRED"
            recommendations["reason"] = "Configuration needs modification to reduce risk"
        elif risk_score > 30:
            recommendations["action"] = "PROCEED_WITH_CAUTION"
            recommendations["reason"] = "Configuration has moderate risk"
        else:
            recommendations["action"] = "SAFE_TO_PROCEED"
            recommendations["reason"] = "Configuration appears reasonable"
        
        return recommendations
    
    def _check_minimum_order_sizes(self, config: GridConfig, 
                                  current_price: float,
                                  exchange) -> Dict[str, Any]:
        """Check if calculated order sizes meet exchange minimums"""
        warnings = []
        errors = []
        risk_score = 0
        
        # Get symbol info
        try:
            from exchanges.utils.precision import SymbolPrecisionManager
            # BitUnix uses hardcoded "BitUnix" string for precision manager
            precision_manager = SymbolPrecisionManager.get_instance("BitUnix")
            symbol_info = precision_manager.get_symbol_info(config.symbol)
            
            if not symbol_info:
                warnings.append(
                    f"Could not verify minimum order size for {config.symbol}"
                )
                return {
                    "warnings": warnings,
                    "errors": errors,
                    "risk_score": risk_score
                }
            
            min_qty = symbol_info.get('minTradeVolume', 0.0001)
            
            # Calculate position sizes
            # Initial position calculation
            price_position_pct = ((current_price - config.lower_price) / 
                                (config.upper_price - config.lower_price)) * 100
            
            # Estimate grids above current price (for LONG, these would be SELL orders)
            grids_above = int(config.grid_count * (100 - price_position_pct) / 100)
            
            # Calculate per-grid investment with leverage
            per_grid_value = (config.total_investment * config.leverage) / config.grid_count
            
            # Calculate quantity per grid at average price
            avg_price = (config.upper_price + config.lower_price) / 2
            qty_per_grid = per_grid_value / avg_price
            
            # Check grid order sizes
            if qty_per_grid < min_qty:
                errors.append(
                    f"Grid order size ({qty_per_grid:.6f} {config.symbol.replace('USDT', '')}) "
                    f"is below exchange minimum ({min_qty} {config.symbol.replace('USDT', '')}). "
                    f"Bot cannot place orders!"
                )
                risk_score += 50
                
                # Calculate minimum investment needed
                min_investment_needed = (min_qty * avg_price * config.grid_count) / config.leverage
                errors.append(
                    f"Minimum investment needed: ${min_investment_needed:.2f} "
                    f"(or reduce grid count to {int(config.total_investment * config.leverage / (min_qty * avg_price))})"
                )
            
            # Check initial position size
            if grids_above > 0:
                initial_position_size = grids_above * qty_per_grid
                if initial_position_size < min_qty:
                    errors.append(
                        f"Initial position size ({initial_position_size:.6f} {config.symbol.replace('USDT', '')}) "
                        f"is below exchange minimum. Cannot establish initial position!"
                    )
                    risk_score += 50
            
        except Exception as e:
            warnings.append(f"Could not check minimum order sizes: {str(e)}")
        
        return {
            "warnings": warnings,
            "errors": errors,
            "risk_score": risk_score
        }
    
    def format_safety_report(self, result: SafetyCheckResult, 
                           current_price: float) -> str:
        """Format safety check result as readable report"""
        report = []
        report.append("\n" + "="*60)
        report.append("GRID BOT SAFETY CHECK REPORT")
        report.append("="*60)
        
        # Risk score with color coding
        risk_level = "LOW" if result.risk_score < 30 else \
                    "MODERATE" if result.risk_score < 50 else \
                    "HIGH" if result.risk_score < 70 else "EXTREME"
        
        report.append(f"\n📊 Overall Risk Score: {result.risk_score:.1f}/100 ({risk_level})")
        
        if result.liquidation_price:
            report.append(f"💀 Liquidation Price: ${result.liquidation_price:,.2f}")
            distance_pct = abs((current_price - result.liquidation_price) / current_price * 100)
            report.append(f"   Distance from current: {distance_pct:.2f}%")
        
        if result.max_loss_usd:
            report.append(f"💸 Maximum Potential Loss: ${result.max_loss_usd:.2f}")
        
        # Errors (critical issues)
        if result.errors:
            report.append("\n❌ CRITICAL ISSUES:")
            for error in result.errors:
                report.append(f"   • {error}")
        
        # Warnings
        if result.warnings:
            report.append("\n⚠️  WARNINGS:")
            for warning in result.warnings:
                report.append(f"   • {warning}")
        
        # Recommendations
        if result.recommended_changes:
            report.append("\n💡 RECOMMENDATIONS:")
            action = result.recommended_changes.get("action", "")
            reason = result.recommended_changes.get("reason", "")
            
            report.append(f"   Action: {action}")
            report.append(f"   Reason: {reason}")
            
            # Specific parameter recommendations
            for key, value in result.recommended_changes.items():
                if key not in ["action", "reason"]:
                    report.append(f"   • Change {key} to {value}")
        
        # Final verdict
        report.append("\n" + "="*60)
        if result.passed:
            if result.risk_score < 30:
                report.append("✅ VERDICT: Configuration is SAFE to use")
            else:
                report.append("⚠️  VERDICT: Configuration is ACCEPTABLE but has risks")
        else:
            report.append("❌ VERDICT: Configuration is UNSAFE - DO NOT PROCEED")
        report.append("="*60)
        
        return "\n".join(report)