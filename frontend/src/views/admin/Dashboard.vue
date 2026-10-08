<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="page-card">
      <el-col :xs="12" :sm="8" :md="4" v-for="c in cards" :key="c.label" style="margin-bottom: 12px">
        <el-card shadow="hover">
          <div class="stat">
            <span class="num" :style="{ color: c.color }">{{ c.value }}</span>
            <span class="label">{{ c.label }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :xs="24" :sm="12">
        <el-card shadow="never" class="page-card">
          <template #header><b>近 7 天营收（元）</b></template>
          <div ref="revenueChart" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12">
        <el-card shadow="never" class="page-card">
          <template #header><b>预订状态分布</b></template>
          <div ref="bookingChart" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 超时自动退房 -->
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="ac-head">
          <b>超时自动退房</b>
          <el-tag :type="ac.enabled ? 'success' : 'info'" effect="plain">
            {{ ac.enabled ? `已开启（退房时限 ${ac.checkout_hour}:00 + 宽限 ${ac.grace_hours} 小时，每 ${ac.interval_seconds} 秒扫描）` : '已关闭' }}
          </el-tag>
        </div>
      </template>
      <div v-if="ac.overdue.length" class="ac-overdue">
        <el-alert type="warning" :closable="false"
                  :title="`当前有 ${ac.overdue.length} 笔超期未退房的在住记录，超期后系统将自动退房并生成待支付账单`" />
        <el-table :data="ac.overdue" size="small" style="margin-top: 10px">
          <el-table-column prop="room_number" label="房号" width="80" />
          <el-table-column prop="guest_name" label="客人" width="110" />
          <el-table-column prop="expected_check_out" label="预计离店" width="120" />
          <el-table-column prop="check_in_time" label="入住时间" />
        </el-table>
      </div>
      <el-empty v-else description="当前没有超期未退房的在住记录" :image-size="60" />
      <div class="ac-foot">
        <span v-if="ac.last_run" class="muted">
          最近扫描：{{ ac.last_run.time }}，自动退房 {{ ac.last_run.count }} 笔
        </span>
        <el-button type="primary" size="small" :loading="ac.running" @click="runScan">
          立即扫描
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import client from '../../api/client'

const cards = ref([])
const revenueChart = ref(null)
const bookingChart = ref(null)
const ac = reactive({ enabled: false, checkout_hour: 12, grace_hours: 2, interval_seconds: 60,
                      last_run: null, overdue: [], running: false })

async function loadAutoCheckout() {
  const s = await client.get('/admin/auto-checkout')
  Object.assign(ac, {
    enabled: s.enabled, checkout_hour: s.checkout_hour, grace_hours: s.grace_hours,
    interval_seconds: s.interval_seconds, last_run: s.last_run, overdue: s.overdue,
  })
}

async function runScan() {
  ac.running = true
  try {
    const res = await client.post('/admin/auto-checkout/run')
    if (res.count > 0) {
      ElMessage.success(res.message)
      await Promise.all([load(), loadAutoCheckout()])
    } else {
      ElMessage.info(res.message)
      await loadAutoCheckout()
    }
  } finally {
    ac.running = false
  }
}

const STATUS_LABEL = { pending: '待到店', checked_in: '已入住', completed: '已完成', cancelled: '已取消' }

async function load() {
  const s = await client.get('/admin/stats')
  cards.value = [
    { label: '总房数', value: s.total_rooms, color: '#409eff' },
    { label: '入住率 %', value: s.occupancy_rate, color: '#67c23a' },
    { label: '当前在住', value: s.occupied_rooms, color: '#e6a23c' },
    { label: '今日待到店', value: s.today_arrivals, color: '#f56c6c' },
    { label: '今日营收(元)', value: s.revenue_today, color: '#f56c6c' },
    { label: '累计营收(元)', value: s.revenue_total, color: '#67c23a' },
  ]

  // 营收折线图
  const rc = echarts.init(revenueChart.value)
  rc.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: s.revenue_by_day.map((d) => d.date.slice(5)) },
    yAxis: { type: 'value' },
    series: [{
      type: 'line', smooth: true, areaStyle: { opacity: 0.15 },
      data: s.revenue_by_day.map((d) => d.amount), itemStyle: { color: '#409eff' },
    }],
  })

  // 预订状态饼图
  const bc = echarts.init(bookingChart.value)
  bc.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['40%', '65%'],
      data: Object.entries(s.booking_status_count).map(([k, v]) => ({
        name: STATUS_LABEL[k] || k, value: v,
      })),
    }],
  })

  window.addEventListener('resize', () => { rc.resize(); bc.resize() })
}

onMounted(() => { load(); loadAutoCheckout() })
</script>

<style scoped>
.stat { text-align: center; }
.stat .num { display: block; font-size: 26px; font-weight: 700; }
.stat .label { font-size: 13px; color: #909399; }
.chart { height: 320px; }
.ac-head { display: flex; justify-content: space-between; align-items: center; }
.ac-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 6px; }
.muted { color: #909399; font-size: 13px; }
</style>
