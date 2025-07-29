'use client'

import React, { useState, useCallback, useEffect } from 'react'
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  MeasuringStrategy,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
} from '@dnd-kit/sortable'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { DragHandle } from './DraggablePanel'
import { MarketList } from '@/components/markets/MarketList'
import { ChartContainer } from '@/components/trading/ChartContainer'
import { OrderBook } from '@/components/trading/OrderBook'
import { OrderForm } from '@/components/trading/OrderForm'
import { RecentTrades } from '@/components/trading/RecentTrades'
import { OpenOrders } from '@/components/trading/OpenOrders'
import { Positions } from '@/components/trading/Positions'
import { MarketInfo } from '@/components/trading/MarketInfo'
import { useMarket } from '@/contexts/MarketContext'

// Panel definitions with default grid positions
export const PANEL_CONFIG = {
  'market-list': { 
    title: 'MARKETS', 
    defaultPos: { x: 0, y: 0, w: 2, h: 6 },
    minW: 2, minH: 3,
    component: MarketList 
  },
  'chart': { 
    title: 'CHART', 
    defaultPos: { x: 2, y: 0, w: 4, h: 4 },
    minW: 3, minH: 3,
    component: ChartContainer 
  },
  'orderbook': { 
    title: 'ORDER BOOK', 
    defaultPos: { x: 6, y: 0, w: 2, h: 3 },
    minW: 2, minH: 2,
    component: OrderBook 
  },
  'trades': { 
    title: 'RECENT TRADES', 
    defaultPos: { x: 6, y: 3, w: 2, h: 3 },
    minW: 2, minH: 2,
    component: RecentTrades 
  },
  'orderform': { 
    title: 'PLACE ORDER', 
    defaultPos: { x: 2, y: 4, w: 2, h: 2 },
    minW: 2, minH: 2,
    component: OrderForm 
  },
  'positions': { 
    title: 'POSITIONS & ORDERS', 
    defaultPos: { x: 4, y: 4, w: 4, h: 2 },
    minW: 3, minH: 2,
    component: Positions 
  },
}

const GRID_COLS = 8
const GRID_ROWS = 6

interface GridPanelProps {
  id: string
  children: React.ReactNode
  title: string
  position: { x: number; y: number; w: number; h: number }
}

function GridPanel({ id, children, title, position }: GridPanelProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    gridColumn: `${position.x + 1} / span ${position.w}`,
    gridRow: `${position.y + 1} / span ${position.h}`,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`bg-background-primary border border-border-primary rounded-lg overflow-hidden ${
        isDragging ? 'z-50 shadow-2xl' : ''
      }`}
    >
      <div className="h-full flex flex-col">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border-primary bg-background-secondary">
          <div 
            ref={setActivatorNodeRef}
            {...attributes}
            {...listeners}
            className="cursor-grab active:cursor-grabbing"
          >
            <DragHandle />
          </div>
          <h3 className="text-xs font-medium text-text-secondary uppercase select-none">{title}</h3>
        </div>
        <div className="flex-1 overflow-hidden">
          {children}
        </div>
      </div>
    </div>
  )
}

const STORAGE_KEY = 'trading-grid-layout'

