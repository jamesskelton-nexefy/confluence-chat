import { useState, useCallback, useRef } from 'react'

interface AudioRecordingState {
  isRecording: boolean
  audioUrl: string | null
  error: string | null
  duration: number
  visualizerData: number[]
}

export function useAudioRecording() {
  const [state, setState] = useState<AudioRecordingState>({
    isRecording: false,
    audioUrl: null,
    error: null,
    duration: 0,
    visualizerData: []
  })
  
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const audioChunks = useRef<Blob[]>([])
  const animationFrame = useRef<number | undefined>(undefined)
  const audioContext = useRef<AudioContext | undefined>(undefined)
  const analyzer = useRef<AnalyserNode | undefined>(undefined)
  const startTime = useRef<number>(0)

  const updateVisualizer = useCallback(() => {
    if (!analyzer.current) return
    
    const dataArray = new Uint8Array(analyzer.current.frequencyBinCount)
    analyzer.current.getByteFrequencyData(dataArray)
    
    // Convert to normalized values between 0-1
    const normalizedData = Array.from(dataArray)
      .slice(0, 32) // Take first 32 frequency bands
      .map(value => value / 255)
    
    setState(prev => ({
      ...prev,
      visualizerData: normalizedData,
      duration: (Date.now() - startTime.current) / 1000
    }))
    
    animationFrame.current = requestAnimationFrame(updateVisualizer)
  }, [])

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      // Set up audio context and analyzer
      audioContext.current = new AudioContext()
      const source = audioContext.current.createMediaStreamSource(stream)
      analyzer.current = audioContext.current.createAnalyser()
      analyzer.current.fftSize = 256
      source.connect(analyzer.current)
      
      mediaRecorder.current = new MediaRecorder(stream)
      audioChunks.current = []
      
      mediaRecorder.current.ondataavailable = (event) => {
        audioChunks.current.push(event.data)
      }
      
      mediaRecorder.current.onstop = () => {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/wav' })
        const audioUrl = URL.createObjectURL(audioBlob)
        setState(prev => ({ ...prev, audioUrl, isRecording: false }))
      }
      
      mediaRecorder.current.start()
      startTime.current = Date.now()
      updateVisualizer()
      setState(prev => ({ ...prev, isRecording: true, error: null, audioUrl: null }))
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: 'Microphone access denied or not available',
        isRecording: false
      }))
    }
  }, [updateVisualizer])

  const stopRecording = useCallback(() => {
    if (mediaRecorder.current && state.isRecording) {
      mediaRecorder.current.stop()
      mediaRecorder.current.stream.getTracks().forEach(track => track.stop())
    }
    
    if (animationFrame.current) {
      cancelAnimationFrame(animationFrame.current)
    }
    
    if (audioContext.current) {
      audioContext.current.close()
    }
    
    setState(prev => ({
      ...prev,
      isRecording: false,
      visualizerData: []
    }))
  }, [state.isRecording])

  const clearRecording = useCallback(() => {
    if (state.audioUrl) {
      URL.revokeObjectURL(state.audioUrl)
    }
    setState(prev => ({
      ...prev,
      audioUrl: null,
      duration: 0,
      visualizerData: []
    }))
  }, [state.audioUrl])

  return {
    ...state,
    startRecording,
    stopRecording,
    clearRecording
  }
} 