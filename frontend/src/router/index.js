import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  // 顾客界面
  {
    path: '/customer',
    component: () => import('../layouts/PortalLayout.vue'),
    meta: { role: 'customer' },
    children: [
      { path: '', component: () => import('../views/customer/Home.vue') },
      { path: 'bookings', component: () => import('../views/customer/MyBookings.vue') },
    ],
  },
  // 服务员界面
  {
    path: '/reception',
    component: () => import('../layouts/PortalLayout.vue'),
    meta: { role: 'receptionist' },
    children: [
      { path: '', component: () => import('../views/reception/Dashboard.vue') },
      { path: 'stays', component: () => import('../views/reception/Stays.vue') },
      { path: 'bills', component: () => import('../views/reception/Bills.vue') },
    ],
  },
  // 管理员界面
  {
    path: '/admin',
    component: () => import('../layouts/PortalLayout.vue'),
    meta: { role: 'admin' },
    children: [
      { path: '', component: () => import('../views/admin/Dashboard.vue') },
      { path: 'rooms', component: () => import('../views/admin/Rooms.vue') },
      { path: 'types', component: () => import('../views/admin/RoomTypes.vue') },
      { path: 'bookings', component: () => import('../views/admin/Bookings.vue') },
      { path: 'users', component: () => import('../views/admin/Users.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (auth.isLoggedIn) return auth.homePath
    return true
  }
  if (!auth.isLoggedIn) return '/login'
  if (to.meta.role && to.meta.role !== auth.role) return auth.homePath
  return true
})

export default router
