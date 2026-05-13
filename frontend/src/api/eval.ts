import { authFetch } from './client'
import type {
  ClassificationEvalConfig,
  ClassificationEvalResult,
  LLMScoringEvalConfig,
  LLMScoringEvalEvent,
} from '../types'

export async function runClassificationEval(
  taskId: string,
  config: ClassificationEvalConfig,
): Promise<ClassificationEvalResult> {
  const res = await authFetch(`/api/eval/${taskId}/run-classification`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId, config }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '客观评测失败')
  }
  return res.json()
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

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: LLMScoringEvalEvent = JSON.parse(line.slice(6))
              switch (event.type) {
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
          }
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

export async function checkClassificationResult(taskId: string): Promise<boolean> {
  try {
    const res = await authFetch(`/api/eval/${taskId}/classification-result`)
    return res.ok
  } catch {
    return false
  }
}

export function classificationDownloadUrl(taskId: string): string {
  return `/api/eval/${taskId}/classification-download`
}

export function llmScoringDownloadUrl(taskId: string): string {
  return `/api/eval/${taskId}/llm-scoring-download`
}
