<template>
  <div class="chat-window">
    <div v-if="!store.currentConversation" class="empty-state">
      <h2>LLM Chat</h2>
      <p>创建新会话或选择已有会话开始聊天</p>
    </div>
    <template v-else>
      <div class="messages" ref="messagesRef">
        <MessageBubble
          v-for="msg in store.currentConversation.messages"
          :key="msg.id"
          :message="msg"
        />
      </div>
      <InputBox />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useChatStore } from '../stores/chat'
import MessageBubble from './MessageBubble.vue'
import InputBox from './InputBox.vue'

const store = useChatStore()
const messagesRef = ref<HTMLElement>()

watch(
  () => store.currentConversation?.messages.length,
  async () => {
    await nextTick()
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  },
)

watch(
  () => store.streamingContent,
  async () => {
    await nextTick()
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  },
)
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #888;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
</style>
