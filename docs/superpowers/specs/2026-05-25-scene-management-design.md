# Scene Management Design

## Overview

Add scene grouping, public/private visibility display, and cascade delete functionality to the SceneSelector page.

## Requirements

1. **Public/Private badge** — Show `公开` / `私有` tag on custom scene cards
2. **Scene grouping** — Users can create/manage groups; default group is "默认分组"; all scenes (built-in + custom) can be assigned to a group; group filter in SceneSelector left sidebar
3. **Cascade delete** — Deleting a scene removes: model file (local + MinIO), DB record, all detection history records for that scene

## Architecture

### New DB Table: `scene_groups`

```sql
CREATE TABLE scene_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_scene_groups_user_id ON scene_groups (user_id);
```

### Modified Table: `custom_scenes`

- Add `group_id` column (UUID, nullable, FK → scene_groups.id)

### Detection History Cascade

Delete `detection_records` where `scene` matches the scene key (e.g., `custom_{uuid}` for custom scenes, `steel`/`general` for built-in).

### Backend API Changes

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/scenes/groups` | GET | List user's groups |
| `/api/scenes/groups` | POST | Create a group |
| `/api/scenes/groups/{id}` | PUT | Rename a group |
| `/api/scenes/groups/{id}` | DELETE | Delete a group (scenes revert to default) |
| `/api/scenes/{id}/group` | PUT | Assign a scene to a group |
| `/api/scenes/{id}` | DELETE | Extended: also delete detection history |

### Modified Response: `GET /api/scenes`

Each scene dict gains:
- `"is_public": bool` for built-in scenes (default false)
- `"group_id": str | null`
- `"group_name": str | null`

### Frontend Changes

#### SceneSelector.vue

- **Left sidebar panel**: Group list with count badges, "全部场景" default, click to filter
  - "新建分组" button at bottom
  - Group context menu (rename, delete); delete requires empty group or reassign
- **Scene cards**: Add public/private badge, group tag
- **Delete button**: Enhanced confirmation dialog listing what will be deleted (model, history records)
- **Group management dialog**: Create/rename groups inline
- **Scene grouping**: Drag or dropdown to assign scene to a group

#### Scene Card Layout

```
┌───────────────────────────────────┐
│ [icon]  Scene Name        [自定义] [私有] │
│         subtitle                   │
│ ───────────────────────────────── │
│ 模型: best    [默认分组]      [删除] │
└───────────────────────────────────┘
```

### Data Flow: Delete Scene

```
User clicks delete
  → Confirmation dialog (model + history warning)
  → DELETE /api/scenes/{id}
    → Remove .pt file from backend/models/
    → Remove .pt from MinIO models bucket
    → DELETE FROM custom_scenes WHERE id = ?
    → DELETE FROM detection_records WHERE scene = 'custom_{uuid}'
    → Return success
  → Refresh scene list
```

## API Details

### POST /api/scenes/groups

```json
// Request
{ "name": "生产检测" }

// Response
{ "success": true, "data": { "id": "uuid", "name": "生产检测", "scene_count": 0 } }
```

### PUT /api/scenes/groups/{id}

```json
// Request
{ "name": "新名称" }

// Response
{ "success": true, "data": { "id": "uuid", "name": "新名称" } }
```

### DELETE /api/scenes/groups/{id}

- Scenes in this group get `group_id` set to NULL
- Group record is deleted
- Returns `{ "success": true }`

### PUT /api/scenes/{id}/group

```json
// Request
{ "group_id": "uuid" | null }

// Response
{ "success": true }
```

- For built-in scenes (`steel`, `general`): store group assignment in a user_scenes_group table or in-memory... 
  - Actually, built-in scenes don't have DB records. Need to handle this.
  
Hmm, I need to reconsider grouping for built-in scenes. Since built-in scenes are not stored in the DB, they can't have a `group_id`. Options:
1. Create a `user_scene_groups` table mapping `(user_id, scene_key, group_id)` for all scenes
2. Only custom scenes can be grouped (simpler)
3. Build a generic mapping table

Given the user wants ALL scenes to be groupable, option 1 or 3 is needed.

### User Scene Group Mapping Table

```sql
CREATE TABLE user_scene_group_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    scene_key VARCHAR(100) NOT NULL,
    group_id UUID NOT NULL REFERENCES scene_groups(id),
    UNIQUE (user_id, scene_key)
);
```

This allows any scene (identified by its `key`) to be assigned to a group by a user.

## Frontend: Group Filter Logic

- "全部场景" selected: show all scenes
- Specific group selected: filter scenes by `scene.group_id === selectedGroupId`
- Scenes without a group are shown when "未分组" selected or "全部场景"

## Caveats

1. **Built-in scenes and groups**: Group assignment for built-in scenes needs a separate mapping table since they have no DB row
2. **Existing custom scenes**: After migration, existing scenes have `group_id = NULL` and `original_model_name = NULL`, treated as ungrouped
3. **Delete group**: Does not delete scenes; scenes become ungrouped (group_id → NULL)
4. **Scene grouping**: Only built-in and the user's own custom scenes can be grouped; other users' public custom scenes cannot be rearranged
