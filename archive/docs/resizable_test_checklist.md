# Resizable Components Test Checklist

## Manual Testing Steps

### 1. Basic Resizing
- [ ] Access http://localhost:3001
- [ ] Drag the vertical divider between market list and trading view
- [ ] Drag the horizontal divider between chart and order book
- [ ] Drag the vertical divider between order book and trade history
- [ ] Verify all panels resize smoothly without flickering

### 2. Layout Presets
- [ ] Click the Layout dropdown in the header
- [ ] Switch to "Trading" preset - verify sizes adjust
- [ ] Switch to "Analysis" preset - verify chart gets larger
- [ ] Switch to "Compact" preset - verify balanced layout
- [ ] Refresh the page - verify selected preset persists

### 3. Keyboard Shortcuts
- [ ] Press Cmd+Shift+L to cycle through layout presets
- [ ] Press Cmd+Shift+R to reset current layout to default sizes
- [ ] Verify shortcuts don't trigger when typing in input fields

### 4. Responsive Design
- [ ] Resize browser window to tablet size (~1024px)
- [ ] Verify panels still resize properly
- [ ] Resize to mobile size (~768px)
- [ ] Verify panels stack vertically
- [ ] Verify market list has max height on mobile
- [ ] Verify resize handles are hidden on mobile

### 5. Chart Responsiveness
- [ ] Resize the chart panel
- [ ] Verify TradingView chart resizes dynamically
- [ ] Check that chart maintains aspect ratio
- [ ] Verify no chart overflow or clipping

### 6. Content Adaptation
- [ ] Make panels very small
- [ ] Verify text sizes adjust appropriately
- [ ] Verify less important elements hide when space is constrained
- [ ] Check order book depth visualization adapts

### 7. Performance
- [ ] Rapidly resize panels
- [ ] Check for smooth performance without lag
- [ ] Monitor console for any errors
- [ ] Verify WebSocket connections remain stable

### 8. Edge Cases
- [ ] Try to resize panels to minimum size
- [ ] Try to resize panels to maximum size
- [ ] Test with multiple browser tabs open
- [ ] Test after clearing localStorage

## Known Issues to Verify Fixed
- [ ] WebSocket subscription spam
- [ ] Order 400 errors
- [ ] toFixed errors on Decimal values
- [ ] Thread creation crashes

## Browser Testing
- [ ] Chrome/Edge
- [ ] Safari
- [ ] Firefox

## Final Verification
- [ ] All panels are independently resizable
- [ ] Layout persists between sessions
- [ ] Mobile responsive design works
- [ ] No console errors
- [ ] Smooth performance