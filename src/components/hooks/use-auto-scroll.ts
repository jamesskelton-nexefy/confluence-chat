import { useCallback, useEffect, useRef, useState } from "react"

export function useAutoScroll(deps: any[] = []) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true)
  const [userHasScrolled, setUserHasScrolled] = useState(false)

  const scrollToBottom = useCallback(() => {
    if (!containerRef.current) return

    const container = containerRef.current
    container.scrollTop = container.scrollHeight
    setShouldAutoScroll(true)
  }, [])

  useEffect(() => {
    if (!shouldAutoScroll || !containerRef.current) return

    scrollToBottom()
  }, [shouldAutoScroll, scrollToBottom, ...deps])

  const handleScroll = useCallback(() => {
    if (!containerRef.current || !userHasScrolled) return

    const container = containerRef.current
    const isAtBottom =
      Math.abs(
        container.scrollHeight - container.scrollTop - container.clientHeight
      ) < 100

    setShouldAutoScroll(isAtBottom)
  }, [userHasScrolled])

  const handleTouchStart = useCallback(() => {
    setUserHasScrolled(true)
  }, [])

  return {
    containerRef,
    scrollToBottom,
    handleScroll,
    shouldAutoScroll,
    handleTouchStart,
  }
} 