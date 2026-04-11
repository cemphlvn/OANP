<template>
  <div class="beliefs-view">
    <div class="bv-header">
      <span class="bv-title">Opponent Models</span>
      <span class="bv-count">{{ beliefHistory.length }} updates</span>
    </div>

    <div v-if="columns.length > 0" class="bv-columns" :class="{ 'bv-single': columns.length === 1 }">
      <div v-for="col in columns" :key="col.key" class="bv-column">
        <!-- Column header -->
        <div class="bv-col-header">
          <span class="bv-col-dot" :style="{ background: col.color }"></span>
          <span>{{ col.observerName }}'s model of {{ col.targetName }}</span>
        </div>

        <!-- Chart -->
        <div class="bv-chart">
          <div v-if="col.history.length < 2" class="bv-chart-empty">
            Awaiting more data points...
          </div>
          <svg v-else :width="chartWidth" :height="180" class="bv-svg">
            <line v-for="y in yTicks" :key="'g'+y"
              :x1="pad" :x2="chartWidth - pad"
              :y1="yScale(y, 180)" :y2="yScale(y, 180)"
              stroke="#F0F0F0" stroke-width="1" />
            <text v-for="y in yTicks" :key="'yl'+y"
              :x="pad - 4" :y="yScale(y, 180) + 3"
              text-anchor="end" fill="#BBB" font-size="9"
              font-family="JetBrains Mono, monospace">{{ y.toFixed(1) }}</text>
            <path v-for="(line, idx) in col.chartLines" :key="'l'+idx"
              :d="line.path" fill="none"
              :stroke="line.color" stroke-width="2"
              stroke-linejoin="round" />
          </svg>
          <!-- Legend below chart -->
          <div v-if="col.chartLines.length > 0" class="bv-legend">
            <div v-for="(line, idx) in col.chartLines" :key="'leg'+idx" class="bv-legend-item">
              <span class="bv-legend-dot" :style="{ background: line.color }"></span>
              <span class="bv-legend-label">{{ line.label }}</span>
              <span class="bv-legend-val">{{ line.lastVal.toFixed(2) }}</span>
            </div>
          </div>
        </div>

        <!-- Weights table -->
        <div class="bv-table">
          <div class="bv-table-title">Current Estimates</div>
          <div v-for="item in col.sortedWeights" :key="item.id" class="bv-table-row">
            <span class="bv-td-issue">{{ item.name }}</span>
            <span class="bv-td-weight">{{ item.weight.toFixed(3) }}</span>
            <div class="bv-td-bar">
              <div class="bv-td-fill" :style="{ width: (item.weight * 100) + '%', background: col.color }"></div>
            </div>
          </div>
        </div>

        <!-- Meta -->
        <div class="bv-meta-row">
          <div class="bv-meta">
            <span class="bv-meta-label">Confidence</span>
            <span class="bv-meta-val">{{ (col.belief.confidence * 100).toFixed(0) }}%</span>
          </div>
          <div v-if="col.belief.estimated_batna_utility != null" class="bv-meta">
            <span class="bv-meta-label">Est. BATNA</span>
            <span class="bv-meta-val">{{ col.belief.estimated_batna_utility.toFixed(2) }}</span>
          </div>
          <div class="bv-meta">
            <span class="bv-meta-label">Observations</span>
            <span class="bv-meta-val">{{ col.belief.evidence?.length || 0 }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="bv-empty">No opponent model data yet</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { PARTY_COLORS } from '@/types/protocol'

const props = defineProps({
  parties: { type: Array, default: () => [] },
  beliefs: { type: Object, default: () => ({}) },
  beliefHistory: { type: Array, default: () => [] },
  issues: { type: Array, default: () => [] },
})

const pad = 32
const yTicks = [0.0, 0.25, 0.5, 0.75, 1.0]
const issueColors = ['#000', '#666', '#999', '#BBB', '#DDD']

const chartWidth = computed(() => props.parties.length >= 2 ? 280 : 480)

function yScale(val, h) {
  return pad + (1 - val) * (h - pad * 2)
}

const columns = computed(() => {
  const cols = []
  for (let i = 0; i < props.parties.length; i++) {
    for (let j = 0; j < props.parties.length; j++) {
      if (i === j) continue
      const obs = props.parties[i]
      const tgt = props.parties[j]
      const key = `${obs.id}→${tgt.id}`
      const belief = props.beliefs[key]
      if (!belief) continue

      const history = props.beliefHistory.filter(
        h => h.observer_party_id === obs.id && h.target_party_id === tgt.id
      )

      const sortedWeights = belief.estimated_priorities
        ? Object.entries(belief.estimated_priorities)
            .map(([id, weight]) => ({
              id,
              name: props.issues.find(x => x.id === id || x.name === id)?.name || id,
              weight,
            }))
            .sort((a, b) => b.weight - a.weight)
        : []

      // Build chart lines
      const chartLines = history.length >= 2
        ? buildChartLines(history, sortedWeights)
        : []

      cols.push({
        key,
        observerId: obs.id,
        targetId: tgt.id,
        observerName: obs.name,
        targetName: tgt.name,
        color: PARTY_COLORS[i] || '#999',
        belief,
        history,
        sortedWeights,
        chartLines,
      })
    }
  }
  return cols
})

function buildChartLines(history, sortedWeights) {
  if (!history.length || !history[0].estimated_priorities) return []
  const issueIds = Object.keys(history[0].estimated_priorities)
  const n = history.length
  const w = chartWidth.value
  const xStep = (w - pad * 2) / Math.max(n - 1, 1)

  return issueIds.map((iid, idx) => {
    const issue = props.issues.find(x => x.id === iid || x.name === iid)
    const points = history.map((h, t) => {
      const x = pad + t * xStep
      const y = yScale(h.estimated_priorities?.[iid] || 0, 180)
      return `${x},${y}`
    })
    const lastVal = history[n - 1]?.estimated_priorities?.[iid] || 0
    const isTop = sortedWeights[0]?.id === iid
    const color = isTop ? '#FF5722' : (issueColors[idx] || '#CCC')
    return {
      path: 'M ' + points.join(' L '),
      color,
      label: issue?.name || iid,
      lastVal,
    }
  })
}
</script>

<style scoped>
.beliefs-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #FAFAFA;
}

