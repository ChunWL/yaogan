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
