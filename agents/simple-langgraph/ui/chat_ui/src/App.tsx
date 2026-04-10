import { useState, useRef, useEffect, type KeyboardEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, BriefcaseBusiness, Sparkles, User, Bot, AlertCircle, RotateCcw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { ScrollArea } from '@/components/ui/scroll-area'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const API_URL = '/api'

/** Matches `prompt-scenarios/demo-prompts.txt` user text between --- blocks. `fullPrompt` is sent verbatim on click (no clipping). */
const DEMO_SCENARIOS: { title: string; preview: string; fullPrompt: string }[] = [
  {
    title: 'Demo 1: Customer notes (renewal call)',
    preview: 'Brightwave Technologies, CUST-8821, open issues',
    fullPrompt: `I have a renewal call with Brightwave Technologies in 10 minutes.
Can you pull up their account notes for customer ID CUST-8821 so
I can quickly scan what was discussed last time and whether there
are any open issues?`,
  },
  {
    title: "Demo 2: Today's inbound leads",
    preview: 'Pipeline review summary: who, company, deal stage',
    fullPrompt: `I need a quick look at today's inbound leads before my pipeline review.
Can you pull them up and give me a summary - who came in, what company
they're from, and what their deal stage is?`,
  },
  {
    title: 'Demo 3: Knowledge base pricing',
    preview: 'Enterprise pricing tiers and discount thresholds',
    fullPrompt: `A prospect just asked about volume discounts for an enterprise deal.
Can you search our knowledge base for the current enterprise pricing
tiers and discount thresholds so I can give them an accurate quote?`,
  },
  {
    title: 'Demo 4: Internal ops report (web)',
    preview: 'reports.acmecorp.com - highlights and risks',
    fullPrompt: `Can you grab the content from our internal ops report at
https://reports.acmecorp.com/q4-ops.html and give me the key
highlights? Just the top action items and any risks flagged.`,
  },
  {
    title: 'Demo 5: Competitive analysis PDF (URL)',
    preview: 'internal.acmecorp.com competitive analysis summary',
    fullPrompt: `I need to review the competitive analysis document at
https://internal.acmecorp.com/competitive-analysis-2026.pdf.
Can you fetch it and give me a summary of the key findings
and how we compare to the main competitors?`,
  },
  {
    title: 'Demo 6: Local PDF summary',
    preview: 'Q4 Operations Report.pdf - bullet summary for CFO',
    fullPrompt: `I have a meeting with the CFO today. Read the contents from the document : Q4 Operations Report.pdf
Then summarise the main points as bullet points.`,
  },
]

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

  const resetToHome = () => {
    setMessages([])
    setInput('')
    setError(null)
  }

  const sendMessage = async (text?: string) => {
    const trimmed = (text ?? input).trim()
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
      <header className="flex items-center justify-between gap-3 px-6 py-4 border-b border-border bg-card">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10 shrink-0">
            <BriefcaseBusiness className="w-5 h-5 text-primary" />
          </div>
          <div className="min-w-0">
            <h1 className="text-base font-semibold text-foreground tracking-tight">Sales Assistant</h1>
            <p className="text-xs text-muted-foreground">Powered by LangGraph</p>
          </div>
        </div>
        {(messages.length > 0 || error) && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={loading}
            onClick={resetToHome}
            className="shrink-0 gap-1.5"
            title="Clear chat and show scenario shortcuts again (same as refreshing the page)"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            New chat
          </Button>
        )}
      </header>

      <ScrollArea className="flex-1">
        <div className="px-4 py-6">
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.length === 0 && !loading && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 mb-6">
                  <Sparkles className="w-8 h-8 text-primary" />
                </div>
                <h2 className="text-xl font-semibold text-foreground mb-2">How can I help you today?</h2>
                <p className="text-sm text-muted-foreground max-w-md mb-2">
                  Ask me about customers, leads, documents, or anything in your CRM.
                </p>
                <p className="text-xs text-muted-foreground max-w-md mb-8">
                  Pick a demo scenario below. The full prompt from <code className="text-[0.8rem] px-1 rounded bg-secondary">demo-prompts.txt</code> is sent when you click (nothing is clipped). Use New chat in the header or refresh the page to return here.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-3xl">
                  {DEMO_SCENARIOS.map((scenario, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => sendMessage(scenario.fullPrompt)}
                      className="text-left text-sm px-4 py-3 rounded-xl border border-border bg-card hover:bg-accent hover:border-ring/40 transition-colors text-foreground"
                    >
                      <span className="font-medium text-foreground block">{scenario.title}</span>
                      <span className="text-xs text-muted-foreground mt-1 block line-clamp-2">{scenario.preview}</span>
                    </button>
                  ))}
                </div>
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
              onClick={() => sendMessage()}
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
