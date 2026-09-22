<template>
  <el-card shadow="never">
    <template #header>
      <div class="head">
        <b>房间管理</b>
        <div>
          <el-select v-model="filterType" placeholder="全部房型" clearable style="width: 150px; margin-right: 8px"
                     @change="load">
            <el-option v-for="t in types" :key="t.id" :value="t.id" :label="t.name" />
          </el-select>
          <el-button type="primary" @click="dialog.visible = true">新增房间</el-button>
        </div>
      </div>
    </template>
    <el-table :data="rooms" stripe>
      <el-table-column prop="room_number" label="房号" width="100" />
      <el-table-column prop="type_name" label="房型" width="140" />
      <el-table-column prop="price" label="价格(元/晚)" width="120" />
      <el-table-column prop="floor" label="楼层" width="80" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="STATUS_TAG[row.status]" effect="plain">{{ STATUS_LABEL[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="note" label="备注" min-width="120" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'available'" link type="warning" @click="setStatus(row, 'maintenance', '维修中')">设为维修</el-button>
          <el-button v-if="row.status === 'maintenance'" link type="success" @click="setStatus(row, 'available', '')">恢复可用</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog.visible" title="新增房间" width="420px">
      <el-form label-width="90px">
        <el-form-item label="房号"><el-input v-model="dialog.room_number" placeholder="如 701" /></el-form-item>
        <el-form-item label="房型">
          <el-select v-model="dialog.type_id" style="width: 100%">
            <el-option v-for="t in types" :key="t.id" :value="t.id" :label="t.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="楼层"><el-input-number v-model="dialog.floor" :min="1" :max="30" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="create">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../../api/client'

const STATUS_LABEL = { available: '空闲', booked: '已订', occupied: '入住中', maintenance: '维修中' }
const STATUS_TAG = { available: 'success', booked: 'warning', occupied: 'danger', maintenance: 'info' }

const rooms = ref([])
const types = ref([])
const filterType = ref(null)
const dialog = reactive({ visible: false, room_number: '', type_id: null, floor: 1 })

async function load() {
  types.value = await client.get('/rooms/types')
  rooms.value = await client.get('/rooms', { params: filterType.value ? { type_id: filterType.value } : {} })
}

async function setStatus(row, status, note) {
  await client.put(`/admin/rooms/${row.id}/status`, { status, note })
  ElMessage.success(`${row.room_number} 状态已更新`)
  load()
}

function remove(row) {
  ElMessageBox.confirm(`确定删除房间 ${row.room_number} 吗？`, '删除房间', { type: 'warning' })
    .then(async () => {
      await client.delete(`/admin/rooms/${row.id}`)
      ElMessage.success('已删除')
      load()
    })
    .catch(() => {})
}

async function create() {
  if (!dialog.room_number || !dialog.type_id) return ElMessage.warning('请填写房号并选择房型')
  await client.post('/admin/rooms', null, {
    params: { room_number: dialog.room_number, type_id: dialog.type_id, floor: dialog.floor },
  })
  ElMessage.success('房间已新增')
  dialog.visible = false
  dialog.room_number = ''
  load()
}

onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
</style>
