<template>
  <div class="beliefs-view">
    <div class="bv-header">
      <div class="bv-party-tabs">
        <button
          v-for="p in parties"
          :key="p.id"
          class="bv-tab"
          :class="{ active: selectedParty === p.id }"
          @click="selectedParty = p.id"
        >{{ p.name }}</button>
      </div>
      <span class="bv-round">{{ beliefHistory.length }} updates</span>
    </div>

    <div v-if="currentBelief" class="bv-content">
      <!-- Weight Evolution Chart -->
      <div class="bv-section">
        <div class="bv-section-title">Priority Evolution Over Rounds</div>
        <div class="bv-chart" ref="chartRef">
          <div v-if="historyForParty.length < 2" class="bv-chart-empty">
            Awaiting more data points...
          </div>
          <svg v-else :width="chartWidth" :height="chartHeight">
            <!-- Grid lines -->
            <line v-for="y in yTicks" :key="'g'+y"
              :x1="pad" :x2="chartWidth - pad"
              :y1="yScale(y)" :y2="yScale(y)"
              stroke="#F0F0F0" stroke-width="1" />
            <!-- Y axis labels -->
            <text v-for="y in yTicks" :key="'yl'+y"
              :x="pad - 4" :y="yScale(y) + 3"
              text-anchor="end" fill="#BBB" font-size="9"
              font-family="JetBrains Mono, monospace">{{ y.toFixed(1) }}</text>
            <!-- Lines per issue -->
            <path v-for="(line, idx) in chartLines" :key="'l'+idx"
              :d="line.path" fill="none"
              :stroke="line.color" stroke-width="2"
              stroke-linejoin="round" />
            <!-- Legend -->
            <g v-for="(line, idx) in chartLines" :key="'leg'+idx"
              :transform="`translate(${pad + idx * 120}, ${chartHeight - 6})`">
              <rect :fill="line.color" width="10" height="3" rx="1" />
              <text x="14" y="3" fill="#666" font-size="9"
                font-family="JetBrains Mono, monospace">{{ line.label }} ({{ line.lastVal.toFixed(2) }})</text>
            </g>
          </svg>
        </div>
      </div>

      <!-- Current Estimates Table -->
      <div class="bv-section">
        <div class="bv-section-title">Current Estimates (Confidence: {{ (currentBelief.confidence * 100).toFixed(0) }}%)</div>
        <div class="bv-table">
          <div class="bv-table-header">
            <span class="bv-th">Issue</span>
            <span class="bv-th">Weight</span>
            <span class="bv-th">Bar</span>
          </div>
          <div
            v-for="item in sortedWeights"
            :key="item.id"
            class="bv-table-row"
          >
            <span class="bv-td bv-td-issue">{{ item.name }}</span>
            <span class="bv-td bv-td-weight">{{ item.weight.toFixed(3) }}</span>
            <div class="bv-td bv-td-bar">
              <div class="bv-weight-bar">
                <div class="bv-weight-fill" :style="{ width: (item.weight * 100) + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- BATNA + Confidence -->
      <div class="bv-section bv-meta-row">
        <div v-if="currentBelief.estimated_batna_utility != null" class="bv-meta">
          <span class="bv-meta-label">Est. BATNA Utility</span>
          <span class="bv-meta-val">{{ currentBelief.estimated_batna_utility.toFixed(3) }}</span>
        </div>
        <div class="bv-meta">
          <span class="bv-meta-label">Observations</span>
          <span class="bv-meta-val">{{ currentBelief.evidence?.length || 0 }}</span>
        </div>
        <div class="bv-meta">
          <span class="bv-meta-label">Confidence</span>
          <span class="bv-meta-val">{{ (currentBelief.confidence * 100).toFixed(0) }}%</span>
        </div>
      </div>
    </div>

    <div v-else class="bv-empty">
      Select a party to view their opponent model
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  parties: { type: Array, default: () => [] },
  beliefs: { type: Object, default: () => ({}) },
  beliefHistory: { type: Array, default: () => [] },
  issues: { type: Array, default: () => [] },
})

const selectedParty = ref(props.parties[0]?.id || null)
const chartWidth = 600
const chartHeight = 220
const pad = 36
const yTicks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

// Issue colors — monochrome palette with accent for top issue
const issueColors = ['#000', '#666', '#999', '#BBB', '#DDD']

