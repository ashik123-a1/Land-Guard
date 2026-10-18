"""Notification Domain Service
Handles creating, querying, and updating in-app notifications.
"""

import datetime
import uuid
from typing import Dict, Any, List, Optional
from src.landguard_data.database import LandGuardDatabase


class NotificationService:
    """Domain service managing user notifications."""

    def __init__(self, db: Optional[LandGuardDatabase] = None, notifications_cache: Optional[List[Dict[str, Any]]] = None):
        self.db = db or LandGuardDatabase()
        self.notifications: List[Dict[str, Any]] = notifications_cache if notifications_cache is not None else []

    def create_notification(
        self,
        recipient_user_id: str,
        title: str,
        message: str,
        link_url: Optional[str] = None,
        notif_type: str = "INFO",
    ) -> Dict[str, Any]:
        """Creates an in-app notification in memory and SQLite."""
        now = datetime.datetime.now().isoformat()
        notif = {
            "notification_id": f"NOTIF-{uuid.uuid4().hex[:6].upper()}",
            "recipient_user_id": recipient_user_id,
            "title": title,
            "message": message,
            "link_url": link_url,
            "type": notif_type,
            "is_read": False,
            "created_at": now,
        }
        self.notifications.append(notif)
        try:
            self.db.create_notification(
                recipient_user_id=recipient_user_id,
                title=title,
                message=message,
                link_url=link_url,
                notification_id=notif["notification_id"],
            )
        except Exception as e:
            print(f"[NotificationService] Warning: Failed to persist notification in SQLite: {e}")
        return notif

    def get_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns all notifications for given user, newest first, from SQLite or memory."""
        try:
            db_notifs = self.db.get_notifications(user_id)
            if db_notifs:
                return db_notifs
        except Exception as e:
            print(f"[NotificationService] Warning: Failed to get notifications from SQLite: {e}")

        user_notifs = [n for n in self.notifications if n.get("recipient_user_id") == user_id]
        return sorted(user_notifs, key=lambda n: n.get("created_at", ""), reverse=True)

    def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Marks notification as read in memory and SQLite."""
        try:
            self.db.mark_notification_read(notification_id)
        except Exception:
            pass
        for n in self.notifications:
            if n.get("notification_id") == notification_id and n.get("recipient_user_id") == user_id:
                n["is_read"] = True
                return True
        return False

    def mark_all_read(self, user_id: str) -> int:
        """Marks all unread notifications as read for user in SQLite and memory."""
        count = 0
        try:
            count = self.db.mark_all_notifications_read(user_id)
        except Exception as e:
            print(f"[NotificationService] Warning: Failed to mark all notifications read in SQLite: {e}")
        for n in self.notifications:
            if n.get("recipient_user_id") == user_id and not n.get("is_read"):
                n["is_read"] = True
                if count == 0:
                    count += 1
        return count

