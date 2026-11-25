import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Bot, BookOpen, RotateCcw, SendHorizonal, Wrench } from 'lucide-react'
import Markdown from 'react-markdown'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useAuth } from '@/features/auth/auth-context'
import { api } from '@/lib/api/endpoints'
import type { ChatMessage, ChatSource, ChatToolCall, Role } from '@/lib/types'
import { cn, initials } from '@/lib/utils'

interface UiMessage extends ChatMessage {
  tool_calls?: ChatToolCall[]
  sources?: ChatSource[]
  error?: boolean
}

/** How many previous turns we send back to the model for multi-turn context. */
const HISTORY_LIMIT = 20
const STORAGE_KEY = 'baribhara.chat'

const SUGGESTIONS: Record<Role, string[]> = {
  tenant: ['How much rent do I owe?', 'Is the gas bill included in the service charge?', 'How much notice do I need to give before moving out?', 'My kitchen tap is leaking'],
  admin: ["How is this month's collection?", 'Show vacant flats in Mirpur under 20k', 'What does the Rent Control Act say about raising rent?', 'What time is the main gate locked?'],
  staff: ['Show vacant flats', 'What are the rules for overnight guests?', 'When is garbage collected?', 'How do tenants recharge the DESCO meter?'],
}

const TOOL_LABELS: Record<string, string> = {
  get_my_rent_status: 'Checked your rent records',
  list_vacant_flats: 'Searched vacant flats',
  create_maintenance_request: 'Created a maintenance request',
  get_collection_summary: 'Calculated collection summary',
  search_knowledge: 'Searched building documents',
}

function loadHistory(userId: number): UiMessage[] {
  try {
    const raw = sessionStorage.getItem(`${STORAGE_KEY}.${userId}`)
    return raw ? (JSON.parse(raw) as UiMessage[]) : []
  } catch {
    return []
  }
}

