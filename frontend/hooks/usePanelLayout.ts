'use client'

import { useState, useEffect, useCallback } from 'react'

interface PanelLayout {
  panels: string[]
  positions: Record<string, number>
}

const STORAGE_KEY = 'trading-panel-layout'

export function usePanelLayout(defaultPanels: string[]) {
  const getDefaultLayout = (): PanelLayout => ({
    panels: defaultPanels,
    positions: defaultPanels.reduce((acc, panel, index) => ({
      ...acc,
      [panel]: index
    }), {})
  })

  const [layout, setLayout] = useState<PanelLayout>(getDefaultLayout)
  const [isHydrated, setIsHydrated] = useState(false)

  // Load from localStorage after hydration
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        // Validate that all panels are present
        if (parsed.panels && parsed.panels.length === defaultPanels.length) {
          setLayout(parsed)
        }
      } catch (e) {
        console.error('Failed to parse saved layout:', e)
      }
    }
    setIsHydrated(true)
  }, [])

  // Save to localStorage whenever layout changes (only after hydration)
  useEffect(() => {
    if (isHydrated) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(layout))
    }
  }, [layout, isHydrated])

  // Reorder panels
  const reorderPanels = useCallback((newOrder: string[]) => {
    setLayout({
      panels: newOrder,
      positions: newOrder.reduce((acc, panel, index) => ({
        ...acc,
        [panel]: index
      }), {})
    })
  }, [])

  // Reset to default order
  const resetLayout = useCallback(() => {
    setLayout(getDefaultLayout())
  }, [defaultPanels])

  return {
    panels: layout.panels,
    positions: layout.positions,
    reorderPanels,
    resetLayout
  }
}