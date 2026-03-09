import { useState, useRef, useEffect, type KeyboardEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, MessageSquare, Sparkles, User, Bot, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { ScrollArea } from '@/components/ui/scroll-area'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const API_URL = '/api'

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`
    }
  }, [input])

  const sendMessage = async () => {
    const trimmed = input.trim()
    if (!trimmed || loading) return

    setError(null)
    const userMessage: Message = { role: 'user', content: trimmed }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed }),
      })

      if (!res.ok) throw new Error(`Server responded with ${res.status}`)

      const data = await res.json()
      const assistantMessage: Message = {
        role: 'assistant',
        content: data.output || 'No response received.',
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setLoading(false)
      textareaRef.current?.focus()
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-screen bg-background">
      <header className="flex items-center gap-3 px-6 py-4 border-b border-border bg-card">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10">
          <MessageSquare className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-base font-semibold text-foreground tracking-tight">Research Assistant</h1>
          <p className="text-xs text-muted-foreground">Powered by OpenAI SDK</p>
        </div>
      </header>

      <ScrollArea className="flex-1">
        <div className="px-4 py-6">
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.length === 0 && !loading && (
              <div className="flex flex-col items-center justify-center py-24 text-center">
                <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 mb-6">
                  <Sparkles className="w-8 h-8 text-primary" />
                </div>
                <h2 className="text-xl font-semibold text-foreground mb-2">How can I help you?</h2>
                <p className="text-sm text-muted-foreground max-w-sm">
                  Ask me anything — I can search the web, look things up, and help with your research.
                </p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={cn(
                  'flex gap-3',
                  msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                )}
              >
                <Avatar className="w-8 h-8 shrink-0">
                  <AvatarFallback className={cn(
                    'text-xs font-medium',
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-primary/10 text-primary'
                  )}>
                    {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </AvatarFallback>
                </Avatar>

                <div className={cn(
                  'max-w-[85%] rounded-2xl px-4 py-2.5 text-sm',
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-card ring-1 ring-border'
                )}>
                  {msg.role === 'assistant' ? (
                    <div className="prose-chat">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-3">
                <Avatar className="w-8 h-8 shrink-0">
                  <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
                    <Bot className="w-4 h-4" />
                  </AvatarFallback>
                </Avatar>
                <div className="bg-card ring-1 ring-border rounded-2xl px-4 py-2.5">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                    <span className="w-2 h-2 rounded-full bg-primary animate-pulse [animation-delay:150ms]" />
                    <span className="w-2 h-2 rounded-full bg-primary animate-pulse [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div className="flex items-center justify-center">
                <div className="flex items-center gap-2 bg-destructive/10 ring-1 ring-destructive/20 rounded-lg px-4 py-2.5 text-destructive text-sm">
                  <AlertCircle className="w-4 h-4" />
                  <span>Failed to get response: {error}</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
      </ScrollArea>

      <div className="px-4 py-4 border-t border-border bg-card">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-3">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message…"
              rows={1}
              disabled={loading}
              className="flex-1 bg-input/30 border border-input rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-ring focus:ring-2 focus:ring-ring/50 resize-none disabled:opacity-50"
            />
            <Button
              size="icon"
              onClick={sendMessage}
              disabled={!input.trim() || loading}
              className="h-10 w-10 shrink-0"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-3">
            Press Enter to send, Shift + Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}

export default App
