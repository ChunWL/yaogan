import request from "../utils/request";

// 单图检测接口
export const detectSingleImage = (data) => {
  return request({
    url: "/detection/single",
    method: "post",
    data,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

// 批量检测接口
export const detectBatchImages = (data) => {
  return request({
    url: "/detection/batch",
    method: "post",
    data,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

// 获取检测历史
export const getDetectionHistory = (params) => {
  return request({
    url: "/detection/history",
    method: "get",
    params,
  });
};

// 获取检测详情
export const getDetectionDetail = (id) => {
  return request({
    url: `/detection/detail/${id}`,
    method: "get",
  });
};

// 删除检测历史
export const deleteDetectionHistory = (id) => {
  return request({
    url: `/detection/history/${id}`,
    method: "delete",
  });
};

// 获取目标库列表
export const getTargetList = () => {
  return request({
    url: "/targets/list",
    method: "get",
  });
};

// 视频检测接口
export const detectVideo = (data) => {
  return request({
    url: "/detection/video",
    method: "post",
    data,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

// 获取可用模型列表
export const getModelsList = () => {
  return request({
    url: "/models/list",
    method: "get",
  });
};

// 查询视频检测进度
export const getVideoProgress = (taskId) => {
  return request({
    url: `/detection/video/progress/${taskId}`,
    method: "get",
  });
};

// WebSocket camera detection
export const getCameraWsUrl = (token, modelName = "yolo11n") => {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/api/detection/ws/camera?token=${encodeURIComponent(token)}&model_name=${encodeURIComponent(modelName)}`;
};