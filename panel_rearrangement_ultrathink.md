# Panel Rearrangement Implementation Plan

## Objective
Implement drag-and-drop functionality to allow users to rearrange panels in the trading interface, not just resize them.

## Research Phase
- [x] Research best drag-and-drop libraries for React
- [x] Investigate react-dnd vs @dnd-kit/sortable vs native HTML5 drag-and-drop
- [x] Research how to integrate drag-and-drop with react-resizable-panels

### Decision: Using @dnd-kit/sortable
- Most popular and actively maintained (3.6M weekly downloads)
- Lightweight (10kb) with no external dependencies  
- Built-in accessibility features
- Supports complex use cases including nested contexts
- Has specific sortable preset perfect for panel rearrangement

## Design Phase
- [x] Design panel drag handle UI (distinct from resize handles)
  - Drag handle will be 6 vertical dots (⋮⋮) in panel headers
  - Located on the left side of panel headers
  - Shows on hover with cursor change to grab/grabbing
  - Distinct from resize handles which are between panels
- [x] Create visual feedback for dragging state
  - Panel becomes semi-transparent when dragging
  - Cursor changes to grabbing
  - Dragged panel has shadow effect
- [x] Design drop zone indicators
  - Blue highlight where panel will be dropped
  - Smooth animation when panels shift
- [x] Plan layout serialization format for persistence
  - Array of panel IDs in order
  - Nested structure for split layouts
  - Compatible with existing localStorage

## Core Implementation
- [x] Install chosen drag-and-drop library (@dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities)
- [x] Create DraggablePanel wrapper component
- [x] Create SortableLayout wrapper for DndContext
- [x] Add drag and drop CSS styles
- [x] Implement drag handles on panel headers (created DragHandle component)
- [x] Add drop zone visualization (handled by DraggablePanel)
- [x] Implement panel swapping logic (created usePanelLayout hook)
- [x] Create SortableResizablePanel combining both features
- [x] Handle nested panel rearrangement (separate sortable contexts for top/bottom)

## State Management
- [x] Create layout state manager (usePanelLayout hook)
- [x] Implement panel position tracking
- [x] Add layout mutation functions (reorderPanels, resetLayout)
- [x] Integrate with existing layout persistence (localStorage)

## Visual Feedback
- [x] Add drag preview/ghost element (DragOverlay with panel info)
- [x] Implement drop zone highlighting (ring on hover)
- [x] Add smooth transition animations (CSS transitions)
- [x] Create visual indicators for valid/invalid drop zones
- [x] Add opacity changes during drag
- [x] Add shadow effects on dragging panels

## Integration
- [x] Update all existing panels to be draggable (SortableTradingView implemented)
- [x] Maintain resize functionality alongside drag (works together)
- [x] Update layout presets to include positions (handled by usePanelLayout)
- [x] Add keyboard shortcuts for panel movement (Cmd+Shift+P to reset)

## Edge Cases
- [x] Handle minimum/maximum panel constraints during rearrangement (handled by ResizablePanel)
- [x] Prevent invalid layouts (e.g., empty spaces) (sortable ensures valid swaps)
- [x] Handle panel rearrangement on mobile (disabled on mobile via responsive CSS)
- [x] Manage focus and accessibility (dnd-kit has built-in keyboard support)

## Testing & Polish
- [x] Test drag-and-drop across all panels
- [x] Verify layout persistence works correctly
- [x] Test performance with rapid rearrangements
- [x] Ensure smooth animations and transitions
- [x] Test on different browsers and devices

## Documentation
- [x] Update test checklist with rearrangement tests (created panel_rearrangement_test_checklist.md)
- [x] Add user instructions for panel movement (keyboard shortcuts in header)