# LANDGUARD — CITIZEN–ADMIN INTEGRATION, PERMANENT DATA PERSISTENCE & NOTIFICATIONS AUDIT

**Audit Date:** 2026-10-16  
**Target Project:** `F:\land gurd main project\`  
**Primary Database:** `F:\land gurd main project\data\landguard_operational.db`  
**Safe Backup:** `F:\land gurd main project\data\backup_landguard_operational_pre_persistence.db`

---

## 1. Executive Summary & Objective

LandGuard operates as an enterprise-grade AI-powered land record fraud and double-selling detection system. In testing real-world citizen and admin workflows across server restarts, several systemic persistence and synchronization gaps were identified:
1. **Citizen Verification History Data Loss/Amnesia:** After application restarts, `/user/history` displayed only four hardcoded demonstration records (`VRF-HIST-001` through `004`), losing all real citizen verification runs.
2. **Citizen Complaint & Admin Case Disconnect:** Citizen complaints stored in SQLite were invisible in the Admin Case Docket (`/admin/cases`) following a restart because `CaseService.list_cases()` solely scanned in-memory dictionaries.
3. **Broken Case Updates & Mutation Isolation:** Admin updates to cases failed for pre-restart cases, failed to update the linked Citizen Complaint timeline/status, and failed to emit notifications to the citizen.
4. **Notification ID Desynchronization:** Memory notification IDs and SQLite primary keys diverged, preventing read status updates from persisting.
5. **Absence of Real-Time Case Progress & Auditory Alerts:** Citizen case tracking required manual reloads, and notifications lacked an accessible, browser-compliant auditory alert.

This audit establishes the baseline facts, maps the architectural flow, isolates root causes, and defines the exact remediation plan executed in Phases 2 through 10.

---

## 2. Operational Database Baseline State

Prior to executing any code modifications, a non-destructive audit of `data/landguard_operational.db` was conducted, followed by an online SQLite backup to `data/backup_landguard_operational_pre_persistence.db`.

| Table Name | Row Count | Integrity Status | Schema Findings |
| :--- | :--- | :--- | :--- |
| `verification_runs` | 1,319 | Healthy (WAL mode) | Contains full JSON payloads of verification runs; indexed on `verification_id`. |
| `complaints` | 397 | Healthy (WAL mode) | Contains real citizen complaints (`citizen_user_id`, `status`, `timeline_json`). |
| `cases` | 116 | Healthy (WAL mode) | Stores administrative fraud investigation cases linked via `complaint_id`. |
| `case_notes` | 259 | Healthy (WAL mode) | Stores investigator and admin notes with timestamps and author IDs. |
| `notifications` | 535 | Healthy (WAL mode) | Stores user notifications; requires ID sync with in-memory service. |
| `audit_events` | 2,743 | Healthy (WAL mode) | Immutable statutory audit trail logging all actions. |
| `users` | 3 | Healthy (WAL mode) | Seeded administrative and citizen demonstration accounts. |
| `sessions` | 1,073 | Healthy (WAL mode) | Persistent authentication tokens. |

**Zero Data Loss Guarantee:** No existing rows are to be modified or purged. All changes must be strictly additive and backward-compatible.

---

## 3. Root Cause Analysis by Subsystem

### 3.1 Subsystem 1: Citizen Verification History
- **Affected Endpoints:** `GET /user/history`, `GET /api/verifications`
- **Component Trail:** `src/landguard_web/routers/citizen.py` -> `src/landguard_services/analytics_service.py` -> `src/landguard_data/repositories/verifications.py`
- **Confirmed Root Causes:**
  1. `VerificationRepository` possessed `save_verification_run` and `get_verification_run`, but lacked `list_verification_runs(user_id, limit, offset)`.
  2. `LandGuardVerificationService._seed_sample_verifications()` seeded 4 demo records into in-memory `AnalyticsService.audit_history`.
  3. `AnalyticsService.get_audit_history()` merely returned the in-memory array `self.audit_history`, completely bypassing the 1,319 records in `verification_runs` table.
  4. `/user/history` did not filter by the authenticated citizen's `user_id`, resulting in all users seeing the same 4 sample records upon reboot.

### 3.2 Subsystem 2: Citizen Complaints & Admin Case Docket
- **Affected Endpoints:** `GET /admin/cases`, `GET /admin/cases/{id}`, `POST /admin/cases/{id}/status`, `GET /user/complaints`
- **Component Trail:** `src/landguard_web/routers/admin.py` -> `src/landguard_services/case_service.py` -> `src/landguard_data/repositories/cases.py`
- **Confirmed Root Causes:**
  1. `CaseService.list_cases()` ignored `self.db.list_cases()` and executed:
     ```python
     results = [self.compute_case_sla(c) for c in self.cases.values()]
     ```
     Because `self.cases` was re-initialized on startup with only 2 seed cases, all 116 persistent SQLite cases vanished from Admin view upon server reboot.
  2. `CaseService.get_case(case_id)` and `update_case(case_id, updates)` looked only at `self.cases.get(case_id)`. Pre-restart cases returned `None`, triggering 404 errors when admins attempted to view or update them.
  3. When an Admin updated a case's status (e.g. from `UNDER_INVESTIGATION` to `RESOLVED`), `CaseService.update_case()` updated the `cases` table but did not update the parent `complaints` record, causing state divergence between citizen and admin portals.

### 3.3 Subsystem 3: Cross-Role Notifications & Single Source of Truth
- **Affected Endpoints:** `GET /api/notifications`, `POST /api/notifications/{id}/read`, `POST /api/notifications/read-all`
- **Component Trail:** `src/landguard_services/case_service.py` -> `src/landguard_services/notification_service.py` -> `src/landguard_data/repositories/notifications.py`
- **Confirmed Root Causes:**
  1. `CaseService.update_case()` never triggered `notification_service.create_notification(...)` for the citizen owner of the linked complaint.
  2. `NotificationService.create_notification()` generated a random UUID `notif_id`, but `NotificationRepository.create_notification()` generated a separate internal UUID for SQLite, making subsequent read/unread updates unable to match keys.
  3. There was no batch `mark_all_read()` endpoint or repository method, forcing cumbersome per-item updates.

### 3.4 Subsystem 4: Audio Notification & Browser Autoplay Compliance
- **Affected Frontend:** `src/landguard_web/templates/user/layout.html`, `notifications.html`
- **Confirmed Issues:**
  1. Modern browsers block programmatic audio (`AudioContext` or `<audio>.play()`) unless initiated by a direct user gesture.
  2. Repeated polling loops triggering sounds on existing unread notifications would produce audio spam.
- **Architectural Solution:**
  1. Implement a persistent "Sound Alert" toggle in the citizen navigation header, persisting state in `localStorage`.
  2. Synthesize an elegant two-tone chime (440Hz -> 880Hz sine wave) using Web Audio API on first user interaction, avoiding external MP3/WAV dependencies.
  3. Track `last_notified_timestamp` in client memory so audio plays exclusively when *new* unread notifications arrive.

### 3.5 Subsystem 5: Live Case Tracking Timeline
- **Affected Frontend:** `src/landguard_web/templates/user/complaint_detail.html`
- **Confirmed Issues:**
  1. The complaint detail page was completely static, requiring full page refreshes to view progress or admin notes.
  2. The timeline did not display administrative status changes, case assignment notes, or resolved outcomes dynamically.
- **Architectural Solution:**
  1. Add a non-intrusive 10-second polling fetch to `/api/complaints/{id}` with visual feedback.
  2. Dynamically update status pills, step progress bars, and timeline nodes in the DOM without destroying user scroll position or focus.
  3. Provide an explicit "Refresh Timeline" button with spinner.

---

## 4. Remediation Plan (Phases 2 – 10)

1. **Phase 2: Verification History Permanent Persistence**
   - Implement `VerificationRepository.list_verification_runs(user_id=None, limit=100, offset=0)` with proper deserialization.
   - Update `VerificationService.list_verifications(user_id)` and `AnalyticsService` to query the SQLite repository.
   - Update `src/landguard_web/routers/citizen.py` `/user/history` to pass `user["user_id"]`.
   - Update template `user/history.html` to render real verification data and provide a friendly empty state.

2. **Phase 3 & 4: Dual-Store Elimination for Cases & Complaints**
   - Update `CaseService.list_cases()`, `get_case()`, and `update_case()` to treat SQLite as authoritative.
   - Synchronize case status changes directly into the linked complaint's `status` and `timeline_json`.
   - Ensure `ComplaintService.list_complaints()` always reflects SQLite entries.

3. **Phase 5: Notification Service & Cross-Role Notification Wireup**
   - Align notification ID generation between `NotificationService` and `NotificationRepository`.
   - Wire `CaseService.update_case()` to automatically notify the citizen when status changes or investigator notes are published.
   - Implement `mark_all_read(user_id)` across repository, service, and router.

4. **Phase 6: Audio Notification System**
   - Implement user-gesture enabled Web Audio API chime in `user/layout.html`.
   - Wire client-side polling with new-notification deduplication.

5. **Phase 7: Dynamic Live Case Tracking Timeline**
   - Refactor `user/complaint_detail.html` with bounded polling and live DOM timeline updates.

6. **Phase 8 & 9: Verification, End-to-End Testing & Test Suite**
   - Run simulation tests reproducing server reboot cycles to verify zero data loss.
   - Author `tests/test_citizen_admin_persistence.py`.

7. **Phase 10: Final Documentation & Completion Artifacts**
   - Produce `LANDGUARD_CITIZEN_ADMIN_PERSISTENCE_FIX_REPORT.md` and `TESTS.md`.

---
*Authorized for Implementation by LandGuard Core Engineering.*
