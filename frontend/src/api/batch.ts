import type { UploadResponse, BatchRunConfig, BatchEvent } from '../types'

export async function uploadExcel(file: File, taskId?: string): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  if (taskId) form.append('task_id', taskId)
  const res = await fetch('/api/batch/upload', { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '上传失败')
  }
  return res.json()
}

export function runBatch(
  config: BatchRunConfig,
  onProgress: (completed: number, total: number) => void,
  onRowResult: (row: number, input: string, output: string, parsed?: Record<string, string>) => void,
  onRowError: (row: number, input: string, error: string) => void,
  onDone: (taskId: string) => void,
  onError: (msg: string) => void,
): AbortController {
  const controller = new AbortController()

  fetch('/api/batch/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
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
              const event: BatchEvent = JSON.parse(line.slice(6))
              switch (event.type) {
                case 'progress':
                  onProgress(event.completed || 0, event.total || 0)
                  break
                case 'row_result':
                  onRowResult(event.row || 0, event.input || '', event.output || '', event.parsed)
                  break
                case 'row_error':
                  onRowError(event.row || 0, event.input || '', event.error || '未知错误')
                  break
                case 'done':
                  onDone(event.task_id || '')
                  break
                case 'error':
                  onError(event.content || '跑批失败')
                  break
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

export function downloadUrl(taskId: string): string {
  return `/api/batch/${taskId}/download`
}
