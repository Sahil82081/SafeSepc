import React, { createContext, useContext, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useRuns } from '../api/queries'

interface RunContextType {
  selectedRunId: string
  setSelectedRunId: (id: string) => void
  clearRun: () => void
  isLoadingRuns: boolean
}

const RunContext = createContext<RunContextType | undefined>(undefined)

export function RunProvider({ children }: { children: React.ReactNode }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const { data: runs, isLoading } = useRuns()

  const [selectedRunId, setSelectedRunIdState] = useState<string>(() => {
    return (
      searchParams.get('runId') ||
      localStorage.getItem('safespec-active-run') ||
      ''
    )
  })

  // Auto-select latest run if none selected, or reset if no runs exist
  useEffect(() => {
    if (!isLoading && runs) {
      if (runs.length === 0) {
        if (selectedRunId) {
          setSelectedRunIdState('')
          localStorage.removeItem('safespec-active-run')
        }
      } else {
        const runExists = runs.some((r) => r.run_id === selectedRunId)
        if (!selectedRunId || !runExists) {
          const defaultId = runs[0].run_id
          setSelectedRunIdState(defaultId)
          localStorage.setItem('safespec-active-run', defaultId)
        }
      }
    }
  }, [runs, isLoading, selectedRunId])

  // Sync with search params if present
  useEffect(() => {
    const urlRunId = searchParams.get('runId')
    if (urlRunId && urlRunId !== selectedRunId) {
      setSelectedRunIdState(urlRunId)
      localStorage.setItem('safespec-active-run', urlRunId)
    }
  }, [searchParams, selectedRunId])

  const clearRun = () => {
    setSelectedRunIdState('')
    localStorage.removeItem('safespec-active-run')
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete('runId')
      return next
    })
  }

  const setSelectedRunId = (id: string) => {
    setSelectedRunIdState(id)
    if (id) {
      localStorage.setItem('safespec-active-run', id)
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        next.set('runId', id)
        return next
      })
    } else {
      localStorage.removeItem('safespec-active-run')
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        next.delete('runId')
        return next
      })
    }
  }

  return (
    <RunContext.Provider
      value={{
        selectedRunId,
        setSelectedRunId,
        clearRun,
        isLoadingRuns: isLoading,
      }}
    >
      {children}
    </RunContext.Provider>
  )
}

export function useRunContext() {
  const context = useContext(RunContext)
  if (!context) {
    throw new Error('useRunContext must be used within a RunProvider')
  }
  return context
}
