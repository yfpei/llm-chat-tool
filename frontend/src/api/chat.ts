import type { ChatEvent, TokenUsage } from '../types'
import { authFetch } from './client'

export function sendMessage(
  conversationId: string,
  content: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
  onUsage?: (usage: TokenUsage) => void,
): AbortController {
  const controller = new AbortController()

  authFetch(`/api/chat/${conversationId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.json()
        onError(err.detail || '请求失败')
        return
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: ChatEvent = JSON.parse(line.slice(6))
              if (event.type === 'chunk') {
                onChunk(event.content as string)
              } else if (event.type === 'usage' && onUsage) {
                onUsage(event.content as TokenUsage)
              } else if (event.type === 'done') {
                onDone()
              } else if (event.type === 'error') {
                onError(event.content as string)
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError('连接中断')
      }
    })

  return controller
}
