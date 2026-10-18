"""Notification Repository
Handles persistence and querying for citizen and administrative in-app notifications.
"""

import datetime
import uuid
from typing import Dict, Any, List, Optional
from src.landguard_data.repositories.base import BaseRepository


class NotificationRepository(BaseRepository):
    """Data access repository for in-app notifications."""

    def create_notification(
        self,
        recipient_user_id: str,
        title: str,
        message: str,
        link_url: Optional[str] = None,
        notification_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates and persists an in-app notification."""
        conn = self._get_connection()
        try:
            nid = notification_id or f"NOTIF-{uuid.uuid4().hex[:6].upper()}"
            now = datetime.datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO notifications (notification_id, recipient_user_id, title, message, link_url, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (nid, recipient_user_id, title, message, link_url, now),
            )
            conn.commit()
            return {
                "notification_id": nid,
                "recipient_user_id": recipient_user_id,
                "title": title,
                "message": message,
                "link_url": link_url,
                "is_read": False,
                "created_at": now,
            }
        finally:
            conn.close()

    def get_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns all notifications for a specific user, sorted newest first."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT notification_id, recipient_user_id, title, message, link_url, is_read, created_at
                FROM notifications
                WHERE recipient_user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            out = []
            for r in cur.fetchall():
                d = dict(r)
                d["is_read"] = bool(d["is_read"])
                out.append(d)
            return out
        finally:
            conn.close()

    def mark_notification_read(self, notification_id: str):
        """Marks a notification as read."""
        conn = self._get_connection()
        try:
            conn.execute("UPDATE notifications SET is_read = 1 WHERE notification_id = ?", (notification_id,))
            conn.commit()
        finally:
            conn.close()

    def mark_all_read(self, user_id: str) -> int:
        """Marks all notifications as read for a specific user."""
        conn = self._get_connection()
        try:
            cur = conn.execute("UPDATE notifications SET is_read = 1 WHERE recipient_user_id = ? AND is_read = 0", (user_id,))
            affected = cur.rowcount
            conn.commit()
            return affected
        finally:
            conn.close()
