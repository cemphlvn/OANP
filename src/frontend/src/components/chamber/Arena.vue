<template>
  <div class="arena" ref="arenaRef">
    <!-- Party A column -->
    <div class="arena-col arena-col-a">
      <div class="col-header">
        <span class="col-dot" :style="{ background: partyAColor }"></span>
        <span class="col-name">{{ partyAName }}</span>
      </div>
      <div class="col-moves" ref="colARef">
        <TransitionGroup name="card-enter">
          <MoveCard
            v-for="m in partyAMoves"
            :key="m.id"
            :move="m"
            :partyName="partyAName"
            :partyColor="partyAColor"
            :isLatest="m.id === lastMoveId"
          />
        </TransitionGroup>
        <ThinkingCard
          v-if="thinkingPartyId === partyAId"
          :partyName="partyAName"
          :partyColor="partyAColor"
        />
      </div>
    </div>

    <!-- Mediator column (center, only if mediator moves exist) -->
    <div v-if="mediatorMoves.length > 0" class="arena-col arena-col-med">
      <div class="col-header">
        <span class="col-dot" style="background: #22c55e"></span>
        <span class="col-name">Mediator</span>
      </div>
      <div class="col-moves">
        <TransitionGroup name="card-enter">
          <MoveCard
            v-for="m in mediatorMoves"
            :key="m.id"
            :move="m"
            partyName="Mediator"
            partyColor="#22c55e"
          />
        </TransitionGroup>
      </div>
    </div>

    <!-- Party B column -->
    <div class="arena-col arena-col-b">
      <div class="col-header">
        <span class="col-dot" :style="{ background: partyBColor }"></span>
        <span class="col-name">{{ partyBName }}</span>
      </div>
      <div class="col-moves" ref="colBRef">
        <TransitionGroup name="card-enter">
          <MoveCard
            v-for="m in partyBMoves"
            :key="m.id"
            :move="m"
            :partyName="partyBName"
            :partyColor="partyBColor"
            :isLatest="m.id === lastMoveId"
          />
        </TransitionGroup>
        <ThinkingCard
          v-if="thinkingPartyId === partyBId"
          :partyName="partyBName"
          :partyColor="partyBColor"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import MoveCard from './MoveCard.vue'
import ThinkingCard from './ThinkingCard.vue'
import { PARTY_COLORS, MEDIATOR_COLOR } from '@/types/protocol'

const props = defineProps({
  moves: { type: Array, default: () => [] },
  parties: { type: Array, default: () => [] },
  thinkingPartyId: { type: String, default: null }
})

const colARef = ref(null)
const colBRef = ref(null)

const partyAId = computed(() => props.parties[0]?.id)
const partyBId = computed(() => props.parties[1]?.id)
const partyAName = computed(() => props.parties[0]?.name || 'Party A')
const partyBName = computed(() => props.parties[1]?.name || 'Party B')
const partyAColor = computed(() => PARTY_COLORS[0])
const partyBColor = computed(() => PARTY_COLORS[1])

const partyAMoves = computed(() => props.moves.filter(m => m.party_id === partyAId.value && !m._isMediatorNote))
const partyBMoves = computed(() => props.moves.filter(m => m.party_id === partyBId.value && !m._isMediatorNote))
const mediatorMoves = computed(() => props.moves.filter(m => m._isMediatorNote || m.party_id === 'mediator'))

const lastMoveId = computed(() => {
  if (props.moves.length === 0) return null
  return props.moves[props.moves.length - 1].id
})

// Auto-scroll columns
watch(() => props.moves.length, () => {
  nextTick(() => {
    colARef.value?.scrollTo({ top: colARef.value.scrollHeight, behavior: 'smooth' })
    colBRef.value?.scrollTo({ top: colBRef.value.scrollHeight, behavior: 'smooth' })
  })
})
</script>

<style scoped>
.arena {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.arena-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.arena-col-a { border-right: 1px solid var(--border); }
.arena-col-b { border-left: 1px solid var(--border); }
.arena-col-med { max-width: 280px; border-right: 1px solid var(--border); }

.col-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 2px solid var(--border);
  background: #FAFAFA;
  flex-shrink: 0;
}

.col-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.col-name { font-weight: 700; font-size: 13px; letter-spacing: 0.3px; }

.col-moves {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Transition */
.card-enter-enter-active { transition: all 0.3s ease-out; }
.card-enter-enter-from { opacity: 0; transform: translateY(12px); }
</style>
