<template>
  <div class="status-strip">
    <div class="ss-left">
      <span class="ss-brand" @click="$router.push('/')">OANP</span>
      <span class="ss-sep"></span>
      <span class="ss-phase">
        <span class="ss-dot" :style="{ background: phaseColor }"></span>
        {{ phase?.toUpperCase() }}
      </span>
      <span class="ss-sep"></span>
      <span class="ss-stat">Round <strong>{{ round }}</strong><span v-if="totalRounds">/{{ totalRounds }}</span></span>
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
import { PHASE_COLORS } from '@/types/protocol'

const props = defineProps({
  phase: String,
  round: { type: Number, default: 0 },
  totalRounds: { type: Number, default: 0 },
  moveCount: { type: Number, default: 0 },
  resolvedCount: { type: Number, default: 0 },
  totalIssues: { type: Number, default: 0 },
  convergence: { type: Number, default: 0 },
  outcome: { type: String, default: null }
})

defineEmits(['viewAnalysis'])

const phaseColor = computed(() => PHASE_COLORS[props.phase] || '#999')
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
</style>
