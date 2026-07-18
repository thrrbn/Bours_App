<script setup>
defineProps({
  modelValue: { type: String, required: true },
});
const emit = defineEmits(["update:modelValue"]);

const horizons = [
  { value: "short", label: "Court terme" },
  { value: "medium", label: "Moyen terme" },
  { value: "long", label: "Long terme" },
];
</script>

<template>
  <div class="flex gap-2 border-b border-gray-200 mb-4">
    <button
      v-for="h in horizons"
      :key="h.value"
      class="px-3 py-2 text-sm border-b-2 transition-colors"
      :class="modelValue === h.value ? 'border-gray-900 font-medium' : 'border-transparent text-gray-500 hover:text-gray-800'"
      @click="emit('update:modelValue', h.value)"
    >
      {{ h.label }}
    </button>
  </div>
</template>
