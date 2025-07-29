'use client'

import { useState, useEffect } from 'react'
import { LayoutPresets } from '@/components/layout/ResizableLayout'

const STORAGE_KEY = 'trading-layout-preset'

export function useLayoutPreset() {
  const [preset, setPreset] = useState<keyof typeof LayoutPresets>('trading')
  const [isHydrated, setIsHydrated] = useState(false)

  // Load preset from localStorage on mount
  useEffect(() => {
    const savedPreset = localStorage.getItem(STORAGE_KEY)
    if (savedPreset && savedPreset in LayoutPresets) {
      setPreset(savedPreset as keyof typeof LayoutPresets)
    }
    setIsHydrated(true)
  }, [])

  // Save preset to localStorage when it changes
  const updatePreset = (newPreset: keyof typeof LayoutPresets) => {
    setPreset(newPreset)
    if (isHydrated) {
      localStorage.setItem(STORAGE_KEY, newPreset)
      
      // Trigger a custom event to notify other components
      window.dispatchEvent(new CustomEvent('layout-preset-change', { 
        detail: { preset: newPreset } 
      }))
    }
  }

  return { preset, updatePreset }
}