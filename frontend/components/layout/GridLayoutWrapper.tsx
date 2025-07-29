'use client'

import React, { useState, useCallback, useEffect } from 'react'
import { Responsive, WidthProvider, Layout, Layouts } from 'react-grid-layout'
import { MarketList } from '@/components/markets/MarketList'
import { ChartContainer } from '@/components/trading/ChartContainer'
import { OrderBook } from '@/components/trading/OrderBook'
import { OrderFormV3 as OrderForm } from '@/components/trading/OrderFormV3'
import { RecentTrades } from '@/components/trading/RecentTrades'
import { OpenOrders } from '@/components/trading/OpenOrders'
import { Positions } from '@/components/trading/Positions'
import { MarketInfo } from '@/components/trading/MarketInfo'
import { useMarket } from '@/contexts/MarketContext'
import { DragHandle } from './DraggablePanel'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

const ResponsiveGridLayout = WidthProvider(Responsive)

// Panel definitions with their components
const PANEL_COMPONENTS = {
  'market-list': { 
    title: 'MARKETS', 
    component: MarketList,
    minW: 2,
    minH: 10,
    maxW: 4,
  },
  'chart': { 
    title: 'CHART', 
    component: ChartContainer,
    minW: 3,
    minH: 8,
    maxW: 8,
  },
  'orderbook': { 
    title: 'ORDER BOOK', 
    component: OrderBook,
    minW: 2,
    minH: 6,
    maxW: 4,
  },
  'trades': { 
    title: 'RECENT TRADES', 
    component: RecentTrades,
    minW: 2,
    minH: 6,
    maxW: 4,
  },
  'orderform': { 
    title: 'PLACE ORDER', 
    component: OrderForm,
    minW: 2,
    minH: 8,
    maxW: 4,
  },
  'positions': { 
    title: 'POSITIONS & ORDERS', 
    component: Positions,
    minW: 3,
    minH: 6,
    maxW: 12,
  },
}

// Default layouts for different breakpoints
const DEFAULT_LAYOUTS: Layouts = {
  lg: [
    { i: 'market-list', x: 0, y: 0, w: 3, h: 20 },
    { i: 'chart', x: 3, y: 0, w: 6, h: 12 },
    { i: 'orderbook', x: 9, y: 0, w: 3, h: 10 },
    { i: 'trades', x: 9, y: 10, w: 3, h: 10 },
    { i: 'orderform', x: 3, y: 12, w: 3, h: 8 },
    { i: 'positions', x: 6, y: 12, w: 6, h: 8 },
  ],
  md: [
    { i: 'market-list', x: 0, y: 0, w: 3, h: 16 },
    { i: 'chart', x: 3, y: 0, w: 6, h: 10 },
    { i: 'orderbook', x: 9, y: 0, w: 3, h: 8 },
    { i: 'trades', x: 9, y: 8, w: 3, h: 8 },
    { i: 'orderform', x: 3, y: 10, w: 3, h: 6 },
    { i: 'positions', x: 6, y: 10, w: 6, h: 6 },
  ],
  sm: [
    { i: 'market-list', x: 0, y: 0, w: 6, h: 10 },
    { i: 'chart', x: 0, y: 10, w: 6, h: 10 },
    { i: 'orderbook', x: 0, y: 20, w: 3, h: 8 },
    { i: 'trades', x: 3, y: 20, w: 3, h: 8 },
    { i: 'orderform', x: 0, y: 28, w: 6, h: 8 },
    { i: 'positions', x: 0, y: 36, w: 6, h: 8 },
  ],
  xs: [
    { i: 'market-list', x: 0, y: 0, w: 4, h: 10 },
    { i: 'chart', x: 0, y: 10, w: 4, h: 10 },
    { i: 'orderbook', x: 0, y: 20, w: 4, h: 8 },
    { i: 'trades', x: 0, y: 28, w: 4, h: 8 },
    { i: 'orderform', x: 0, y: 36, w: 4, h: 8 },
    { i: 'positions', x: 0, y: 44, w: 4, h: 8 },
  ],
  xxs: [
    { i: 'market-list', x: 0, y: 0, w: 2, h: 10 },
    { i: 'chart', x: 0, y: 10, w: 2, h: 10 },
    { i: 'orderbook', x: 0, y: 20, w: 2, h: 8 },
    { i: 'trades', x: 0, y: 28, w: 2, h: 8 },
    { i: 'orderform', x: 0, y: 36, w: 2, h: 8 },
    { i: 'positions', x: 0, y: 44, w: 2, h: 8 },
  ],
}

