# Custom Scene Upload — Design Spec

## Overview

Allow users to upload custom `.pt` YOLO models via the SceneSelector page, auto-creating a new detection scene with model class names extracted dynamically. Users can choose to make their scene public (visible to all) or private (visible only to themselves).

## Data Model

### `custom_scenes` Table (PostgreSQL)

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK → users.id | Uploader |
| name | VARCHAR(100) | User-given scene display name |
| model_filename | VARCHAR(255) | Saved .pt filename (e.g. `custom_abc123.pt`) |
| class_names | JSON | Model class names: `{"0": "person", "1": "car", ...}` |
| is_public | BOOLEAN | True = visible to all, False = uploader only |
| created_at | TIMESTAMP | |

## Backend

### New File: `app/models/custom_scene.py`

SQLAlchemy model for `custom_scenes` table, auto-created via `Base.metadata.create_all()` in lifespan handler.

### New File: `app/api/scenes.py`

Three endpoints:

**`POST /api/scenes/upload`** (auth required)
- Accept: `file` (.pt), `name` (str), `is_public` (bool)
- Generate unique key: `custom_{uuid4_hex}`
- Save .pt file to `models/{key}.pt`
- Upload .pt to MinIO `models` bucket
- Load model with YOLO, extract `model.names` as class_names
- Create `CustomScene` DB record
- Return scene config (key, name, class_names, etc.)

**`GET /api/scenes`** (auth required)
- Return hardcoded scenes (steel, general) + public custom scenes + current user's private custom scenes
- Each scene includes: key, name, defaultModel, classNames, targetGroups, icon

**`DELETE /api/scenes/{id}`** (auth required)
- Only the uploader can delete
- Delete DB record + local model file + MinIO model

### Modified: `app/services/detection_service.py`

Add method `get_model_class_names(model_name_or_path: str) -> dict`:
- Load or load model, return `model.names` excluding pure-numeric labels
- Used by upload endpoint

### Modified: `main.py`

Register `scenes_router` at `/api`.

## Frontend

### New File: `src/api/scenes.js`

```javascript
export const uploadCustomScene = (formData) => request.post("/scenes/upload", formData)
export const getScenes = () => request.get("/scenes")
export const deleteCustomScene = (id) => request.delete(`/scenes/${id}`)
```

### Modified: `src/config/scenes.js`

- Add `customScenes` reactive ref
- Add `async function fetchCustomScenes()` that calls `getScenes()` API
- Update `getSceneConfig(key)` to check `customScenes` after `SCENES`
- Update `SCENE_LIST` export to include custom scenes

### Modified: `src/views/SceneSelector.vue`

- On mounted, call `fetchCustomScenes()`
- Scene list renders built-in + custom scenes from combined list
- Add "上传模型" upload card/button
- Upload dialog with:
  - File selector (.pt only)
  - Scene name input
  - Public/private toggle (el-switch)
  - Upload progress
- Custom scene cards show a delete button (only for user's own scenes)

### Custom Scene Display

- Icon: default to Monitor icon for all custom scenes
- Scene info: show user-given name, show filename in footer tag
- Labels: use generic defaults ("目标", "检测到 {count} 个目标", etc.)
- Model name: show the stored model_filename without extension
- targetGroups: auto-generated single group with all class_names as targets

## Data Flow

```
Upload:
  SceneSelector → POST /api/scenes/upload
    → Save .pt to models/{key}.pt + MinIO
    → YOLO(model).names → class_names
    → INSERT custom_scenes
    → Return scene config

List:
  SceneSelector → GET /api/scenes
    → Built-in steel/general
    + custom_scenes WHERE is_public=true OR user_id=current
    → Frontend merges into SCENE_LIST

Use:
  Select scene → localStorage + /detection?scene=custom_{id}
  DetectionPage → reads scene from SCENE_LIST
  → model_name = scene.defaultModel (= model_filename)
  → Same detection pipeline

TargetsPage:
  → Reads scene.classNames from SCENE_LIST
  → Generates single-group target list
```

## Files Changed

| File | Action |
|------|--------|
| `backend/app/models/__init__.py` | Edit (import) |
| `backend/app/models/custom_scene.py` | **New** |
| `backend/app/api/scenes.py` | **New** |
| `backend/app/services/detection_service.py` | Edit (+ get_model_class_names) |
| `backend/main.py` | Edit (+ register scenes router) |
| `frontend/src/api/scenes.js` | **New** |
| `frontend/src/config/scenes.js` | Edit (+ custom scene support) |
| `frontend/src/views/SceneSelector.vue` | Edit (+ upload UI) |
