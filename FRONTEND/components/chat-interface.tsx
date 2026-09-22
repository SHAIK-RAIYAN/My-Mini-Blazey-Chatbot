"use client"

import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Flame,
  Send,
  User,
  RotateCcw,
  Loader2,
  ArrowRight,
  ListTodo,
  Users,
  PlusCircle,
  FolderGit2,
  MessageSquare,
  Menu,
  Plus,
  History,
  Square,
} from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { useAgentChat } from "@/hooks/use-agent-chat"

const PROMPT_SUGGESTIONS = [
  {
    icon: FolderGit2,
    title: "My Profile",
    prompt: "Search for my profile details.",
  },
  {
    icon: PlusCircle,
    title: "Create Task",
    prompt: "Create a personal task to review API logs.",
  },
  {
    icon: Users,
    title: "Team Members",
    prompt: "Search for employees in my team.",
  },
  {
    icon: ListTodo,
    title: "Recent Tasks",
    prompt: "List 5 of my recent personal tasks.",
  },
]

function formatThreadId(id: string): string {
  if (!id) return "New Chat"
  return "New Chat"
}

function sanitizeAssistantContent(content: string): string {
  if (!content) return ""
  return content
    .replace(/^\s*\|?\s*(?:MongoDB\s*(?:Object)?ID|_id|Mongo\s*ID)\s*\|.*$\n?/gim, "")
    .replace(/(?:,\s*)?(?:\(?\s*MongoDB\s*(?:Object)?ID\s*:\s*[0-9a-fA-F]{24}\s*\)?)/gi, "")
    .replace(/\b[0-9a-fA-F]{24}\b/g, "")
}