const STORAGE_KEY = 'trading-grid-layouts'
const EDIT_MODE_KEY = 'trading-grid-edit-mode'

interface GridPanelProps {
  id: string
  children: React.ReactNode
}

function GridPanel({ id, children }: GridPanelProps) {
  const config = PANEL_COMPONENTS[id as keyof typeof PANEL_COMPONENTS]
  
  return (
    <div className="h-full flex flex-col bg-[#1a1d29] border border-gray-600 rounded-lg overflow-hidden">
      <div className="flex items-center gap-1.5 px-2 py-0.5 border-b border-gray-600 bg-[#2a2d3a]">
        <div className="cursor-move">
          <DragHandle />
        </div>
        <h3 className="text-[10px] font-medium text-gray-400 uppercase select-none">{config.title}</h3>
      </div>
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  )
}

interface GridLayoutWrapperProps {
  editMode?: boolean
  onEditModeChange?: (editMode: boolean) => void
  onResetLayout?: () => void
  resetTrigger?: number
}

export function GridLayoutWrapper({ 
  editMode: externalEditMode, 
  onEditModeChange,
  onResetLayout,
  resetTrigger 
}: GridLayoutWrapperProps) {
  const { selectedSymbol, selectedExchange } = useMarket()
  const [layouts, setLayouts] = useState<Layouts>(() => {
    // Try to load from localStorage first
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        try {
          return JSON.parse(saved)
        } catch (e) {
          console.error('Failed to parse saved layouts:', e)
        }
      }
    }
    return DEFAULT_LAYOUTS
  })
  
  const [internalEditMode, setInternalEditMode] = useState(() => {
    // Load from localStorage
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(EDIT_MODE_KEY)
      return saved ? saved === 'true' : true
    }
    return true
  })
  const [isHydrated, setIsHydrated] = useState(false)
  
  // Use external editMode if provided, otherwise use internal
  const editMode = externalEditMode !== undefined ? externalEditMode : internalEditMode
  const setEditMode = onEditModeChange || setInternalEditMode
  
  const [activeBottomTab, setActiveBottomTab] = useState<'balances' | 'orders' | 'history'>('orders')
  const [currentBreakpoint, setCurrentBreakpoint] = useState('lg')

  // Hydration effect
  useEffect(() => {
    setIsHydrated(true)
  }, [])

  // Save layouts when they change
  const handleLayoutChange = useCallback((currentLayout: Layout[], allLayouts: Layouts) => {
    setLayouts(allLayouts)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(allLayouts))
  }, [])

  // Toggle edit mode
  const toggleEditMode = useCallback(() => {
    const newMode = !editMode
    setEditMode(newMode)
    localStorage.setItem(EDIT_MODE_KEY, String(newMode))
  }, [editMode, setEditMode])

  // Reset layouts
  const resetLayouts = useCallback(() => {
    setLayouts(DEFAULT_LAYOUTS)
    localStorage.removeItem(STORAGE_KEY)
    onResetLayout?.()
  }, [onResetLayout])
  
  // Handle reset trigger from parent
  useEffect(() => {
    if (resetTrigger && resetTrigger > 0) {
      resetLayouts()
    }
  }, [resetTrigger, resetLayouts])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check for cmd/ctrl + shift combinations
      if ((e.metaKey || e.ctrlKey) && e.shiftKey) {
        switch (e.key.toLowerCase()) {
          case 'r':
            e.preventDefault()
            resetLayouts()
            break
          case 'l':
            e.preventDefault()
            toggleEditMode()
            break
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [toggleEditMode, resetLayouts])

  // Handle breakpoint changes
  const handleBreakpointChange = useCallback((breakpoint: string) => {
    setCurrentBreakpoint(breakpoint)
  }, [])

  // Render panel content
  const renderPanelContent = (panelId: string) => {
    const config = PANEL_COMPONENTS[panelId as keyof typeof PANEL_COMPONENTS]
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
          <div className="flex border-b border-gray-600">
            <button
              className={`px-3 py-0.5 text-[10px] font-medium ${
                activeBottomTab === 'balances'
                  ? 'text-white border-b-2 border-[#00d395]'
                  : 'text-gray-400 hover:text-white'
              }`}
              onClick={() => setActiveBottomTab('balances')}
            >
              Balances
            </button>
            <button
              className={`px-3 py-0.5 text-[10px] font-medium ${
                activeBottomTab === 'orders'
                  ? 'text-white border-b-2 border-[#00d395]'
                  : 'text-gray-400 hover:text-white'
              }`}
              onClick={() => setActiveBottomTab('orders')}
            >
              Open Orders
            </button>
            <button
              className={`px-3 py-0.5 text-[10px] font-medium ${
                activeBottomTab === 'history'
                  ? 'text-white border-b-2 border-[#00d395]'
                  : 'text-gray-400 hover:text-white'
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
              <div className="p-4 text-gray-400 text-xs">
                Order history not implemented yet
              </div>
            )}
          </div>
        </div>
      )
    }

    return <Component {...props} />
  }

  // Don't render the grid until hydrated to avoid SSR/client mismatch
  if (!isHydrated) {
    return (
      <>
        {/* Market info bar */}
        <div className="h-12 border-b border-gray-600">
          <MarketInfo symbol={selectedSymbol} exchange={selectedExchange} />
        </div>
        
        {/* Loading placeholder */}
        <div className="flex-1 flex items-center justify-center">
          <div className="text-gray-400">Loading layout...</div>
        </div>
      </>
    )
  }

  return (
    <>
      {/* Market info bar */}
      <div className="h-12 border-b border-gray-600">
        <MarketInfo symbol={selectedSymbol} exchange={selectedExchange} />
      </div>
      
      {/* Grid layout */}
      <div className="flex-1 p-2 overflow-auto">
        <ResponsiveGridLayout
          className={`layout ${editMode ? 'edit-mode' : ''}`}
          layouts={layouts}
          onLayoutChange={handleLayoutChange}
          onBreakpointChange={handleBreakpointChange}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 12, md: 12, sm: 6, xs: 4, xxs: 2 }}
          rowHeight={30}
          containerPadding={[0, 0]}
          margin={[8, 8]}
          isDraggable={editMode}
          isResizable={editMode}
          compactType="vertical"
          preventCollision={false}
          useCSSTransforms={true}
          draggableHandle=".cursor-move"
          resizeHandles={['se', 'sw', 'ne', 'nw', 'e', 'w', 's', 'n']}
        >
          {Object.keys(PANEL_COMPONENTS).map((panelId) => {
            const config = PANEL_COMPONENTS[panelId as keyof typeof PANEL_COMPONENTS]
            // Find the layout for this panel in the current breakpoint
            const currentLayout = layouts[currentBreakpoint as keyof Layouts] || layouts.lg
            const panelLayout = currentLayout.find(item => item.i === panelId)
            
            // Provide default layout if not found
            const layoutProps = panelLayout || DEFAULT_LAYOUTS.lg.find(item => item.i === panelId) || { x: 0, y: 0, w: 3, h: 10 }
            
            return (
              <div 
                key={panelId}
                data-grid={{
                  ...layoutProps,
                  minW: config.minW,
                  minH: config.minH,
                  maxW: config.maxW,
                }}
              >
                <GridPanel id={panelId}>
                  {renderPanelContent(panelId)}
                </GridPanel>
              </div>
            )
          })}
        </ResponsiveGridLayout>
      </div>
    </>
  )
}