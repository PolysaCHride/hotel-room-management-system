<template>
  <div>
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="head">
          <b>员工与用户管理</b>
          <el-button type="primary" @click="dialog.visible = true">新增服务员</el-button>
        </div>
      </template>
      <el-radio-group v-model="filterRole" @change="load" style="margin-bottom: 12px">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="admin">管理员</el-radio-button>
        <el-radio-button value="receptionist">服务员</el-radio-button>
        <el-radio-button value="customer">顾客</el-radio-button>
      </el-radio-group>
      <el-table :data="users" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" width="130" />
        <el-table-column prop="real_name" label="姓名" width="150" />
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="ROLE_TAG[row.role]" effect="plain">{{ ROLE_LABEL[row.role] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '正常' : '已禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.is_active" link type="danger" @click="toggle(row, false)">禁用</el-button>
            <el-button v-else link type="success" @click="toggle(row, true)">启用</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog.visible" title="新增服务员账号" width="420px">
      <el-form label-width="80px">
        <el-form-item label="用户名"><el-input v-model="dialog.username" /></el-form-item>
        <el-form-item label="初始密码"><el-input v-model="dialog.password" placeholder="至少 6 位" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="dialog.real_name" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="dialog.phone" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="createStaff">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../../api/client'

const ROLE_LABEL = { admin: '管理员', receptionist: '服务员', customer: '顾客' }
const ROLE_TAG = { admin: 'danger', receptionist: 'warning', customer: 'success' }

const users = ref([])
const filterRole = ref('')
const dialog = reactive({ visible: false, username: '', password: '', real_name: '', phone: '' })

async function load() {
  users.value = await client.get('/admin/users',
    { params: filterRole.value ? { role: filterRole.value } : {} })
}

function toggle(row, active) {
  ElMessageBox.confirm(`确定${active ? '启用' : '禁用'}账号「${row.username}」吗？`, '提示', { type: 'warning' })
    .then(async () => {
      await client.put(`/admin/users/${row.id}/active`, null, { params: { is_active: active } })
      ElMessage.success('操作成功')
      load()
    })
    .catch(() => {})
}

async function createStaff() {
  if (!dialog.username || dialog.password.length < 6) return ElMessage.warning('请填写用户名和至少 6 位密码')
  await client.post('/admin/staff', null, { params: { ...dialog, visible: undefined } })
  ElMessage.success('服务员账号已创建')
  dialog.visible = false
  Object.assign(dialog, { username: '', password: '', real_name: '', phone: '' })
  load()
}

onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
</style>
