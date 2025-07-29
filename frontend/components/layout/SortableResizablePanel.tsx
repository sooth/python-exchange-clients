'use client'

import { ReactNode, forwardRef } from 'react'
import { ResizablePanel } from './ResizableLayout'
import { DraggablePanel, DragHandle } from './DraggablePanel'
import { ImperativePanelHandle } from 'react-resizable-panels'

interface SortableResizablePanelProps {
  id: string
  children: ReactNode
  defaultSize?: number
  minSize?: number
  maxSize?: number
  order?: number
  className?: string
  title?: string
  showDragHandle?: boolean
  dragDisabled?: boolean
}

export const SortableResizablePanel = forwardRef<ImperativePanelHandle, SortableResizablePanelProps>(
  ({ 
    id,
    children, 
    defaultSize, 
    minSize = 10, 
    maxSize, 
    order, 
    className = '',
    title,
    showDragHandle = true,
    dragDisabled = false
  }, ref) => {
    return (
      <ResizablePanel
        ref={ref}
        id={id}
        defaultSize={defaultSize}
        minSize={minSize}
        maxSize={maxSize}
        order={order}
        className={className}
      >
        <DraggablePanel 
          id={id} 
          disabled={dragDisabled}
        >
          {({ dragHandleProps, isDragging }: any) => (
            <div className={`h-full flex flex-col ${isDragging ? 'select-none' : ''}`}>
              {/* Panel header with drag handle */}
              {title && (
                <div className="flex items-center gap-2 px-3 py-2 border-b border-border-primary bg-background-secondary">
                  {showDragHandle && (
                    <div {...dragHandleProps}>
                      <DragHandle className="cursor-grab active:cursor-grabbing" />
                    </div>
                  )}
                  <h3 className="text-xs font-medium text-text-secondary uppercase select-none">{title}</h3>
                </div>
              )}
              
              {/* Panel content */}
              <div className="flex-1 overflow-hidden">
                {children}
              </div>
            </div>
          )}
        </DraggablePanel>
      </ResizablePanel>
    )
  }
)

SortableResizablePanel.displayName = 'SortableResizablePanel'