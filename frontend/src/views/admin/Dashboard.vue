<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="page-card">
      <el-col :span="4" v-for="c in cards" :key="c.label">
        <el-card shadow="hover">
          <div class="stat">
            <span class="num" :style="{ color: c.color }">{{ c.value }}</span>
            <span class="label">{{ c.label }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="page-card">
          <template #header><b>近 7 天营收（元）</b></template>
          <div ref="revenueChart" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="page-card">
          <template #header><b>预订状态分布</b></template>
          <div ref="bookingChart" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import client from '../../api/client'

const cards = ref([])
const revenueChart = ref(null)
const bookingChart = ref(null)

const STATUS_LABEL = { pending: '待到店', checked_in: '已入住', completed: '已完成', cancelled: '已取消' }

async function load() {
  const s = await client.get('/admin/stats')
  cards.value = [
    { label: '总房数', value: s.total_rooms, color: '#409eff' },
    { label: '入住率 %', value: s.occupancy_rate, color: '#67c23a' },
    { label: '当前在住', value: s.occupied_rooms, color: '#e6a23c' },
    { label: '今日到店', value: s.today_arrivals, color: '#f56c6c' },
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

onMounted(load)
</script>

<style scoped>
.stat { text-align: center; }
.stat .num { display: block; font-size: 26px; font-weight: 700; }
.stat .label { font-size: 13px; color: #909399; }
.chart { height: 320px; }
</style>
