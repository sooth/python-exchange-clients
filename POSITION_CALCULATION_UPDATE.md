# Grid Bot Initial Position Calculation Update

## Problem Statement

The original initial position calculation had a fundamental flaw:
- For LONG positions, it opened a position equal to the number of grid levels ABOVE current price
- However, these levels would have SELL orders placed on them
- This resulted in an imbalanced position where the total BUYs ≠ total SELLs

### Example (LONG position)
- Current price: $115,312
- Grid: 14 BUY orders below, 36 SELL orders above
- OLD: Opens 0.036 BTC (matching grid count above)
- Result: 0.036 initial + 0.014 BUYs = 0.050 total BUY vs 0.036 SELL
- **Problem**: 0.014 BTC remains after all orders execute!

## Solution

The new calculator (`initial_position_calculator_v2.py`) implements correct logic:

### For LONG positions
```
Initial position = Total SELL quantity - Total BUY quantity
```
This ensures: Initial + Grid BUYs = Grid SELLs

### For SHORT positions
```
If SELLs > BUYs:
    Initial position = Total BUY quantity (partial grid)
Else:
    Initial position = 0 (cannot maintain SHORT)
```

## Key Changes

1. **File**: `gridbot/initial_position_calculator_v2.py`
   - Complete rewrite of position calculation logic
   - Added position verification to ensure balanced grids
   - Better handling of edge cases (e.g., SHORT with more BUYs than SELLs)

2. **File**: `gridbot/core.py`
   - Updated import to use new calculator: `from .initial_position_calculator_v2 import InitialPositionCalculatorV2 as InitialPositionCalculator`

3. **Test Files**:
   - `test_position_calculation.py` - Compares old vs new calculation
   - `test_gridbot_new_calc.py` - Full workflow test with new calculator

## Results

### LONG Position Example
- Grid: 14 BUYs @ 0.001 each, 36 SELLs @ 0.001 each
- Initial position: BUY 0.022 BTC
- Total after all BUYs: 0.022 + 0.014 = 0.036 BTC
- Total SELLs: 0.036 BTC
- **Result**: Position closes perfectly to 0!

### SHORT Position Example  
- When BUYs > SELLs: No initial position (cannot maintain SHORT)
- When SELLs > BUYs: Partial grid matching BUY orders only

## Usage

The new calculator is automatically used by the grid bot. No configuration changes needed.

## Testing

Run the test scripts to verify:
```bash
# Compare old vs new calculation
python test_position_calculation.py

# Test full workflow
python test_gridbot_new_calc.py
```