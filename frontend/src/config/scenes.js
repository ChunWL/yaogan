/**
 * 检测场景配置
 * 内置场景 + 用户自定义场景（从 API 获取）
 *
 * key:        场景唯一标识
 * name:       场景显示名称
 * subtitle:   页面副标题
 * description:场景简短描述
 * defaultModel:默认使用的模型名（对应 backend/models/{name}.pt）
 * icon:       Element Plus 图标组件名
 * labels:     场景文案标签
 * classNames: 该场景的目标类别中文映射
 * targetGroups: 目标类型库的分组数据
 * is_custom:  是否为用户自定义场景
 */
export const SCENES = {
  steel: {
    key: "steel",
    name: "钢铁表面缺陷检测",
    subtitle: "支持轧制氧化皮 / 斑块 / 开裂 / 点蚀表面 / 内含物 / 划痕等缺陷检测",
    description: "对钢铁表面图像进行缺陷识别与定位",
    defaultModel: "gt",
    icon: "Monitor",
    labels: {
      target: "缺陷",
      targetUnit: "处缺陷",
      empty: "未检测到表面缺陷",
      emptyDesc: "表面无异常缺陷",
      diagnosis: "检测到 {count} 处缺陷，耗时 {time}s。 模型: {model}",
      videoDiagnosis: "视频检测完成：共 {count} 处缺陷，分布在 {frames} 帧中，耗时 {time}s。",
      targetLib: "缺陷类型库",
      targetLibDesc: "钢铁表面常见的缺陷类型及其说明",
      searchPlaceholder: "搜索缺陷类型...",
      totalTargets: "缺陷类型总数",
      categoryCount: "缺陷类别数",
      noMatch: "未找到匹配的缺陷类型",
    },
    classNames: {
      "rolled-in_scale": "轧制氧化皮",
      patches: "斑块",
      crazing: "开裂",
      pitted_surface: "点蚀表面",
      inclusion: "内含物",
      scratches: "划痕",
    },
    targetGroups: [
      {
        id: 1,
        name: "表面缺陷",
        icon: "Remove",
        color: "#1a56db",
        targets: [
          { id: 1, name: "轧制氧化皮", categoryId: 1, description: "rolled-in scale — 轧制过程中形成的氧化皮压入表面", accuracy: "96.5%" },
          { id: 2, name: "斑块", categoryId: 1, description: "patches — 表面局部区域的不规则色斑或粗糙斑块", accuracy: "95.2%" },
          { id: 3, name: "划痕", categoryId: 1, description: "scratches — 机械摩擦或搬运过程中产生的线状划伤", accuracy: "97.8%" },
        ],
      },
      {
        id: 2,
        name: "结构缺陷",
        icon: "Setting",
        color: "#dc2626",
        targets: [
          { id: 4, name: "开裂", categoryId: 2, description: "crazing — 表面或次表面产生的网状或线状裂纹", accuracy: "94.1%" },
          { id: 5, name: "点蚀表面", categoryId: 2, description: "pitted surface — 局部腐蚀形成的点状凹坑密集分布", accuracy: "93.6%" },
          { id: 6, name: "内含物", categoryId: 2, description: "inclusion — 钢基体中夹杂的非金属物质暴露于表面", accuracy: "92.3%" },
        ],
      },
    ],
  },
  general: {
    key: "general",
    name: "通用目标检测",
    subtitle: "使用 YOLO 模型检测常见物体类别",
    description: "基于 COCO 数据集的通用目标识别",
    defaultModel: "yolo11n",
    icon: "Picture",
    labels: {
      target: "目标",
      targetUnit: "个目标",
      empty: "未检测到目标",
      emptyDesc: "画面中无识别目标",
      diagnosis: "检测到 {count} 个目标，耗时 {time}s。 模型: {model}",
      videoDiagnosis: "视频检测完成：共 {count} 个目标，分布在 {frames} 帧中，耗时 {time}s。",
      targetLib: "目标类型库",
      targetLibDesc: "YOLO 模型支持的常见物体类别",
      searchPlaceholder: "搜索目标类型...",
      totalTargets: "目标类型总数",
      categoryCount: "识别类别数",
      noMatch: "未找到匹配的目标类型",
    },
    classNames: {},
    targetGroups: [
      {
        id: 1,
        name: "常见物体",
        icon: "User",
        color: "#1a56db",
        targets: [
          { id: 1, name: "person", categoryId: 1, description: "行人", accuracy: "-" },
          { id: 2, name: "bicycle", categoryId: 1, description: "自行车", accuracy: "-" },
          { id: 3, name: "car", categoryId: 1, description: "汽车", accuracy: "-" },
          { id: 4, name: "motorcycle", categoryId: 1, description: "摩托车", accuracy: "-" },
          { id: 5, name: "bus", categoryId: 1, description: "公交车", accuracy: "-" },
          { id: 6, name: "truck", categoryId: 1, description: "卡车", accuracy: "-" },
        ],
      },
      {
        id: 2,
        name: "动物",
        icon: "Monitor",
        color: "#10b981",
        targets: [
          { id: 7, name: "dog", categoryId: 2, description: "狗", accuracy: "-" },
          { id: 8, name: "cat", categoryId: 2, description: "猫", accuracy: "-" },
          { id: 9, name: "bird", categoryId: 2, description: "鸟", accuracy: "-" },
          { id: 10, name: "horse", categoryId: 2, description: "马", accuracy: "-" },
          { id: 11, name: "cow", categoryId: 2, description: "牛", accuracy: "-" },
        ],
      },
      {
        id: 3,
        name: "室内物品",
        icon: "Sell",
        color: "#8b5cf6",
        targets: [
          { id: 12, name: "chair", categoryId: 3, description: "椅子", accuracy: "-" },
          { id: 13, name: "couch", categoryId: 3, description: "沙发", accuracy: "-" },
          { id: 14, name: "tv", categoryId: 3, description: "电视", accuracy: "-" },
          { id: 15, name: "laptop", categoryId: 3, description: "笔记本电脑", accuracy: "-" },
          { id: 16, name: "cell phone", categoryId: 3, description: "手机", accuracy: "-" },
        ],
      },
    ],
  },
}

