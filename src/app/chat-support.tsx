"use client"

import { useChat } from "ai/react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar } from "@/components/ui/avatar"
import { ScrollArea } from "@/components/ui/scroll-area"

interface Message {
  id: string
  role: "user" | "assistant" | "system" | "data"
  content: string
}

export default function ChatSupport() {
  const { messages: aiMessages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: "http://localhost:8000/api/chat",
  })

  // Convert AI messages to our Message format
  const messages: Message[] = aiMessages.map(msg => ({
    id: msg.id,
    role: msg.role,
    content: msg.content
  }))

  const lastMessage = messages.at(-1)
  const isEmpty = messages.length === 0
  const isTyping = lastMessage?.role === "user"

  return (
    <Card className="h-full">
      <CardContent className="flex flex-col h-full p-6">
        <div className="flex flex-col space-y-4 h-full">
          {!isEmpty ? (
            <ScrollArea className="flex-1 pr-4">
              <div className="space-y-4 pt-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`flex items-start gap-3 max-w-[80%] ${
                        message.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      } p-3 rounded-lg`}
                    >
                      {message.role !== "user" && (
                        <Avatar>
                          <div className="w-10 h-10 flex items-center justify-center bg-primary-foreground text-primary font-semibold rounded-full">
                            AI
                          </div>
                        </Avatar>
                      )}
                      <div>
                        <p className="text-sm">{message.content}</p>
                      </div>
                    </div>
                  </div>
                ))}
                {isTyping && (
                  <div className="flex justify-start">
                    <div className="bg-muted p-3 rounded-lg">
                      <p className="text-sm">Typing...</p>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-center text-muted-foreground">
                Ask me anything about your Confluence documentation!
              </p>
            </div>
          )}

          <form 
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit(e);
            }}
            className="flex items-center space-x-2"
          >
            <Input
              value={input}
              onChange={handleInputChange}
              placeholder="Ask a question..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button type="submit" disabled={isLoading || !input.trim()}>
              Send
            </Button>
          </form>
        </div>
      </CardContent>
    </Card>
  )
} 