<template>
  <div class="compliance-sidebar">
    <!-- Header -->
    <div class="cs-header">
      <span class="cs-title">COMPLIANCE</span>
      <button class="cs-close" @click="$emit('close')">&times;</button>
    </div>

    <!-- Current Tier -->
    <div class="cs-section">
      <div class="cs-section-label">CURRENT TIER</div>
      <div class="cs-tier-name" :style="{ color: currentTierColor }">
        {{ TIER_LABELS[currentTierName] || 'N/A' }}
      </div>
      <div class="cs-bar-track">
        <div
          class="cs-bar-fill"
          :style="{ width: tierProgress + '%', background: currentTierColor }"
        ></div>
      </div>
      <div class="cs-bar-label">
        {{ tierRoundsUsed }} / {{ tierRoundLimit }} rounds
      </div>
    </div>

    <!-- Hard Deadline -->
    <div class="cs-section">
      <div class="cs-section-label">HARD DEADLINE</div>
      <div class="cs-bar-track">
        <div
          class="cs-bar-fill"
          :style="{ width: hardDeadlineProgress + '%', background: hardDeadlineUrgent ? '#ef4444' : '#666' }"
        ></div>
      </div>
      <div class="cs-bar-label">
        {{ totalRoundsUsed }} / {{ hardLimit }} rounds
        <span v-if="deadlineStatus?.remaining != null">({{ deadlineStatus.remaining }} left)</span>
      </div>
    </div>

    <!-- Participation -->
    <div class="cs-section">
      <div class="cs-section-label">PARTICIPATION</div>
      <div v-for="party in parties" :key="party.name || party" class="cs-participation-row">
        <span class="cs-party-name">{{ party.name || party }}</span>
        <div class="cs-bar-track cs-bar-sm">
          <div
            class="cs-bar-fill"
            :style="{ width: participationPct(party) + '%', background: '#FFF' }"
          ></div>
        </div>
        <span class="cs-pct">{{ participationPct(party) }}%</span>
      </div>
      <div class="cs-balance-tag" :class="isBalanced ? 'balanced' : 'imbalanced'">
        {{ isBalanced ? 'Balanced' : 'Imbalanced' }}
      </div>
    </div>

    <!-- Escalation History -->
    <div class="cs-section">
      <div class="cs-section-label">ESCALATION HISTORY</div>
      <div v-if="!tierHistory || tierHistory.length === 0" class="cs-empty">No escalations yet</div>
      <div v-for="(evt, i) in tierHistory" :key="i" class="cs-escalation-entry">
        <span class="cs-esc-round">R{{ evt.round || evt.at_round || '?' }}</span>
        <span class="cs-esc-text">
          {{ TIER_LABELS[evt.from_tier || evt.old_tier] || '?' }}
          &rarr;
          {{ TIER_LABELS[evt.to_tier || evt.new_tier] || '?' }}
        </span>
        <span v-if="evt.reason" class="cs-esc-reason">({{ evt.reason }})</span>
      </div>
    </div>

    <!-- Stagnation -->
    <div class="cs-section">
      <div class="cs-section-label">STAGNATION</div>
      <div v-if="stagnationDetected" class="cs-stagnation-warn">
        Stagnation detected &mdash; escalation may trigger
      </div>
      <div v-else class="cs-stagnation-ok">Not detected</div>
    </div>

    <!-- Due Process Log -->
    <div class="cs-section cs-section-log">
      <div class="cs-section-label">DUE PROCESS LOG</div>
      <div class="cs-log-scroll">
        <div v-if="logEntries.length === 0" class="cs-empty">No log entries</div>
        <div v-for="(entry, i) in logEntries" :key="i" class="cs-log-entry">
          <span class="cs-log-round">R{{ entry.round || '?' }}</span>
          <span class="cs-log-text">{{ entry.event || entry.message || entry }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { TIER_COLORS, TIER_LABELS } from '@/types/protocol'

const props = defineProps({
  compliance: { type: Object, default: () => ({}) },
  moves: { type: Array, default: () => [] },
  parties: { type: Array, default: () => [] },
  tierHistory: { type: Array, default: () => [] },
  deadlineStatus: { type: Object, default: null },
  stagnationDetected: { type: Boolean, default: false }
})

defineEmits(['close'])

const currentTierName = computed(() => {
  return props.compliance?.current_tier || props.compliance?.escalation_tier || 'negotiation'
})

const currentTierColor = computed(() => TIER_COLORS[currentTierName.value] || '#999')

const tierRoundsUsed = computed(() => {
  return props.deadlineStatus?.current || props.compliance?.tier_round || 0
})

const tierRoundLimit = computed(() => {
  return props.deadlineStatus?.limit || props.compliance?.tier_limit || 10
})

const tierProgress = computed(() => {
  if (!tierRoundLimit.value) return 0
  return Math.min(100, Math.round((tierRoundsUsed.value / tierRoundLimit.value) * 100))
})

const hardLimit = computed(() => {
  return props.compliance?.hard_deadline || 20
})

const totalRoundsUsed = computed(() => {
  return props.compliance?.total_rounds || props.compliance?.round || 0
})

const hardDeadlineProgress = computed(() => {
  if (!hardLimit.value) return 0
  return Math.min(100, Math.round((totalRoundsUsed.value / hardLimit.value) * 100))
})

const hardDeadlineUrgent = computed(() => {
  return hardDeadlineProgress.value > 80
})

function participationPct(party) {
  const name = party.name || party
  if (!props.moves || props.moves.length === 0) return 0
  const count = props.moves.filter(m => m.party === name || m.party_name === name).length
  return Math.round((count / props.moves.length) * 100)
}

const isBalanced = computed(() => {
  if (!props.parties || props.parties.length < 2) return true
  const pcts = props.parties.map(p => participationPct(p))
  const max = Math.max(...pcts)
  const min = Math.min(...pcts)
  return min >= 30 && max <= 70
})

const logEntries = computed(() => {
  const log = props.compliance?.due_process_log || []
  return log.slice(-20)
})
</script>

<style scoped>
.compliance-sidebar {
  width: 280px;
  background: #1A1A1A;
  color: #CCC;
  font-family: var(--font-mono);
  font-size: 11px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  border-left: 1px solid #333;
  flex-shrink: 0;
}

.cs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #333;
}

