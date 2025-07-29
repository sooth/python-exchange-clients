'use client'

import { useState } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useMarket } from '@/contexts/MarketContext'

interface HeaderProps {
  editMode?: boolean
  onToggleEditMode?: () => void
  onResetLayout?: () => void
}

export function Header({ editMode = false, onToggleEditMode, onResetLayout }: HeaderProps) {
  const { isConnected } = useWebSocket()
  const { selectedSymbol, selectedExchange } = useMarket()

  return (
    <header className="h-12 border-b border-border-primary bg-background-primary">
      <div className="h-full flex items-center px-4">
        {/* Left section */}
        <div className="flex items-center space-x-6">
          {/* Logo */}
          <div className="flex items-center space-x-2">
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
              <rect width="32" height="32" rx="6" fill="#5FCADE"/>
              <path d="M8 12H24V14H8V12Z" fill="#000000"/>
              <path d="M8 18H24V20H8V18Z" fill="#000000"/>
              <path d="M14 8V24H16V8H14Z" fill="#000000"/>
            </svg>
            <span className="text-lg font-semibold">FTX</span>
          </div>

          {/* Navigation */}
          <nav className="flex items-center space-x-1">
            <a href="#" className="px-3 py-1.5 text-sm font-medium text-text-primary hover:text-accent-primary transition-colors">
              MARKETS
            </a>
            <a href="#" className="px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors">
              WALLET
            </a>
            <a href="#" className="px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors">
              OTC
            </a>
            <a href="#" className="px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors">
              FTT
            </a>
            <a href="#" className="px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors">
              HELP
            </a>
          </nav>
        </div>

        {/* Center - Search */}
        <div className="flex-1 flex justify-center">
          <div className="relative w-96">
            <input
              type="text"
              placeholder="Search markets"
              className="w-full px-3 py-1.5 bg-background-secondary border border-border-primary text-sm placeholder-text-muted focus:outline-none focus:border-accent-primary"
            />
            <svg className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        {/* Right section */}
        <div className="flex items-center space-x-4">
          {/* Layout controls */}
          {onToggleEditMode && (
            <>
              <button
                onClick={onToggleEditMode}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                  editMode
                    ? 'bg-accent-primary text-background-primary'
                    : 'bg-background-secondary text-text-secondary border border-border-primary hover:text-text-primary'
                }`}
              >
                {editMode ? 'Lock Layout' : 'Edit Layout'}
              </button>
              {editMode && onResetLayout && (
                <button
                  onClick={onResetLayout}
                  className="px-3 py-1 text-xs font-medium rounded bg-background-secondary text-text-secondary border border-border-primary hover:text-text-primary transition-colors"
                >
                  Reset Layout
                </button>
              )}
            </>
          )}

          {/* Connection status */}
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success' : 'bg-error'}`} />
          </div>

          {/* Settings */}
          <button className="text-text-secondary hover:text-text-primary transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>

          {/* Theme toggle */}
          <button className="text-text-secondary hover:text-text-primary transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          </button>

          {/* Menu */}
          <button className="text-text-secondary hover:text-text-primary transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  )
}