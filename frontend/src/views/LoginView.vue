<template>
  <div class="login-page">
    <div class="login-card">
      <div class="brand">
        <el-icon :size="40" color="#409eff"><OfficeBuilding /></el-icon>
        <h1>宾馆客房管理系统</h1>
        <p>学生毕业实训项目 · 演示系统</p>
      </div>

      <el-tabs v-model="tab" stretch>
        <el-tab-pane label="登 录" name="login">
          <el-form :model="loginForm" label-width="0" @keyup.enter="doLogin">
            <el-form-item>
              <el-input v-model="loginForm.username" placeholder="用户名" size="large">
                <template #prefix><el-icon><User /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-input v-model="loginForm.password" type="password" placeholder="密码" size="large" show-password>
                <template #prefix><el-icon><Lock /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="doLogin">
              登 录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="顾客注册" name="register">
          <el-form :model="regForm" label-width="0" @keyup.enter="doRegister">
            <el-form-item>
              <el-input v-model="regForm.username" placeholder="用户名（3 位以上）" size="large">
                <template #prefix><el-icon><User /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.real_name" placeholder="姓名" size="large">
                <template #prefix><el-icon><Postcard /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.phone" placeholder="手机号" size="large">
                <template #prefix><el-icon><Iphone /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.password" type="password" placeholder="密码（6 位以上）" size="large" show-password>
                <template #prefix><el-icon><Lock /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-button type="success" size="large" style="width: 100%" :loading="loading" @click="doRegister">
              注 册
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <el-divider>演示账号（点击快速填充）</el-divider>
      <div class="demo-accounts">
        <el-button size="small" @click="fill('admin', 'admin123')">管理员 admin</el-button>
        <el-button size="small" @click="fill('reception', '123456')">服务员 reception</el-button>
        <el-button size="small" @click="fill('guest', '123456')">顾客 guest</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import client from '../api/client'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const tab = ref('login')
const loading = ref(false)

const loginForm = reactive({ username: '', password: '' })
const regForm = reactive({ username: '', password: '', real_name: '', phone: '' })

function fill(u, p) {
  tab.value = 'login'
  loginForm.username = u
  loginForm.password = p
}

async function doLogin() {
  if (!loginForm.username || !loginForm.password) return ElMessage.warning('请输入用户名和密码')
  loading.value = true
  try {
    const res = await client.post('/auth/login', loginForm)
    auth.setSession(res.token, res.user)
    ElMessage.success(`欢迎，${res.user.real_name}（${auth.roleLabel}）`)
    router.push(auth.homePath)
  } finally {
    loading.value = false
  }
}

async function doRegister() {
  loading.value = true
  try {
    await client.post('/auth/register', regForm)
    ElMessage.success('注册成功，请登录')
    loginForm.username = regForm.username
    loginForm.password = ''
    tab.value = 'login'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100%;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #1f2d3d 0%, #2b4a6f 100%);
}
.login-card {
  width: 400px; background: #fff; border-radius: 12px; padding: 32px;
  box-shadow: 0 12px 40px rgba(0,0,0,.3);
}
.brand { text-align: center; margin-bottom: 20px; }
.brand h1 { font-size: 20px; color: #303133; margin: 10px 0 4px; }
.brand p { font-size: 12px; color: #909399; }
.demo-accounts { display: flex; justify-content: center; gap: 4px; flex-wrap: wrap; }
</style>
