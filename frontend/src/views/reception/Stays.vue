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
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="checkout(row)">
              <el-icon><CircleCheck /></el-icon> 退房结算
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 结算结果 -->
    <el-dialog v-model="bill.visible" title="退房结算单" width="420px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="房号">{{ bill.room_number }}</el-descriptions-item>
        <el-descriptions-item label="客人">{{ bill.guest_name }}</el-descriptions-item>
        <el-descriptions-item label="入住晚数">{{ bill.days }} 晚</el-descriptions-item>
        <el-descriptions-item label="单价">¥{{ bill.room_price }} / 晚</el-descriptions-item>
        <el-descriptions-item label="应付金额">
          <span class="amount">¥{{ bill.amount }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="支付状态">
          <el-tag type="success">已支付</el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="bill.visible = false">完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../../api/client'

const stays = ref([])
const bill = reactive({ visible: false, room_number: '', guest_name: '', days: 1, room_price: 0, amount: 0 })

function nights(row) {
  const d = (Date.now() - new Date(row.check_in_time.replace(' ', 'T'))) / 86400000
  return Math.max(Math.ceil(d), 1)
}

async function load() {
  stays.value = await client.get('/reception/stays')
}

function checkout(row) {
  ElMessageBox.confirm(
    `确认为 ${row.room_number} 房（${row.guest_name}）办理退房并生成账单吗？`,
    '退房结算', { type: 'warning' }
  ).then(async () => {
    const b = await client.post(`/reception/check-out/${row.id}`)
    Object.assign(bill, { visible: true, room_number: b.room_number, guest_name: b.guest_name,
                          days: b.days, room_price: b.room_price, amount: b.amount })
    ElMessage.success('退房完成，账单已生成')
    load()
  }).catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.amount { font-size: 22px; font-weight: 700; color: #f56c6c; }
</style>
