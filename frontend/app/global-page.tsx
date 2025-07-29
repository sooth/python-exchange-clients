'use client'

import React, { useState, useCallback } from 'react'
import { Header } from '@/components/layout/Header'
import { GridLayoutWrapper } from '@/components/layout/GridLayoutWrapper'
import { ForceDefaults } from '@/components/ForceDefaults'

const EDIT_MODE_KEY = 'trading-grid-edit-mode'

export default function GlobalPage() {
  const [editMode, setEditMode] = useState(() => {
    // Load from localStorage
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(EDIT_MODE_KEY)
      return saved ? saved === 'true' : true
    }
    return true
  })
  
  const [resetTrigger, setResetTrigger] = useState(0)
  
  const toggleEditMode = useCallback(() => {
    setEditMode(prev => !prev)
  }, [])
  
  const handleResetLayout = useCallback(() => {
    setResetTrigger(prev => prev + 1)
  }, [])
  
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <ForceDefaults />
      <Header 
        editMode={editMode}
        onToggleEditMode={toggleEditMode}
        onResetLayout={handleResetLayout}
      />
      {/* Grid layout with resize and drag */}
      <div className="flex-1 overflow-hidden">
        <GridLayoutWrapper 
          editMode={editMode}
          onEditModeChange={setEditMode}
          resetTrigger={resetTrigger}
        />
      </div>
    </div>
  )
}