# Multi-User Auth & Permission Management — Design Spec

**Date:** 2026-05-12
**Status:** Approved
**Project:** LLM Chat Tool

## Overview

Add multi-user support (up to 10 users) with role-based access control to the existing single-user LLM Chat Tool.

### Requirements Summary

| Dimension | Decision |
|-----------|----------|
| Permission model | Two-level: admin + regular user |
| Authentication | Username + password + JWT |
| API Key management | Mixed mode (shared keys + private keys) |
| Data isolation | Complete — users cannot see each other's data; admin cannot see user business data or private keys |
| User features | Register, login, change password, password reset, admin user management |
| Deployment | No new infrastructure, stays on SQLite |

---

## Database Design

### New Tables

**users**

```sql
CREATE TABLE users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role         VARCHAR(10) NOT NULL DEFAULT 'user',  -- 'admin' | 'user'
    is_active    BOOLEAN DEFAULT TRUE,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**user_key_overrides** — per-user overrides on shared API keys (only `enable_thinking` and `max_context_tokens`)

```sql
CREATE TABLE user_key_overrides (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    api_key_id         INTEGER NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    enable_thinking    BOOLEAN,
    max_context_tokens INTEGER,
    UNIQUE(user_id, api_key_id)
);
```

### Modified Tables

Each existing business table gets a `user_id` foreign key:

- `api_keys` + `user_id INTEGER REFERENCES users(id)` — NULL = shared by admin, non-NULL = private key
- `conversations` + `user_id INTEGER REFERENCES users(id) NOT NULL`
- `batch_tasks` + `user_id INTEGER REFERENCES users(id) NOT NULL`
- `es_export_tasks` + `user_id INTEGER REFERENCES users(id) NOT NULL`

Migrations: all new columns use ALTER TABLE ADD COLUMN. For existing rows, `user_id` defaults to NULL for api_keys and batch_tasks/es_export_tasks (unlinked to any user post-migration). Conversations can be assigned to a default admin user if needed.

---

## Authentication Flow

### JWT Design

- Library: `PyJWT` (python-jose or direct pyjwt)
- Algorithm: HS256
- Payload: `{ sub: user_id, role: "user"|"admin", exp: timestamp }`
- Token lifetime: 24 hours
- Token sent as `Authorization: Bearer <token>` header

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/login` | None | Username + password → `{ access_token, user }` |
| POST | `/api/auth/register` | None | Username + password → `{ access_token, user }` (first user auto-admin) |
| POST | `/api/auth/change-password` | Required | `{ old_password, new_password }` → 200 |
| POST | `/api/auth/reset-password/{user_id}` | Admin | → new random password returned to admin |

### Password Handling

- Library: `passlib` with bcrypt
- Never logged, never returned in API responses
- Admin reset generates a random 12-char password, returned once

---

## Authorization Rules

### get_current_user Dependency

Every protected endpoint adds `Depends(get_current_user)`:
1. Extract token from `Authorization` header
2. Decode and verify JWT
3. Query user by `sub` claim
4. Check `is_active` — 403 if disabled
5. Return `current_user`

### Role-based Access Matrix

| Resource | Regular User | Admin |
|----------|-------------|-------|
| Own conversations/messages | Full CRUD | No access |
| Own batch tasks | Full CRUD | No access |
| Own ES export tasks | Full CRUD | No access |
| Own private API keys | Full CRUD | No access |
| Shared API keys (user_id=NULL) | Read-only + can override `enable_thinking` & `max_context_tokens` | Full CRUD (all fields) |
| User management (`/api/users/*`) | 403 | Full CRUD (create/disable/delete/reset-password) |

**Key rule:** Admin role is purely for user lifecycle management. Admin cannot access any user's conversations, tasks, or private keys. Admin CANNOT see user data content.

### Data Isolation Pattern

All business queries filter by `user_id = current_user.id`:

```python
stmt = select(Conversation).where(
    Conversation.user_id == current_user.id
).order_by(Conversation.updated_at.desc())
```

