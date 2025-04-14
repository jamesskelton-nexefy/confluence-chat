"use client"

import ChatSupport from "./chat-support"

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      <header className="border-b">
        <div className="container mx-auto py-4">
          <h1 className="text-2xl font-bold">Confluence Chat</h1>
        </div>
      </header>
      <main className="flex-1 container mx-auto py-4">
        <div className="max-w-3xl mx-auto h-[calc(100vh-8rem)]">
          <ChatSupport />
        </div>
      </main>
    </div>
  )
}
