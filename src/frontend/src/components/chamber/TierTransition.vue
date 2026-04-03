<template>
  <Transition name="tier-fade">
    <div v-if="visible" class="tier-transition-overlay" :style="{ '--tier-color': tierColor }">
      <div class="tier-sweep"></div>
      <div class="tier-content">
        <div class="tier-label">E S C A L A T I O N</div>
        <div class="tier-arrow">
          <span class="tier-from">{{ fromLabel }}</span>
          <span class="tier-arrow-icon">&#10230;</span>
          <span class="tier-to" :style="{ color: tierColor }">{{ toLabel }}</span>
        </div>
        <div class="tier-reason">{{ reason }}</div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed } from 'vue'
import { TIER_COLORS, TIER_LABELS } from '@/types/protocol'

const props = defineProps({
  visible: { type: Boolean, default: false },
  from: { type: String, default: '' },
  to: { type: String, default: '' },
  reason: { type: String, default: '' },
})

const tierColor = computed(() => TIER_COLORS[props.to] || '#999')
const fromLabel = computed(() => (TIER_LABELS[props.from] || props.from || '').toUpperCase())
const toLabel = computed(() => (TIER_LABELS[props.to] || props.to || '').toUpperCase())
</script>

<style scoped>
.tier-transition-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  pointer-events: none;
}

.tier-sweep {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, var(--tier-color) 50%, transparent 100%);
  opacity: 0.15;
  animation: sweep-tier 2.5s ease-in-out;
}

@keyframes sweep-tier {
  0% { transform: translateX(-100%); opacity: 0; }
  30% { opacity: 0.2; }
  50% { transform: translateX(0); opacity: 0.15; }
  100% { transform: translateX(100%); opacity: 0; }
}

.tier-content {
  text-align: center;
  z-index: 1;
  animation: tier-pop 0.5s cubic-bezier(0.25, 0.8, 0.25, 1);
}

@keyframes tier-pop {
  0% { transform: scale(0.8); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

.tier-label {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 8px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 24px;
}

.tier-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-bottom: 16px;
}

.tier-from {
  font-family: var(--font-mono);
  font-size: 24px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 2px;
}

.tier-arrow-icon {
  font-size: 28px;
  color: rgba(255, 255, 255, 0.6);
}

.tier-to {
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 2px;
}

.tier-reason {
  font-family: var(--font-mono);
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 1px;
}

/* Transition */
.tier-fade-enter-active { transition: opacity 0.3s ease; }
.tier-fade-leave-active { transition: opacity 0.5s ease 2s; }
.tier-fade-enter-from, .tier-fade-leave-to { opacity: 0; }
</style>
