<template>
  <div class="view-toggle">
    <button
      v-for="mode in modes"
      :key="mode.value"
      class="vt-btn"
      :class="{ active: modelValue === mode.value }"
      @click="$emit('update:modelValue', mode.value)"
    >
      {{ mode.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: 'arena' }
})

defineEmits(['update:modelValue'])

const modes = [
  { value: 'arena', label: 'Arena' },
  { value: 'xray', label: 'X-Ray' },
  { value: 'timeline', label: 'Timeline' }
]
</script>

<style scoped>
.view-toggle {
  display: flex; background: #F5F5F5;
  padding: 3px; border-radius: 6px; gap: 3px;
}

.vt-btn {
  border: none; background: transparent;
  padding: 5px 14px; font-size: 11px; font-weight: 600;
  color: #999; border-radius: 4px; cursor: pointer;
  transition: all 0.15s; font-family: var(--font-heading);
}

.vt-btn.active {
  background: #FFF; color: #000;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.vt-btn:hover:not(.active) { color: #666; }
</style>