.bv-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  background: #FFF;
}
.bv-title {
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.bv-count {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #BBB;
}

.bv-columns {
  display: flex;
  gap: 16px;
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}
.bv-single { justify-content: center; }
.bv-column {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bv-single .bv-column { max-width: 520px; }

.bv-col-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 600;
}
.bv-col-dot { width: 8px; height: 8px; border-radius: 50%; }

/* Chart */
.bv-chart {
  background: #FFF;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
}
.bv-chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 120px;
  color: #CCC;
  font-family: var(--font-mono);
  font-size: 11px;
}
.bv-svg { display: block; }

.bv-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  padding-top: 8px;
  border-top: 1px solid #F0F0F0;
  margin-top: 8px;
}
.bv-legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 9px;
}
.bv-legend-dot { width: 6px; height: 3px; border-radius: 1px; }
.bv-legend-label { color: #666; }
.bv-legend-val { color: #000; font-weight: 600; }

/* Table */
.bv-table {
  background: #FFF;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
}
.bv-table-title {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
}
.bv-table-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
}
.bv-td-issue {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #555;
  min-width: 70px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bv-td-weight {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  min-width: 36px;
  text-align: right;
}
.bv-td-bar {
  flex: 1;
  height: 4px;
  background: #F0F0F0;
  border-radius: 2px;
  overflow: hidden;
}
.bv-td-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s ease;
}

/* Meta */
.bv-meta-row {
  display: flex;
  gap: 8px;
}
.bv-meta {
  flex: 1;
  background: #FFF;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
}
.bv-meta-label {
  display: block;
  font-family: var(--font-mono);
  font-size: 8px;
  color: #BBB;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
}
.bv-meta-val {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
}

.bv-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: #CCC;
  font-family: var(--font-mono);
  font-size: 12px;
}
</style>
