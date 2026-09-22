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
      <el-table-column prop="created_at" label="结算时间" width="150" />
    </el-table>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import client from '../../api/client'

const bills = ref([])

async function load() {
  bills.value = await client.get('/reception/bills')
}

onMounted(load)
</script>
