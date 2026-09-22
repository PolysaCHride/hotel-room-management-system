<template>
  <el-card shadow="never">
    <template #header>
      <div class="head">
        <b>房型与房价管理</b>
        <el-button type="primary" @click="openCreate">新增房型</el-button>
      </div>
    </template>
    <el-table :data="types" stripe>
      <el-table-column prop="name" label="房型" width="150" />
      <el-table-column label="价格(元/晚)" width="150">
        <template #default="{ row }">
          <el-input-number v-model="row.price" :min="0" size="small" @change="savePrice(row)" />
        </template>
      </el-table-column>
      <el-table-column prop="capacity" label="可住人数" width="100" />
      <el-table-column prop="room_count" label="房间数" width="90" />
      <el-table-column prop="free_count" label="今日空闲" width="100" />
      <el-table-column prop="description" label="描述" min-width="180" />
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog.visible" title="新增房型" width="440px">
      <el-form label-width="90px">
        <el-form-item label="房型名"><el-input v-model="dialog.name" /></el-form-item>
        <el-form-item label="价格(元)"><el-input-number v-model="dialog.price" :min="0" /></el-form-item>
        <el-form-item label="可住人数"><el-input-number v-model="dialog.capacity" :min="1" :max="6" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="dialog.description" type="textarea" :rows="2" /></el-form-item>
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

const types = ref([])
const dialog = reactive({ visible: false, name: '', price: 100, capacity: 2, description: '' })

async function load() {
  types.value = await client.get('/rooms/types')
}

async function savePrice(row) {
  await client.put(`/admin/room-types/${row.id}`, { price: row.price })
  ElMessage.success(`已将「${row.name}」价格调整为 ¥${row.price}/晚`)
}

function openCreate() {
  Object.assign(dialog, { visible: true, name: '', price: 100, capacity: 2, description: '' })
}

async function create() {
  if (!dialog.name) return ElMessage.warning('请填写房型名')
  await client.post('/admin/room-types', null, {
    params: { name: dialog.name, price: dialog.price, capacity: dialog.capacity, description: dialog.description },
  })
  ElMessage.success('房型已新增')
  dialog.visible = false
  load()
}

function remove(row) {
  ElMessageBox.confirm(`确定删除房型「${row.name}」吗？`, '删除房型', { type: 'warning' })
    .then(async () => {
      await client.delete(`/admin/room-types/${row.id}`)
      ElMessage.success('已删除')
      load()
    })
    .catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
</style>
