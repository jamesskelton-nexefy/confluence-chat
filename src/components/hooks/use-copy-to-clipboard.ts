import { useState, useCallback } from 'react'

export function useCopyToClipboard(duration = 2000) {
  const [hasCopied, setHasCopied] = useState(false)

  const copyToClipboard = useCallback(
    async (value: string) => {
      try {
        await navigator.clipboard.writeText(value)
        setHasCopied(true)
        
        // Reset copy state after duration
        setTimeout(() => {
          setHasCopied(false)
        }, duration)
        
        return true
      } catch (error) {
        console.error('Failed to copy text:', error)
        setHasCopied(false)
        return false
      }
    },
    [duration]
  )

  return {
    hasCopied,
    copyToClipboard
  }
} 