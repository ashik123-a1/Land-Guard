#!/usr/bin/env python3
"""LandGuard Persistent Database Initialization & Seeding Guard.

Guarantees data preservation and volume initialization for Render cloud deployments:
1. If the persistent volume target database does NOT exist, seeds it from the repository's
   canonical operational database (data/landguard_operational.db) using SQLite backup API.
2. If the target database ALREADY exists, strictly SKIPS re-initialization to preserve
   all existing and runtime records across redeployments and service restarts.
3. Verifies schema integrity and foreign key constraints.
4. Prepares persistent uploads directory structure.
"""

import os
import sys
import sqlite3
import shutil


def init_persistent_storage() -> bool:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    seed_db_path = os.path.abspath(os.path.join(repo_root, "data", "landguard_operational.db"))
    
    # Target path from environment or default
    target_env = os.environ.get("LANDGUARD_DB_PATH")
    if target_env and target_env.strip():
        target_db_path = os.path.abspath(target_env.strip())
    else:
        target_db_path = seed_db_path

    uploads_env = os.environ.get("LANDGUARD_UPLOADS_PATH")
    if uploads_env and uploads_env.strip():
        uploads_path = os.path.abspath(uploads_env.strip())
    else:
        uploads_path = os.path.abspath(os.path.join(repo_root, "data", "uploads"))

    # Ensure uploads directories exist
    os.makedirs(os.path.join(uploads_path, "deeds"), exist_ok=True)
    print(f"[LandGuard Storage] Uploads directory ready at: {uploads_path}")

    # Case 1: Target is same as seed database (e.g., local development)
    if os.path.abspath(target_db_path) == os.path.abspath(seed_db_path):
        if not os.path.exists(seed_db_path):
            print(f"[LandGuard DB Init] ERROR: Seed database not found at {seed_db_path}!")
            return False
        
        print(f"[LandGuard DB Init] Running on canonical local database: {target_db_path}")
        return verify_database(target_db_path)

    # Case 2: Target is on a persistent volume (e.g., /var/data/landguard_operational.db)
    target_dir = os.path.dirname(target_db_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    if os.path.exists(target_db_path) and os.path.getsize(target_db_path) > 0:
        print(f"[LandGuard DB Init] Existing persistent database detected at {target_db_path}.")
        print("[LandGuard DB Init] PRESERVATION RULE APPLIED: Overwrite strictly avoided.")
        return verify_database(target_db_path)
    else:
        print(f"[LandGuard DB Init] Fresh persistent volume detected. Seeding from {seed_db_path} -> {target_db_path}...")
        if not os.path.exists(seed_db_path):
            print(f"[LandGuard DB Init] ERROR: Canonical seed database not found at {seed_db_path}!")
            return False

        try:
            # Use SQLite backup API to copy cleanly including active transactions
            src_conn = sqlite3.connect(f"file:{seed_db_path}?mode=ro", uri=True)
            dst_conn = sqlite3.connect(target_db_path)
            with dst_conn:
                src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
            print(f"[LandGuard DB Init] Successfully seeded persistent database ({os.path.getsize(target_db_path):,} bytes).")
            return verify_database(target_db_path)
        except Exception as e:
            print(f"[LandGuard DB Init] ERROR: Seeding failed: {e}")
            return False


def verify_database(db_path: str) -> bool:
    """Verifies SQLite integrity, foreign keys, and entity counts."""
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Check integrity
        cur.execute("PRAGMA quick_check;")
        quick_check = cur.fetchone()[0]
        if quick_check != "ok":
            print(f"[LandGuard DB Init] WARNING: quick_check returned: {quick_check}")

        cur.execute("PRAGMA foreign_key_check;")
        fk_violations = cur.fetchall()
        if fk_violations:
            print(f"[LandGuard DB Init] WARNING: {len(fk_violations)} foreign key violations detected!")
        else:
            print("[LandGuard DB Init] Foreign key integrity: 100% CLEAN (0 violations).")

        # Entity counts
        counts = {}
        for table in ["complaints", "cases", "users", "verification_runs", "parcels", "audit_events"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table};")
                counts[table] = cur.fetchone()[0]
            except Exception:
                counts[table] = "N/A"

        cur.close()
        conn.close()

        print(
            f"[LandGuard DB Init] Database verification complete:\n"
            f"  - Database: {db_path}\n"
            f"  - Complaints: {counts.get('complaints')}\n"
            f"  - Cases: {counts.get('cases')}\n"
            f"  - Users: {counts.get('users')}\n"
            f"  - Verifications: {counts.get('verification_runs')}\n"
            f"  - Parcels: {counts.get('parcels')}\n"
            f"  - Audit Events: {counts.get('audit_events')}"
        )
        return True
    except Exception as e:
        print(f"[LandGuard DB Init] ERROR verifying database {db_path}: {e}")
        return False


if __name__ == "__main__":
    success = init_persistent_storage()
    if not success:
        sys.exit(1)
    print("[LandGuard DB Init] Ready for ASGI service startup.")
    sys.exit(0)
