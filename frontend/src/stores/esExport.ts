import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { EsExportTask } from '../types'
import * as esExportApi from '../api/esExport'

export const useEsExportStore = defineStore('esExport', () => {
  const tasks = ref<EsExportTask[]>([])
  const currentTask = ref<EsExportTask | null>(null)

  async function loadTasks() {
    tasks.value = await esExportApi.listTasks()
  }

  async function selectTask(id: string) {
    const task = await esExportApi.getTask(id)
    currentTask.value = task
  }

  async function createTask(data: {
    title?: string
    es_host: string
    es_username?: string
    es_password?: string
  }) {
    const task = await esExportApi.createTask(data)
    tasks.value.unshift(task)
    currentTask.value = task
    return task
  }

  async function updateTask(id: string, data: {
    title?: string
    es_host?: string
    es_username?: string
    es_password?: string
    index_name?: string
    query_dsl?: string
    output_fields?: string
    config_json?: string
  }) {
    const task = await esExportApi.updateTask(id, data)
    const idx = tasks.value.findIndex((t) => t.id === id)
    if (idx !== -1) tasks.value[idx] = task
    if (currentTask.value?.id === id) currentTask.value = task
    return task
  }

  async function renameTask(id: string, title: string) {
    await updateTask(id, { title })
  }

  async function removeTask(id: string) {
    await esExportApi.deleteTask(id)
    tasks.value = tasks.value.filter((t) => t.id !== id)
    if (currentTask.value?.id === id) currentTask.value = null
  }

  function newTask() {
    currentTask.value = null
  }

  return {
    tasks, currentTask,
    loadTasks, selectTask, createTask, updateTask, renameTask, removeTask, newTask,
  }
})
