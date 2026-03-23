<template>
  <div class="move-card" :style="{ borderLeftColor: partyColor }">
    <!-- Header -->
    <div class="mc-header">
      <div class="mc-party">
        <span class="mc-avatar" :style="{ background: partyColor }">{{ (partyName || 'A')[0] }}</span>
        <span class="mc-name">{{ partyName }}</span>
        <span class="mc-round" v-if="move.round">R{{ move.round }}</span>
      </div>
      <span class="mc-badge" :style="{ background: moveColor }">{{ moveLabel }}</span>
    </div>

    <!-- Package -->
    <div v-if="move.package?.issue_values" class="mc-package">
      <div v-for="(val, key) in move.package.issue_values" :key="key" class="mc-pkg-row">
        <span class="mc-pkg-key">{{ key }}</span>
        <span class="mc-pkg-val">{{ val }}</span>
      </div>
      <div v-if="move.package.rationale" class="mc-rationale">{{ move.package.rationale }}</div>
    </div>

    <!-- Argument -->
    <div v-if="move.argument" class="mc-argument">
      <div class="mc-claim">"{{ move.argument.claim }}"</div>
      <div v-for="g in (move.argument.grounds || [])" :key="g" class="mc-ground">-> {{ g }}</div>
    </div>

    <!-- Disclosed Interest -->
    <div v-if="move.disclosed_interest" class="mc-interest">
      <span class="mc-int-badge" :style="{ background: interestColor }">{{ move.disclosed_interest.interest_type?.toUpperCase() }}</span>
      <span class="mc-int-desc">{{ move.disclosed_interest.description }}</span>
      <span class="mc-int-priority">{{ move.disclosed_interest.priority }}</span>
    </div>

    <!-- Reasoning (collapsible) -->
    <div v-if="move.reasoning && (showReasoning || reasoningExpanded)" class="mc-reasoning">
      <div class="mc-reasoning-text">{{ move.reasoning }}</div>
    </div>
    <button
      v-if="move.reasoning && !showReasoning"
      class="mc-reasoning-toggle"
      @click="reasoningExpanded = !reasoningExpanded"
    >
      {{ reasoningExpanded ? '- Hide reasoning' : '+ Show reasoning' }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { MOVE_LABELS, MOVE_COLORS, INTEREST_TYPE_COLORS } from '@/types/protocol'

const props = defineProps({
  move: { type: Object, required: true },
  partyName: { type: String, default: '' },
  partyColor: { type: String, default: '#999' },
  isLatest: { type: Boolean, default: false },
  showReasoning: { type: Boolean, default: false }
})

const reasoningExpanded = ref(false)
const moveLabel = computed(() => MOVE_LABELS[props.move.move_type] || props.move.move_type)
const moveColor = computed(() => MOVE_COLORS[props.move.move_type] || '#999')
const interestColor = computed(() => INTEREST_TYPE_COLORS[props.move.disclosed_interest?.interest_type] || '#999')
</script>

<style scoped>
.move-card {
  background: #FFF;
  border: 1px solid var(--border);
  border-left: 3px solid #CCC;
  border-radius: 6px;
  padding: 14px 16px;
  font-size: 13px;
}

.mc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.mc-party { display: flex; align-items: center; gap: 8px; }

.mc-avatar {
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #FFF; font-size: 10px; font-weight: 700;
}

.mc-name { font-weight: 600; font-size: 13px; }

.mc-round {
  font-family: var(--font-mono); font-size: 10px; color: #BBB;
}

.mc-badge {
  font-family: var(--font-mono); font-size: 9px; font-weight: 700;
  color: #FFF; padding: 3px 8px; border-radius: 3px;
  text-transform: uppercase; letter-spacing: 0.5px;
}

/* Package */
.mc-package {
  background: #F9F9F9; border: 1px solid #EEE;
  border-radius: 4px; padding: 8px 12px; margin-bottom: 8px;
}

.mc-pkg-row {
  display: flex; justify-content: space-between;
  padding: 3px 0; border-bottom: 1px solid #F0F0F0; font-size: 12px;
}

.mc-pkg-row:last-of-type { border-bottom: none; }
.mc-pkg-key { color: #888; }
.mc-pkg-val { font-family: var(--font-mono); font-weight: 600; color: #000; }

.mc-rationale {
  margin-top: 8px; padding-top: 8px; border-top: 1px dashed #EEE;
  font-size: 11px; color: #666; font-style: italic; line-height: 1.5;
}

/* Argument */
.mc-argument { margin-bottom: 8px; }

.mc-claim {
  font-style: italic; color: #444; font-size: 12px;
  margin-bottom: 4px; line-height: 1.5;
}

.mc-ground {
  font-size: 11px; color: #888; padding-left: 8px; line-height: 1.6;
  font-family: var(--font-mono);
}

/* Interest */
.mc-interest {
  display: flex; align-items: center; gap: 8px;
  flex-wrap: wrap; font-size: 12px; margin-bottom: 4px;
}

.mc-int-badge {
  font-family: var(--font-mono); font-size: 8px; font-weight: 700;
  color: #FFF; padding: 2px 5px; border-radius: 2px;
}

.mc-int-desc { color: #333; flex: 1; min-width: 0; }
.mc-int-priority { font-family: var(--font-mono); font-size: 10px; color: #BBB; }

/* Reasoning */
.mc-reasoning {
  margin-top: 8px; padding: 10px; background: #FFFBF5;
  border: 1px dashed #F0E0C0; border-radius: 4px;
}

.mc-reasoning-text {
  font-size: 11px; color: #886; line-height: 1.6; white-space: pre-wrap;
}

.mc-reasoning-toggle {
  background: none; border: none; cursor: pointer;
  font-family: var(--font-mono); font-size: 10px; color: #BBB;
  margin-top: 6px; padding: 0;
}

.mc-reasoning-toggle:hover { color: var(--accent); }
</style>
