<template>
  <div class="pay-result-page">
    <el-card class="result-card" shadow="hover">
      <div class="icon-wrap">
        <el-icon v-if="status === 'success'" :size="64" color="#07c160"><CircleCheckFilled /></el-icon>
        <el-icon v-else-if="status === 'failed'" :size="64" color="#ff4d4f"><CircleCloseFilled /></el-icon>
        <el-icon v-else-if="status === 'cancelled'" :size="64" color="#909399"><RemoveFilled /></el-icon>
        <el-icon v-else :size="64" color="#409eff" class="spin"><Loading /></el-icon>
      </div>
      <h2 :class="['title', status]">{{ titleText }}</h2>
      <p v-if="payment" class="info">
        支付单号：{{ payment.pay_no }}&nbsp;&nbsp;金额：<b class="amount">¥{{ Number(payment.amount).toFixed(2) }}</b>
        <template v-if="payment.channel">（{{ payment.channel === 'alipay' ? '支付宝' : '微信支付' }}）</template>
      </p>
      <p v-if="status === 'pending'" class="tip">正在确认支付结果，请稍候…（若长时间未确认会自动向支付网关补单查询）</p>
      <p v-if="status === 'success'" class="tip">预订已支付完成，到店后出示订单即可办理入住。</p>
      <p v-if="status === 'failed'" class="tip">支付失败，可返回重新发起支付。</p>
      <p v-if="status === 'cancelled'" class="tip">您已取消本次支付，订单仍保留，可随时重新支付。</p>

      <div class="actions">
        <el-button v-if="status === 'failed' || status === 'cancelled'" type="primary" :loading="paying"
                   @click="repay">重新支付</el-button>
        <el-button @click="$router.push('/customer/bookings')">返回我的预订</el-button>
        <el-button v-if="status === 'pending'" link type="primary" @click="refreshOnce">手动刷新</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import client from '../../api/client'

const route = useRoute()
const router = useRouter()
const payment = ref(null)
const status = ref('pending')
const paying = ref(false)
let timer = null
let tries = 0
const MAX_TRIES = 30

const titleText = computed(() => ({
  pending: '支付结果确认中…',
  success: '支付成功',
  failed: '支付失败',
  cancelled: '已取消支付',
}[status.value]))

async function refreshOnce() {
  try {
    const res = await client.get(`/payments/${route.query.pay_no}`)
    payment.value = res
    status.value = res.status === 'pending' ? 'pending' : res.status
    return res.status
  } catch {
    return null
  }
}

async function poll() {
  const s = await refreshOnce()
  tries += 1
  if (s && s !== 'pending') return stop()
  if (tries >= MAX_TRIES) {
    ElMessage.warning('支付结果确认超时，请稍后在“我的预订”中查看')
    return stop()
  }
  timer = setTimeout(poll, 2000)
}

function stop() {
  if (timer) { clearTimeout(timer); timer = null }
}

async function repay() {
  paying.value = true
  try {
    const res = await client.post('/payments/create', {
      biz_type: payment.value.biz_type, biz_id: payment.value.biz_id,
    })
    window.location.href = res.cashier_url
  } finally {
    paying.value = false
  }
}

onMounted(async () => {
  if (!route.query.pay_no) {
    ElMessage.error('缺少支付单号')
    router.replace('/customer/bookings')
    return
  }
  poll()
})

onUnmounted(stop)
</script>

<style scoped>
.pay-result-page {
  display: flex; align-items: center; justify-content: center;
  min-height: calc(100vh - 120px);
}
.result-card { width: min(460px, 92vw); text-align: center; padding: 12px 8px; }
.icon-wrap { margin: 10px 0 6px; }
.spin { animation: spin 1.2s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.title { margin: 8px 0; color: #303133; }
.title.success { color: #07c160; }
.title.failed { color: #ff4d4f; }
.info { color: #606266; font-size: 14px; margin-bottom: 6px; }
.amount { color: #fa541c; font-size: 16px; }
.tip { color: #909399; font-size: 13px; margin-bottom: 8px; }
.actions { margin-top: 14px; display: flex; justify-content: center; gap: 4px; }
</style>