export default function AssistantPage() {
  const { user } = useAuth()
  const [messages, setMessages] = useState<UiMessage[]>(() => (user ? loadHistory(user.id) : []))
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const send = useMutation({ mutationFn: api.chat.send })

  useEffect(() => {
    if (user) sessionStorage.setItem(`${STORAGE_KEY}.${user.id}`, JSON.stringify(messages))
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, user])

  if (!user) return null

  async function submit(text: string) {
    const message = text.trim()
    if (!message || send.isPending) return
    // Only successful turns go back to the model as context
    const history: ChatMessage[] = messages
      .filter((m) => !m.error)
      .slice(-HISTORY_LIMIT)
      .map(({ role, content }) => ({ role, content }))
    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setInput('')
    try {
      const res = await send.mutateAsync({ message, history })
      setMessages((prev) => [...prev, { role: 'assistant', content: res.reply, tool_calls: res.tool_calls, sources: res.sources }])
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: (err as Error).message, error: true }])
    }
    inputRef.current?.focus()
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    void submit(input)
  }
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      void submit(input)
    }
  }

  return (
    <div className="flex h-[calc(100dvh-7.5rem)] flex-col lg:h-[calc(100dvh-4rem)]">
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">AI assistant</h1>
          <p className="mt-1 text-sm text-stone-500">Ask about rent, flats, repairs or house rules — in Bangla or English.</p>
        </div>
        {messages.length > 0 && (
          <Button variant="secondary" size="sm" onClick={() => setMessages([])}>
            <RotateCcw className="h-4 w-4" /> New chat
          </Button>
        )}
      </div>

      <Card className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex-1 space-y-5 overflow-y-auto px-4 py-5 sm:px-6">
          {messages.length === 0 ? (
            <div className="mx-auto flex h-full max-w-lg flex-col items-center justify-center text-center">
              <div className="mb-4 rounded-2xl bg-brand-50 p-4 text-brand-700">
                <Bot className="h-8 w-8" />
              </div>
              <h2 className="text-lg font-semibold">How can I help?</h2>
              <p className="mt-1 mb-6 text-sm text-stone-500">I can look up your records and answer from the building's rules and agreement.</p>
              <div className="grid w-full gap-2 sm:grid-cols-2">
                {SUGGESTIONS[user.role].map((s) => (
                  <button
                    key={s}
                    onClick={() => void submit(s)}
                    className="rounded-xl border border-stone-200 bg-white px-4 py-3 text-left text-sm text-stone-700 shadow-sm transition-colors hover:border-brand-300 hover:bg-brand-50/50"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => <MessageBubble key={i} message={m} userInitials={initials(user.full_name)} />)
          )}
          {send.isPending && (
            <div className="flex gap-3">
              <Avatar bot />
              <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm bg-stone-100 px-4 py-3">
                {[0, 150, 300].map((d) => (
                  <span key={d} className="h-2 w-2 animate-bounce rounded-full bg-stone-400" style={{ animationDelay: `${d}ms` }} />
                ))}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form onSubmit={onSubmit} className="border-t border-stone-200 bg-white p-3 sm:p-4">
          <div className="flex items-end gap-2 rounded-xl border border-stone-300 bg-white p-1.5 pl-3 shadow-sm focus-within:border-brand-600 focus-within:ring-2 focus-within:ring-brand-600/20">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Type your question… (Enter to send, Shift+Enter for a new line)"
              className="max-h-32 min-h-9 flex-1 resize-none bg-transparent py-2 text-sm placeholder:text-stone-400 focus:outline-none"
              aria-label="Message"
            />
            <Button type="submit" size="icon" className="h-9 w-9" disabled={!input.trim()} loading={send.isPending} aria-label="Send">
              {!send.isPending && <SendHorizonal className="h-4 w-4" />}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}

function Avatar({ bot, label }: { bot?: boolean; label?: string }) {
  return (
    <div className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold', bot ? 'bg-brand-700 text-white' : 'bg-stone-200 text-stone-700')}>
      {bot ? <Bot className="h-4 w-4" /> : label}
    </div>
  )
}

function MessageBubble({ message, userInitials }: { message: UiMessage; userInitials: string }) {
  const isUser = message.role === 'user'
  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      <Avatar bot={!isUser} label={userInitials} />
      <div className={cn('flex max-w-[85%] flex-col gap-2 sm:max-w-[75%]', isUser && 'items-end')}>
        {!!message.tool_calls?.length && (
          <div className="flex flex-wrap gap-1.5">
            {message.tool_calls.map((t, i) => (
              <span
                key={i}
                title={`${t.name}(${JSON.stringify(t.arguments)})`}
                className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-700 ring-1 ring-violet-200 ring-inset"
              >
                <Wrench className="h-3 w-3" /> {TOOL_LABELS[t.name] ?? t.name}
              </span>
            ))}
          </div>
        )}
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
            isUser ? 'rounded-tr-sm bg-brand-700 text-white' : message.error ? 'rounded-tl-sm bg-red-50 text-red-700' : 'rounded-tl-sm bg-stone-100 text-stone-800',
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="space-y-2 [&_li]:ml-4 [&_ol]:list-decimal [&_strong]:font-semibold [&_ul]:list-disc">
              <Markdown>{message.content}</Markdown>
            </div>
          )}
        </div>
        {!!message.sources?.length && (
          <details className="w-full rounded-lg border border-stone-200 bg-white text-xs">
            <summary className="flex cursor-pointer items-center gap-1.5 px-3 py-2 font-medium text-stone-600">
              <BookOpen className="h-3.5 w-3.5" /> {message.sources.length} source{message.sources.length > 1 ? 's' : ''} from building documents
            </summary>
            <ul className="space-y-2 border-t border-stone-100 px-3 py-2">
              {message.sources.map((s, i) => (
                <li key={i}>
                  <div className="flex justify-between gap-2 font-medium text-stone-700">
                    <span>{s.title}</span>
                    <span className="text-stone-400 tabular-nums">{Math.round(s.score * 100)}% match</span>
                  </div>
                  <p className="mt-0.5 text-stone-500">{s.snippet}</p>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  )
}
