---
name: Scene permissions and admin model management
description: Fix scene removal for acquired models, filter model selector by user permission, add admin public model management (suspend/delete)
---

# Scene Permissions and Admin Model Management

## Problem Summary

Three user-reported issues:

1. **No way to remove acquired scenes**: After acquiring a public model, the user cannot remove it from their scene list. The backend has `DELETE /api/scenes/acquire/{scene_id}` but no frontend UI for it.
2. **Model selector shows unauthorized models**: `GET /api/models/list` scans the filesystem for all `.pt` files, showing models from other users' private scenes. The dropdown on DetectionPage displays models the user shouldn't see.
3. **No admin tooling for public models**: Admin cannot suspend (soft-disable) or permanently delete public models from the marketplace.

## Design

### 1. "Remove" Button on Acquired Scenes

**Frontend**: SceneSelector.vue — add a "移除" (Remove) button on scene cards where:
- `scene.is_custom === true`
- `scene.user_id !== currentUserId` (the scene is acquired from another user)

The button calls `DELETE /api/scenes/acquire/{scene_id}` which already exists on the backend.

**Visual**: A text link button with `type="info"`, placed alongside the visibility badge. Label: "移除" with el-icon `<Remove>`.

**Confirmation**: Show ElMessageBox confirm dialog before removing.

### 2. Filter Model Selector by User Permission

**Backend** (`GET /api/models/list` in `main.py`):

Replace the filesystem-scan approach with a DB query. The response should include only models the current user has access to:
- Built-in models: `gt` (steel scene), `yolo11n` (general scene)
- The user's own custom scene models
- Acquired models (from public scenes by other users, that user has acquired)

**Implementation**:
```python
@app.get("/api/models/list")
async def get_models_list(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["sub"]
    
    # 1. Built-in models
    result = [
        {"name": "gt", "displayName": "钢铁缺陷检测"},
        {"name": "yolo11n", "displayName": "通用目标检测"},
    ]
    
    # 2. User's own custom scenes
    own_scenes = db.query(CustomScene).filter(
        CustomScene.user_id == user_id
    ).all()
    
    # 3. Acquired scenes (public models from other users)
    acquired_ids = [
        a.custom_scene_id
        for a in db.query(AcquiredScene).filter(AcquiredScene.user_id == user_id).all()
    ]
    acquired_scenes = []
    if acquired_ids:
        acquired_scenes = db.query(CustomScene).filter(
            CustomScene.id.in_(acquired_ids)
        ).all()
    
    for s in own_scenes + acquired_scenes:
        result.append({
            "name": s.model_filename.replace(".pt", ""),
            "displayName": s.original_model_name or s.name,
        })
    
    return {"success": True, "data": result}
```

Remove the old filesystem-scan-based implementation.

**Also remove** `detection_service.get_available_models()` if it's only used by this endpoint. If used elsewhere (e.g., model lazy-loading), keep it but don't use it for the API response.

### 3. Admin Public Model Management

#### 3.1 Data Model: Add `status` field to CustomScene

Add a `status` column to the `CustomScene` model:
- `"active"` (default) — visible in marketplace, can be acquired
- `"suspended"` — hidden from marketplace, cannot be newly acquired

**Migration**: Add column with default `"active"`. Run from `main.py` lifespan.

#### 3.2 Behavior Rules

| State | Marketplace visibility | Already-acquired users | Non-acquired users |
|-------|----------------------|----------------------|-------------------|
| `active` | Visible | Normal usage | Can acquire |
| `suspended` | Hidden | **Can still use** (local .pt exists) | Cannot acquire, not visible |
| `deleted` (DB record removed) | Gone forever | **Card turns gray**, shows "该模型已被管理员删除" + "删除" button to clean up locally | N/A |

**Key principle**: Suspending != blocking. Already-downloaded users keep full functionality. Deleting != force-removing local files. Users clean up locally via the gray card's delete button.

#### 3.3 Backend: Admin Endpoints

**`GET /api/admin/models`** — List all public models across all users, with status info. Admin-only.

```python
@router.get("/admin/models")
async def admin_list_models(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # require_admin check
    scenes = db.query(CustomScene).filter(
        CustomScene.is_public == True
    ).order_by(CustomScene.created_at.desc()).all()
    
    user_ids = [str(s.user_id) for s in scenes]
    users = {str(u.id): u.username for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    
    result = []
    for s in scenes:
        d = _custom_scene_to_dict(s)
        d["status"] = s.status  # "active" or "suspended"
        d["creator_name"] = users.get(str(s.user_id), "未知")
        result.append(d)
    return {"success": True, "data": result}
```

**`PUT /api/admin/models/{scene_id}/status`** — Toggle status between `"active"` and `"suspended"`.

```python
@router.put("/admin/models/{scene_id}/status")
async def admin_toggle_model_status(
    scene_id: str,
    status: str = Form(...),  # "active" or "suspended"
    ...
):
    # require_admin, validate scene exists and is_public
    # Update scene.status
```

**`DELETE /api/admin/models/{scene_id}`** — Permanently delete a public model.

Admin delete DOES:
- Remove `.pt` from MinIO models bucket (source of truth gone)
- Delete local `backend/models/{filename}.pt`
- Delete the CustomScene DB record
- **Keep** AcquiredScene records intact (so users know what they had)

