<template>
  <div class="process-timeline">
    <div class="pt-track">
      <template v-for="(tier, idx) in tiers" :key="tier">
        <!-- Connector line -->
        <div
          v-if="idx > 0"
          class="pt-connector"
          :class="{ past: tierIndex(tier) <= currentIndex }"
        >
          <span v-if="transitionLabel(idx)" class="pt-transition-label">{{ transitionLabel(idx) }}</span>
        </div>
        <!-- Tier node -->
        <div class="pt-node" :class="nodeClass(tier)">
          <div
            class="pt-circle"
            :style="circleStyle(tier)"
          ></div>
          <div class="pt-tier-label">{{ TIER_LABELS[tier] || tier }}</div>
          <div class="pt-round-limit">{{ tierLimits[tier] || '?' }} rounds</div>
        </div>
      </template>
    </div>
    <div class="pt-footer">
      <span class="pt-deadline">Hard deadline: {{ hardDeadline }} rounds total</span>
      <span class="pt-auto">Auto-escalate: On stagnation or deadline</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { TIER_COLORS, TIER_LABELS } from '@/types/protocol'

const props = defineProps({
  tiers: {
    type: Array,
    default: () => ['negotiation', 'mediation', 'arbitration']
  },
  currentTier: {
    type: String,
    default: 'negotiation'
  },
  tierLimits: {
    type: Object,
    default: () => ({ negotiation: 10, mediation: 6, arbitration: 4 })
  },
  hardDeadline: {
    type: Number,
    default: 20
  },
  tierHistory: {
    type: Array,
    default: () => []
  }
})

const currentIndex = computed(() => props.tiers.indexOf(props.currentTier))

function tierIndex(tier) {
  return props.tiers.indexOf(tier)
}

function nodeClass(tier) {
  const idx = tierIndex(tier)
  if (idx < currentIndex.value) return 'past'
  if (idx === currentIndex.value) return 'active'
  return 'future'
}

function circleStyle(tier) {
  const color = TIER_COLORS[tier] || '#999'
  const idx = tierIndex(tier)
  if (idx < currentIndex.value) {
    return { background: color, opacity: 0.4 }
  }
  if (idx === currentIndex.value) {
    return { background: color, boxShadow: `0 0 0 4px ${color}33` }
  }
  return { background: 'transparent', border: `2px solid ${color}` }
}

function transitionLabel(idx) {
  if (!props.tierHistory || props.tierHistory.length === 0) return null
  const transition = props.tierHistory.find(
    t => t.to_tier === props.tiers[idx] || t.new_tier === props.tiers[idx]
  )
  if (!transition) return null
  return `R${transition.round || transition.at_round || '?'}`
}
</script>

<style scoped>
.process-timeline {
  font-family: var(--font-mono);
}

.pt-track {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 0;
}

.pt-connector {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  width: 48px;
  height: 24px;
  margin-top: 0;
}

.pt-connector::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 2px;
  background: #DDD;
  transform: translateY(-50%);
}

.pt-connector.past::before {
  background: #999;
}

.pt-transition-label {
  position: absolute;
  top: -14px;
  font-size: 9px;
  color: #999;
  white-space: nowrap;
  background: transparent;
}

.pt-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.pt-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  transition: all 0.3s ease;
  box-sizing: border-box;
}

.pt-node.active .pt-circle {
  width: 28px;
  height: 28px;
}

.pt-node.future .pt-circle {
  opacity: 0.7;
}

.pt-tier-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.3px;
  color: #333;
  text-transform: uppercase;
}

.pt-node.future .pt-tier-label {
  color: #BBB;
}

.pt-node.past .pt-tier-label {
  color: #999;
}

.pt-round-limit {
  font-size: 9px;
  color: #AAA;
}

.pt-footer {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 14px;
  font-size: 10px;
  color: #999;
}

.pt-deadline {
  font-weight: 600;
}
</style>
