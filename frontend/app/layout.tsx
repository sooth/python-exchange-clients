import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import '../styles/resizable.css'
import { Providers } from './providers'
import { Toaster } from 'react-hot-toast'
import { DebugInfo } from '@/components/debug/DebugInfo'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'FTX',
  description: 'Professional cryptocurrency trading platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-background-primary text-text-primary`}>
        <Providers>
          {children}
          <Toaster
            position="bottom-right"
            toastOptions={{
              className: '',
              style: {
                background: '#1a1d21',
                color: '#ffffff',
                border: '1px solid #2a2d31',
                fontSize: '14px',
              },
            }}
          />
          <DebugInfo />
        </Providers>
      </body>
    </html>
  )
}