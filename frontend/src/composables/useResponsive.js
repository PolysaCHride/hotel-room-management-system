import { ref, onMounted, onUnmounted } from 'vue'

// 全站共享的移动端断点（≤768px 视为竖屏手机/窄屏）
const isMobile = ref(false)
let mql = null
let bound = false

function update(e) {
  isMobile.value = e.matches
}

/** 响应式断点：组件内调用获取共享的 isMobile（模块级单例，监听只挂一次） */
export function useResponsive() {
  if (!bound && typeof window !== 'undefined' && window.matchMedia) {
    mql = window.matchMedia('(max-width: 768px)')
    isMobile.value = mql.matches
    mql.addEventListener('change', update)
    bound = true
  }
  if (!bound) {
    // 兜底：极旧浏览器不支持 matchMedia 监听时，跟随窗口 resize
    const onResize = () => { isMobile.value = window.innerWidth <= 768 }
    onMounted(() => { onResize(); window.addEventListener('resize', onResize) })
    onUnmounted(() => window.removeEventListener('resize', onResize))
  }
  return { isMobile }
}