Admin delete does NOT:
- Delete AcquiredScene records (orphaned, allow frontend to show gray card)
- Delete detection_history records (keep for reference)

```python
@router.delete("/admin/models/{scene_id}")
async def admin_delete_model(
    scene_id: str,
    ...
):
    # require_admin
    # Delete .pt from MinIO
    # Delete local .pt file
    # Delete CustomScene record
    # Leave AcquiredScene records (orphaned)
    # Leave detection_history records
```

#### 3.4 Backend: Marketplace Filtering

Modify `GET /api/scenes/marketplace` to exclude suspended models:
```python
query = db.query(CustomScene).filter(
    CustomScene.is_public == True,
    CustomScene.status == "active",  # new filter
    CustomScene.user_id != user_id,
)
```

#### 3.5 Backend: Update `GET /api/scenes/acquired` to Include Deleted Models

The current endpoint filters by `CustomScene.id.in_(scene_ids)`, which excludes deleted models. Update to also detect orphaned AcquiredScene records:

```python
@router.get("/api/scenes/acquired")
async def list_acquired_scenes(current_user, db):
    user_id = current_user["sub"]
    records = db.query(AcquiredScene).filter(
        AcquiredScene.user_id == user_id
    ).order_by(AcquiredScene.created_at.desc()).all()

    scene_ids = [r.custom_scene_id for r in records]
    scenes = db.query(CustomScene).filter(CustomScene.id.in_(scene_ids)).all() if scene_ids else []
    scene_map = {str(s.id): s for s in scenes}

    result = []
    for r in records:
        s = scene_map.get(str(r.custom_scene_id))
        if s:
            scene_key = f"custom_{s.id.hex}"
            result.append({
                "key": scene_key,
                "name": s.name,
                "originalModelName": s.original_model_name or s.name,
                "defaultModel": s.model_filename.replace(".pt", ""),
                "status": getattr(s, "status", "active"),
                "deleted": False,
            })
        else:
            # Orphaned AcquiredScene — model was deleted by admin
            result.append({
                "key": f"acquired_{r.custom_scene_id.hex}",
                "name": "（已删除的模型）",
                "originalModelName": "已删除",
                "defaultModel": "",
                "acquired_scene_id": str(r.id),
                "deleted": True,
            })
    
    return {"success": True, "data": result}
```

The `deleted: True` flag lets the frontend render the gray card.

#### 3.6 Frontend: Admin Panel Tab

In SceneSelector.vue, add a third tab that only shows for admins:

```
el-tab-pane label="管理模型" name="admin" (v-if="isAdmin")
```

Admin tab content: card list of all public models (from `GET /api/admin/models`), each card shows:
- Model name, creator username
- Status tag: green "正常" (active) or orange "已暂停" (suspended)
- Actions:
  - "暂停" / "恢复" toggle button → `PUT /api/admin/models/{id}/status`
  - "删除" button → ElMessageBox confirm → `DELETE /api/admin/models/{id}`

#### 3.7 Frontend: Gray Card for Deleted Acquired Scenes

In SceneSelector.vue's "我的场景" tab, when a scene card has `deleted: true`:
- Render with reduced opacity / gray background
- Card shows "该模型已被管理员删除" message
- No navigation on click
- Add a "删除" button → calls `DELETE /api/scenes/acquire/{acquired_scene_id}` (the existing unacquire endpoint)
- After deletion, the card disappears from the grid

## Backend Changes Summary

| File | Change |
|------|--------|
| `app/models/custom_scene.py` | Add `status` column (String, default `"active"`), nullable=False |
| `backend/main.py` | Rewrite `GET /api/models/list` to use DB query instead of filesystem scan |
| `backend/app/api/scenes.py` | Modify `marketplace` query to filter `status == "active"`; update `list_acquired_scenes` to detect orphaned (deleted) acquired scenes |
| `backend/app/api/admin.py` | Add 3 new admin endpoints: `GET /admin/models`, `PUT /admin/models/{id}/status`, `DELETE /admin/models/{id}` |

## Frontend Changes Summary

| File | Change |
|------|--------|
| `frontend/src/views/SceneSelector.vue` | Add "移除" button on acquired scenes; add admin "管理模型" tab (v-if admin) with card list; render gray cards for deleted acquired scenes with local delete button |
| `frontend/src/api/scenes.js` | Add admin model API calls (`getAdminModels`, `toggleModelStatus`, `adminDeleteModel`) |

## No Changes Needed

- Auth/permission system — reuse existing `require_admin` and `get_current_user`
- `detection_service` — no changes (suspended models don't block already-acquired users)
- Existing `DELETE /api/scenes/{scene_id}` — already correctly restricts to owner
- `DELETE /api/scenes/acquire/{scene_id}` — reused for local deletion of orphaned acquired scenes

## Error Handling

- Suspended model: simply hidden from marketplace. Already-acquired users see no difference in functionality.
- Admin delete of public model: `AcquiredScene` records become orphaned. Frontend checks `deleted` flag.
- Orphaned acquired scene: clicking gray card does nothing; "删除" button calls `DELETE /api/scenes/acquire/{id}` to clean up.
- Admin delete on already-suspended model: perfectly valid, same delete logic.
- Non-admin accessing admin endpoints: 403 via existing `require_admin` dependency.
