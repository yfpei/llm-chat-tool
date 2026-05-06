import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { BatchTask, UploadResponse } from '../types'
import * as batchTasksApi from '../api/batchTasks'

export const useBatchStore = defineStore('batch', () => {
  const batchTasks = ref<BatchTask[]>([])
  const currentTask = ref<BatchTask | null>(null)
  const uploadResult = ref<UploadResponse | null>(null)

  async function loadBatchTasks() {
    batchTasks.value = await batchTasksApi.fetchBatchTasks()
  }

  function setUploadResult(result: UploadResponse) {
    uploadResult.value = result
  }

  async function selectBatchTask(id: string) {
    const task = await batchTasksApi.getBatchTask(id)
    currentTask.value = task
    if (task) {
      let preview: any[] = []
      try {
        const p = await batchTasksApi.getTaskPreview(task.id)
        preview = p.preview
      } catch { /* file may be gone */ }
      uploadResult.value = {
        task_id: task.id,
        file_id: task.file_id,
        filename: task.filename,
        columns: JSON.parse(task.columns),
        headers: JSON.parse(task.headers),
        total_rows: task.total_rows,
        preview,
      }
    }
  }

  async function renameBatchTask(id: string, title: string) {
    await batchTasksApi.updateBatchTask(id, { title })
    const task = batchTasks.value.find((t) => t.id === id)
    if (task) task.title = title
    if (currentTask.value?.id === id) {
      currentTask.value.title = title
    }
  }

  async function saveBatchTaskConfig(id: string, config: object) {
    const configJson = JSON.stringify(config)
    await batchTasksApi.updateBatchTask(id, { config_json: configJson })
    if (currentTask.value?.id === id) {
      currentTask.value.config_json = configJson
    }
  }

  async function removeBatchTask(id: string) {
    await batchTasksApi.deleteBatchTask(id)
    batchTasks.value = batchTasks.value.filter((t) => t.id !== id)
    if (currentTask.value?.id === id) {
      currentTask.value = null
      uploadResult.value = null
    }
  }

  function addBatchTaskToList(task: BatchTask) {
    batchTasks.value.unshift(task)
  }

  function newBatchTask() {
    currentTask.value = null
    uploadResult.value = null
  }

  return {
    batchTasks, currentTask, uploadResult,
    loadBatchTasks, setUploadResult, selectBatchTask,
    renameBatchTask, saveBatchTaskConfig, removeBatchTask,
    addBatchTaskToList, newBatchTask,
  }
})
