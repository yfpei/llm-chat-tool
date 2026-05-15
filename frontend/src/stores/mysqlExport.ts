import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MySQLExportTask } from '../types'
import * as mysqlExportApi from '../api/mysqlExport'

export const useMySQLExportStore = defineStore('mysqlExport', () => {
  const tasks = ref<MySQLExportTask[]>([])
  const currentTask = ref<MySQLExportTask | null>(null)

  async function loadTasks() {
    tasks.value = await mysqlExportApi.listTasks()
  }

  async function selectTask(id: string) {
    const task = await mysqlExportApi.getTask(id)
    currentTask.value = task
  }

  async function createTask(data: {
    title?: string
    mysql_host: string
    mysql_port?: number
    mysql_username?: string
    mysql_password?: string
  }) {
    const task = await mysqlExportApi.createTask(data)
    tasks.value.unshift(task)
    currentTask.value = task
    return task
  }

  async function updateTask(id: string, data: {
    title?: string
    mysql_host?: string
    mysql_port?: number
    mysql_username?: string
    mysql_password?: string
    database_name?: string
    table_name?: string
    where_clause?: string
    custom_sql?: string
    output_columns?: string
    config_json?: string
  }) {
    const task = await mysqlExportApi.updateTask(id, data)
    const idx = tasks.value.findIndex((t) => t.id === id)
    if (idx !== -1) tasks.value[idx] = task
    if (currentTask.value?.id === id) currentTask.value = task
    return task
  }

  async function renameTask(id: string, title: string) {
    await updateTask(id, { title })
  }

  async function removeTask(id: string) {
    await mysqlExportApi.deleteTask(id)
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
