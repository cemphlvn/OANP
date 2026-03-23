<template>
  <div class="thinking-card">
    <span class="tc-avatar" :style="{ background: partyColor }">{{ (partyName || '?')[0] }}</span>
    <div class="tc-body">
      <span class="tc-name">{{ partyName }}</span>
      <div class="tc-dots"><span></span><span></span><span></span></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  partyName: { type: String, default: '' },
  partyColor: { type: String, default: '#CCC' }
})
</script>

<style scoped>
.thinking-card {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px; opacity: 0.6;
}

.tc-avatar {
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #FFF; font-size: 10px; font-weight: 700; flex-shrink: 0;
}

.tc-body { display: flex; align-items: center; gap: 10px; }
.tc-name { font-size: 12px; color: #999; }

.tc-dots { display: flex; gap: 4px; }

.tc-dots span {
  width: 5px; height: 5px; border-radius: 50%; background: #CCC;
  animation: dot-pulse 1.4s infinite ease-in-out both;
}

.tc-dots span:nth-child(1) { animation-delay: 0s; }
.tc-dots span:nth-child(2) { animation-delay: 0.2s; }
.tc-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-pulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
</style>
