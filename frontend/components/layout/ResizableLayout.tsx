'use client'

import { ReactNode, forwardRef } from 'react'
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
  ImperativePanelHandle,
} from 'react-resizable-panels'

interface ResizablePanelProps {
  children: ReactNode
  defaultSize?: number
  minSize?: number
  maxSize?: number
  id?: string
  order?: number
  className?: string
}

export const ResizablePanel = forwardRef<ImperativePanelHandle, ResizablePanelProps>(
  ({ children, defaultSize, minSize = 10, maxSize, id, order, className = '' }, ref) => {
    return (
      <Panel
        ref={ref}
        defaultSize={defaultSize}
        minSize={minSize}
        maxSize={maxSize}
        id={id}
        order={order}
        className={`overflow-hidden ${className}`}
      >
        {children}
      </Panel>
    )
  }
)

ResizablePanel.displayName = 'ResizablePanel'

interface ResizableHandleProps {
  className?: string
  disabled?: boolean
}

export function ResizableHandle({ 
  className = '', 
  disabled = false,
  direction = 'horizontal'
}: ResizableHandleProps & { direction?: 'horizontal' | 'vertical' }) {
  const isVertical = direction === 'vertical'
  
  return (
    <PanelResizeHandle
      disabled={disabled}
      className={`
        group relative ${isVertical ? 'py-1.5 px-0' : 'px-1.5 py-0'}
        data-[resize-handle-state=drag]:bg-accent-primary/30
        data-[resize-handle-state=hover]:bg-accent-primary/20
        transition-all duration-150
        ${className}
      `}
    >
      {/* Main line */}
      {isVertical ? (
        <div className="absolute inset-y-0 left-1/2 w-[3px] -translate-x-1/2 bg-border-primary 
                        group-hover:bg-accent-primary group-data-[resize-handle-state=drag]:bg-accent-primary 
                        transition-all duration-150
                        group-hover:w-[4px] group-data-[resize-handle-state=drag]:w-[4px]" />
      ) : (
        <div className="absolute inset-x-0 top-1/2 h-[3px] -translate-y-1/2 bg-border-primary 
                        group-hover:bg-accent-primary group-data-[resize-handle-state=drag]:bg-accent-primary 
                        transition-all duration-150
                        group-hover:h-[4px] group-data-[resize-handle-state=drag]:h-[4px]" />
      )}
      
      {/* Grip dots indicator */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className={`flex ${isVertical ? 'flex-row gap-1' : 'flex-col gap-1'} opacity-0 group-hover:opacity-100 transition-opacity duration-150`}>
          <div className="w-1.5 h-1.5 bg-accent-primary rounded-full shadow-sm" />
          <div className="w-1.5 h-1.5 bg-accent-primary rounded-full shadow-sm" />
          <div className="w-1.5 h-1.5 bg-accent-primary rounded-full shadow-sm" />
        </div>
      </div>
      
      {/* Tooltip on hover */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
        <div className={`
          bg-background-primary border border-border-primary px-2 py-1 rounded text-xs text-text-secondary
          opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-500
          whitespace-nowrap shadow-lg
          ${isVertical ? '-translate-x-16' : '-translate-y-8'}
        `}>
          Drag to resize
        </div>
      </div>
    </PanelResizeHandle>
  )
}

interface ResizableLayoutProps {
  children: ReactNode
  direction?: 'horizontal' | 'vertical'
  autoSaveId?: string
  className?: string
}

export function ResizableLayout({
  children,
  direction = 'horizontal',
  autoSaveId,
  className = ''
}: ResizableLayoutProps) {
  return (
    <PanelGroup
      direction={direction}
      autoSaveId={autoSaveId}
      className={`h-full w-full ${className}`}
    >
      {children}
    </PanelGroup>
  )
}

// Preset layouts for common configurations
export const LayoutPresets = {
  trading: {
    leftPanel: 20,    // Market list
    centerPanel: 50,  // Chart
    rightPanel: 30,   // Order book + trades
  },
  analysis: {
    leftPanel: 15,
    centerPanel: 70,
    rightPanel: 15,
  },
  compact: {
    leftPanel: 25,
    centerPanel: 45,
    rightPanel: 30,
  },
}

interface LayoutManagerProps {
  preset: keyof typeof LayoutPresets
  onPresetChange?: (preset: keyof typeof LayoutPresets) => void
}

export function LayoutManager({ preset, onPresetChange }: LayoutManagerProps) {
  return (
    <div className="flex items-center space-x-2 px-2 py-1">
      <span className="text-xs text-text-secondary">Layout:</span>
      <select
        value={preset}
        onChange={(e) => onPresetChange?.(e.target.value as keyof typeof LayoutPresets)}
        className="bg-background-secondary border border-border-primary px-2 py-0.5 text-xs text-text-primary focus:outline-none"
      >
        <option value="trading">Trading</option>
        <option value="analysis">Analysis</option>
        <option value="compact">Compact</option>
      </select>
    </div>
  )
}