"""Document Repository
Handles persistence and querying for uploaded deed documents and metadata.
"""

import datetime
import uuid
from typing import Dict, Any, Optional
from src.landguard_data.repositories.base import BaseRepository


class DocumentRepository(BaseRepository):
    """Data access repository for uploaded deed documents."""

    def save_document(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Saves metadata for an uploaded deed document."""
        conn = self._get_connection()
        try:
            now = datetime.datetime.now().isoformat()
            did = doc_data.get("document_id") or f"DOC-{uuid.uuid4().hex[:8].upper()}"
            conn.execute(
                """
                INSERT OR REPLACE INTO documents (
                    document_id, filename, file_path, mime_type, byte_size,
                    sha256_hash, uploaded_by, is_synthetic, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    did,
                    doc_data.get("filename", "deed.png"),
                    doc_data.get("file_path", ""),
                    doc_data.get("mime_type", "image/png"),
                    int(doc_data.get("byte_size") or 0),
                    doc_data.get("sha256_hash", ""),
                    doc_data.get("uploaded_by") or "USR-CITIZEN-001",
                    now,
                ),
            )
            conn.commit()
            doc_data["document_id"] = did
            return doc_data
        finally:
            conn.close()

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves document record by document_id."""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_document(self, document_id: str) -> bool:
        """Deletes a document record from documents table."""
        conn = self._get_connection()
        try:
            cur = conn.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

