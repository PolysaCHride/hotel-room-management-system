<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="8" v-for="t in types" :key="t.id">
        <el-card shadow="hover" class="type-card">
          <div class="type-head">
            <span class="type-name">{{ t.name }}</span>
            <el-tag :type="t.free_count > 0 ? 'success' : 'danger'" effect="plain">
              今日剩余 {{ t.free_count }} 间
            </el-tag>
          </div>
          <div class="price">¥<span class="num">{{ t.price }}</span><span class="unit"> / 晚</span></div>
          <p class="desc">{{ t.description }}</p>
          <div class="meta">
            <el-icon><User /></el-icon> 可住 {{ t.capacity }} 人
            <el-divider direction="vertical" />
            <el-icon><OfficeBuilding /></el-icon> 共 {{ t.room_count }} 间
          </div>
          <el-button type="primary" style="width: 100%" :disabled="t.free_count <= 0" @click="openBooking(t)">
            立即预订
          </el-button>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="page-card" style="margin-top: 16px">
      <template #header><b>房间实时状态</b></template>
      <el-table :data="rooms" size="default" stripe>
        <el-table-column prop="room_number" label="房号" width="100" />
        <el-table-column prop="type_name" label="房型" width="140" />
        <el-table-column prop="price" label="价格(元/晚)" width="120" />
        <el-table-column prop="floor" label="楼层" width="80" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="STATUS_TAG[row.status]" effect="plain">{{ STATUS_LABEL[row.status] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" />
      </el-table>
    </el-card>

    <!-- 预订对话框 -->
    <el-dialog v-model="dialog.visible" :title="`预订 · ${dialog.typeName}`" width="460px">
      <el-form label-width="90px">
        <el-form-item label="入住日期">
          <el-date-picker v-model="dialog.dates" type="daterange" value-format="YYYY-MM-DD"
                          start-placeholder="入住" end-placeholder="离店" style="width: 100%" />
        </el-form-item>
        <el-form-item label="入住人数">
          <el-input-number v-model="dialog.guests" :min="1" :max="dialog.capacity" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="dialog.remark" type="textarea" :rows="2" placeholder="如：高楼层、靠窗" />
        </el-form-item>
        <el-alert v-if="estimated > 0" type="info" :closable="false"
                  :title="`预计费用：${nights} 晚 × ¥${dialog.price} = ¥${estimated}`" />
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitBooking">提交预订</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../../api/client'

const STATUS_LABEL = { available: '空闲', booked: '已订', occupied: '入住中', maintenance: '维修中' }
const STATUS_TAG = { available: 'success', booked: 'warning', occupied: 'danger', maintenance: 'info' }

const types = ref([])
const rooms = ref([])
const submitting = ref(false)
const dialog = reactive({ visible: false, typeId: null, typeName: '', price: 0, capacity: 1,
                          dates: [], guests: 1, remark: '' })

const nights = () => {
  if (!dialog.dates || dialog.dates.length !== 2) return 0
  const d = (new Date(dialog.dates[1]) - new Date(dialog.dates[0])) / 86400000
  return Math.max(d, 1)
}
const estimated = () => nights() * dialog.price

async function load() {
  types.value = await client.get('/rooms/types')
  rooms.value = await client.get('/rooms')
}

function openBooking(t) {
  Object.assign(dialog, { visible: true, typeId: t.id, typeName: t.name, price: t.price,
                          capacity: t.capacity, dates: [], guests: 1, remark: '' })
}

async function submitBooking() {
  if (!dialog.dates || dialog.dates.length !== 2) return ElMessage.warning('请选择入住和离店日期')
  submitting.value = true
  try {
    await client.post('/bookings', {
      room_type_id: dialog.typeId,
      check_in_date: dialog.dates[0],
      check_out_date: dialog.dates[1],
      guests: dialog.guests,
      remark: dialog.remark,
    })
    ElMessage.success('预订成功！请于入住日到前台办理入住')
    dialog.visible = false
    load()
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.type-card { margin-bottom: 16px; }
.type-head { display: flex; justify-content: space-between; align-items: center; }
.type-name { font-size: 17px; font-weight: 600; color: #303133; }
.price { margin: 10px 0; color: #f56c6c; }
.price .num { font-size: 26px; font-weight: 700; }
.price .unit { font-size: 12px; color: #909399; }
.desc { font-size: 13px; color: #606266; min-height: 40px; line-height: 1.5; }
.meta { display: flex; align-items: center; gap: 6px; color: #909399; font-size: 13px; margin-bottom: 12px; }
</style>
