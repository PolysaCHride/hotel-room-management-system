<template>
  <div>
    <el-card shadow="never" class="page-card">
      <template #header><b>当前在住（点击办理退房结算）</b></template>
      <el-table :data="stays" stripe>
        <el-table-column prop="room_number" label="房号" width="90" />
        <el-table-column prop="room_type_name" label="房型" width="130" />
        <el-table-column prop="guest_name" label="客人" width="110" />
        <el-table-column prop="guest_phone" label="手机号" width="130" />
        <el-table-column prop="check_in_time" label="入住时间" width="150" />
        <el-table-column prop="expected_check_out" label="预计离店" width="120" />
        <el-table-column label="已住晚数" width="100">
          <template #default="{ row }">{{ nights(row) }} 晚</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openRenew(row)">
              <el-icon><Calendar /></el-icon> 续订
            </el-button>
            <el-button link type="danger" @click="checkout(row)">
              <el-icon><CircleCheck /></el-icon> 退房结算
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 续订弹窗 -->
    <el-dialog v-model="renew.visible" title="续订（延长离店日期）" width="420px">
      <el-form label-width="110px">
        <el-form-item label="房间 / 客人">
          <span>{{ renew.room_number }} 房 · {{ renew.guest_name }}</span>
        </el-form-item>
        <el-form-item label="当前离店日期">
          <span>{{ renew.old_date }}</span>
        </el-form-item>
        <el-form-item label="延长至">
          <el-date-picker v-model="renew.new_date" type="date" value-format="YYYY-MM-DD"
                          :disabled-date="disabledRenewDate" placeholder="新离店日期" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renew.visible = false">取消</el-button>
        <el-button type="primary" :loading="renew.loading" @click="submitRenew">确认续订</el-button>
      </template>
    </el-dialog>

    <!-- 结算结果 -->
    <el-dialog v-model="bill.visible" title="退房结算单" width="440px" :close-on-click-modal="false">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="房号">{{ bill.room_number }}</el-descriptions-item>
        <el-descriptions-item label="客人">{{ bill.guest_name }}</el-descriptions-item>
        <el-descriptions-item label="入住晚数">{{ bill.days }} 晚</el-descriptions-item>
        <el-descriptions-item label="单价">¥{{ bill.room_price }} / 晚</el-descriptions-item>
        <el-descriptions-item label="应付金额">
          <span class="amount">¥{{ bill.amount }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="支付状态">
          <el-tag v-if="bill.is_paid" type="success">已支付（{{ bill.pay_via === 'online' ? '在线' : '现金' }}）</el-tag>
          <el-tag v-else type="warning">待支付</el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <el-alert v-if="payingOnline" type="info" :closable="false" style="margin-top: 10px"
                title="已打开模拟收银台，等待客人支付…确认后本页面自动更新（也可在收银台操作 付款失败/取消支付 观察对应结果）" />
      <template #footer>
        <template v-if="!bill.is_paid">
          <el-button type="success" :disabled="payingOnline" @click="cashPay">
            <el-icon><Money /></el-icon> 现金收款
          </el-button>
          <el-button type="primary" :loading="payingOnline" @click="onlinePay">
            <el-icon><Iphone /></el-icon> 在线收款
          </el-button>
        </template>
        <el-button @click="bill.visible = false">{{ bill.is_paid ? '完成' : '稍后收款' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../../api/client'

const stays = ref([])
const bill = reactive({ visible: false, id: null, room_number: '', guest_name: '', days: 1, room_price: 0,
                         amount: 0, is_paid: false, pay_via: '' })
const renew = reactive({ visible: false, loading: false, id: null, booking_id: null, room_number: '',
                         guest_name: '', old_date: '', new_date: '' })
const payingOnline = ref(false)
let payTimer = null

function nights(row) {
  const d = (Date.now() - new Date(row.check_in_time.replace(' ', 'T'))) / 86400000
  return Math.max(Math.ceil(d), 1)
}

async function load() {
  stays.value = await client.get('/reception/stays')
}

function openRenew(row) {
  Object.assign(renew, {
    visible: true, loading: false, id: row.id, booking_id: row.booking_id,
    room_number: row.room_number, guest_name: row.guest_name,
    old_date: row.expected_check_out, new_date: '',
  })
}

function disabledRenewDate(d) {
  if (!renew.old_date) return true
  return d.getTime() <= new Date(renew.old_date).getTime()
}

async function submitRenew() {
  if (!renew.new_date) return ElMessage.warning('请选择新的离店日期')
  if (!renew.booking_id) return ElMessage.warning('该入住记录没有关联预订，无法续订')
  renew.loading = true
  try {
    await client.post(`/reception/renewals/${renew.booking_id}/direct`, { new_check_out_date: renew.new_date })
    ElMessage.success(`续订成功，${renew.room_number} 房离店日期已延长至 ${renew.new_date}`)
    renew.visible = false
    load()
  } finally {
    renew.loading = false
  }
}

function checkout(row) {
  ElMessageBox.confirm(
    `确认为 ${row.room_number} 房（${row.guest_name}）办理退房并生成账单吗？`,
    '退房结算', { type: 'warning' }
  ).then(async () => {
    const b = await client.post(`/reception/check-out/${row.id}`)
    Object.assign(bill, { visible: true, id: b.id, room_number: b.room_number, guest_name: b.guest_name,
                          days: b.days, room_price: b.room_price, amount: b.amount,
                          is_paid: b.is_paid, pay_via: b.pay_via || '' })
    ElMessage.success('退房完成，账单已生成，请选择收款方式')
    load()
  }).catch(() => {})
}

async function cashPay() {
  const b = await client.post(`/reception/bills/${bill.id}/cash-pay`)
  bill.is_paid = b.is_paid
  bill.pay_via = b.pay_via
  ElMessage.success('现金收款完成')
}

async function onlinePay() {
  payingOnline.value = true
  try {
    const res = await client.post('/payments/create', { biz_type: 'bill', biz_id: bill.id })
    window.open(res.cashier_url, '_blank')
    ElMessage.success('收银台已在新窗口打开，等待客人支付…')
    let tries = 0
    payTimer = setInterval(async () => {
      tries += 1
      const st = await client.get(`/payments/${res.pay_no}`)
      if (st.status !== 'pending') {
        clearInterval(payTimer)
        payingOnline.value = false
        if (st.status === 'success') {
          bill.is_paid = true
          bill.pay_via = 'online'
          ElMessage.success('在线收款成功！')
        } else {
          ElMessage.warning(st.status === 'cancelled' ? '客人已取消支付' : '支付失败，可重新发起')
        }
      } else if (tries >= 60) {
        clearInterval(payTimer)
        payingOnline.value = false
        ElMessage.warning('等待支付超时，可稍后在账单记录中继续收款')
      }
    }, 2000)
  } catch (e) {
    payingOnline.value = false
  }
}

onMounted(load)
onUnmounted(() => { if (payTimer) clearInterval(payTimer) })
</script>

<style scoped>
.amount { font-size: 22px; font-weight: 700; color: #f56c6c; }
</style>
