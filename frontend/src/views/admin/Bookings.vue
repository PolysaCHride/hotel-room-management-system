<template>
  <el-card shadow="never">
    <template #header>
      <div class="head">
        <b>预订管理</b>
        <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width: 140px" @change="load">
          <el-option v-for="(label, key) in STATUS_LABEL" :key="key" :value="key" :label="label" />
        </el-select>
      </div>
    </template>
    <el-table :data="bookings" stripe>
      <el-table-column prop="id" label="单号" width="70" />
      <el-table-column prop="customer_name" label="顾客" width="110" />
      <el-table-column prop="room_type_name" label="房型" width="130" />
      <el-table-column label="入住 — 离店" width="200">
        <template #default="{ row }">{{ row.check_in_date }} ~ {{ row.check_out_date }}</template>
      </el-table-column>
      <el-table-column prop="guests" label="人数" width="70" />
      <el-table-column prop="estimated_price" label="预计(元)" width="100" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="STATUS_TAG[row.status]" effect="plain">{{ STATUS_LABEL[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="下单时间" width="150" />
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" link type="danger" @click="cancel(row)">取消</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../../api/client'

const STATUS_LABEL = { pending: '待到店', checked_in: '已入住', completed: '已完成', cancelled: '已取消' }
const STATUS_TAG = { pending: 'warning', checked_in: 'success', completed: 'info', cancelled: 'danger' }

const bookings = ref([])
const filterStatus = ref(null)

async function load() {
  bookings.value = await client.get('/admin/bookings',
    { params: filterStatus.value ? { status: filterStatus.value } : {} })
}

function cancel(row) {
  ElMessageBox.confirm(`确定取消预订单 #${row.id} 吗？`, '取消预订', { type: 'warning' })
    .then(async () => {
      await client.post(`/admin/bookings/${row.id}/cancel`)
      ElMessage.success('已取消')
      load()
    })
    .catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
</style>
