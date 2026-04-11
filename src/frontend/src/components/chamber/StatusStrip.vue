<template>
  <div class="status-strip">
    <div class="ss-left">
      <span class="ss-brand" @click="$router.push('/')">OANP</span>
      <span class="ss-sep"></span>
      <span class="ss-phase">
        <span class="ss-dot" :style="{ background: phaseColor }"></span>
        {{ phase?.toUpperCase() }}
      </span>
      <!-- Tier badge (advanced mode) -->
      <template v-if="isAdvancedMode && escalationTier">
        <span class="ss-sep"></span>
        <span
          class="ss-tier-badge"
          :style="{ background: tierColor, color: '#FFF' }"
        >
          {{ tierLabel }}
        </span>
      </template>
      <span class="ss-sep"></span>
      <span class="ss-stat" :class="deadlineUrgency">
        Round <strong>{{ round }}</strong><span v-if="roundLimit">/{{ roundLimit }}</span>
      </span>
      <span class="ss-sep"></span>
      <span class="ss-stat">Moves <strong>{{ moveCount }}</strong></span>
      <span class="ss-sep"></span>
      <span class="ss-stat">Issues <strong>{{ resolvedCount }}/{{ totalIssues }}</strong></span>
    </div>
    <div class="ss-center">
      <slot />
    </div>
    <div class="ss-right">
      <span class="ss-convergence-label">Convergence</span>
      <div class="ss-convergence-bar">
        <div class="ss-convergence-fill" :style="{ width: convergence + '%' }"></div>
      </div>
      <span class="ss-convergence-pct">{{ convergence }}%</span>
      <!-- Demo speed control -->
      <div v-if="isDemoMode && !outcome" class="ss-speed">
        <button
          v-for="s in [1, 2, 5]" :key="s"
          class="ss-speed-btn"
          :class="{ active: currentSpeed === s }"
          @click="$emit('setSpeed', s)"
        >{{ s }}x</button>
      </div>
      <!-- Compliance sidebar toggle (advanced mode) -->
      <button
        v-if="isAdvancedMode"
        class="ss-compliance-btn"
        :class="{ active: complianceOpen }"
        @click="$emit('toggleCompliance')"
        title="Toggle compliance panel"
      >&#9878;</button>
      <button
        v-if="outcome"
        class="ss-analysis-btn"
        @click="$emit('viewAnalysis')"
      >
        View Analysis &#8594;
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { PHASE_COLORS, TIER_COLORS, TIER_LABELS } from '@/types/protocol'

const props = defineProps({
  phase: String,
  round: { type: Number, default: 0 },
  totalRounds: { type: Number, default: 0 },
  moveCount: { type: Number, default: 0 },
  resolvedCount: { type: Number, default: 0 },
  totalIssues: { type: Number, default: 0 },
  convergence: { type: Number, default: 0 },
  outcome: { type: String, default: null },
  isDemoMode: { type: Boolean, default: false },
  currentSpeed: { type: Number, default: 1 },
  // Advanced mode props
  isAdvancedMode: { type: Boolean, default: false },
  escalationTier: { type: String, default: null },
  tierDeadline: { type: Number, default: null },
  complianceOpen: { type: Boolean, default: false },
  stagnationDetected: { type: Boolean, default: false },
})

defineEmits(['viewAnalysis', 'toggleCompliance', 'setSpeed'])

const phaseColor = computed(() => PHASE_COLORS[props.phase] || '#999')
const tierColor = computed(() => TIER_COLORS[props.escalationTier] || '#999')
const tierLabel = computed(() => {
  const idx = ['negotiation', 'mediation', 'arbitration'].indexOf(props.escalationTier) + 1
  const label = TIER_LABELS[props.escalationTier] || props.escalationTier
  return `TIER ${idx}: ${label.toUpperCase()}`
})

const roundLimit = computed(() => {
  if (props.tierDeadline) return props.tierDeadline
  if (props.totalRounds) return props.totalRounds
  return null
})

const deadlineUrgency = computed(() => {
  if (!roundLimit.value) return ''
  const remaining = roundLimit.value - props.round
  if (remaining <= 1) return 'ss-deadline-critical'
  if (remaining <= 2) return 'ss-deadline-warning'
  return ''
})
</script>

<style scoped>
.status-strip {
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid var(--border);
  background: #FFF;
  font-size: 12px;
  flex-shrink: 0;
}

.ss-left { display: flex; align-items: center; gap: 12px; }

.ss-brand {
  font-family: var(--font-mono);
  font-weight: 800;
  font-size: 14px;
  letter-spacing: 1px;
  cursor: pointer;
}
.ss-center { display: flex; align-items: center; }
.ss-right { display: flex; align-items: center; gap: 8px; }

.ss-phase {
  display: flex; align-items: center; gap: 6px;
  font-family: var(--font-mono); font-weight: 700; font-size: 11px;
  letter-spacing: 0.5px;
}

.ss-dot { width: 8px; height: 8px; border-radius: 50%; }

.ss-sep { width: 1px; height: 12px; background: #E0E0E0; }

.ss-stat { color: #666; }
.ss-stat strong { color: #000; font-weight: 700; font-family: var(--font-mono); }

.ss-convergence-label { font-family: var(--font-mono); font-size: 10px; color: #999; }

.ss-convergence-bar {
  width: 80px; height: 6px; background: #F0F0F0;
  border-radius: 3px; overflow: hidden;
}

.ss-convergence-fill {
  height: 100%; background: var(--accent);
  border-radius: 3px; transition: width 0.6s ease;
}

.ss-convergence-pct { font-family: var(--font-mono); font-size: 11px; font-weight: 700; min-width: 30px; }

.ss-speed {
  display: flex;
  gap: 2px;
  background: #F0F0F0;
  padding: 2px;
  border-radius: 4px;
  margin-left: 8px;
}
.ss-speed-btn {
  border: none;
  background: transparent;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: #999;
  padding: 2px 8px;
  border-radius: 3px;
  cursor: pointer;
}
.ss-speed-btn.active {
  background: #FFF;
  color: #000;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
.ss-speed-btn:hover:not(.active) { color: #666; }

.ss-analysis-btn {
  background: #000;
  color: #FFF;
  border: none;
  padding: 5px 14px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  border-radius: 4px;
  margin-left: 8px;
  transition: background 0.15s;
}

.ss-analysis-btn:hover { background: var(--accent); }

/* Tier badge (advanced mode) */
.ss-tier-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 2px 8px;
  border-radius: 3px;
  white-space: nowrap;
}

/* Deadline urgency */
.ss-deadline-warning { color: #f59e0b !important; }
.ss-deadline-warning strong { color: #f59e0b !important; }
.ss-deadline-critical { color: #ef4444 !important; }
.ss-deadline-critical strong { color: #ef4444 !important; animation: pulse-deadline 1s infinite; }

@keyframes pulse-deadline {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Compliance toggle */
.ss-compliance-btn {
  background: transparent;
  border: 1px solid #E0E0E0;
  color: #666;
  width: 28px;
  height: 28px;
  font-size: 14px;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.ss-compliance-btn:hover { border-color: #999; color: #000; }
.ss-compliance-btn.active { background: #000; color: #FFF; border-color: #000; }
</style>
