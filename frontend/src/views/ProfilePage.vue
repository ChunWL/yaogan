<template>
  <div class="profile-page">
    <div class="page-header">
      <h1 class="page-title">个人中心</h1>
      <p class="page-subtitle">管理你的账户信息和使用统计</p>
    </div>

    <div class="profile-content">
      <div class="user-info-card">
        <div class="user-avatar-section">
          <el-avatar :size="80">
            <img :src="profile.avatar_url || defaultAvatar" alt="用户头像" />
          </el-avatar>
          <div class="user-basic-info">
            <div class="user-name">{{ profile.username }}</div>
            <div class="user-role">{{ profile.is_admin ? '管理员' : '普通用户' }}</div>
            <div class="user-email">{{ profile.email }}</div>
            <div class="user-meta">
              注册于 {{ profile.created_at }} · 已使用 {{ profile.usage_days }} 天
            </div>
            <el-button
              size="small"
              type="primary"
              plain
              style="margin-top: 8px"
              @click="showEditDialog = true"
            >
              编辑资料
            </el-button>
          </div>
        </div>
      </div>

      <div class="stats-cards">
        <div class="stat-card">
          <div class="stat-value">{{ profile.total_detections }}</div>
          <div class="stat-label">总检测次数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ profile.total_objects }}</div>
          <div class="stat-label">累计检测目标</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ profile.success_rate }}%</div>
          <div class="stat-label">检测成功率</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ profile.usage_days }}</div>
          <div class="stat-label">使用天数</div>
        </div>
      </div>
    </div>

    <!-- 编辑资料对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑资料" width="460px" @closed="handleDialogClosed">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="修改邮箱" name="email">
          <el-form
            ref="emailFormRef"
            :model="emailForm"
            :rules="emailRules"
            label-width="80px"
          >
            <el-form-item label="当前邮箱">
              <span class="form-text">{{ profile.email }}</span>
            </el-form-item>
            <el-form-item label="新邮箱" prop="email">
              <el-input v-model="emailForm.email" placeholder="请输入新邮箱" />
            </el-form-item>
          </el-form>
          <div style="text-align: right; margin-top: 16px">
            <el-button type="primary" :loading="emailLoading" @click="handleUpdateEmail">
              保存
            </el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="修改密码" name="password">
          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-width="80px"
          >
            <el-form-item label="旧密码" prop="old_password">
              <el-input
                v-model="passwordForm.old_password"
                type="password"
                placeholder="请输入旧密码"
                show-password
              />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input
                v-model="passwordForm.new_password"
                type="password"
                placeholder="6-30位，需包含字母和数字"
                show-password
              />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm_password">
              <el-input
                v-model="passwordForm.confirm_password"
                type="password"
                placeholder="请再次输入新密码"
                show-password
              />
            </el-form-item>
          </el-form>
          <div style="text-align: right; margin-top: 16px">
            <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">
              修改密码
            </el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="更换头像" name="avatar">
          <div style="text-align: center; padding: 16px 0">
            <el-avatar :size="100" style="margin-bottom: 16px">
              <img :src="avatarPreview || profile.avatar_url || defaultAvatar" />
            </el-avatar>
            <el-upload
              ref="avatarUploadRef"
              :auto-upload="false"
              :show-file-list="false"
              accept=".jpg,.jpeg,.png,.gif,.webp"
              :on-change="handleAvatarChange"
            >
              <el-button type="primary" plain>选择图片</el-button>
              <template #tip>
                <div style="font-size: 12px; color: #9ca3af; margin-top: 8px">
                  支持 JPG/PNG/GIF/WebP，最大 2MB
                </div>
              </template>
            </el-upload>
            <div v-if="avatarFile" style="margin-top: 12px; font-size: 13px; color: var(--text-secondary)">
              已选择: {{ avatarFile.name }}
            </div>
            <div style="margin-top: 20px">
              <el-button
                type="primary"
                :loading="avatarLoading"
                :disabled="!avatarFile"
                @click="handleUploadAvatar"
              >
                保存头像
              </el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import request from "../utils/request";

const defaultAvatar = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect fill='%231a56db' width='100' height='100'/%3E%3Ctext x='50' y='56' text-anchor='middle' fill='white' font-size='40' font-family='sans-serif'%3E%3C/text%3E%3C/svg%3E";

const showEditDialog = ref(false);
const activeTab = ref("email");
const emailLoading = ref(false);
const passwordLoading = ref(false);
const emailFormRef = ref(null);
const passwordFormRef = ref(null);

const avatarUploadRef = ref(null);
const avatarFile = ref(null);
const avatarPreview = ref("");
const avatarLoading = ref(false);

const profile = ref({
  username: "",
  email: "",
  is_admin: false,
  created_at: "",
  total_detections: 0,
  total_objects: 0,
  success_rate: 100,
  usage_days: 0,
});

