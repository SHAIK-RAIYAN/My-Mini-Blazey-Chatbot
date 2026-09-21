"use client"

import { useState, useCallback, useRef } from "react"

export interface PendingAction {
  name: string
  args: Record<string, unknown>
  id?: string
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "tool" | "system"
  content: string
  node?: string
  toolCalls?: Array<{
    name: string
    args: Record<string, unknown>
    id?: string
  }>
  pendingAction?: PendingAction | null
  requiresApproval?: boolean
  timestamp: number
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [pendingApproval, setPendingApproval] = useState(false)
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null)
  const [threadId, setThreadId] = useState<string>(
    () => `thread-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
  )

  const abortControllerRef = useRef<AbortController | null>(null)

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
              continue
            }

            if (data.requires_approval) {
              setPendingApproval(true)
              if (data.pending_action) {
                setPendingAction(data.pending_action)
              }
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

              setMessages((prev) => {
                const isAfterTool = prev.length > 0 && prev.some((m) => m.role === "tool")
                const targetId = isAfterTool ? `${currentAssistantId}-final` : currentAssistantId

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
              const rawResult = data.message.content
              const toolResult = typeof rawResult === "string" ? rawResult : JSON.stringify(rawResult)
              if (toolResult) {
                setMessages((prev) => [
                  ...prev,
                  {
                    id: `tool-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                    role: "tool",
                    content: toolResult,
                    node: "execute_tools",
                    timestamp: Date.now(),
                  },
                ])
              }
            }

            if (data.done) {
              setIsLoading(false)
            }
          } catch {}
        }
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const sendMessage = useCallback(
    async (overrideText?: string) => {
      const text = (overrideText !== undefined ? overrideText : input).trim()
      if (!text || isLoading || pendingApproval) return

      setInput("")
      setIsLoading(true)

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
            thread_id: threadId,
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
          return
        }

        await processSSE(response, assistantMsgId)
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          setIsLoading(false)
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
      }
    },
    [input, isLoading, pendingApproval, threadId, processSSE]
  )

  const handleApproval = useCallback(
    async (approved: boolean) => {
      if (!pendingApproval || isLoading) return

      setIsLoading(true)
      setPendingApproval(false)

      const approvalStatusMsgId = `approval-${Date.now()}`
      setMessages((prev) => [
        ...prev,
        {
          id: approvalStatusMsgId,
          role: "system",
          content: approved
            ? `Action approved by supervisor. Executing: ${pendingAction?.name || "Operation"}`
            : `Action rejected by supervisor. Cancelling: ${pendingAction?.name || "Operation"}`,
          timestamp: Date.now(),
        },
      ])

      const nextAssistantId = `assistant-post-approval-${Date.now()}`

      try {
        abortControllerRef.current = new AbortController()
        const response = await fetch(`${BACKEND_URL}/api/chat/approve`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            thread_id: threadId,
            approved,
          }),
          signal: abortControllerRef.current.signal,
        })

        setPendingAction(null)

        if (!response.ok) {
          const errText = await response.text()
          setMessages((prev) => [
            ...prev,
            {
              id: `err-${Date.now()}`,
              role: "assistant",
              content: `Approval request failed (${response.status}): ${errText}`,
              timestamp: Date.now(),
            },
          ])
          setIsLoading(false)
          return
        }

        await processSSE(response, nextAssistantId)
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          setIsLoading(false)
          return
        }
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            role: "assistant",
            content: `Failed to submit approval to backend`,
            timestamp: Date.now(),
          },
        ])
        setIsLoading(false)
      }
    },
    [pendingApproval, isLoading, pendingAction, threadId, processSSE]
  )

  const resetChat = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setMessages([])
    setInput("")
    setIsLoading(false)
    setPendingApproval(false)
    setPendingAction(null)
    setThreadId(`thread-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`)
  }, [])

  return {
    messages,
    input,
    setInput,
    isLoading,
    pendingApproval,
    pendingAction,
    threadId,
    sendMessage,
    handleApproval,
    resetChat,
  }
}