.cs-title {
  font-weight: 800;
  font-size: 11px;
  letter-spacing: 1.5px;
  color: #FFF;
}

.cs-close {
  background: transparent;
  border: none;
  color: #666;
  font-size: 18px;
  cursor: pointer;
  line-height: 1;
  padding: 0;
}

.cs-close:hover {
  color: #FFF;
}

.cs-section {
  padding: 12px 16px;
  border-bottom: 1px solid #2A2A2A;
}

.cs-section-label {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #666;
  margin-bottom: 8px;
}

.cs-tier-name {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 6px;
}

.cs-bar-track {
  width: 100%;
  height: 4px;
  background: #333;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 4px;
}

.cs-bar-sm {
  flex: 1;
  height: 3px;
}

.cs-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.4s ease;
}

.cs-bar-label {
  font-size: 10px;
  color: #888;
}

.cs-participation-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.cs-party-name {
  width: 60px;
  font-size: 10px;
  color: #AAA;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cs-pct {
  font-size: 10px;
  color: #888;
  min-width: 28px;
  text-align: right;
}

.cs-balance-tag {
  display: inline-block;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 2px 6px;
  border-radius: 3px;
  margin-top: 4px;
}

.cs-balance-tag.balanced {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.15);
}

.cs-balance-tag.imbalanced {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.15);
}

.cs-escalation-entry {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
  line-height: 1.4;
}

.cs-esc-round {
  color: #666;
  font-weight: 600;
}

.cs-esc-text {
  color: #CCC;
}

.cs-esc-reason {
  color: #888;
  font-size: 10px;
}

.cs-empty {
  color: #555;
  font-style: italic;
  font-size: 10px;
}

.cs-stagnation-warn {
  color: #f59e0b;
  font-weight: 600;
}

.cs-stagnation-ok {
  color: #22c55e;
}

.cs-section-log {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.cs-log-scroll {
  flex: 1;
  overflow-y: auto;
  max-height: 200px;
}

.cs-log-entry {
  display: flex;
  gap: 6px;
  padding: 3px 0;
  border-bottom: 1px solid #222;
  font-size: 10px;
}

.cs-log-round {
  color: #555;
  font-weight: 600;
  min-width: 24px;
}

.cs-log-text {
  color: #999;
  word-break: break-word;
}
</style>