const emailForm = reactive({ email: "" });
const emailRules = {
  email: [
    { required: true, message: "请输入邮箱", trigger: "blur" },
    { type: "email", message: "邮箱格式不正确", trigger: "blur" },
  ],
};

const passwordForm = reactive({
  old_password: "",
  new_password: "",
  confirm_password: "",
});

const validateConfirmPassword = (_rule, value, callback) => {
  if (!value) {
    callback(new Error("请确认新密码"));
  } else if (value !== passwordForm.new_password) {
    callback(new Error("两次密码不一致"));
  } else {
    callback();
  }
};

const passwordRules = {
  old_password: [{ required: true, message: "请输入旧密码", trigger: "blur" }],
  new_password: [
    { required: true, message: "请输入新密码", trigger: "blur" },
    { min: 6, max: 30, message: "密码长度6-30位", trigger: "blur" },
  ],
  confirm_password: [{ validator: validateConfirmPassword, trigger: "blur" }],
};

const fetchProfile = async () => {
  try {
    const res = await request.get("/auth/profile");
    profile.value = res.data;
    localStorage.setItem(
      "user",
      JSON.stringify({
        id: res.data.id,
        username: res.data.username,
        email: res.data.email,
        is_admin: res.data.is_admin,
        avatar_url: res.data.avatar_url,
      })
    );
  } catch {
    ElMessage.error("获取用户信息失败");
  }
};

const handleUpdateEmail = async () => {
  const valid = await emailFormRef.value.validate().catch(() => false);
  if (!valid) return;
  emailLoading.value = true;
  try {
    await request.put("/auth/profile", { email: emailForm.email });
    ElMessage.success("邮箱修改成功");
    showEditDialog.value = false;
    fetchProfile();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "修改失败");
  } finally {
    emailLoading.value = false;
  }
};

const handleChangePassword = async () => {
  const valid = await passwordFormRef.value.validate().catch(() => false);
  if (!valid) return;
  passwordLoading.value = true;
  try {
    await request.put("/auth/password", {
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    });
    ElMessage.success("密码修改成功，请重新登录");
    showEditDialog.value = false;
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "/login";
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "修改失败");
  } finally {
    passwordLoading.value = false;
  }
};

const handleAvatarChange = (uploadFile) => {
  if (!uploadFile.raw) return;
  avatarFile.value = uploadFile.raw;
  avatarPreview.value = URL.createObjectURL(uploadFile.raw);
};

const handleUploadAvatar = async () => {
  if (!avatarFile.value) return;

  // Validate file type and size before upload
  const allowedTypes = [".jpg", ".jpeg", ".png", ".gif", ".webp"];
  const ext = "." + avatarFile.value.name.split(".").pop().toLowerCase();
  if (!allowedTypes.includes(ext)) {
    ElMessage.error("不支持的头像格式，仅支持 JPG/PNG/GIF/WebP");
    return;
  }
  if (avatarFile.value.size > 2 * 1024 * 1024) {
    ElMessage.error("头像文件不能超过 2MB");
    return;
  }

  avatarLoading.value = true;
  try {
    const formData = new FormData();
    formData.append("file", avatarFile.value);
    await request.post("/auth/avatar", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    ElMessage.success("头像上传成功");
    showEditDialog.value = false;
    avatarFile.value = null;
    avatarPreview.value = "";
    await fetchProfile();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "头像上传失败");
  } finally {
    avatarLoading.value = false;
  }
};

const handleDialogClosed = () => {
  if (avatarPreview.value) {
    URL.revokeObjectURL(avatarPreview.value);
    avatarPreview.value = "";
  }
  avatarFile.value = null;
};

onMounted(() => {
  fetchProfile();
});
</script>

<style scoped lang="scss">
.profile-page {
  width: 100%;

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

  .profile-content {
    display: flex;
    flex-direction: column;
    gap: 24px;

    .user-info-card {
      background-color: #ffffff;
      border-radius: 10px;
      padding: 24px;
      box-shadow: var(--card-shadow);

      .user-avatar-section {
        display: flex;
        align-items: center;

        .user-basic-info {
          margin-left: 24px;

          .user-name {
            font-size: 24px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 4px;
          }

          .user-role {
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 4px;
          }

          .user-email {
            font-size: 13px;
            color: #9ca3af;
          }

          .user-meta {
            font-size: 12px;
            color: #9ca3af;
            margin-top: 4px;
          }
        }
      }
    }

    .stats-cards {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 24px;

      .stat-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 24px;
        text-align: center;
        box-shadow: var(--card-shadow);

        .stat-value {
          font-size: 32px;
          font-weight: 700;
          color: var(--primary-color);
          margin-bottom: 8px;
        }

        .stat-label {
          font-size: 14px;
          color: var(--text-secondary);
        }
      }
    }
  }

  .form-text {
    color: var(--text-secondary);
    font-size: 14px;
  }
}
</style>
