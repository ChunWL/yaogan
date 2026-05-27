<template>
  <div class="forgot-container">
    <div class="forgot-card">
      <div class="forgot-header">
        <div class="logo-icon">
          <el-icon :size="40" color="#1a56db"><Lock /></el-icon>
        </div>
        <h1 class="forgot-title">{{ submitted ? '重置链接已生成' : '找回密码' }}</h1>
        <p class="forgot-subtitle">
          {{ submitted ? '请复制以下链接在浏览器中打开以重置密码（链接1小时内有效）' : '输入您的注册邮箱' }}
        </p>
      </div>

      <template v-if="!submitted">
        <el-form
          ref="forgotForm"
          :model="forgotForm"
          :rules="forgotRules"
          class="forgot-form"
        >
          <el-form-item prop="email">
            <el-input
              v-model="forgotForm.email"
              type="email"
              placeholder="请输入注册邮箱"
              size="large"
              prefix-icon="Message"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="handleSubmit">
              发送重置链接
            </el-button>
          </el-form-item>
        </el-form>
      </template>

      <template v-else>
        <div class="reset-link-box">
          <el-input
            :model-value="resetUrl"
            readonly
            type="textarea"
            :rows="2"
            class="reset-url-input"
          />
          <el-button type="primary" size="large" class="submit-btn" @click="copyLink">
            复制链接
          </el-button>
          <el-button size="large" class="submit-btn" @click="resetForm">
            重新输入邮箱
          </el-button>
        </div>
      </template>

      <div class="back-link">
        <span>想起密码了？</span>
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import { Lock, Message } from "@element-plus/icons-vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import request from "../utils/request.js";

const router = useRouter();

const forgotForm = reactive({
  email: "",
});

const forgotRules = {
  email: [
    { required: true, message: "请输入邮箱", trigger: "blur" },
    { type: "email", message: "请输入正确的邮箱格式", trigger: "blur" },
  ],
};

const forgotFormRef = ref(null);
const loading = ref(false);
const submitted = ref(false);
const resetUrl = ref("");

const handleSubmit = () => {
  forgotFormRef.value.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      const res = await request.post("/auth/forgot-password", {
        email: forgotForm.email,
      });
      if (res.reset_url) {
        resetUrl.value = res.reset_url;
        submitted.value = true;
      } else {
        ElMessage.success(res.message);
        setTimeout(() => router.push("/login"), 1500);
      }
    } finally {
      loading.value = false;
    }
  });
};

const copyLink = async () => {
  try {
    await navigator.clipboard.writeText(resetUrl.value);
    ElMessage.success("已复制到剪贴板");
  } catch {
    ElMessage.info("请手动复制链接");
  }
};

const resetForm = () => {
  submitted.value = false;
  forgotForm.email = "";
};
</script>

<style scoped>
.forgot-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8f0fe 0%, #dbeafe 100%);
}

.forgot-card {
  width: 100%;
  max-width: 400px;
  padding: 40px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.forgot-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  width: 60px;
  height: 60px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #1e3a5f 0%, #1a56db 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.forgot-title {
  font-size: 22px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 6px;
}

.forgot-subtitle {
  font-size: 13px;
  color: #6b7280;
}

.forgot-form {
  margin-bottom: 24px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
}

.back-link {
  text-align: center;
  font-size: 13px;
  color: #6b7280;
}

.back-link a {
  color: #1a56db;
  margin-left: 4px;
}

.back-link a:hover {
  text-decoration: underline;
}

.reset-link-box {
  margin-bottom: 24px;
}

.reset-url-input {
  margin-bottom: 16px;
}

.reset-url-input :deep(.el-textarea__inner) {
  color: #1a56db;
  font-size: 13px;
  word-break: break-all;
  background: #f0f5ff;
}

.reset-link-box .submit-btn {
  width: 100%;
  height: 44px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 8px;
}
</style>