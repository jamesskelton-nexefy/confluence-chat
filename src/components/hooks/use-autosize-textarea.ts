import { useEffect, useRef } from 'react'

export function useAutosizeTextArea() {
  const textAreaRef = useRef<HTMLTextAreaElement>(null)

  const adjustHeight = () => {
    const textArea = textAreaRef.current
    if (!textArea) return

    // Reset height to allow shrinking
    textArea.style.height = 'auto'
    
    // Set new height based on scrollHeight
    const newHeight = Math.min(textArea.scrollHeight, 200) // Max height of 200px
    textArea.style.height = `${newHeight}px`
  }

  useEffect(() => {
    const textArea = textAreaRef.current
    if (!textArea) return

    // Set initial height
    adjustHeight()

    // Add resize observer to handle window/content changes
    const resizeObserver = new ResizeObserver(adjustHeight)
    resizeObserver.observe(textArea)

    return () => {
      resizeObserver.disconnect()
    }
  }, [])

  return {
    textAreaRef,
    adjustHeight
  }
} 