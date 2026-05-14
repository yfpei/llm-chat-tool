import { authFetch } from './client'
import type {
  ClassificationEvalConfig,
  ClassificationEvalResult,
  LLMScoringEvalConfig,
  LLMScoringEvalEvent,
} from '../types'

export function runClassificationEval(
  taskId: string,
  config: ClassificationEvalConfig,
  onDone: (result: ClassificationEvalResult) => void,
  onError: (msg: string) => void,
): AbortController {
  const controller = new AbortController()

  authFetch(`/api/eval/${taskId}/run-classification`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId, config }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json()
        onError(err.detail || '客观评测失败')
        return
      }
      const data = await res.json()
      onDone(data)
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError('请求中断或超时')
      }
    })

  return controller
}

export function runLLMScoringEval(
  taskId: string,
  config: LLMScoringEvalConfig,
  onProgress: (completed: number, total: number) => void,
  onRowResult: (row: number, score: string) => void,
  onRowError: (row: number, error: string) => void,
  onDone: (total: number, avgScore: number) => void,
  onError: (msg: string) => void,
): AbortController {
  const controller = new AbortController()

  authFetch(`/api/eval/${taskId}/run-llm-scoring`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId, config }),
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
      let finished = false
      let currentEventType = ''

      function processLine(line: string) {
        if (line.startsWith('event: ')) {
          currentEventType = line.slice(7)
        } else if (line.startsWith('data: ')) {
          try {
            const event: LLMScoringEvalEvent = JSON.parse(line.slice(6))
            const eventType = event.type || currentEventType
            switch (eventType) {
              case 'progress':
                onProgress(event.completed || 0, event.total || 0)
                break
              case 'row_result':
                onRowResult(event.row || 0, event.score || '')
                break
              case 'row_error':
                onRowError(event.row || 0, event.error || '未知错误')
                break
              case 'done':
                finished = true
                onDone(event.total || 0, event.avg_score || 0)
                break
              case 'error':
                finished = true
                onError(event.message || '评分失败')
                break
            }
          } catch { /* skip malformed JSON */ }
          currentEventType = ''
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          // Flush remaining buffer before breaking
          if (buffer.trim()) {
            const lines = buffer.split('\n')
            for (const line of lines) {
              processLine(line)
            }
          }
          break
        }
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          processLine(line)
        }
      }
      if (!finished) {
        onError('服务器连接意外关闭')
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError('连接中断')
      }
    })

  return controller
}

export async function checkClassificationResult(taskId: string): Promise<ClassificationEvalResult | null> {
  try {
    const res = await authFetch(`/api/eval/${taskId}/classification-result`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function getLLMScoringResult(taskId: string): Promise<{
  scores: { row: number; score: string; status: string }[]
  avg_score: number
  total: number
  score_column: string
} | null> {
  try {
    const res = await authFetch(`/api/eval/${taskId}/llm-scoring-result`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export function classificationDownloadUrl(taskId: string): string {
  return `/api/eval/${taskId}/classification-download`
}

export function llmScoringDownloadUrl(taskId: string): string {
  return `/api/eval/${taskId}/llm-scoring-download`
}
