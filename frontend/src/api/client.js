import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { useAuthStore } from '../stores/auth'

const client = axios.create({ baseURL: '/api', timeout: 15000 })

client.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) config.headers.Authorization = `Bearer ${auth.token}`
  return config
})

client.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    const isLoginRequest = err.config?.url?.startsWith('/auth/login')
    if (err.response?.status === 401 && !isLoginRequest) {
      // 会话过期（登录接口的 401 属于密码错误，走通用提示）
      const auth = useAuthStore()
      auth.logout()
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else {
      // detail 可能是 FastAPI 校验错误数组
      const text = Array.isArray(msg) ? msg.map((m) => m.msg).join('；') : msg
      ElMessage.error(text)
    }
    return Promise.reject(err)
  }
)

export default client
