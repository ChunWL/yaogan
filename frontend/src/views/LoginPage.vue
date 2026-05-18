<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="logo-icon">
          <el-icon :size="40" color="#27ae60"><Picture /></el-icon>
        </div>
        <h1 class="login-title">遥感目标智能检测平台</h1>
        <p class="login-subtitle">多场景遥感影像 · 精准目标检测</p>
      </div>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item class="form-actions">
          <el-checkbox v-model="loginForm.remember">记住我</el-checkbox>
          <router-link to="/forgot-password" class="forgot-password">忘记密码?</router-link>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" class="login-btn" @click="handleLogin">
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="register-link">
        <span>还没有账号？</span>
        <router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import { Picture, User, Lock } from "@element-plus/icons-vue";
import { useRouter } from "vue-router";

const router = useRouter();

const loginForm = reactive({
  username: "",
  password: "",
  remember: false,
});

const loginRules = {
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { min: 3, max: 20, message: "用户名长度在3到20个字符", trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 6, max: 30, message: "密码长度在6到30个字符", trigger: "blur" },
  ],
};

const loginFormRef = ref(null);

const handleLogin = () => {
  loginFormRef.value.validate((valid) => {
    if (valid) {
      console.log("登录请求:", loginForm);
      localStorage.setItem("token", "mock-token");
      router.push("/detection");
    }
  });
};
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 40px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.login-header {
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

.login-title {
  font-size: 22px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 6px;
}

.login-subtitle {
  font-size: 13px;
  color: #6b7280;
}

.login-form {
  margin-bottom: 24px;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.forgot-password {
  font-size: 13px;
  color: #27ae60;
  cursor: pointer;
}

.forgot-password:hover {
  text-decoration: underline;
}

.login-btn {
  width: 100%;
  height: 44px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
}

.register-link {
  text-align: center;
  font-size: 13px;
  color: #6b7280;
}

.register-link a {
  color: #27ae60;
  margin-left: 4px;
  cursor: pointer;
}

.register-link a:hover {
  text-decoration: underline;
}
</style>