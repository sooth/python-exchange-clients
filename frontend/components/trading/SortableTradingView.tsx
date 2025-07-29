'use client'

import React, { useState, useRef } from 'react'
import { ChartContainer } from './ChartContainer'
import { OrderBook } from './OrderBook'
import { OrderForm } from './OrderForm'
import { RecentTrades } from './RecentTrades'
import { OpenOrders } from './OpenOrders'
import { Positions } from './Positions'
import { MarketInfo } from './MarketInfo'
import { useMarket } from '@/contexts/MarketContext'
import { 
  ResizableLayout, 
  ResizablePanel, 
  ResizableHandle 
} from '@/components/layout/ResizableLayout'
import { SortableLayout } from '@/components/layout/SortableLayout'
import { SortableResizablePanel } from '@/components/layout/SortableResizablePanel'
import { usePanelLayout } from '@/hooks/usePanelLayout'
import { ImperativePanelHandle } from 'react-resizable-panels'

// Define panel IDs
const PANEL_IDS = {
  CHART: 'chart',
  ORDERBOOK: 'orderbook', 
  TRADES: 'trades',
  ORDERFORM: 'orderform',
  POSITIONS: 'positions'
}

export function SortableTradingView() {
  const { selectedSymbol, selectedExchange } = useMarket()
  const [activeBottomTab, setActiveBottomTab] = useState<'balances' | 'orders' | 'history'>('orders')
  
  // Panel layout management
  const topPanels = [PANEL_IDS.CHART, PANEL_IDS.ORDERBOOK]
  const { panels: topPanelOrder, reorderPanels: reorderTopPanels } = usePanelLayout(topPanels)
  
  const bottomPanels = [PANEL_IDS.ORDERFORM, PANEL_IDS.POSITIONS]
  const { panels: bottomPanelOrder, reorderPanels: reorderBottomPanels } = usePanelLayout(bottomPanels)

  // Panel refs for programmatic control
  const chartRef = useRef<ImperativePanelHandle>(null)
  const orderbookRef = useRef<ImperativePanelHandle>(null)
  
  // Render panel content based on ID
  const renderPanelContent = (panelId: string) => {
    switch (panelId) {
      case PANEL_IDS.CHART:
        return (
          <SortableResizablePanel
            ref={chartRef}
            id={PANEL_IDS.CHART}
            defaultSize={70}
            minSize={40}
            title="CHART"
            showDragHandle={true}
          >
            <ChartContainer symbol={selectedSymbol} />
          </SortableResizablePanel>
        )
      
      case PANEL_IDS.ORDERBOOK:
        return (
          <SortableResizablePanel
            ref={orderbookRef}
            id={PANEL_IDS.ORDERBOOK}
            defaultSize={30}
            minSize={20}
            maxSize={50}
            title="ORDER BOOK & TRADES"
            showDragHandle={true}
          >
            <ResizableLayout direction="vertical" autoSaveId="orderbook-trades">
              <ResizablePanel defaultSize={60} minSize={30}>
                <OrderBook symbol={selectedSymbol} />
              </ResizablePanel>
              <ResizableHandle direction="vertical" />
              <ResizablePanel defaultSize={40} minSize={20}>
                <RecentTrades symbol={selectedSymbol} />
              </ResizablePanel>
            </ResizableLayout>
          </SortableResizablePanel>
        )
        
      case PANEL_IDS.ORDERFORM:
        return (
          <SortableResizablePanel
            id={PANEL_IDS.ORDERFORM}
            defaultSize={25}
            minSize={15}
            maxSize={40}
            title="PLACE ORDER"
            showDragHandle={true}
          >
            <OrderForm symbol={selectedSymbol} exchange={selectedExchange} />
          </SortableResizablePanel>
        )
        
      case PANEL_IDS.POSITIONS:
        return (
          <SortableResizablePanel
            id={PANEL_IDS.POSITIONS}
            defaultSize={75}
            minSize={50}
            title="POSITIONS & ORDERS"
            showDragHandle={true}
          >
            <div className="h-full flex flex-col">
              {/* Tab headers */}
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

              {/* Tab content */}
              <div className="flex-1 overflow-hidden">
                {activeBottomTab === 'balances' && (
                  <Positions exchange={selectedExchange} />
                )}
                {activeBottomTab === 'orders' && (
                  <OpenOrders symbol={selectedSymbol} exchange={selectedExchange} />
                )}
                {activeBottomTab === 'history' && (
                  <div className="p-4 text-text-secondary text-xs">
                    Order history not implemented yet
                  </div>
                )}
              </div>
            </div>
          </SortableResizablePanel>
        )
        
      default:
        return null
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Market info bar */}
      <div className="h-12 border-b border-border-primary">
        <MarketInfo symbol={selectedSymbol} exchange={selectedExchange} />
      </div>

      {/* Main content with vertical split */}
      <ResizableLayout direction="vertical" autoSaveId="trading-vertical-sortable">
        {/* Top section - Chart and order book (sortable) */}
        <ResizablePanel defaultSize={70} minSize={40}>
          <SortableLayout
            items={topPanelOrder}
            onReorder={reorderTopPanels}
            direction="horizontal"
          >
            <ResizableLayout direction="horizontal" autoSaveId="trading-top-sortable">
              {topPanelOrder.map((panelId, index) => (
                <React.Fragment key={panelId}>
                  {index > 0 && <ResizableHandle />}
                  {renderPanelContent(panelId)}
                </React.Fragment>
              ))}
            </ResizableLayout>
          </SortableLayout>
        </ResizablePanel>
        
        <ResizableHandle direction="vertical" />
        
        {/* Bottom section - Order form and positions (sortable) */}
        <ResizablePanel defaultSize={30} minSize={20} maxSize={50}>
          <SortableLayout
            items={bottomPanelOrder}
            onReorder={reorderBottomPanels}
            direction="horizontal"
          >
            <ResizableLayout direction="horizontal" autoSaveId="trading-bottom-sortable">
              {bottomPanelOrder.map((panelId, index) => (
                <React.Fragment key={panelId}>
                  {index > 0 && <ResizableHandle />}
                  {renderPanelContent(panelId)}
                </React.Fragment>
              ))}
            </ResizableLayout>
          </SortableLayout>
        </ResizablePanel>
      </ResizableLayout>
    </div>
  )
}