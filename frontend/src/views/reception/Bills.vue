<template>
  <el-card shadow="never">
    <template #header><b>账单记录（最近 100 条）</b></template>
    <el-table :data="bills" stripe>
      <el-table-column prop="id" label="账单号" width="80" />
      <el-table-column prop="room_number" label="房号" width="90" />
      <el-table-column prop="guest_name" label="客人" width="110" />
      <el-table-column prop="days" label="晚数" width="70" />
      <el-table-column prop="room_price" label="单价(元)" width="100" />
      <el-table-column prop="amount" label="金额(元)" width="110">
        <template #default="{ row }"><b>¥{{ row.amount }}</b></template>
      </el-table-column>
      <el-table-column label="支付状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_paid ? 'success' : 'warning'">{{ row.is_paid ? '已支付' : '待支付' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="支付方式" width="100">
        <template #default="{ row }">
          <span v-if="row.is_paid">{{ row.pay_via === 'online' ? '在线支付' : '现金' }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="结算时间" width="150" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <template v-if="!row.is_paid">
            <el-button link type="success" @click="cashPay(row)">现金收款</el-button>
            <el-button link type="primary" @click="onlinePay(row)">在线收款</el-button>
          </template>
          <span v-else class="muted">已完成</span>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../../api/client'

const bills = ref([])
let payTimer = null

async function load() {
  bills.value = await client.get('/reception/bills')
}

async function cashPay(row) {
  await client.post(`/reception/bills/${row.id}/cash-pay`)
  ElMessage.success('现金收款完成')
  load()
}

async function onlinePay(row) {
  const res = await client.post('/payments/create', { biz_type: 'bill', biz_id: row.id })
  window.open(res.cashier_url, '_blank')
  ElMessage.success('收银台已在新窗口打开，等待客人支付…')
  let tries = 0
  payTimer = setInterval(async () => {
    tries += 1
    const st = await client.get(`/payments/${res.pay_no}`)
    if (st.status !== 'pending') {
      clearInterval(payTimer)
      if (st.status === 'success') ElMessage.success('在线收款成功！')
      else ElMessage.warning(st.status === 'cancelled' ? '客人已取消支付' : '支付失败，可重新发起')
      load()
    } else if (tries >= 60) {
      clearInterval(payTimer)
      ElMessage.warning('等待支付超时，请稍后刷新查看')
    }
  }, 2000)
}

onMounted(load)
onUnmounted(() => { if (payTimer) clearInterval(payTimer) })
</script>

<style scoped>
.muted { color: #909399; }
</style>
