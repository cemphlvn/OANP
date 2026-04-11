<template>
  <div v-if="belief && belief.confidence >= 0.005" class="bp" :class="confClass">
    <div class="bp-header" @click="collapsed = !collapsed">
      <span class="bp-title">OPPONENT MODEL</span>
      <span class="bp-conf">{{ (belief.confidence * 100).toFixed(0) }}%</span>
      <span class="bp-toggle">{{ collapsed ? '+' : '-' }}</span>
    </div>
    <div v-if="!collapsed" class="bp-body">
      <div class="bp-section-title">Estimated Priorities</div>
      <div
        v-for="item in sortedPriorities"
        :key="item.id"
        class="bp-row"
      >
        <span class="bp-issue">{{ item.name }}</span>
        <span class="bp-weight">{{ item.weight.toFixed(2) }}</span>
        <div class="bp-bar">
          <div class="bp-bar-fill" :style="{ width: (item.weight * 100) + '%' }"></div>
        </div>
      </div>
      <div v-if="belief.estimated_batna_utility != null" class="bp-batna">
        <span class="bp-batna-label">Est. BATNA</span>
        <span class="bp-batna-val">{{ belief.estimated_batna_utility.toFixed(2) }}</span>
      </div>
      <div v-if="belief.confidence < 0.5" class="bp-caveat">
        Low confidence — tentative estimates
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  belief: { type: Object, default: null },
  issues: { type: Array, default: () => [] },
})

const collapsed = ref(false)

const confClass = computed(() => {
  if (!props.belief) return ''
  const c = props.belief.confidence
  if (c > 0.6) return 'bp-conf-high'
  if (c > 0.3) return 'bp-conf-mid'
  return 'bp-conf-low'
})

const sortedPriorities = computed(() => {
  if (!props.belief?.estimated_priorities) return []
  return Object.entries(props.belief.estimated_priorities)
    .map(([id, weight]) => {
      const issue = props.issues.find(i => i.id === id || i.name === id)
      return { id, name: issue?.name || id, weight }
    })
    .sort((a, b) => b.weight - a.weight)
})
</script>

<style scoped>
.bp {
  margin-bottom: 8px;
  border: 1px solid #F0E0C0;
  border-radius: 4px;
  background: #FFFBF5;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  transition: opacity 0.3s ease;
}
.bp-conf-low { opacity: 0.7; }
.bp-conf-mid { opacity: 0.85; }
.bp-conf-high { opacity: 1.0; }

.bp-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid #F0E0C0;
}
.bp-title {
  font-weight: 700;
  color: #C4A882;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  flex: 1;
}
.bp-conf {
  color: #886;
  font-weight: 600;
}
.bp-toggle {
  color: #CCC;
  font-size: 12px;
}

.bp-body {
  padding: 8px 10px;
}
.bp-section-title {
  font-weight: 600;
  color: #886;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 9px;
}
.bp-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
}
.bp-issue {
  color: #666;
  min-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bp-weight {
  color: #000;
  font-weight: 600;
  min-width: 30px;
  text-align: right;
}
.bp-bar {
  flex: 1;
  height: 3px;
  background: #F0E0C0;
  border-radius: 1.5px;
  overflow: hidden;
}
.bp-bar-fill {
  height: 100%;
  background: #FF5722;
  border-radius: 1.5px;
  transition: width 0.6s ease;
}

.bp-batna {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #F0E0C0;
  color: #886;
}
.bp-batna-val {
  font-weight: 600;
  color: #000;
}
.bp-caveat {
  margin-top: 6px;
  color: #C4A882;
  font-style: italic;
  font-size: 9px;
}
</style>
