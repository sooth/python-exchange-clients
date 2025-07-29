'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function ClearStoragePage() {
  const router = useRouter()
  
  useEffect(() => {
    // Clear all localStorage
    if (typeof window !== 'undefined') {
      localStorage.clear()
      sessionStorage.clear()
      
      // Clear IndexedDB
      if (window.indexedDB) {
        indexedDB.databases().then(dbs => {
          dbs.forEach(db => {
            if (db.name) {
              indexedDB.deleteDatabase(db.name)
            }
          })
        })
      }
      
      // Clear cookies
      document.cookie.split(";").forEach(c => {
        document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/")
      })
      
      console.log('All storage cleared!')
      
      // Redirect to home
      setTimeout(() => {
        router.push('/')
      }, 1000)
    }
  }, [router])
  
  return (
    <div className="h-screen flex items-center justify-center bg-background-primary">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-text-primary mb-4">Clearing all storage...</h1>
        <p className="text-text-secondary">You will be redirected to the home page.</p>
      </div>
    </div>
  )
}