export function ChatInterface() {
  const {
    messages,
    threads,
    input,
    setInput,
    isLoading,
    isAnalyzing,
    threadId,
    sendMessage,
    stopGeneration,
    createNewChat,
    selectThread,
  } = useAgentChat()

  const [isSidebarOpen, setIsSidebarOpen] = React.useState(false)
  const [isMobile, setIsMobile] = React.useState(false)
  const [mounted, setMounted] = React.useState(false)

  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  React.useEffect(() => {
    setMounted(true)
    const urlParams = new URLSearchParams(window.location.search)
    const urlThreadId = urlParams.get("thread")
    if (urlThreadId) {
      selectThread(urlThreadId)
    }
  }, [selectThread])

  React.useEffect(() => {
    const handlePopState = () => {
      const urlParams = new URLSearchParams(window.location.search)
      const urlThreadId = urlParams.get("thread")
      if (urlThreadId) {
        selectThread(urlThreadId)
      } else {
        createNewChat()
      }
    }
    window.addEventListener("popstate", handlePopState)
    return () => window.removeEventListener("popstate", handlePopState)
  }, [selectThread, createNewChat])

  React.useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      const nextHeight = Math.min(Math.max(textareaRef.current.scrollHeight, 44), 160)
      textareaRef.current.style.height = `${nextHeight}px`
    }
  }, [input])

  React.useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768
      setIsMobile(mobile)
      if (!mobile) {
        setIsSidebarOpen(true)
      } else {
        setIsSidebarOpen(false)
      }
    }
    handleResize()
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isLoading, isAnalyzing])

  const toggleSidebar = () => {
    setIsSidebarOpen((prev) => !prev)
  }

  const handleSelectThread = (tId: string) => {
    selectThread(tId)
    if (typeof window !== "undefined") {
      const newUrl = `/?thread=${encodeURIComponent(tId)}`
      if (window.location.search !== `?thread=${encodeURIComponent(tId)}`) {
        window.history.pushState({ threadId: tId }, "", newUrl)
      }
    }
    if (isMobile) setIsSidebarOpen(false)
  }

  const handleNewChat = () => {
    createNewChat()
    if (typeof window !== "undefined") {
      window.history.pushState({}, "", "/")
    }
    if (isMobile) setIsSidebarOpen(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      if (input && input.trim() && !isLoading) {
        if (typeof window !== "undefined" && threadId) {
          const expected = `?thread=${encodeURIComponent(threadId)}`
          if (window.location.search !== expected) {
            window.history.pushState({ threadId }, "", `/${expected}`)
          }
        }
        sendMessage()
      }
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input && input.trim() && !isLoading) {
      if (typeof window !== "undefined" && threadId) {
        const expected = `?thread=${encodeURIComponent(threadId)}`
        if (window.location.search !== expected) {
          window.history.pushState({ threadId }, "", `/${expected}`)
        }
      }
      sendMessage()
    }
  }

  const handleSelectPrompt = (prompt: string) => {
    setInput(prompt)
    textareaRef.current?.focus()
  }

  const renderThreadList = () => (
    <div className="flex flex-col h-full min-h-0">
      <div className="p-3 border-b border-border/60 flex-shrink-0">
        <Button
          variant="outline"
          onClick={handleNewChat}
          disabled={isLoading}
          className="w-full justify-start gap-2 h-9 text-xs font-medium border-border/80 bg-card hover:bg-muted/60"
        >
          <Plus className="size-4 text-foreground" />
          <span>New Chat</span>
        </Button>
      </div>

      <div className="px-3 pt-3 pb-1 flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-muted-foreground flex-shrink-0">
        <span className="flex items-center gap-1.5">
          <History className="size-3" />
          <span>Chat History</span>
        </span>
        <span className="text-[10px] px-1.5 py-0.2 rounded bg-muted/60">
          {threads.length}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-1 min-h-0">
        <div className="flex flex-col gap-1 pr-2">
          {threads.length === 0 ? (
            <div className="text-center py-8 text-xs text-muted-foreground font-mono">
              No saved threads found
            </div>
          ) : (
            threads.map((t: any) => {
              const tId = typeof t === "string" ? t : t.id
              const displayTitle = (typeof t === "object" && t?.title && t.title !== "Empty Session") ? t.title : "New Chat"
              const isActive = tId === threadId
              return (
                <button
                  key={tId}
                  type="button"
                  onClick={() => handleSelectThread(tId)}
                  className={`group flex items-center gap-2.5 w-full text-left px-2.5 py-2 rounded-lg text-xs transition-all ${
                    isActive
                      ? "bg-foreground text-background font-semibold shadow-xs"
                      : "text-foreground/80 hover:bg-muted/60 hover:text-foreground"
                  }`}
                >
                  <MessageSquare className={`size-3.5 shrink-0 ${isActive ? "text-background" : "text-muted-foreground group-hover:text-foreground"}`} />
                  <span className="truncate flex-1 font-mono text-[11px]">
                    {displayTitle}
                  </span>
                </button>
              )
            })
          )}
        </div>
      </div>
    </div>
  )

  const activeThread = threads.find((t: any) => (typeof t === "string" ? t : t.id) === threadId)
  const activeThreadTitle = (activeThread && typeof activeThread === "object" && activeThread.title && activeThread.title !== "Empty Session")
    ? activeThread.title
    : formatThreadId(threadId)

  return (
    <div className="h-full w-full flex overflow-hidden bg-background">
      <aside
        className={`h-full flex-shrink-0 border-r flex flex-col overflow-hidden border-border/60 bg-card/40 hidden md:flex transition-all duration-300 ease-in-out ${
          isSidebarOpen ? "w-64 opacity-100" : "w-0 opacity-0 border-r-0 pointer-events-none"
        }`}
      >
        <div className="w-64 h-full flex flex-col min-h-0">
          {renderThreadList()}
        </div>
      </aside>

      <Sheet open={isMobile && isSidebarOpen} onOpenChange={setIsSidebarOpen}>
        <SheetContent side="left" className="p-0 w-72 bg-card">
          <SheetHeader className="p-3 pb-0">
            <SheetTitle className="text-sm font-semibold flex items-center gap-2">
              <Flame className="size-4" />
              <span>Conversation Threads</span>
            </SheetTitle>
            <SheetDescription className="sr-only">
              Saved MongoDB conversation sessions
            </SheetDescription>
          </SheetHeader>
          <div className="flex-1 h-[calc(100vh-4rem)]">
            {renderThreadList()}
          </div>
        </SheetContent>
      </Sheet>

      <div className="flex-1 flex flex-col h-full overflow-hidden min-w-0 max-w-5xl mx-auto w-full">
        <div className="flex-shrink-0 flex items-center justify-between px-4 sm:px-6 py-3 border-b border-border/60">
          <div className="flex items-center gap-2.5">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
              className="size-8 text-muted-foreground hover:text-foreground"
              title="Toggle Sidebar"
            >
              <Menu className="size-4" />
              <span className="sr-only">Toggle Sidebar</span>
            </Button>
            <div className="flex items-center gap-2">
              <div
                className={`size-2 rounded-full ${
                  mounted && threadId ? "bg-emerald-500 animate-pulse" : "bg-muted"
                }`}
              />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Chat:
              </span>
              {mounted && threadId ? (
                <span
                  suppressHydrationWarning
                  className="text-xs font-mono font-medium text-foreground truncate max-w-[160px] sm:max-w-xs"
                >
                  {activeThreadTitle}
                </span>
              ) : (
                <span className="inline-block h-3.5 w-24 rounded bg-muted/60 animate-pulse" />
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleNewChat}
            disabled={isLoading}
            className="h-7 text-xs text-muted-foreground hover:text-foreground gap-1.5"
          >
            <RotateCcw className="size-3.5" />
            <span>New Chat</span>
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 min-h-0">
          <div className="flex flex-col gap-4 py-2">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center min-h-[50vh] text-center px-4 py-8">
                <div className="flex size-14 items-center justify-center rounded-2xl border border-border bg-card shadow-xs mb-4">
                  <Flame className="size-7 text-foreground" />
                </div>
                <h2 className="text-xl sm:text-2xl font-semibold tracking-tight text-foreground">
                  What can I help you orchestrate today?
                </h2>
                <p className="text-sm text-muted-foreground max-w-md mt-1 mb-8">
                  Autonomous agent connected to your Employee and Project microservices.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
                  {PROMPT_SUGGESTIONS.map((item, idx) => {
                    const Icon = item.icon
                    return (
                      <Card
                        key={idx}
                        size="sm"
                        onClick={() => handleSelectPrompt(item.prompt)}
                        className="group flex flex-col items-start p-3.5 rounded-xl border border-border bg-card text-left transition-all hover:border-foreground/40 hover:bg-muted/30 cursor-pointer"
                      >
                        <div className="flex items-center justify-between w-full mb-1">
                          <div className="flex items-center gap-2 font-medium text-sm text-foreground">
                            <Icon className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                            <span>{item.title}</span>
                          </div>
                          <ArrowRight className="size-3.5 text-muted-foreground opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {item.prompt}
                        </p>
                      </Card>
                    )
                  })}
                </div>
              </div>
            ) : (
              <AnimatePresence initial={false}>
                {messages.map((msg, idx) => {
                  if (msg.role === "system") {
                    return null
                  }
                  if (
                    msg.role === "assistant" &&
                    !msg.content &&
                    !isAnalyzing &&
                    messages[idx + 1]?.role === "tool"
                  ) {
                    return null
                  }
                  return (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.18 }}
                      className={`flex gap-3 ${
                        msg.role === "user"
                          ? "justify-end"
                          : "justify-start"
                      }`}
                    >
                    {msg.role === "assistant" && (
                      <Avatar size="sm" className="mt-1 border border-border shrink-0">
                        <AvatarFallback className="bg-foreground text-background text-xs font-semibold">
                          <Flame className="size-3.5 fill-current" />
                        </AvatarFallback>
                      </Avatar>
                    )}

                    {msg.role === "user" ? (
                      <div className="flex items-end gap-2 max-w-[85%] sm:max-w-[75%]">
                        <Card
                          size="sm"
                          className="rounded-2xl rounded-tr-xs border-0 bg-foreground text-background shadow-xs"
                        >
                          <CardContent className="p-3.5 text-sm leading-relaxed whitespace-pre-wrap font-medium">
                            {msg.content}
                          </CardContent>
                        </Card>
                        <Avatar size="sm" className="mb-0.5 border border-border shrink-0">
                          <AvatarFallback className="bg-muted text-muted-foreground text-xs">
                            <User className="size-3.5" />
                          </AvatarFallback>
                        </Avatar>
                      </div>
                    ) : msg.role === "tool" ? (
                      <div className="my-1 pl-11">
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border/60 bg-muted/30 font-mono text-xs text-muted-foreground">
                          <span>⚡ Invoked: {msg.name || (() => {
                            for (let i = idx - 1; i >= 0; i--) {
                              if (messages[i].toolCalls && messages[i].toolCalls!.length > 0) {
                                return messages[i].toolCalls![0].name
                              }
                            }
                            return "tool"
                          })()}</span>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col gap-2 max-w-[90%] sm:max-w-[80%] w-full">
                        {msg.content ? (
                          <Card size="sm" className="border-border bg-card shadow-xs">
                            <CardContent className="p-3.5 text-sm leading-relaxed text-card-foreground">
                              <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                  table: ({ children }) => (
                                    <div className="my-3 w-full overflow-x-auto rounded-lg border border-border">
                                      <table className="w-full text-left text-xs border-collapse">
                                        {children}
                                      </table>
                                    </div>
                                  ),
                                  thead: ({ children }) => (
                                    <thead className="bg-muted/60 border-b border-border text-foreground font-semibold">
                                      {children}
                                    </thead>
                                  ),
                                  tbody: ({ children }) => (
                                    <tbody className="divide-y divide-border/40 text-foreground">
                                      {children}
                                    </tbody>
                                  ),
                                  tr: ({ children }) => (
                                    <tr className="hover:bg-muted/30 transition-colors">
                                      {children}
                                    </tr>
                                  ),
                                  th: ({ children }) => (
                                    <th className="px-3 py-2 font-semibold text-foreground whitespace-nowrap">
                                      {children}
                                    </th>
                                  ),
                                  td: ({ children }) => (
                                    <td className="px-3 py-2 text-foreground/90 whitespace-nowrap">
                                      {children}
                                    </td>
                                  ),
                                  p: ({ children }) => (
                                    <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>
                                  ),
                                  ul: ({ children }) => (
                                    <ul className="list-disc pl-5 my-2 space-y-1">{children}</ul>
                                  ),
                                  ol: ({ children }) => (
                                    <ol className="list-decimal pl-5 my-2 space-y-1">{children}</ol>
                                  ),
                                  strong: ({ children }) => (
                                    <strong className="font-semibold text-foreground">{children}</strong>
                                  ),
                                }}
                              >
                                {sanitizeAssistantContent(msg.content)}
                              </ReactMarkdown>
                            </CardContent>
                          </Card>
                        ) : isAnalyzing && idx === messages.length - 1 ? (
                          <Card size="sm" className="border-border bg-card shadow-xs">
                            <CardContent className="p-3.5 text-sm leading-relaxed text-card-foreground">
                              <div className="flex items-center gap-2 text-muted-foreground">
                                <Loader2 className="size-3.5 animate-spin text-foreground" />
                                <span className="text-xs font-mono">Analyzing request...</span>
                              </div>
                            </CardContent>
                          </Card>
                        ) : null}

                        {msg.toolCalls && msg.toolCalls.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {msg.toolCalls.map((tc, tcIdx) => (
                              <div
                                key={tcIdx}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border/60 bg-muted/30 font-mono text-xs text-muted-foreground"
                              >
                                <span>⚡ Invoked: {tc.name}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </motion.div>
                  )
                })}
              </AnimatePresence>
            )}

            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-2 text-xs font-mono text-muted-foreground pl-10"
              >
                <Loader2 className="size-3.5 animate-spin text-foreground" />
                <span>Orchestrating agent response...</span>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="flex-shrink-0 p-4 border-t bg-background">
          <form onSubmit={handleSubmit} className="relative flex items-end w-full">
            <textarea
              ref={textareaRef}
              rows={1}
              placeholder="Ask MyBlazey to manage tasks, team members, or check status..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full min-h-[44px] max-h-[160px] py-2.5 pl-4 pr-12 rounded-xl bg-card border border-border text-sm shadow-xs outline-none focus-visible:ring-1 focus-visible:ring-foreground resize-none overflow-y-auto leading-relaxed disabled:opacity-50 disabled:cursor-not-allowed"
            />
            {isLoading ? (
              <Button
                type="button"
                variant="destructive"
                size="icon"
                onClick={stopGeneration}
                className="absolute right-2 bottom-1.5 size-8 rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-opacity shadow-xs"
              >
                <Square className="size-3.5 fill-current" />
                <span className="sr-only">Stop generation</span>
              </Button>
            ) : (
              <Button
                type="submit"
                size="icon"
                disabled={!input || !input.trim()}
                className="absolute right-2 bottom-1.5 size-8 rounded-lg bg-foreground text-background hover:bg-foreground/90 disabled:opacity-30 transition-opacity"
              >
                <Send className="size-4" />
                <span className="sr-only">Send message</span>
              </Button>
            )}
          </form>
          <p className="text-[11px] text-center text-muted-foreground mt-2 font-mono">
            Enter sends • Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}
