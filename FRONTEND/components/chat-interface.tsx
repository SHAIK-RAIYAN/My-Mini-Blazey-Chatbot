"use client"

import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Flame,
  Send,
  User,
  Sparkles,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Loader2,
  Terminal,
  ArrowRight,
  ListTodo,
  Users,
  PlusCircle,
  FolderGit2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardDescription } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useAgentChat } from "@/hooks/use-agent-chat"

const PROMPT_SUGGESTIONS = [
  {
    icon: ListTodo,
    title: "Check open tasks",
    prompt: "List all open tasks assigned to me with their priority and due dates.",
  },
  {
    icon: Users,
    title: "List team members",
    prompt: "List all employees currently registered in the system.",
  },
  {
    icon: PlusCircle,
    title: "Create personal task",
    prompt: "Create a new high-priority task titled 'Review Q3 API architecture' with status 'open'.",
  },
  {
    icon: FolderGit2,
    title: "Review project tasks",
    prompt: "List the top 5 most recent project tasks and their assignees.",
  },
]

export function ChatInterface() {
  const {
    messages,
    input,
    setInput,
    isLoading,
    pendingApproval,
    pendingAction,
    sendMessage,
    handleApproval,
    resetChat,
  } = useAgentChat()

  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const inputRef = React.useRef<HTMLInputElement>(null)

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isLoading, pendingApproval])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      if (input && input.trim() && !isLoading && !pendingApproval) {
        sendMessage()
      }
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input && input.trim() && !isLoading && !pendingApproval) {
      sendMessage()
    }
  }

  const handleSelectPrompt = (prompt: string) => {
    setInput(prompt)
    inputRef.current?.focus()
  }

  return (
    <div className="flex flex-1 flex-col h-[calc(100vh-3.5rem)] max-w-5xl mx-auto w-full px-4 sm:px-6 py-4">
      <div className="flex items-center justify-between pb-3 border-b border-border/60">
        <div className="flex items-center gap-2">
          <div className="size-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
            Agent Session Active
          </span>
        </div>
        {messages.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={resetChat}
            disabled={isLoading}
            className="h-7 text-xs text-muted-foreground hover:text-foreground gap-1.5"
          >
            <RotateCcw className="size-3.5" />
            <span>New Chat</span>
          </Button>
        )}
      </div>

      <ScrollArea className="flex-1 pr-4 my-3">
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
                Autonomous agent connected to your Employee and Project microservices with supervisor approval guards.
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
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.18 }}
                  className={`flex gap-3 ${
                    msg.role === "user"
                      ? "justify-end"
                      : msg.role === "system"
                      ? "justify-center"
                      : "justify-start"
                  }`}
                >
                  {msg.role === "assistant" && (
                    <Avatar size="sm" className="mt-1 border border-border">
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
                      <Avatar size="sm" className="mb-0.5 border border-border">
                        <AvatarFallback className="bg-muted text-muted-foreground text-xs">
                          <User className="size-3.5" />
                        </AvatarFallback>
                      </Avatar>
                    </div>
                  ) : msg.role === "tool" ? (
                    <div className="w-full max-w-2xl mx-auto my-1">
                      <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-muted/30 font-mono text-xs text-muted-foreground">
                        <Terminal className="size-3.5 shrink-0 text-foreground" />
                        <span className="font-semibold text-foreground">Tool Output:</span>
                        <span className="truncate">{msg.content}</span>
                      </div>
                    </div>
                  ) : msg.role === "system" ? (
                    <div className="my-1 px-3 py-1.5 rounded-full border border-border bg-muted/40 text-xs font-mono text-muted-foreground flex items-center gap-1.5">
                      <Sparkles className="size-3 text-foreground" />
                      <span>{msg.content}</span>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-2 max-w-[90%] sm:max-w-[80%]">
                      <Card size="sm" className="border-border bg-card shadow-xs">
                        <CardContent className="p-3.5 text-sm leading-relaxed whitespace-pre-wrap text-card-foreground">
                          {msg.content || (
                            <div className="flex items-center gap-2 text-muted-foreground">
                              <Loader2 className="size-3.5 animate-spin" />
                              <span className="text-xs font-mono">Analyzing request...</span>
                            </div>
                          )}
                        </CardContent>
                      </Card>

                      {msg.toolCalls && msg.toolCalls.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {msg.toolCalls.map((tc, idx) => (
                            <div
                              key={idx}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border bg-muted/40 text-[11px] font-mono text-muted-foreground"
                            >
                              <Terminal className="size-3 text-foreground" />
                              <span>Invoked:</span>
                              <span className="font-semibold text-foreground">{tc.name}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          )}

          {pendingApproval && (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2 }}
              className="w-full max-w-2xl mx-auto my-2"
            >
              <Card className="border-foreground/30 bg-card shadow-md">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-foreground font-semibold text-sm">
                      <ShieldAlert className="size-4" />
                      <span>Human Authorization Required</span>
                    </div>
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full border border-border bg-muted text-foreground">
                      HITL Interruption
                    </span>
                  </div>
                  <CardDescription className="text-xs text-muted-foreground mt-1">
                    The agent formulated a mutating action that requires explicit supervisor approval before execution.
                  </CardDescription>
                </CardHeader>
                <CardContent className="pb-3 text-xs">
                  <div className="rounded-lg border border-border bg-muted/50 p-2.5 font-mono text-[11px] overflow-x-auto">
                    <div className="font-bold text-foreground mb-1">
                      Action: {pendingAction?.name || "Mutating Operation"}
                    </div>
                    <pre className="text-muted-foreground whitespace-pre-wrap">
                      {JSON.stringify(pendingAction?.args || {}, null, 2)}
                    </pre>
                  </div>
                </CardContent>
                <div className="flex items-center justify-end gap-2 p-3 pt-0 border-t border-border/50">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleApproval(false)}
                    disabled={isLoading}
                    className="gap-1 text-xs"
                  >
                    <XCircle className="size-3.5" />
                    <span>Reject & Abort</span>
                  </Button>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => handleApproval(true)}
                    disabled={isLoading}
                    className="gap-1 text-xs bg-foreground text-background hover:bg-foreground/90"
                  >
                    {isLoading ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="size-3.5" />
                    )}
                    <span>Accept & Execute</span>
                  </Button>
                </div>
              </Card>
            </motion.div>
          )}

          {isLoading && !pendingApproval && (
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
      </ScrollArea>

      <div className="pt-2 border-t border-border/60">
        <form onSubmit={handleSubmit} className="relative flex items-center gap-2">
          <Input
            ref={inputRef}
            type="text"
            placeholder={
              pendingApproval
                ? "Approval required above to continue..."
                : isLoading
                ? "Agent is working..."
                : "Ask MyBlazey to manage tasks, team members, or check status..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading || pendingApproval}
            className="h-11 px-4 pr-12 rounded-xl bg-card border-border text-sm shadow-xs focus-visible:ring-1 focus-visible:ring-foreground"
          />
          <Button
            type="submit"
            size="icon"
            disabled={!input || !input.trim() || isLoading || pendingApproval}
            className="absolute right-1.5 size-8 rounded-lg bg-foreground text-background hover:bg-foreground/90 disabled:opacity-30 transition-opacity"
          >
            {isLoading ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Send className="size-4" />
            )}
            <span className="sr-only">Send message</span>
          </Button>
        </form>
        <p className="text-[11px] text-center text-muted-foreground mt-2 font-mono">
          Enter sends • Mutating actions pause for explicit supervisor approval
        </p>
      </div>
    </div>
  )
}
