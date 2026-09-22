"use client"

import { useState, useCallback, useRef, useEffect } from "react"

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "tool" | "system"
  content: string
  name?: string
  node?: string
  toolCalls?: Array<{
    name: string
    args: Record<string, unknown>
    id?: string
  }>
  timestamp: number
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

export interface ThreadItem {
  id: string
  title: string
}

let initialThreadsLoaded = false

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [threads, setThreads] = useState<ThreadItem[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [threadId, setThreadId] = useState<string>("")

  const abortControllerRef = useRef<AbortController | null>(null)
  const isFetchingThreadsRef = useRef(false)

  useEffect(() => {
    setThreadId(`thread-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`)
  }, [])

  const fetchThreads = useCallback(async () => {
    if (isFetchingThreadsRef.current) return
    isFetchingThreadsRef.current = true
    try {
      const res = await fetch(`${BACKEND_URL}/api/chat/threads`)
      if (res.ok) {
        const data = await res.json()
        const rawList = Array.isArray(data) ? data : data.threads || []
        const normalized: ThreadItem[] = rawList.map((item: any) => {
          if (typeof item === "string") {
            return { id: item, title: "New Chat" }
          }
          return {
            id: item.id || "",
            title: item.title && item.title !== "Empty Session" ? item.title : "New Chat",
          }
        })
        setThreads(normalized)
      }
    } catch {} finally {
      isFetchingThreadsRef.current = false
    }
  }, [])

  useEffect(() => {
    if (initialThreadsLoaded) return
    initialThreadsLoaded = true
    fetchThreads()
  }, [fetchThreads])

  const selectThread = useCallback(async (selectedId: string) => {
    if (!selectedId || (selectedId === threadId && messages.length > 0)) return
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setIsLoading(true)
    setIsAnalyzing(false)
    setThreadId(selectedId)

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat/history/${encodeURIComponent(selectedId)}`)
      if (res.ok) {
        const data = await res.json()
        const historyMsgs = data.messages || []
        setMessages(historyMsgs)
      } else {
        setMessages([])
      }
    } catch {
      setMessages([])
    } finally {
      setIsLoading(false)
    }
  }, [threadId, messages.length])

  const createNewChat = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setMessages([])
    setInput("")
    setIsLoading(false)
    setIsAnalyzing(false)
    setThreadId(`thread-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`)
  }, [])

  const processSSE = useCallback(async (response: Response, currentAssistantId: string) => {
    if (!response.body) return
    const reader = response.body.getReader()
    const decoder = new TextDecoder("utf-8")
    let buffer = ""

    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed) continue

          const jsonStr = trimmed.startsWith("data:")
            ? trimmed.replace(/^data:\s*/, "")
            : trimmed
          if (!jsonStr) continue

          try {
            const data = JSON.parse(jsonStr)

            if (data.error) {
              setMessages((prev) => [
                ...prev,
                {
                  id: `err-${Date.now()}`,
                  role: "assistant",
                  content: `Error: ${data.error}`,
                  timestamp: Date.now(),
                },
              ])
              setIsLoading(false)
              setIsAnalyzing(false)
              continue
            }

            if (data.node === "call_model" && data.message) {
              const rawContent = data.message.content
              let msgContent = ""
              if (typeof rawContent === "string") {
                msgContent = rawContent
              } else if (Array.isArray(rawContent)) {
                msgContent = rawContent
                  .map((item: any) => (typeof item === "string" ? item : item?.text || ""))
                  .join("")
              } else if (rawContent && typeof rawContent === "object") {
                msgContent = (rawContent as any).text || JSON.stringify(rawContent)
              }
              const toolCalls = data.message.tool_calls || []

              if (msgContent.trim() !== "" || toolCalls.length > 0) {
                setIsAnalyzing(false)
              }

              const targetId =
                data.message.id ||
                (toolCalls.length > 0
                  ? `${currentAssistantId}-tools`
                  : `${currentAssistantId}-response`)

              setMessages((prev) => {
                const existingIndex = prev.findIndex((m) => m.id === targetId)
                if (existingIndex >= 0) {
                  const updated = [...prev]
                  updated[existingIndex] = {
                    ...updated[existingIndex],
                    content: msgContent || updated[existingIndex].content,
                    toolCalls: toolCalls.length > 0 ? toolCalls : updated[existingIndex].toolCalls,
                    node: "call_model",
                  }
                  return updated
                } else if (msgContent || toolCalls.length > 0) {
                  return [
                    ...prev,
                    {
                      id: targetId,
                      role: "assistant",
                      content: msgContent,
                      toolCalls,
                      node: "call_model",
                      timestamp: Date.now(),
                    },
                  ]
                }
                return prev
              })
            }

            if (data.node === "execute_tools" && data.message) {
              setIsAnalyzing(false)
              const rawResult = data.message.content
              const toolResult = typeof rawResult === "string" ? rawResult : JSON.stringify(rawResult)
              const toolMsgId =
                data.message.id ||
                `tool-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
              if (toolResult) {
                setMessages((prev) => {
                  const existingIdx = prev.findIndex((m) => m.id === toolMsgId)
                  if (existingIdx >= 0) {
                    const updated = [...prev]
                    updated[existingIdx] = {
                      ...updated[existingIdx],
                      content: toolResult,
                      name: data.message?.name || updated[existingIdx].name,
                    }
                    return updated
                  }
                  return [
                    ...prev,
                    {
                      id: toolMsgId,
                      role: "tool",
                      name:
                        data.message?.name ||
                        (data.message?.tool_calls && data.message.tool_calls[0]?.name) ||
                        "",
                      content: toolResult,
                      node: "execute_tools",
                      timestamp: Date.now(),
                    },
                  ]
                })
              }
            }

            if (data.done) {
              setIsLoading(false)
              setIsAnalyzing(false)
              setMessages((prev) =>
                prev.filter(
                  (m) =>
                    m.role === "tool" ||
                    m.role === "system" ||
                    m.content.trim() !== "" ||
                    (m.toolCalls && m.toolCalls.length > 0)
                )
              )
              fetchThreads()
              try {
                await reader.cancel()
              } catch {}
              break
            }
          } catch {}
        }
      }
    } finally {
      setIsLoading(false)
      setIsAnalyzing(false)
    }
  }, [fetchThreads])

  const sendMessage = useCallback(
    async (overrideText?: string) => {
      const text = (overrideText !== undefined ? overrideText : input).trim()
      if (!text || isLoading) return

      const activeThreadId = threadId || `thread-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
      if (!threadId) {
        setThreadId(activeThreadId)
      }

      const displayTitle = text.length > 35 ? `${text.slice(0, 35)}...` : text
      setThreads((prev) => {
        const existing = prev.find((t) => t.id === activeThreadId)
        const titleToUse = existing?.title && existing.title !== "New Chat" ? existing.title : displayTitle
        const remaining = prev.filter((t) => t.id !== activeThreadId)
        return [{ id: activeThreadId, title: titleToUse }, ...remaining]
      })

      setInput("")
      setIsLoading(true)
      setIsAnalyzing(true)

      const userMsgId = `user-${Date.now()}`
      const assistantMsgId = `assistant-${Date.now()}`

      const userMessage: ChatMessage = {
        id: userMsgId,
        role: "user",
        content: text,
        timestamp: Date.now(),
      }

      setMessages((prev) => [...prev, userMessage])

      try {
        abortControllerRef.current = new AbortController()
        const response = await fetch(`${BACKEND_URL}/api/chat/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            thread_id: activeThreadId,
            message: text,
          }),
          signal: abortControllerRef.current.signal,
        })

        if (!response.ok) {
          const errText = await response.text()
          setMessages((prev) => [
            ...prev,
            {
              id: `err-${Date.now()}`,
              role: "assistant",
              content: `Request failed (${response.status}): ${errText || "Unknown error"}`,
              timestamp: Date.now(),
            },
          ])
          setIsLoading(false)
          setIsAnalyzing(false)
          return
        }

        await processSSE(response, assistantMsgId)
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          setIsLoading(false)
          setIsAnalyzing(false)
          return
        }
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            role: "assistant",
            content: `Connection error: Could not reach agent backend at ${BACKEND_URL}`,
            timestamp: Date.now(),
          },
        ])
        setIsLoading(false)
        setIsAnalyzing(false)
      }
    },
    [input, isLoading, threadId, processSSE]
  )

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsLoading(false)
    setIsAnalyzing(false)
  }, [])

  return {
    messages,
    threads,
    input,
    setInput,
    isLoading,
    isAnalyzing,
    threadId,
    setThreadId,
    sendMessage,
    stopGeneration,
    resetChat: createNewChat,
    createNewChat,
    selectThread,
    fetchThreads,
  }
}
