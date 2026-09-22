<template>
  <el-card shadow="never">
    <template #header><b>我的预订</b></template>
    <el-table :data="bookings" stripe>
      <el-table-column prop="id" label="单号" width="70" />
      <el-table-column prop="room_type_name" label="房型" width="120" />
      <el-table-column label="房间" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.room_number" type="warning" effect="plain">{{ row.room_number }} 房</el-tag>
          <span v-else class="muted">未分配</span>
        </template>
      </el-table-column>
      <el-table-column label="入住 — 离店" width="200">
        <template #default="{ row }">
          {{ row.check_in_date }} ~ {{ row.check_out_date }}
          <el-tag v-if="row.renewal_status === 'pending'" size="small" type="warning" style="margin-left: 6px">
            续订待确认
          </el-tag>
          <el-tag v-else-if="row.renewal_status === 'confirmed'" size="small" type="success" style="margin-left: 6px">
            已续订
          </el-tag>
          <el-tag v-else-if="row.renewal_status === 'rejected'" size="small" type="danger" style="margin-left: 6px">
            续订被拒
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="guests" label="人数" width="70" />
      <el-table-column prop="estimated_price" label="预计费用(元)" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="STATUS_TAG[row.status]" effect="plain">{{ STATUS_LABEL[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="下单时间" width="150" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button v-if="canRenew(row)" link type="primary" @click="openRenew(row)">申请续订</el-button>
          <el-button v-if="row.status === 'pending'" link type="danger" @click="cancel(row)">取消预订</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 申请续订弹窗 -->
    <el-dialog v-model="renew.visible" title="申请续订（延长离店日期）" width="440px">
      <el-form label-width="110px">
        <el-form-item label="房间 / 房型">
          <span>{{ renew.room_number }} 房 · {{ renew.room_type_name }}</span>
        </el-form-item>
        <el-form-item label="当前离店日期"><span>{{ renew.old_date }}</span></el-form-item>
        <el-form-item label="申请延长至">
          <el-date-picker v-model="renew.new_date" type="date" value-format="YYYY-MM-DD"
                          :disabled-date="disabledRenewDate" placeholder="新离店日期" />
        </el-form-item>
      </el-form>
      <el-alert type="info" :closable="false"
                title="提交后由前台服务员确认，确认后即延长成功" />
      <template #footer>
        <el-button @click="renew.visible = false">取消</el-button>
        <el-button type="primary" :loading="renew.loading" @click="submitRenew">提交申请</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../../api/client'

const STATUS_LABEL = { pending: '待到店', checked_in: '已入住', completed: '已完成', cancelled: '已取消' }
const STATUS_TAG = { pending: 'warning', checked_in: 'success', completed: 'info', cancelled: 'danger' }

const bookings = ref([])
const renew = reactive({ visible: false, loading: false, id: null, room_number: '', room_type_name: '',
                         old_date: '', new_date: '' })

async function load() {
  bookings.value = await client.get('/bookings/mine')
}

function canRenew(row) {
  return ['pending', 'checked_in'].includes(row.status) && row.renewal_status !== 'pending'
}

function openRenew(row) {
  Object.assign(renew, {
    visible: true, loading: false, id: row.id,
    room_number: row.room_number || '未分配', room_type_name: row.room_type_name,
    old_date: row.check_out_date, new_date: '',
  })
}

function disabledRenewDate(d) {
  if (!renew.old_date) return true
  return d.getTime() <= new Date(renew.old_date).getTime()
}

async function submitRenew() {
  if (!renew.new_date) return ElMessage.warning('请选择新的离店日期')
  renew.loading = true
  try {
    await client.post(`/bookings/${renew.id}/renew-request`, { new_check_out_date: renew.new_date })
    ElMessage.success('续订申请已提交，请等待前台服务员确认')
    renew.visible = false
    load()
  } finally {
    renew.loading = false
  }
}

function cancel(row) {
  ElMessageBox.confirm(`确定取消预订单 #${row.id}（${row.room_type_name}）吗？`, '取消预订', { type: 'warning' })
    .then(async () => {
      await client.post(`/bookings/${row.id}/cancel`)
      ElMessage.success('已取消')
      load()
    })
    .catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.muted { color: #909399; }
</style>