const opponentId = computed(() => {
  if (!selectedParty.value) return null
  const other = props.parties.find(p => p.id !== selectedParty.value)
  return other?.id || null
})

const currentBelief = computed(() => {
  if (!selectedParty.value || !opponentId.value) return null
  const key = `${selectedParty.value}→${opponentId.value}`
  return props.beliefs[key] || null
})

const historyForParty = computed(() => {
  if (!selectedParty.value || !opponentId.value) return []
  return props.beliefHistory.filter(
    h => h.observer_party_id === selectedParty.value && h.target_party_id === opponentId.value
  )
})

const sortedWeights = computed(() => {
  if (!currentBelief.value?.estimated_priorities) return []
  return Object.entries(currentBelief.value.estimated_priorities)
    .map(([id, weight]) => {
      const issue = props.issues.find(i => i.id === id || i.name === id)
      return { id, name: issue?.name || id, weight }
    })
    .sort((a, b) => b.weight - a.weight)
})

function yScale(val) {
  return pad + (1 - val) * (chartHeight - pad * 2)
}

const chartLines = computed(() => {
  if (historyForParty.value.length < 2) return []
  const issueIds = Object.keys(historyForParty.value[0]?.estimated_priorities || {})
  const n = historyForParty.value.length
  const xStep = (chartWidth - pad * 2) / Math.max(n - 1, 1)

  return issueIds.map((iid, idx) => {
    const issue = props.issues.find(i => i.id === iid || i.name === iid)
    const points = historyForParty.value.map((h, t) => {
      const x = pad + t * xStep
      const y = yScale(h.estimated_priorities?.[iid] || 0)
      return `${x},${y}`
    })
    const lastVal = historyForParty.value[n - 1]?.estimated_priorities?.[iid] || 0
    // Top-weight issue gets accent color
    const color = idx === 0 && sortedWeights.value[0]?.id === iid
      ? '#FF5722'
      : (issueColors[idx] || '#CCC')
    return {
      path: 'M ' + points.join(' L '),
      color,
      label: issue?.name || iid,
      lastVal,
    }
  })
})
</script>

<style scoped>
.beliefs-view {
  height: 100%;
  overflow-y: auto;
  background: #FAFAFA;
  font-family: 'JetBrains Mono', monospace;
}

.bv-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  background: #FFF;
}
.bv-party-tabs { display: flex; gap: 4px; }
.bv-tab {
  border: 1px solid var(--border);
  background: transparent;
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  color: #999;
  font-family: var(--font-heading);
}
.bv-tab.active { background: #000; color: #FFF; border-color: #000; }
.bv-round { font-size: 10px; color: #BBB; }

.bv-content { padding: 20px; }

.bv-section {
  margin-bottom: 24px;
}
.bv-section-title {
  font-size: 10px;
  font-weight: 700;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 12px;
}

.bv-chart {
  background: #FFF;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 16px;
  min-height: 200px;
}
.bv-chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 180px;
  color: #CCC;
  font-size: 11px;
}

.bv-table {
  background: #FFF;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}
.bv-table-header {
  display: flex;
  padding: 8px 12px;
  background: #F9F9F9;
  border-bottom: 1px solid var(--border);
}
.bv-th {
  font-size: 9px;
  font-weight: 700;
  color: #BBB;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.bv-table-row {
  display: flex;
  padding: 6px 12px;
  border-bottom: 1px solid #F5F5F5;
  align-items: center;
}
.bv-table-row:last-child { border-bottom: none; }
.bv-td { font-size: 11px; }
.bv-td-issue { flex: 1; color: #555; }
.bv-td-weight { width: 60px; text-align: right; font-weight: 600; color: #000; }
.bv-td-bar { flex: 1; padding-left: 12px; }
.bv-weight-bar {
  height: 4px;
  background: #F0F0F0;
  border-radius: 2px;
  overflow: hidden;
}
.bv-weight-fill {
  height: 100%;
  background: #FF5722;
  border-radius: 2px;
  transition: width 0.6s ease;
}

.bv-meta-row {
  display: flex;
  gap: 24px;
}
.bv-meta {
  background: #FFF;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px 16px;
  flex: 1;
}
.bv-meta-label {
  display: block;
  font-size: 9px;
  color: #BBB;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}
.bv-meta-val {
  font-size: 18px;
  font-weight: 700;
  color: #000;
}

.bv-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #CCC;
  font-size: 12px;
}
</style>
