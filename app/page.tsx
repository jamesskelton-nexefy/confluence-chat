import { Chat } from './components/chat'

export default function Home() {
  return (
    <main className="min-h-screen bg-[hsl(var(--background))]">
      <header className="border-[hsl(var(--border))]">
        <div className="container mx-auto px-4 h-16 flex items-center">
          <h1 className="text-xl font-semibold text-[hsl(var(--foreground))]">Confluence Chat</h1>
        </div>
      </header>
      <Chat />
    </main>
  )
} 