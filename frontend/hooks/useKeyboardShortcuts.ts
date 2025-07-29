'use client'

import { useEffect } from 'react'

interface ShortcutHandlers {
  onResetLayout?: () => void
  onToggleFullscreen?: () => void
  onCycleLayout?: () => void
  onResetPanelOrder?: () => void
}

export function useKeyboardShortcuts(handlers: ShortcutHandlers) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check if user is typing in an input
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        return
      }

      // Cmd/Ctrl + Shift + R: Reset layout
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'R') {
        e.preventDefault()
        handlers.onResetLayout?.()
      }

      // Cmd/Ctrl + Shift + F: Toggle fullscreen for focused panel
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'F') {
        e.preventDefault()
        handlers.onToggleFullscreen?.()
      }

      // Cmd/Ctrl + Shift + L: Cycle through layouts
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'L') {
        e.preventDefault()
        handlers.onCycleLayout?.()
      }

      // Cmd/Ctrl + Shift + P: Reset panel order
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'P') {
        e.preventDefault()
        handlers.onResetPanelOrder?.()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handlers])
}