'use client'

import { createContext, useContext, useState, ReactNode, useEffect } from 'react'
import { MarketProvider } from '@/contexts/MarketContext'

export function MarketProviderWithDefaults({ children }: { children: ReactNode }) {
  // Force LMEX as default on mount
  useEffect(() => {
    // Clear any cached values
    if (typeof window !== 'undefined') {
      // Force clear any bitunix references
      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        const value = localStorage.getItem(key);
        if (value && value.includes('bitunix')) {
          localStorage.removeItem(key);
        }
      });
    }
  }, []);

  return <MarketProvider>{children}</MarketProvider>
}