export function FlexibleGridLayout() {
  const { selectedSymbol, selectedExchange } = useMarket()
  const [panels, setPanels] = useState(Object.keys(PANEL_CONFIG))
  const [positions, setPositions] = useState<Record<string, { x: number; y: number; w: number; h: number }>>(() => {
    // Try to load from localStorage
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        try {
          return JSON.parse(saved)
        } catch (e) {
          console.error('Failed to parse saved layout:', e)
        }
      }
    }
    
    // Default positions
    const initial: Record<string, { x: number; y: number; w: number; h: number }> = {}
    Object.entries(PANEL_CONFIG).forEach(([id, config]) => {
      initial[id] = config.defaultPos
    })
    return initial
  })
  const [activeId, setActiveId] = useState<string | null>(null)
  const [activeBottomTab, setActiveBottomTab] = useState<'balances' | 'orders' | 'history'>('orders')
  
  // Save layout to localStorage when positions change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(positions))
  }, [positions])

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
      
      // Swap positions
      setPositions((prev) => {
        const activePos = prev[active.id]
        const overPos = prev[over.id]
        return {
          ...prev,
          [active.id]: overPos,
          [over.id]: activePos,
        }
      })
    }
    
    setActiveId(null)
  }

  const renderPanelContent = (panelId: string) => {
    const config = PANEL_CONFIG[panelId as keyof typeof PANEL_CONFIG]
    if (!config) return null

    const Component = config.component
    const props: any = {}

    // Add props based on component type
    if (panelId === 'chart' || panelId === 'orderbook' || panelId === 'trades') {
      props.symbol = selectedSymbol
    }
    if (panelId === 'orderform' || panelId === 'positions') {
      props.exchange = selectedExchange
    }
    if (panelId === 'orderform') {
      props.symbol = selectedSymbol
    }
    if (panelId === 'positions') {
      // Special handling for positions tabs
      return (
        <div className="h-full flex flex-col">
          <div className="flex border-b border-border-primary">
            <button
              className={`px-4 py-2 text-xs font-medium ${
                activeBottomTab === 'balances'
                  ? 'text-text-primary border-b-2 border-accent-primary'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
              onClick={() => setActiveBottomTab('balances')}
            >
              Balances
            </button>
            <button
              className={`px-4 py-2 text-xs font-medium ${
                activeBottomTab === 'orders'
                  ? 'text-text-primary border-b-2 border-accent-primary'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
              onClick={() => setActiveBottomTab('orders')}
            >
              Open Orders
            </button>
            <button
              className={`px-4 py-2 text-xs font-medium ${
                activeBottomTab === 'history'
                  ? 'text-text-primary border-b-2 border-accent-primary'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
              onClick={() => setActiveBottomTab('history')}
            >
              Order History
            </button>
          </div>
          <div className="flex-1 overflow-hidden">
            {activeBottomTab === 'balances' && <Positions exchange={selectedExchange} />}
            {activeBottomTab === 'orders' && <OpenOrders symbol={selectedSymbol} exchange={selectedExchange} />}
            {activeBottomTab === 'history' && (
              <div className="p-4 text-text-secondary text-xs">
                Order history not implemented yet
              </div>
            )}
          </div>
        </div>
      )
    }

    return <Component {...props} />
  }

  return (
    <>
      {/* Market info bar */}
      <div className="h-12 border-b border-border-primary">
        <MarketInfo symbol={selectedSymbol} exchange={selectedExchange} />
      </div>
      
      {/* Grid layout */}
      <div className="flex-1 p-2 overflow-hidden">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          measuring={{
            droppable: {
              strategy: MeasuringStrategy.Always,
            },
          }}
        >
          <SortableContext items={panels} strategy={rectSortingStrategy}>
            <div
              className={`h-full grid gap-2 relative ${activeId ? 'grid-dragging' : ''}`}
              style={{
                gridTemplateColumns: `repeat(${GRID_COLS}, 1fr)`,
                gridTemplateRows: `repeat(${GRID_ROWS}, 1fr)`,
              }}
            >
              {/* Grid guides when dragging */}
              {activeId && (
                <div className="absolute inset-0 pointer-events-none">
                  <div 
                    className="grid h-full"
                    style={{
                      gridTemplateColumns: `repeat(${GRID_COLS}, 1fr)`,
                      gridTemplateRows: `repeat(${GRID_ROWS}, 1fr)`,
                      gap: '8px',
                    }}
                  >
                    {Array.from({ length: GRID_COLS * GRID_ROWS }).map((_, i) => (
                      <div 
                        key={i} 
                        className="border border-dashed border-accent-primary/30 rounded bg-accent-primary/5"
                      />
                    ))}
                  </div>
                </div>
              )}
              
              {panels.map((panelId) => {
                const config = PANEL_CONFIG[panelId as keyof typeof PANEL_CONFIG]
                const position = positions[panelId]
                
                return (
                  <GridPanel
                    key={panelId}
                    id={panelId}
                    title={config.title}
                    position={position}
                  >
                    {renderPanelContent(panelId)}
                  </GridPanel>
                )
              })}
            </div>
          </SortableContext>
          
          <DragOverlay>
            {activeId ? (
              <div className="bg-background-primary shadow-2xl border-2 border-accent-primary rounded-lg p-4 opacity-95">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-accent-primary rounded-full animate-pulse" />
                  <div className="text-sm text-text-primary font-bold">
                    Moving: {PANEL_CONFIG[activeId as keyof typeof PANEL_CONFIG]?.title}
                  </div>
                </div>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>
    </>
  )
}