'use client'

import { FormEvent, useState } from 'react'
import axios from 'axios'
import { Card } from "@/components/ui/card"
import { ChatMessage } from "@/components/ui/chat-message"
import { MessageInput } from "@/components/ui/message-input"
import { MessageList } from "@/components/ui/message-list"

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user', 
      content: input
    }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await axios.post('http://localhost:8000/api/chat', {
        query: input,
        conversation_history: messages.map(({ role, content }) => ({ role, content }))
      })
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.data.response
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error:', error)
      // Add error message to chat
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, there was an error processing your request.'
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="container mx-auto p-4 max-w-4xl h-[calc(100vh-4rem)]">
      <Card className="h-full">
        <div className="h-full flex flex-col">
          <div className="flex-1 overflow-y-auto">
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                Ask me anything about your Confluence documentation!
              </div>
            ) : (
              <MessageList messages={messages} />
            )}
            {isLoading && (
              <ChatMessage
                id="loading"
                role="assistant"
                content="..."
              />
            )}
          </div>
          <form onSubmit={handleSubmit} className="flex items-end gap-2">
            <div className="flex-1">
              <MessageInput
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                isGenerating={isLoading}
                submitOnEnter={true}
                allowAttachments={false}
              />
            </div>
          </form>
        </div>
      </Card>
    </div>
  )
}