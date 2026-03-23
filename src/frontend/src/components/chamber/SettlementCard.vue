<template>
  <Teleport to="body">
    <Transition name="settle">
      <div v-if="visible" class="settlement-overlay" @click.self="$emit('close')">
        <!-- Particles -->
        <div class="particles">
          <span
            v-for="i in 20"
            :key="i"
            class="particle"
            :style="particleStyle(i)"
          ></span>
        </div>

        <!-- Card -->
        <div class="settlement-card">
          <div class="sc-header">
            <span class="sc-emoji">&#129309;</span>
            <div>
              <div class="sc-title">Agreement Reached</div>
              <div class="sc-sub">{{ rounds }} rounds &middot; {{ moveCount }} moves</div>
            </div>
          </div>

          <div class="sc-terms">
            <div class="sc-terms-label">DEAL TERMS</div>
            <div v-for="(val, key) in agreement?.issue_values" :key="key" class="sc-term-row">
              <span class="sc-term-key">{{ key }}</span>
              <span class="sc-term-val">{{ val }}</span>
            </div>
          </div>

          <div v-if="agreement?.rationale" class="sc-rationale">
            {{ agreement.rationale }}
          </div>

          <div class="sc-actions">
            <button class="sc-btn primary" @click="$emit('viewAnalysis')">
              View Analysis &#8594;
            </button>
            <button class="sc-btn secondary" @click="$emit('close')">
              Continue Viewing
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  agreement: { type: Object, default: null },
  rounds: { type: Number, default: 0 },
  moveCount: { type: Number, default: 0 }
})

defineEmits(['close', 'viewAnalysis'])

function particleStyle(i) {
  const x = 30 + Math.random() * 40
  const dur = 2 + Math.random() * 2
  const delay = Math.random() * 1.5
  const size = 4 + Math.random() * 6
  const color = Math.random() > 0.5 ? '#22c55e' : '#f59e0b'
  return {
    left: x + '%',
    animationDuration: dur + 's',
    animationDelay: delay + 's',
    width: size + 'px',
    height: size + 'px',
    background: color
  }
}
</script>

<style scoped>
.settlement-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.particles {
  position: fixed;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.particle {
  position: absolute;
  bottom: -10px;
  border-radius: 50%;
  opacity: 0;
  animation: float-up linear forwards;
}

@keyframes float-up {
  0% { transform: translateY(0); opacity: 0.8; }
  100% { transform: translateY(-100vh); opacity: 0; }
}

.settlement-card {
  background: #FFF;
  border-radius: 12px;
  padding: 32px;
  max-width: 440px;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  animation: card-pop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  z-index: 1;
}

@keyframes card-pop {
  0% { transform: scale(0.8); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

.sc-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.sc-emoji { font-size: 32px; }

.sc-title { font-size: 1.3rem; font-weight: 700; }

.sc-sub {
  font-family: var(--font-mono);
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

.sc-terms {
  background: #F9F9F9;
  border: 1px solid #EEE;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.sc-terms-label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: #AAA;
  letter-spacing: 1px;
  margin-bottom: 10px;
}

.sc-term-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid #F0F0F0;
  font-size: 13px;
}

.sc-term-row:last-child { border-bottom: none; }
.sc-term-key { color: #666; }
.sc-term-val { font-family: var(--font-mono); font-weight: 600; }

.sc-rationale {
  font-size: 12px;
  color: #666;
  font-style: italic;
  line-height: 1.6;
  margin-bottom: 20px;
  padding: 12px;
  background: #FFFBF5;
  border-radius: 6px;
}

.sc-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sc-btn {
  width: 100%;
  padding: 14px;
  border-radius: 6px;
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.sc-btn.primary {
  background: #000;
  color: #FFF;
  border: none;
}

.sc-btn.primary:hover { background: var(--accent); }

.sc-btn.secondary {
  background: transparent;
  color: #999;
  border: 1px solid #E0E0E0;
}

.sc-btn.secondary:hover { border-color: #999; color: #666; }

/* Transitions */
.settle-enter-active { transition: opacity 0.3s; }
.settle-enter-from { opacity: 0; }
.settle-leave-active { transition: opacity 0.2s; }
.settle-leave-to { opacity: 0; }
</style>