const GENERIC_LABELS = {
  target: "目标",
  targetUnit: "个目标",
  empty: "未检测到目标",
  emptyDesc: "画面中无识别目标",
  diagnosis: "检测到 {count} 个目标，耗时 {time}s。 模型: {model}",
  videoDiagnosis: "视频检测完成：共 {count} 个目标，分布在 {frames} 帧中，耗时 {time}s。",
  targetLib: "目标类型库",
  targetLibDesc: "此场景识别的目标类别",
  searchPlaceholder: "搜索目标类型...",
  totalTargets: "目标类型总数",
  categoryCount: "识别类别数",
  noMatch: "未找到匹配的目标类型",
}

// 内置场景列表（稳定引用）
const builtInScenes = Object.values(SCENES)

// 注册的自定义场景（键值对，key → config）
const _customSceneMap = {}

/**
 * 注册自定义场景配置，供 getSceneConfig 查找
 */
export function registerCustomScenes(customSceneList) {
  for (const s of customSceneList) {
    _customSceneMap[s.key] = s
  }
}

/**
 * 获取合并后的场景列表（内置 + 自定义）
 */
export function getSceneList(customScenes) {
  return customScenes && customScenes.length > 0
    ? [...builtInScenes, ...customScenes]
    : builtInScenes
}

export function getSceneConfig(sceneKey) {
  if (SCENES[sceneKey]) return SCENES[sceneKey]
  if (_customSceneMap[sceneKey]) return _customSceneMap[sceneKey]
  return SCENES.steel
}

export function buildCustomSceneConfig(custom) {
  const names = custom.classNames || {}
  const targets = Object.entries(names).map(([nameKey, name], i) => ({
    id: i + 1,
    name: name,
    categoryId: 1,
    description: name,
    accuracy: "-",
  }))

  return {
    key: custom.key,
    name: custom.name || "自定义场景",
    subtitle: `自定义检测场景 - ${custom.name || ""}`,
    description: custom.description || `自定义场景: ${custom.name || ""}`,
    defaultModel: custom.defaultModel,
    originalModelName: custom.originalModelName || custom.defaultModel,
    icon: custom.icon || "Monitor",
    is_custom: true,
    is_public: custom.is_public !== undefined ? custom.is_public : false,
    scene_id: custom.scene_id,
    user_id: custom.user_id,
    group_id: custom.group_id || null,
    labels: GENERIC_LABELS,
    classNames: names,
    targetGroups: targets.length > 0
      ? [{ id: 1, name: "识别目标", icon: "Monitor", color: "#1a56db", targets }]
      : [],
  }
}
