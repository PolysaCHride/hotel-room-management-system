<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon :size="26"><OfficeBuilding /></el-icon>
        <span>宾馆客房管理系统</span>
      </div>
      <el-menu :default-active="$route.path" router background-color="#1f2d3d" text-color="#cfd8e3"
               active-text-color="#409eff" class="menu">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="portal-title">{{ portalTitle }}</span>
        <div class="user-box">
          <el-tag :type="tagType" effect="dark" size="small">{{ auth.roleLabel }}</el-tag>
          <span class="uname">{{ auth.user?.real_name || auth.user?.username }}</span>
          <el-button link type="danger" @click="onLogout">
            <el-icon><SwitchButton /></el-icon> 退出
          </el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const MENU_BY_ROLE = {
  customer: [
    { path: '/customer', title: '浏览房型与预订', icon: 'House' },
    { path: '/customer/bookings', title: '我的预订', icon: 'Tickets' },
  ],
  receptionist: [
    { path: '/reception', title: '前台工作台', icon: 'Bell' },
    { path: '/reception/stays', title: '在住与退房', icon: 'Key' },
    { path: '/reception/bills', title: '账单记录', icon: 'Document' },
  ],
  admin: [
    { path: '/admin', title: '经营看板', icon: 'DataAnalysis' },
    { path: '/admin/types', title: '房型与房价', icon: 'Menu' },
    { path: '/admin/rooms', title: '房间管理', icon: 'OfficeBuilding' },
    { path: '/admin/bookings', title: '预订管理', icon: 'Tickets' },
    { path: '/admin/users', title: '员工与用户', icon: 'User' },
  ],
}

const menus = computed(() => MENU_BY_ROLE[auth.role] || [])
const portalTitle = computed(
  () => ({ customer: '顾客门户', receptionist: '前台服务系统', admin: '管理员后台' })[auth.role] || ''
)
const tagType = computed(() => ({ customer: 'success', receptionist: 'warning', admin: 'danger' })[auth.role] || 'info')

function onLogout() {
  ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' }).then(() => {
    auth.logout()
    router.push('/login')
  }).catch(() => {})
}
</script>

<style scoped>
.layout { height: 100%; }
.aside { background: #1f2d3d; }
.logo {
  height: 60px; display: flex; align-items: center; justify-content: center; gap: 8px;
  color: #fff; font-weight: 600; font-size: 15px; border-bottom: 1px solid rgba(255,255,255,.08);
}
.menu { border-right: none; }
.header {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border-bottom: 1px solid #e6e6e6;
}
.portal-title { font-size: 16px; font-weight: 600; color: #303133; }
.user-box { display: flex; align-items: center; gap: 12px; }
.uname { color: #606266; font-size: 14px; }
.main { background: #f5f7fa; padding: 16px; }
</style>
