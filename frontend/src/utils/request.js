import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 120000
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    const token = localStorage.getItem("token")
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token")
      localStorage.removeItem("user")
      if (window.location.pathname !== "/login") {
        window.location.href = "/login"
      }
      return Promise.reject(error)
    }
    ElMessage.error(error.response?.data?.detail || '请求失败，请稍后重试')
    return Promise.reject(error)
  }
)

export default service