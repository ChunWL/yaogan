<template>
  <div class="qa-page">
    <div class="page-header">
      <h1 class="page-title">AI 智能问答</h1>
      <p class="page-subtitle">关于遥感目标检测的任何问题，都可以问我</p>
    </div>

    <div class="chat-container">
      <div class="chat-messages">
        <div class="message ai-message">
          <div class="message-avatar">
            <el-icon><ChatDotRound /></el-icon>
          </div>
          <div class="message-content">
            你好！我是遥感目标检测AI助手。我可以帮你解答关于飞机、油罐、操场、立交桥、农业病虫害等遥感目标检测的相关问题，也可以为你提供检测结果的详细分析。
          </div>
        </div>
      </div>

      <div class="chat-input">
        <el-input
          v-model="question"
          placeholder="请输入你的问题..."
          :rows="3"
        />
        <el-button type="primary" class="send-btn" :loading="sending">
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";

const question = ref("");
const sending = ref(false);
</script>

<style scoped lang="scss">
.qa-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;

  .page-header {
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 8px;
    }

    .page-subtitle {
      font-size: 14px;
      color: var(--text-secondary);
    }
  }

  .chat-container {
    flex: 1;
    background-color: #ffffff;
    border-radius: 10px;
    box-shadow: var(--card-shadow);
    display: flex;
    flex-direction: column;

    .chat-messages {
      flex: 1;
      padding: 20px;
      overflow-y: auto;

      .message {
        display: flex;
        margin-bottom: 20px;

        .message-avatar {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background-color: var(--primary-color);
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-right: 12px;
          flex-shrink: 0;
        }

        .message-content {
          background-color: #f3f4f6;
          padding: 12px 16px;
          border-radius: 0 12px 12px 12px;
          max-width: 70%;
          line-height: 1.6;
          font-size: 14px;
        }

        &.user-message {
          flex-direction: row-reverse;

          .message-avatar {
            margin-right: 0;
            margin-left: 12px;
            background-color: #60a5fa;
          }

          .message-content {
            background-color: var(--primary-light);
            border-radius: 12px 0 12px 12px;
          }
        }
      }
    }

    .chat-input {
      padding: 20px;
      border-top: 1px solid var(--border-color);
      display: flex;
      gap: 12px;

      .send-btn {
        width: 100px;
        height: auto;
      }
    }
  }
}
</style>