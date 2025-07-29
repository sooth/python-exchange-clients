# Panel Resize Implementation Plan

## Problem Statement
The current implementation uses `FlexibleGridLayout` which only supports drag-and-drop functionality but not resizing. Users need the ability to both drag panels to different positions AND resize them dynamically.

## Current State Analysis
- **Current Implementation**: CSS Grid-based layout with fixed panel sizes
- **Drag Support**: ✅ Working (using @dnd-kit)
- **Resize Support**: ❌ Not implemented
- **Existing Assets**: ResizableLayout component exists but is not used

## Recommended Solution: React Grid Layout

Based on best practices research, **react-grid-layout** is the optimal solution because it:
1. Provides both drag-and-drop AND resize functionality in one library
2. Is specifically designed for dashboard-style applications
3. Has built-in responsive breakpoints
4. Maintains excellent performance with many panels
5. Is actively maintained and widely used in 2024

## Implementation Plan

### Phase 1: Library Setup and Basic Implementation
1. **Install react-grid-layout**
   - Add react-grid-layout package
   - Import required CSS files
   - Remove @dnd-kit dependencies (no longer needed)

2. **Create GridLayoutWrapper Component**
   - Replace FlexibleGridLayout with new implementation
   - Configure grid settings (cols, rowHeight, margins)
   - Set up basic drag and resize functionality

3. **Migrate Panel Configurations**
   - Convert existing panel positions to react-grid-layout format
   - Define min/max constraints for each panel
   - Set up resize handles (se, sw, ne, nw corners)

### Phase 2: Enhanced Functionality
4. **Implement Responsive Breakpoints**
   - Use ResponsiveReactGridLayout with WidthProvider
   - Define layouts for different screen sizes (lg, md, sm, xs)
   - Ensure mobile-friendly behavior

5. **Visual Feedback and UX**
   - Style resize handles with proper hover states
   - Add visual grid guides during drag/resize
   - Implement smooth animations
   - Show panel dimensions during resize

6. **Layout Persistence**
   - Save layout changes to localStorage
   - Handle layout restoration on page load
   - Implement layout reset functionality

### Phase 3: Advanced Features
7. **View/Edit Modes**
   - Add toggle to lock/unlock layout editing
   - Disable drag/resize in view mode
   - Visual indicators for edit mode

8. **Keyboard Shortcuts**
   - Restore layout reset shortcuts
   - Add shortcuts for common layout presets
   - Implement undo/redo for layout changes

9. **Performance Optimization**
   - Implement lazy loading for panel content
   - Optimize re-renders during drag/resize
   - Add debouncing for layout saves

## Technical Details

### Grid Configuration
```javascript
{
  cols: 12,                    // 12-column grid system
  rowHeight: 30,              // Base row height in pixels
  margin: [8, 8],             // Horizontal and vertical margins
  containerPadding: [8, 8],   // Container padding
  isDraggable: true,
  isResizable: true,
  compactType: 'vertical',    // Auto-pack vertically
  preventCollision: false     // Allow overlapping during drag
}
```

### Panel Configuration Example
```javascript
{
  i: 'market-list',           // Unique ID
  x: 0,                       // Grid X position
  y: 0,                       // Grid Y position  
  w: 3,                       // Width in grid units
  h: 20,                      // Height in grid units
  minW: 2,                    // Minimum width
  maxW: 4,                    // Maximum width
  minH: 10,                   // Minimum height
  maxH: 30,                   // Maximum height
  static: false               // Can be moved/resized
}
```

### Responsive Breakpoints
```javascript
{
  lg: 1200,   // Desktop
  md: 996,    // Tablet landscape
  sm: 768,    // Tablet portrait
  xs: 480,    // Mobile
  xxs: 0      // Small mobile
}
```

## Migration Strategy

1. **Parallel Implementation**: Create new component alongside existing one
2. **Feature Parity**: Ensure all current functionality works
3. **Gradual Migration**: Test thoroughly before replacing
4. **Fallback Plan**: Keep old implementation available

## Success Criteria

- ✅ All panels can be dragged to new positions
- ✅ All panels can be resized by dragging corners/edges
- ✅ Layout changes persist across page reloads
- ✅ Responsive behavior on different screen sizes
- ✅ Smooth performance with all panels active
- ✅ Clear visual feedback during interactions
- ✅ No loss of existing functionality

## Timeline Estimate

- Phase 1: 2-3 hours (basic functionality)
- Phase 2: 2-3 hours (enhanced features)
- Phase 3: 1-2 hours (advanced features)
- Testing: 1 hour

Total: 6-9 hours for complete implementation

## Alternative Approaches Considered

1. **Modify FlexibleGridLayout**: Add resize to existing grid
   - Pros: Keeps current architecture
   - Cons: Complex implementation, reinventing the wheel

2. **Use ResizableLayout + DnD Kit**: Combine two libraries
   - Pros: Uses existing components
   - Cons: Complex integration, potential conflicts

3. **React-RnD**: Simple drag and resize
   - Pros: Easy to implement
   - Cons: Not designed for grid layouts, less features

**Conclusion**: React Grid Layout is the best choice for this use case.