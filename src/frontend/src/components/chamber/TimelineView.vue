<template>
  <div class="timeline-view" ref="containerRef">
    <div class="tv-axis"></div>

    <template v-for="(item, idx) in items" :key="item.id || idx">
      <!-- Phase divider -->
      <div v-if="item._type === 'phase'" class="tv-phase">
        <span class="tv-phase-line"></span>
        <span class="tv-phase-label" :style="{ color: phaseColor(item.phase) }">
          {{ item.phase?.toUpperCase() }} (Round {{ item.round }})
        </span>
        <span class="tv-phase-line"></span>
      </div>

      <!-- Move -->
      <div v-else class="tv-item">
        <div class="tv-marker">
          <div
            class="tv-dot"
            :class="{ diamond: item._isMediatorNote }"
            :style="{ background: item._isMediatorNote ? '#22c55e' : getPartyColor(item.party_id) }"
          ></div>
        </div>
        <MoveCard
          :move="item"
          :partyName="getPartyName(item.party_id)"
          :partyColor="item._isMediatorNote ? '#22c55e' : getPartyColor(item.party_id)"
          :isLatest="idx === items.length - 1"
          :showReasoning="showAllReasoning"
        />
      </div>
    </template>

    <ThinkingCard
      v-if="thinkingPartyId"
      :partyName="getPartyName(thinkingPartyId)"
      :partyColor="getPartyColor(thinkingPartyId)"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import MoveCard from './MoveCard.vue'
import ThinkingCard from './ThinkingCard.vue'
import { PARTY_COLORS, PHASE_COLORS } from '@/types/protocol'

const props = defineProps({
  moves: { type: Array, default: () => [] },
  parties: { type: Array, default: () => [] },
  thinkingPartyId: { type: String, default: null },
  showAllReasoning: { type: Boolean, default: false }
})

const containerRef = ref(null)

const items = computed(() => {
  const result = []
  let lastPhase = null
  for (const m of props.moves) {
    if (m.phase && m.phase !== lastPhase) {
      result.push({ _type: 'phase', phase: m.phase, round: m.round, id: `phase-${m.phase}-${m.round}` })
      lastPhase = m.phase
    }
    result.push(m)
  }
  return result
})

function getPartyName(id) {
  if (id === 'mediator') return 'Mediator'
  return props.parties.find(p => p.id === id)?.name || id
}

function getPartyColor(id) {
  if (id === 'mediator') return '#22c55e'
  const idx = props.parties.findIndex(p => p.id === id)
  return idx >= 0 ? PARTY_COLORS[idx] : '#999'
}

function phaseColor(phase) { return PHASE_COLORS[phase] || '#999' }

watch(() => props.moves.length, () => {
  nextTick(() => {
    containerRef.value?.scrollTo({ top: containerRef.value.scrollHeight, behavior: 'smooth' })
  })
})
</script>

<style scoped>
.timeline-view {
  height: 100%;
  overflow-y: auto;
  padding: 20px 20px 20px 48px;
  position: relative;
}

.tv-axis {
  position: absolute;
  left: 28px; top: 0; bottom: 0;
  width: 2px; background: #E0E0E0;
}

.tv-phase {
  display: flex; align-items: center; gap: 12px;
  margin: 20px 0; position: relative; z-index: 1;
}

.tv-phase-line { flex: 1; height: 1px; background: #E0E0E0; }

.tv-phase-label {
  font-family: var(--font-mono); font-size: 10px;
  font-weight: 700; letter-spacing: 2px; white-space: nowrap;
}

.tv-item {
  display: flex; gap: 16px; margin-bottom: 12px; position: relative;
}

.tv-marker { position: absolute; left: -28px; top: 14px; }

.tv-dot {
  width: 10px; height: 10px; border-radius: 50%;
}

.tv-dot.diamond {
  border-radius: 0; transform: rotate(45deg);
  width: 9px; height: 9px;
}

.tv-item > .move-card { flex: 1; }
</style>
