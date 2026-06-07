# Technical Decision Log

Recorded decisions for OPS System Management. New entries should be dated and include context, decision, and consequences.

---

## ADR-001: Replace Excel with a centralized web system

**Status:** Accepted  
**Context:** Workplace POS device tracking in spreadsheets led to audit failures (~95% incorrect parts usage records in one audit).  
**Decision:** Build a dedicated ops management system with real-time status and user activity logging.  
**Consequences:** Requires migration from manual Excel processes; finance module still planned.

---

## ADR-002: Django + React split stack

**Status:** Accepted  
**Context:** Need REST APIs, admin tooling, and a modern interactive UI.  
**Decision:** Django REST Framework backend; Create React App frontend on separate ports with CORS.  
**Consequences:** Two deployable units; JWT used for cross-origin auth instead of session cookies.

---

## ADR-003: JWT with department claims

**Status:** Accepted  
**Context:** Users belong to one department (`hr` or `warehouse`) and should land on the correct dashboard after login.  
**Decision:** Extend Simple JWT serializer to embed `department` and `full_name` in token + login response; mirror department in `localStorage` for routing.  
**Consequences:** Frontend routing is convenient but not authoritative—API permissions (`IsHRStaff`, `IsWarehouseAgent`) must always enforce access.

---

## ADR-004: HR departments as CharField choices (not separate tables)

**Status:** Accepted (demo scope)  
**Context:** Full CRUD for departments/positions adds complexity beyond current demo goals.  
**Decision:** `Employee.department` uses predefined choices (`warehouse`, `hr`).  
**Consequences:** Adding a department requires a code change. Production would use FK to `Department` / `Position` models (see README “HR Module Design Decision”).

---

## ADR-005: Soft status instead of hard deletes (warehouse master data)

**Status:** Accepted  
**Context:** Clients, models, and versions must remain referentially intact for historical devices.  
**Decision:** Use `client_status`, `model_status`, and version `status` fields; avoid deleting master records.  
**Consequences:** Queries may need to filter `Active` records explicitly where relevant.

---

## ADR-006: DeviceStaging without foreign keys

**Status:** Accepted  
**Context:** Scan workflow must validate serial numbers against batch/client/model data before creating permanent `Device` rows.  
**Decision:** `DeviceStaging` stores denormalized `model_name`, `version_name`, `batch_code`, `client_name` plus `status` / `error_message`. Confirmation promotes to `Device` with PROTECT FKs.  
**Consequences:** Possible transient inconsistency if master data changes between scan and confirm; acceptable for staging buffer pattern.

---

## ADR-007: Mode/step dispatch in API views

**Status:** Accepted  
**Context:** Warehouse client API supports single vs bulk and base vs linking without many URL endpoints.  
**Decision:** Single view per resource with `mode` and `step` in JSON body, handler map in view class.  
**Consequences:** Clients must send correct mode/step; OpenAPI documents request bodies per operation mode.

---

## ADR-008: Centralized frontend styles (not colocated CSS)

**Status:** Accepted (2025)  
**Context:** CSS lived beside components (`HRPage.css`, `BulkAddClientForm.css`) and inline styles on login—hard to maintain consistently.  
**Decision:** All styles under `frontend/src/styles/`:

- `global/` — variables and base styles (imported once in `index.js`)
- `pages/` — page shells (`hr-dashboard.css`, `login-page.css`)
- `components/` — feature UI (`bulk-workflow.css`, `register-employee-form.css`)

Components and pages contain JSX only; imports point to `../../styles/...`.  
**Consequences:** Slightly longer import paths; naming follows BEM root class (e.g. `.hr-dashboard`), not React file names.

---

## ADR-009: OpenAPI via drf-spectacular

**Status:** Accepted  
**Context:** API consumers and reviewers need discoverable contracts.  
**Decision:** `drf-spectacular` at `/api/schema/` and Swagger UI at `/api/docs/`.  
**Consequences:** Serializers and views should stay annotated consistently for accurate schema output.

---

## Template for new decisions

```markdown
## ADR-NNN: Title

**Status:** Proposed | Accepted | Superseded  
**Date:** YYYY-MM-DD  
**Context:** …  
**Decision:** …  
**Consequences:** …
```