For shared API keys, query `user_id IS NULL OR user_id = current_user.id`, JOIN with `user_key_overrides` for per-user parameter overrides.

---

## API Key Override Logic

### Rules

| Actor | Action | Behavior |
|-------|--------|----------|
| User | Modify shared key's `enable_thinking` / `max_context_tokens` | Write to `user_key_overrides`, only affects that user |
| Admin | Modify shared key's `enable_thinking` / `max_context_tokens` | Update `api_keys` default only; existing user overrides are NOT affected |
| Admin | Modify shared key's other params (url, model, api_key, etc.) | Update `api_keys`, immediately synced to all users |
| User | No override set for a shared key | Use `api_keys` default values |

### Implementation

When resolving a shared key's effective parameters for a user:

```python
effective_thinking = override.enable_thinking if override else key.enable_thinking
effective_max_tokens = override.max_context_tokens if override else key.max_context_tokens
# url, model, api_key always from key table directly
```

---

## Frontend Architecture

### Router Structure

```
/login          → LoginPage
/register       → RegisterPage
/               → redirect to /chat
/chat           → AppLayout (existing) + ChatWindow
/batch          → AppLayout + BatchPanel
/es-export      → AppLayout + EsExportPanel
/admin/users    → AppLayout + AdminUsersPage (admin only)
/settings       → AppLayout + ChangePasswordPage
```

### Route Guards

- **auth guard**: If no token in localStorage, redirect to `/login`
- **admin guard**: If `user.role !== 'admin'`, redirect to `/chat`

### New Components

| Component | Purpose |
|-----------|---------|
| `LoginPage.vue` | Username + password form, link to register |
| `RegisterPage.vue` | Registration form, auto-login on success |
| `AdminUsersPage.vue` | User table (username, role, status), create/disable/delete/reset-password actions |
| `ChangePasswordModal.vue` | Old + new password form |

### Modified Components

| Component | Change |
|-----------|--------|
| `App.vue` | Replace `<KeepAlive>` with `<router-view>`, add user dropdown (avatar, role badge, change-password, logout), admin sees "User Management" nav item |
| `SettingsPanel.vue` | Key list split into "Shared" (with lock icon, enable_thinking/max_tokens override toggles) and "My Keys" sections |
| API layer (`api/*.ts`) | Wrap fetch with auth header injection and 401 interception |

### Store

**authStore (Pinia)**:
- `user: { id, username, role } | null`
- `token: string | null` (persisted to localStorage)
- Actions: `login()`, `register()`, `logout()`, `changePassword()`, `checkAuth()`

---

## Migration Strategy

1. Create `users` table
2. Create default admin user (credentials from env vars or defaults)
3. Add `user_id` columns (nullable initially)
4. Assign existing data to admin user where applicable
5. Add `user_key_overrides` table
6. Add NOT NULL constraint to `user_id` where needed after data backfill

Existing data is preserved — old conversations/tasks get assigned to the initial admin user.

---

## Dependencies

### New Python Packages

- `PyJWT` — JWT token encode/decode
- `passlib[bcrypt]` — password hashing

### New Frontend Packages

- `vue-router` — routing (already has vue ecosystem, no other new deps)

---

## Testing Strategy

### Backend Tests

- JWT token lifecycle: create, decode, expire, tamper detection
- Auth endpoints: login success/fail, register success/duplicate, password change
- Data isolation: user A cannot access user B's conversations via API
- Admin restrictions: admin cannot access user conversations/tasks/keys
- Key override logic: user override, admin change, resolution priority
- Role gates: regular user 403 on `/api/users/*`

### Frontend Tests

- Login/logout flow
- Route guard redirects
- Admin vs user UI differences
- Shared key override UI behavior

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| SQLite concurrent writes (multi-user) | Request queuing | <10 users, batch tasks write serially — not a real problem |
| Existing functionality regression | Broken existing features | Regression test all main flows (chat, batch, export) |
| Token expiry UX | User kicked to login mid-operation | Frontend 401 interceptor shows re-login dialog |
| Password reset without email | Admin must relay password out-of-band | Acceptable for 10-person team; admin generates and communicates manually |
