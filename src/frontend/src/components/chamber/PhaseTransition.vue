<template>
  <Transition name="phase-anim">
    <div v-if="visible" class="phase-transition" :style="{ '--phase-color': phaseColor }">
      <div class="pt-sweep"></div>
      <div class="pt-content">
        <span class="pt-phase" :style="{ color: phaseColor }">{{ phase?.toUpperCase() }}</span>
        <span class="pt-message" v-if="message">{{ message }}</span>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed } from 'vue'
import { PHASE_COLORS } from '@/types/protocol'

const props = defineProps({
  visible: { type: Boolean, default: false },
  phase: { type: String, default: '' },
  message: { type: String, default: '' }
})

const phaseColor = computed(() => PHASE_COLORS[props.phase] || '#999')
</script>

<style scoped>
.phase-transition {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 900;
  pointer-events: none;
  background: color-mix(in srgb, var(--phase-color) 4%, transparent);
}

.pt-sweep {
  position: absolute;
  left: 0; right: 0;
  top: 50%;
  height: 2px;
  background: var(--phase-color);
  transform-origin: left;
  animation: sweep 0.4s ease-out forwards;
  opacity: 0.4;
}

@keyframes sweep {
  0% { transform: scaleX(0); }
  100% { transform: scaleX(1); }
}

.pt-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  animation: phase-pop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

@keyframes phase-pop {
  0% { transform: scale(1.3); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

.pt-phase {
  font-family: var(--font-mono);
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: 6px;
}

.pt-message {
  font-size: 0.9rem;
  color: #666;
  max-width: 400px;
  text-align: center;
}

/* Transition */
.phase-anim-enter-active { transition: opacity 0.2s; }
.phase-anim-enter-from { opacity: 0; }
.phase-anim-leave-active { transition: opacity 0.5s ease 1s; }
.phase-anim-leave-to { opacity: 0; }
</style>
