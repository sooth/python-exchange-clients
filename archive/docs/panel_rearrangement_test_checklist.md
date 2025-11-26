# Panel Rearrangement Test Checklist

## Manual Testing Steps

### 1. Basic Drag and Drop
- [ ] Access http://localhost:3001
- [ ] Hover over panel title bars to see drag handles appear
- [ ] Drag the CHART panel by its title bar
- [ ] Drop it in place of ORDER BOOK & TRADES panel
- [ ] Verify panels swap positions smoothly
- [ ] Verify resize handles still work after rearrangement

### 2. Multiple Panel Rearrangement
- [ ] Drag ORDER BOOK & TRADES back to its original position
- [ ] Drag PLACE ORDER panel to swap with POSITIONS & ORDERS
- [ ] Verify both top and bottom rows can be rearranged independently
- [ ] Verify all panels maintain their content after moving

### 3. Visual Feedback
- [ ] Start dragging a panel and observe:
  - Panel becomes semi-transparent (70% opacity)
  - Drag overlay appears showing panel name
  - Cursor changes to grabbing
  - Shadow effect appears on dragged panel
- [ ] Hover over drop zones while dragging
  - Target panel shows accent color ring
- [ ] Release to complete the drag
  - Smooth animation as panels swap

### 4. Layout Persistence
- [ ] Rearrange several panels
- [ ] Refresh the page (F5)
- [ ] Verify panel positions are preserved
- [ ] Clear localStorage and refresh
- [ ] Verify panels return to default positions

### 5. Keyboard Shortcuts
- [ ] Rearrange panels into a custom order
- [ ] Press Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows)
- [ ] Verify panels reset to original order
- [ ] Press Cmd+Shift+R to reset panel sizes
- [ ] Press Cmd+Shift+L to cycle through layout presets

### 6. Resize and Drag Integration
- [ ] Resize a panel to make it smaller
- [ ] Drag it to a new position
- [ ] Verify the size is maintained after drag
- [ ] Resize dividers between rearranged panels
- [ ] Verify resize still works correctly

### 7. Edge Cases
- [ ] Try to drag a panel while resizing (should not work)
- [ ] Try to drag panels very quickly
- [ ] Try to drop a panel on itself
- [ ] Rapidly swap panels back and forth
- [ ] All operations should be smooth without errors

### 8. Accessibility
- [ ] Use Tab key to focus on drag handles
- [ ] Use Space/Enter to activate drag
- [ ] Use arrow keys to move panel
- [ ] Use Space/Enter to drop panel
- [ ] Verify screen reader announcements (if available)

### 9. Mobile/Responsive
- [ ] Resize browser to mobile size (<768px)
- [ ] Verify drag handles are not visible
- [ ] Verify panels cannot be dragged on mobile
- [ ] Verify panels stack vertically as expected

### 10. Performance
- [ ] Monitor browser console for errors
- [ ] Check for smooth animations (60fps)
- [ ] Verify no memory leaks after multiple drags
- [ ] Verify WebSocket connections remain stable

## Expected Behavior Summary
✅ Panels can be dragged by their title bars
✅ Visual feedback during drag operations
✅ Smooth animations and transitions
✅ Layout persists between sessions
✅ Keyboard shortcuts work correctly
✅ Resize functionality unaffected
✅ Mobile experience unchanged
✅ No console errors or warnings