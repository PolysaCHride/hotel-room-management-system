<template>
  <div>
    <!-- 统计条 -->
    <el-row :gutter="16" class="page-card">
      <el-col :span="6" v-for="c in cards" :key="c.label">
        <el-card shadow="hover">
          <div class="stat"><span class="num">{{ c.value }}</span><span class="label">{{ c.label }}</span></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 续订确认 -->
    <el-card v-if="renewals.length" shadow="never" class="page-card">
      <template #header><b>续订确认（{{ renewals.length }} 条待处理）</b></template>
      <el-table :data="renewals" stripe>
        <el-table-column prop="id" label="单号" width="70" />
        <el-table-column prop="customer_name" label="客人" width="110" />
        <el-table-column prop="room_number" label="房间" width="90" />
        <el-table-column prop="room_type_name" label="房型" width="130" />
        <el-table-column label="当前离店" width="120" prop="check_out_date" />
        <el-table-column label="申请延长至" width="130">
          <template #default="{ row }">
            <b class="highlight">{{ row.requested_check_out }}</b>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'checked_in' ? 'success' : 'warning'" effect="plain">
              {{ row.status === 'checked_in' ? '在住' : '待到店' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="confirmRenewal(row)">确认续订</el-button>
            <el-button link type="danger" @click="rejectRenewal(row)">拒绝</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 办理入住 -->
    <el-card shadow="never" class="page-card">
      <template #header><b>办理入住</b></template>
      <el-form inline>
        <el-form-item label="入住方式">
          <el-radio-group v-model="form.mode">
            <el-radio-button value="booking">预订入住</el-radio-button>
            <el-radio-button value="walkin">散客开房</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <template v-if="form.mode === 'booking'">
          <el-form-item label="待到店预订">
            <el-select v-model="form.booking_id" placeholder="选择待到店的预订" style="width: 300px"
                       @change="onBookingPicked">
              <el-option v-for="a in arrivals" :key="a.id" :value="a.id"
                         :label="`#${a.id} ${a.customer_name} · ${a.room_type_name}${a.room_number ? ' · ' + a.room_number + '房' : ''} · ${a.check_in_date}`" />
            </el-select>
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item label="客人姓名">
            <el-input v-model="form.guest_name" placeholder="姓名" style="width: 120px" />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input v-model="form.guest_phone" placeholder="手机号" style="width: 140px" />
          </el-form-item>
          <el-form-item label="房型">
            <el-select v-model="form.room_type_id" placeholder="选择房型" style="width: 140px" @change="loadRooms">
              <el-option v-for="t in types" :key="t.id" :value="t.id"
                         :label="`${t.name}（空${t.free_count}）`" />
            </el-select>
          </el-form-item>
        </template>
        <el-form-item label="预计离店">
          <el-date-picker v-model="form.expected_check_out" type="date" value-format="YYYY-MM-DD"
                          :disabled-date="(d) => d.getTime() <= Date.now()" placeholder="离店日期"
                          @change="loadRooms" />
        </el-form-item>
        <el-form-item label="分配方式">
          <el-radio-group v-model="form.assign_mode" @change="loadRooms">
            <el-radio-button value="auto">自动分配</el-radio-button>
            <el-radio-button value="manual">指定房间</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.assign_mode === 'manual'" label="指定房间">
          <el-select v-model="form.room_id" placeholder="选择可用房间" style="width: 160px">
            <el-option v-for="r in availableRooms" :key="r.id" :value="r.id"
                       :label="`${r.room_number} 房（${r.floor}层）`" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="checkingIn" @click="checkIn">
            <el-icon><Key /></el-icon> 办理入住
          </el-button>
        </el-form-item>
      </el-form>
      <el-alert v-if="pickedBooking" type="info" :closable="false" style="margin-top: -8px"
                :title="`预订客人：${pickedBooking.customer_name}（${pickedBooking.customer_phone}），` +
                        `入住 ${pickedBooking.check_in_date} ~ ${pickedBooking.check_out_date}` +
                        (pickedBooking.room_number ? `，预订锁定房间 ${pickedBooking.room_number}` : '')" />
    </el-card>

    <!-- 今日待到店 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-head">
          <b>今日待到店</b>
          <el-checkbox v-model="showAllPending" @change="loadArrivals">显示全部待到店</el-checkbox>
        </div>
      </template>
      <el-table :data="arrivals" stripe>
        <el-table-column prop="id" label="单号" width="70" />
        <el-table-column prop="customer_name" label="客人" width="110" />
        <el-table-column prop="customer_phone" label="手机号" width="130" />
        <el-table-column prop="room_type_name" label="房型" width="120" />
        <el-table-column prop="room_number" label="锁定房间" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.room_number" type="warning" effect="plain">{{ row.room_number }} 房</el-tag>
            <span v-else class="muted">未分配</span>
          </template>
        </el-table-column>
        <el-table-column label="入住 — 离店" width="190">
          <template #default="{ row }">{{ row.check_in_date }} ~ {{ row.check_out_date }}</template>
        </el-table-column>
        <el-table-column prop="guests" label="人数" width="70" />
        <el-table-column prop="estimated_price" label="预计(元)" width="100" />
        <el-table-column prop="remark" label="备注" min-width="100" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="pickBooking(row)">办理入住</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../../api/client'

const cards = ref([
  { label: '今日待到店', value: 0 },
  { label: '当前在住', value: 0 },
  { label: '空闲房间', value: 0 },
  { label: '维修中', value: 0 },
])
const arrivals = ref([])
const renewals = ref([])
const types = ref([])
const availableRooms = ref([])
const showAllPending = ref(false)
const checkingIn = ref(false)

const form = reactive({
  mode: 'booking',
  booking_id: null,
  guest_name: '',
  guest_phone: '',
  room_type_id: null,
  room_id: null,
  assign_mode: 'auto',
  expected_check_out: '',
})

const pickedBooking = computed(() => arrivals.value.find((a) => a.id === form.booking_id))

async function loadArrivals() {
  arrivals.value = await client.get('/reception/arrivals', { params: { all_pending: showAllPending.value } })
  cards.value[0].value = arrivals.value.length
}

async function loadRenewals() {
  renewals.value = await client.get('/reception/renewals')
}

async function loadStats() {
  const s = await client.get('/reception/room-summary').catch(() => null)
  if (!s) return
  cards.value[1].value = s.occupied_rooms
  cards.value[2].value = s.free_rooms
  cards.value[3].value = s.maintenance_rooms
}

/** 选择房间/房型/离店日期后，加载可用房间列表（排除被预订房间） */
async function loadRooms() {
  const typeId = form.mode === 'booking' ? pickedBooking.value?.room_type_id : form.room_type_id
  if (form.assign_mode !== 'manual' || !typeId || !form.expected_check_out) {
    availableRooms.value = []
    return
  }
  availableRooms.value = await client.get('/reception/available-rooms', {
    params: {
      room_type_id: typeId,
      expected_out: form.expected_check_out,
      ...(form.booking_id ? { booking_id: form.booking_id } : {}),
    },
  })
  // 预订入住默认选中预订锁定的房间
  const locked = pickedBooking.value?.room_id
  if (locked && availableRooms.value.some((r) => r.id === locked)) form.room_id = locked
  else if (!availableRooms.value.some((r) => r.id === form.room_id)) form.room_id = null
}

async function load() {
  await Promise.all([loadArrivals(), loadStats(), loadRenewals()])
  types.value = await client.get('/rooms/types')
}

function pickBooking(row) {
  form.mode = 'booking'
  form.booking_id = row.id
  onBookingPicked(row.id)
}

function onBookingPicked(id) {
  const row = arrivals.value.find((a) => a.id === id)
  if (row && !form.expected_check_out) form.expected_check_out = row.check_out_date
  if (form.assign_mode === 'manual') loadRooms()
}

async function checkIn() {
  const payload = { expected_check_out: form.expected_check_out }
  if (form.mode === 'booking') {
    if (!form.booking_id) return ElMessage.warning('请选择待到店预订')
    payload.booking_id = form.booking_id
  } else {
    if (!form.guest_name) return ElMessage.warning('请填写客人姓名')
    if (!form.room_type_id) return ElMessage.warning('请选择房型')
    payload.guest_name = form.guest_name
    payload.guest_phone = form.guest_phone
    payload.room_type_id = form.room_type_id
  }
  if (!form.expected_check_out) return ElMessage.warning('请选择预计离店日期')
  if (form.assign_mode === 'manual') {
    if (!form.room_id) return ElMessage.warning('请选择指定房间')
    payload.room_id = form.room_id
  }
  checkingIn.value = true
  try {
    const rec = await client.post('/reception/check-in', payload)
    ElMessage.success(`入住成功！已分配房间 ${rec.room_number}`)
    form.booking_id = null
    form.room_id = null
    form.guest_name = ''
    form.guest_phone = ''
    load()
  } finally {
    checkingIn.value = false
  }
}

function confirmRenewal(row) {
  ElMessageBox.confirm(
    `确认将 #${row.id}（${row.customer_name}，${row.room_number} 房）的离店日期从 ${row.check_out_date} 延长至 ${row.requested_check_out} 吗？`,
    '确认续订', { type: 'warning' }
  ).then(async () => {
    await client.post(`/reception/renewals/${row.id}/confirm`)
    ElMessage.success('续订已确认')
    load()
  }).catch(() => {})
}

function rejectRenewal(row) {
  ElMessageBox.confirm(`确定拒绝 #${row.id} 的续订申请吗？`, '拒绝续订', { type: 'warning' })
    .then(async () => {
      await client.post(`/reception/renewals/${row.id}/reject`)
      ElMessage.success('已拒绝该续订申请')
      load()
    }).catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.stat { text-align: center; }
.stat .num { display: block; font-size: 28px; font-weight: 700; color: #409eff; }
.stat .label { font-size: 13px; color: #909399; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.highlight { color: #e6a23c; }
.muted { color: #909399; }
</style>
