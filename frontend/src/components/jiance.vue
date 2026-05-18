<template>
  <div>
    <!-- 并排对比模式 -->
    <div v-if="compareMode === 'side'" class="side-by-side">
      <div class="image-card">
        <h4>原图</h4>
        <img :src="originalImage" alt="原图" />
      </div>
      <div class="image-card">
        <h4>AI标注结果</h4>
        <img :src="annotatedImage" alt="标注图" />
      </div>
    </div>

    <!-- 滑块对比模式 -->
    <div v-if="compareMode === 'slider'" class="slider-container">
      <SliderCompare 
        :before="originalImage" 
        :after="annotatedImage" 
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SliderCompare from '@/components/SliderCompare.vue'

const compareMode = ref('side') // 'side' 或 'slider'
const originalImage = ref('')
const annotatedImage = ref('')
</script>