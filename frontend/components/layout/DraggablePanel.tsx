'use client'

import React, { ReactNode, CSSProperties } from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

interface DraggablePanelProps {
  id: string
  children: (props: { dragHandleProps: any; isDragging: boolean }) => ReactNode
  dragHandleClassName?: string
  disabled?: boolean
}

export function DraggablePanel({ 
  id, 
  children, 
  dragHandleClassName = 'drag-handle',
  disabled = false 
}: DraggablePanelProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
    isSorting,
    over,
  } = useSortable({ 
    id,
    disabled,
  })

  const style: CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.7 : 1,
    position: 'relative' as const,
  }

  // Highlight drop zones
  const isOverlay = over?.id === id

  const dragHandleProps = {
    ref: setActivatorNodeRef,
    ...attributes,
    ...listeners,
  }

  return (
    <div 
      ref={setNodeRef} 
      style={style}
      className={`relative h-full ${isDragging ? 'z-50 shadow-2xl' : ''} ${isOverlay ? 'ring-2 ring-[#00d395]' : ''}`}
    >
      {children({ dragHandleProps, isDragging })}
      
      {/* Dragging indicator */}
      {isDragging && (
        <div className="absolute inset-0 bg-[#00d395]/5 pointer-events-none rounded" />
      )}
    </div>
  )
}

// Drag handle component to be used inside panel headers
export function DragHandle({ className = '' }: { className?: string }) {
  return (
    <div 
      className={`drag-handle ${className}`}
      title="Drag to rearrange"
    >
      <svg 
        width="8" 
        height="12" 
        viewBox="0 0 12 20" 
        fill="none"
        className="text-gray-400 hover:text-white transition-colors"
      >
        <circle cx="3" cy="3" r="1.5" fill="currentColor" />
        <circle cx="9" cy="3" r="1.5" fill="currentColor" />
        <circle cx="3" cy="10" r="1.5" fill="currentColor" />
        <circle cx="9" cy="10" r="1.5" fill="currentColor" />
        <circle cx="3" cy="17" r="1.5" fill="currentColor" />
        <circle cx="9" cy="17" r="1.5" fill="currentColor" />
      </svg>
    </div>
  )
}