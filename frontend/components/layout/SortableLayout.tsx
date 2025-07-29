'use client'

import { ReactNode, useState, useEffect } from 'react'
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
  verticalListSortingStrategy,
  horizontalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'

interface SortableLayoutProps {
  children: ReactNode
  items: string[]
  onReorder: (newOrder: string[]) => void
  direction?: 'horizontal' | 'vertical'
}

export function SortableLayout({
  children,
  items,
  onReorder,
  direction = 'horizontal'
}: SortableLayoutProps) {
  const [activeId, setActiveId] = useState<string | null>(null)
  
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // Require 8px drag before activating to prevent accidental drags
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const strategy = direction === 'horizontal' 
    ? horizontalListSortingStrategy 
    : verticalListSortingStrategy

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      const oldIndex = items.indexOf(active.id as string)
      const newIndex = items.indexOf(over.id as string)
      
      const newOrder = arrayMove(items, oldIndex, newIndex)
      onReorder(newOrder)
    }
    
    setActiveId(null)
  }

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
      <SortableContext items={items} strategy={strategy}>
        {children}
      </SortableContext>
      
      {/* Drag overlay for better visual feedback */}
      <DragOverlay>
        {activeId ? (
          <div className="bg-background-primary shadow-2xl border border-accent-primary rounded-lg p-3 opacity-90">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-accent-primary rounded-full animate-pulse" />
              <div className="text-sm text-text-primary font-medium">
                Panel: {activeId}
              </div>
            </div>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}