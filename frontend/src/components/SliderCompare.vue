<template>
  <div class="slider-compare" ref="sliderRef">
    <!-- 左侧原图 -->
    <div class="image-layer image-before">
      <img :src="before" alt="原图" draggable="false" />
    </div>

    <!-- 右侧标注图（宽度动态变化） -->
    <div class="image-layer image-after" :style="{ width: sliderPosition + '%' }">
      <img :src="after" alt="标注图" draggable="false" />
    </div>

    <!-- 滑块手柄 -->
    <div 
      class="slider-handle" 
      :style="{ left: sliderPosition + '%' }"
      @mousedown="startDrag"
      @touchstart="startDrag"
    >
      <div class="handle-icon">⟷</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'

const props = defineProps({
  before: {
    type: String,
    required: true
  },
  after: {
    type: String,
    required: true
  }
})

const sliderRef = ref(null)
const sliderPosition = ref(50) // 默认中间位置
let isDragging = false

const startDrag = () => {
  isDragging = true
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', onDrag)
  document.addEventListener('touchend', stopDrag)
}

const onDrag = (e) => {
  if (!isDragging || !sliderRef.value) return
  e.preventDefault()
  
  const rect = sliderRef.value.getBoundingClientRect()
  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const x = clientX - rect.left
  const width = rect.width
  
  // 限制滑块在0-100%范围内
  let position = (x / width) * 100
  position = Math.max(0, Math.min(100, position))
  sliderPosition.value = position
}

const stopDrag = () => {
  isDragging = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
}

onUnmounted(() => {
  stopDrag()
})
</script>

<style scoped>
.slider-compare {
  position: relative;
  width: 100%;
  height: 500px;
  overflow: hidden;
  border-radius: 8px;
  user-select: none;
  cursor: ew-resize;
}

.image-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.image-layer img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.image-after {
  overflow: hidden;
  border-right: 3px solid #fff;
}

.slider-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 3px;
  background-color: #fff;
  z-index: 10;
}

.handle-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: bold;
  color: #333;
}
</style>