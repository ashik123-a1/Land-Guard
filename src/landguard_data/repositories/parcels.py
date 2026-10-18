"""Parcel Repository
Handles database persistence and retrieval for cadastral parcels and ownership events.
Supports both SQLite operational store and Neon PostgreSQL.
"""

import datetime
import os
import uuid
from typing import Dict, Any, List, Optional
from src.landguard_data.repositories.base import BaseRepository


class ParcelRepository(BaseRepository):
    """Data access repository for cadastral parcels and ownership history events."""

    def create_parcel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Inserts a new canonical cadastral parcel into the operational store."""
        plot_str = str(data.get("dag_plot_number", "")).strip()
        parcel_id = data.get("parcel_id") or f"PAR-{plot_str}-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.datetime.now().isoformat()

        row = {
            "parcel_id": parcel_id,
            "dag_plot_number": plot_str,
            "khatian_number": str(data.get("khatian_number") or "").strip(),
            "mouza": str(data.get("mouza") or "").strip(),
            "jl_number": str(data.get("jl_number") or "").strip(),
            "upazila": str(data.get("upazila") or "").strip(),
            "district": str(data.get("district") or "").strip(),
            "division": str(data.get("division") or "Dhaka").strip(),
            "total_area_decimal": float(data.get("total_area_decimal", 0.0)),
            "land_classification": str(data.get("land_classification") or "Nal").strip(),
            "cs_plot": str(data.get("cs_plot") or "").strip(),
            "sa_plot": str(data.get("sa_plot") or "").strip(),
            "rs_plot": str(data.get("rs_plot") or "").strip(),
            "bs_plot": str(data.get("bs_plot") or plot_str).strip(),
            "provenance": str(data.get("provenance") or "ADMIN_REGISTERED").strip(),
            "created_at": now,
        }

        conn = self._get_connection()
        try:
            if self.db_type == "POSTGRESQL":
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO parcels (
                        parcel_id, dag_plot_number, khatian_number, mouza, jl_number,
                        upazila, district, division, total_area_decimal, land_classification,
                        cs_plot, sa_plot, rs_plot, bs_plot, provenance, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        row["parcel_id"], row["dag_plot_number"], row["khatian_number"], row["mouza"], row["jl_number"],
                        row["upazila"], row["district"], row["division"], row["total_area_decimal"], row["land_classification"],
                        row["cs_plot"], row["sa_plot"], row["rs_plot"], row["bs_plot"], row["provenance"], row["created_at"],
                    ),
                )
                conn.commit()
                cur.close()
            else:
                conn.execute(
                    """
                    INSERT INTO parcels (
                        parcel_id, dag_plot_number, khatian_number, mouza, jl_number,
                        upazila, district, division, total_area_decimal, land_classification,
                        cs_plot, sa_plot, rs_plot, bs_plot, provenance, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["parcel_id"], row["dag_plot_number"], row["khatian_number"], row["mouza"], row["jl_number"],
                        row["upazila"], row["district"], row["division"], row["total_area_decimal"], row["land_classification"],
                        row["cs_plot"], row["sa_plot"], row["rs_plot"], row["bs_plot"], row["provenance"], row["created_at"],
                    ),
                )
                conn.commit()
            return row
        finally:
            conn.close()

    def get_parcel_by_plot(self, plot_number: str, mouza: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves a parcel by dag plot number and optional mouza."""
        p_str = str(plot_number).strip()
        conn = self._get_connection()
        try:
            if mouza and mouza.strip():
                m_str = mouza.strip().lower()
                if self.db_type == "POSTGRESQL":
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT * FROM parcels WHERE LOWER(dag_plot_number) = LOWER(%s) AND LOWER(mouza) = LOWER(%s) LIMIT 1",
                        (p_str, m_str),
                    )
                    r = cur.fetchone()
                    cur.close()
                else:
                    r = conn.execute(
                        "SELECT * FROM parcels WHERE LOWER(dag_plot_number) = LOWER(?) AND LOWER(mouza) = LOWER(?) LIMIT 1",
                        (p_str, m_str),
                    ).fetchone()
            else:
                if self.db_type == "POSTGRESQL":
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT * FROM parcels WHERE LOWER(dag_plot_number) = LOWER(%s) LIMIT 1",
                        (p_str,),
                    )
                    r = cur.fetchone()
                    cur.close()
                else:
                    r = conn.execute(
                        "SELECT * FROM parcels WHERE LOWER(dag_plot_number) = LOWER(?) LIMIT 1",
                        (p_str,),
                    ).fetchone()

            if not r:
                return None
            return dict(r)
        finally:
            conn.close()

    def list_parcels(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieves all registered parcels from the database."""
        conn = self._get_connection()
        try:
            if self.db_type == "POSTGRESQL":
                cur = conn.cursor()
                cur.execute("SELECT * FROM parcels ORDER BY created_at DESC LIMIT %s", (limit,))
                rows = cur.fetchall()
                cur.close()
                return [dict(r) for r in rows]
            else:
                rows = conn.execute("SELECT * FROM parcels ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
                return [dict(r) for r in rows]
        finally:
            conn.close()

    def create_ownership_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Inserts a historical or current ownership event for a parcel."""
        event_id = data.get("event_id") or f"EVT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.datetime.now().isoformat()
        row = {
            "event_id": event_id,
            "parcel_id": str(data.get("parcel_id")),
            "event_type": str(data.get("event_type") or "BS_MUTATION"),
            "record_date": str(data.get("record_date") or datetime.date.today().isoformat()),
            "owner_name": str(data.get("owner_name") or ""),
            "owner_nid": str(data.get("owner_nid") or ""),
            "area_decimal": float(data.get("area_decimal", 0.0)),
            "document_ref": str(data.get("document_ref") or ""),
            "created_at": now,
        }

        conn = self._get_connection()
        try:
            if self.db_type == "POSTGRESQL":
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO ownership_events (event_id, parcel_id, event_type, record_date, owner_name, owner_nid, area_decimal, document_ref, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        row["event_id"], row["parcel_id"], row["event_type"], row["record_date"],
                        row["owner_name"], row["owner_nid"], row["area_decimal"], row["document_ref"], row["created_at"],
                    ),
                )
                conn.commit()
                cur.close()
            else:
                conn.execute(
                    """
                    INSERT INTO ownership_events (event_id, parcel_id, event_type, record_date, owner_name, owner_nid, area_decimal, document_ref, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["event_id"], row["parcel_id"], row["event_type"], row["record_date"],
                        row["owner_name"], row["owner_nid"], row["area_decimal"], row["document_ref"], row["created_at"],
                    ),
                )
                conn.commit()
            return row
        finally:
            conn.close()
