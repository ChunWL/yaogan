<template>
  <div class="forgot-container">
    <div class="forgot-card">
      <div class="forgot-header">
        <div class="logo-icon">
          <el-icon :size="40" color="#27ae60"><Lock /></el-icon>
        </div>
        <h1 class="forgot-title">找回密码</h1>
        <p class="forgot-subtitle">输入您的注册邮箱，我们将发送重置链接</p>
      </div>

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
          <el-button type="primary" size="large" class="submit-btn" @click="handleSubmit">
            发送重置链接
          </el-button>
        </el-form-item>
      </el-form>

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

const handleSubmit = () => {
  forgotFormRef.value.validate((valid) => {
    if (valid) {
      console.log("找回密码请求:", forgotForm.email);
      ElMessage.success("重置链接已发送到您的邮箱");
      setTimeout(() => {
        router.push("/login");
      }, 1500);
    }
  });
};
</script>

<style scoped>
.forgot-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
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
  background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
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
  color: #27ae60;
  margin-left: 4px;
}

.back-link a:hover {
  text-decoration: underline;
}
</style>