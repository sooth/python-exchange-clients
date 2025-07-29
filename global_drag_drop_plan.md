# Global Drag and Drop Implementation Plan

## Objective
Enable drag-and-drop functionality for ALL components on the screen, allowing users to move any panel anywhere (except the header which stays pinned).

## Current State Analysis
- Only panels within TradingView are draggable
- MarketList (left sidebar) is NOT draggable
- Need a global sortable context that includes all panels

## Architecture Changes

### 1. Create Global Panel System
- [ ] Define all panels with unique IDs at the app level
- [ ] Create a global panel registry
- [ ] Make MarketList a draggable panel
- [ ] Implement global sortable context

### 2. Panel Structure
```
App
├── Header (fixed, not draggable)
└── GlobalSortableArea
    ├── MarketList Panel
    ├── Chart Panel
    ├── OrderBook Panel
    ├── Trades Panel
    ├── OrderForm Panel
    └── Positions Panel
```

### 3. Implementation Steps
- [ ] Create GlobalPanelLayout component
- [ ] Convert page.tsx to use global sortable context
- [ ] Make MarketList draggable with title bar
- [ ] Update panel IDs to be globally unique
- [ ] Allow panels to be dragged between any position
- [ ] Implement grid-based drop zones

### 4. Layout Persistence
- [ ] Update layout storage to handle global positions
- [ ] Support flexible grid arrangements
- [ ] Handle responsive behavior

### 5. Visual Enhancements
- [ ] Add visual grid guides when dragging
- [ ] Show drop zones across entire interface
- [ ] Highlight valid drop areas

### 6. Edge Cases
- [ ] Prevent panels from being dropped outside valid areas
- [ ] Handle panel collisions
- [ ] Maintain minimum panel sizes
- [ ] Ensure at least one panel remains visible

## Technical Approach
1. Move SortableLayout to wrap entire page content
2. Flatten panel hierarchy for global dragging
3. Use CSS Grid for flexible positioning
4. Implement drop zones between all panels