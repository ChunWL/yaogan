<template>
  <div class="reset-container">
    <div class="reset-card">
      <div class="reset-header">
        <div class="logo-icon">
          <el-icon :size="40" color="#1a56db"><Lock /></el-icon>
        </div>
        <h1 class="reset-title">重置密码</h1>
        <p class="reset-subtitle">请输入您的新密码</p>
      </div>

      <el-form
        ref="resetForm"
        :model="form"
        :rules="rules"
        class="reset-form"
      >
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="新密码（6-30位，包含字母和数字）"
            size="large"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="确认新密码"
            size="large"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="handleSubmit">
            重置密码
          </el-button>
        </el-form-item>
      </el-form>

      <div class="back-link">
        <span>已想起密码？</span>
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from "vue";
import { Lock } from "@element-plus/icons-vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import request from "../utils/request.js";

const router = useRouter();
const route = useRoute();

const token = computed(() => route.query.token);

const form = reactive({
  password: "",
  confirmPassword: "",
});

const validatePass = (rule, value, callback) => {
  if (value.length < 6 || value.length > 30) {
    callback(new Error("密码长度需要6-30位"));
  } else if (!/[a-zA-Z]/.test(value) || !/\d/.test(value)) {
    callback(new Error("密码需要包含字母和数字"));
  } else {
    callback();
  }
};

const validateConfirm = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error("两次输入的密码不一致"));
  } else {
    callback();
  }
};

const rules = {
  password: [
    { required: true, message: "请输入新密码", trigger: "blur" },
    { validator: validatePass, trigger: "blur" },
  ],
  confirmPassword: [
    { required: true, message: "请确认新密码", trigger: "blur" },
    { validator: validateConfirm, trigger: "blur" },
  ],
};

const resetForm = ref(null);
const loading = ref(false);

const handleSubmit = () => {
  if (!token.value) {
    ElMessage.error("重置链接无效，缺少参数");
    return;
  }
  resetForm.value.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      const res = await request.post("/auth/reset-password", {
        token: token.value,
        new_password: form.password,
      });
      ElMessage.success(res.message);
      setTimeout(() => router.push("/login"), 1500);
    } finally {
      loading.value = false;
    }
  });
};
</script>

<style scoped>
.reset-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8f0fe 0%, #dbeafe 100%);
}

.reset-card {
  width: 100%;
  max-width: 400px;
  padding: 40px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.reset-header {
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

.reset-title {
  font-size: 22px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 6px;
}

.reset-subtitle {
  font-size: 13px;
  color: #6b7280;
}

.reset-form {
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
</style>
