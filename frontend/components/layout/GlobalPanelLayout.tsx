'use client'

import React, { ReactNode, useState, useCallback } from 'react'
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  MeasuringStrategy,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import { ResizableLayout, ResizablePanel, ResizableHandle } from './ResizableLayout'
import { SortableResizablePanel } from './SortableResizablePanel'

// Global panel IDs
export const GLOBAL_PANELS = {
  MARKET_LIST: 'global-market-list',
  CHART: 'global-chart',
  ORDERBOOK: 'global-orderbook',
  TRADES: 'global-trades',
  ORDERFORM: 'global-orderform',
  POSITIONS: 'global-positions',
}

interface GlobalPanelLayoutProps {
  children: (props: {
    panels: string[]
    renderPanel: (panelId: string) => ReactNode
  }) => ReactNode
}

export function GlobalPanelLayout({ children }: GlobalPanelLayoutProps) {
  const [panels, setPanels] = useState<string[]>(Object.values(GLOBAL_PANELS))
  const [activeId, setActiveId] = useState<string | null>(null)
  
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      setPanels((items) => {
        const oldIndex = items.indexOf(active.id as string)
        const newIndex = items.indexOf(over.id as string)
        return arrayMove(items, oldIndex, newIndex)
      })
    }
    
    setActiveId(null)
  }

  const renderPanel = useCallback((panelId: string) => {
    // This will be overridden by the parent component
    return null
  }, [])

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      measuring={{
        droppable: {
          strategy: MeasuringStrategy.Always,
        },
      }}
    >
      <SortableContext items={panels} strategy={rectSortingStrategy}>
        {children({ panels, renderPanel })}
      </SortableContext>
      
      {/* Drag overlay */}
      <DragOverlay>
        {activeId ? (
          <div className="bg-background-primary shadow-2xl border-2 border-accent-primary rounded-lg p-4 opacity-95">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-accent-primary rounded-full animate-pulse" />
              <div className="text-sm text-text-primary font-bold">
                Moving: {activeId.replace('global-', '').replace('-', ' ').toUpperCase()}
              </div>
            </div>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}