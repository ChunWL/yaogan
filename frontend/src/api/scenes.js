import request from "../utils/request";

export const getScenes = () => {
  return request({
    url: "/scenes",
    method: "get",
  });
};

export const uploadCustomScene = (formData) => {
  return request({
    url: "/scenes/upload",
    method: "post",
    data: formData,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const updateCustomScene = (id, formData) => {
  return request({
    url: `/scenes/${id}`,
    method: "put",
    data: formData,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const deleteCustomScene = (id) => {
  return request({
    url: `/scenes/${id}`,
    method: "delete",
  });
};

export const getSceneGroups = () => {
  return request({
    url: "/scenes/groups",
    method: "get",
  });
};

export const createSceneGroup = (name) => {
  const formData = new FormData();
  formData.append("name", name);
  return request({
    url: "/scenes/groups",
    method: "post",
    data: formData,
  });
};

export const renameSceneGroup = (id, name) => {
  const formData = new FormData();
  formData.append("name", name);
  return request({
    url: `/scenes/groups/${id}`,
    method: "put",
    data: formData,
  });
};

export const deleteSceneGroup = (id) => {
  return request({
    url: `/scenes/groups/${id}`,
    method: "delete",
  });
};

export const assignSceneGroup = (sceneKey, groupId) => {
  const formData = new FormData();
  if (groupId) formData.append("group_id", groupId);
  return request({
    url: `/scenes/${sceneKey}/group`,
    method: "put",
    data: formData,
  });
};

export const getModelMarketplace = () => {
  return request({
    url: "/scenes/marketplace",
    method: "get",
  });
};

export const acquireModel = (sceneId) => {
  return request({
    url: `/scenes/acquire/${sceneId}`,
    method: "post",
  });
};

export const unacquireModel = (sceneId) => {
  return request({
    url: `/scenes/acquire/${sceneId}`,
    method: "delete",
  });
};

export const getAcquiredModels = () => {
  return request({
    url: "/scenes/acquired",
    method: "get",
  });
};

// Admin model management
export const getAdminModels = () => {
  return request({
    url: "/admin/models",
    method: "get",
  });
};

export const toggleModelStatus = (sceneId, status) => {
  const formData = new FormData();
  formData.append("status", status);
  return request({
    url: `/admin/models/${sceneId}/status`,
    method: "put",
    data: formData,
  });
};

export const adminDeleteModel = (sceneId) => {
  return request({
    url: `/admin/models/${sceneId}`,
    method: "delete",
  });
};

// Announcements
export const getAnnouncements = () => {
  return request({
    url: "/announcements",
    method: "get",
  });
};

export const createAnnouncement = (title, message) => {
  const formData = new FormData();
  formData.append("title", title || "");
  formData.append("message", message);
  return request({
    url: "/announcements",
    method: "post",
    data: formData,
  });
};

export const updateAnnouncement = (id, title, message) => {
  const formData = new FormData();
  formData.append("title", title || "");
  formData.append("message", message);
  return request({
    url: `/announcements/${id}`,
    method: "put",
    data: formData,
  });
};

export const deleteAnnouncement = (id) => {
  return request({
    url: `/announcements/${id}`,
    method: "delete",
  });
};
