import { useState, useRef, useEffect, type KeyboardEvent, type ChangeEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, BriefcaseBusiness, Sparkles, User, Bot, AlertCircle, RotateCcw, Paperclip, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { ScrollArea } from '@/components/ui/scroll-area'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface DemoScenario {
  num: number
  title: string
  fullPrompt: string
  preview: string
}

const API_URL = '/api'

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [attachedPdf, setAttachedPdf] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [demoScenarios, setDemoScenarios] = useState<DemoScenario[]>([])
  const [scenariosLoading, setScenariosLoading] = useState(true)
  const [scenariosError, setScenariosError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const pdfInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setScenariosLoading(true)
      setScenariosError(null)
      try {
        const res = await fetch(`${API_URL}/scenarios`)
        if (!res.ok) {
          throw new Error(`Server responded with ${res.status}`)
        }
        const data = (await res.json()) as DemoScenario[]
        if (!cancelled) {
          setDemoScenarios(Array.isArray(data) ? data : [])
        }
      } catch {
        if (!cancelled) {
          setScenariosError('Could not load scenario shortcuts. Is the API running?')
          setDemoScenarios([])
        }
      } finally {
        if (!cancelled) setScenariosLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`
    }
  }, [input])

  const resetToHome = () => {
    setMessages([])
    setInput('')
    setAttachedPdf(null)
    setError(null)
    if (pdfInputRef.current) pdfInputRef.current.value = ''
  }

  const sendMessage = async (text?: string) => {
    const trimmed = (text ?? input).trim()
    if ((!trimmed && !attachedPdf) || loading) return

    setError(null)
    const attachNote = attachedPdf ? `\n\n(Attached PDF: ${attachedPdf.name})` : ''
    const userMessage: Message = { role: 'user', content: trimmed + attachNote }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const fd = new FormData()
      fd.append('message', trimmed)
      if (attachedPdf) fd.append('file', attachedPdf)

      const res = await fetch(`${API_URL}/send`, {
        method: 'POST',
        body: fd,
      })

      if (!res.ok) {
        const errText = await res.text()
        throw new Error(errText || `Server responded with ${res.status}`)
      }

      const data = await res.json()
      const assistantMessage: Message = {
        role: 'assistant',
        content: data.output || 'No response received.',
      }
      setMessages(prev => [...prev, assistantMessage])
      setAttachedPdf(null)
      if (pdfInputRef.current) pdfInputRef.current.value = ''
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

  const onPickPdf = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    if (!f.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported.')
      e.target.value = ''
      return
    }
    setError(null)
    setAttachedPdf(f)
  }

  return (
    <div className="flex flex-col h-screen bg-background">
      <header className="flex items-center justify-between gap-3 px-6 py-4 border-b border-border bg-card">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10 shrink-0">
            <BriefcaseBusiness className="w-5 h-5 text-primary" />
          </div>
          <div className="min-w-0">
            <h1 className="text-base font-semibold text-foreground tracking-tight">Sales Agent</h1>
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
                <h2 className="text-xl font-semibold text-foreground mb-6">How can I help you today?</h2>
                <h3 className="text-sm font-semibold text-foreground tracking-tight mb-3 w-full max-w-3xl text-left">
                  Frequently asked questions
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-3xl">
                  {scenariosLoading && (
                    <p className="text-sm text-muted-foreground col-span-full text-center py-4">
                      Loading scenarios…
                    </p>
                  )}
                  {scenariosError && !scenariosLoading && (
                    <p className="text-sm text-destructive col-span-full text-center py-4">{scenariosError}</p>
                  )}
                  {!scenariosLoading &&
                    !scenariosError &&
                    demoScenarios.map((scenario) => (
                      <button
                        key={scenario.num}
                        type="button"
                        onClick={() => sendMessage(scenario.fullPrompt)}
                        className="text-left text-sm px-4 py-3 rounded-xl border border-border bg-card hover:bg-accent hover:border-ring/40 transition-colors text-foreground"
                      >
                        <span className="font-medium text-foreground block">{scenario.title}</span>
                        <span className="text-xs text-muted-foreground mt-1 block line-clamp-2">
                          {scenario.preview}
                        </span>
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
          <input
            ref={pdfInputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={onPickPdf}
          />
          {attachedPdf && (
            <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-secondary/40 px-2.5 py-1 text-foreground max-w-[min(100%,280px)]">
                <span className="truncate" title={attachedPdf.name}>{attachedPdf.name}</span>
                <button
                  type="button"
                  onClick={() => {
                    setAttachedPdf(null)
                    if (pdfInputRef.current) pdfInputRef.current.value = ''
                  }}
                  className="shrink-0 rounded p-0.5 hover:bg-secondary"
                  aria-label="Remove attachment"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </span>
            </div>
          )}
          <div className="flex items-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="icon"
              disabled={loading}
              className="h-10 w-10 shrink-0"
              title="Attach PDF"
              onClick={() => pdfInputRef.current?.click()}
            >
              <Paperclip className="w-4 h-4" />
            </Button>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message…"
              rows={1}
              disabled={loading}
              className="flex-1 min-w-0 bg-input/30 border border-input rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-ring focus:ring-2 focus:ring-ring/50 resize-none disabled:opacity-50"
            />
            <Button
              size="icon"
              onClick={() => sendMessage()}
              disabled={(!input.trim() && !attachedPdf) || loading}
              className="h-10 w-10 shrink-0"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-3">
            PDF only. Press Enter to send, Shift + Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}

export default App
