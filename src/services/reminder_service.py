"""
Reminder service for handling recurring alert reminders.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session

from src.models.alert import Alert, AlertStatus
from src.services.notification_service import notification_service
from src.database.database import get_db_session
from src.config import settings


class ReminderService:
    """Service for managing recurring alert reminders."""
    
    def __init__(self):
        self._running = False
        self._thread = None
        self._check_interval = settings.REMINDER_CHECK_INTERVAL_SECONDS
    
    def start(self):
        """Start the reminder service."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_reminder_loop, daemon=True)
        self._thread.start()
        print(f"🔔 Reminder service started (checking every {self._check_interval}s)")
    
    def stop(self):
        """Stop the reminder service."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("🔕 Reminder service stopped")
    
    def _run_reminder_loop(self):
        """Main reminder loop."""
        while self._running:
            try:
                self._process_reminders()
            except Exception as e:
                print(f"❌ Error in reminder loop: {str(e)}")
            
            # Sleep for the check interval
            time.sleep(self._check_interval)
    
    def _process_reminders(self):
        """Process all active alerts for reminders."""
        with get_db_session() as db:
            # Get all active alerts with reminders enabled
            active_alerts = db.query(Alert).filter(
                Alert.status == AlertStatus.ACTIVE,
                Alert.reminders_enabled == True,
                Alert.start_time <= datetime.utcnow()
            ).all()
            
            reminders_sent = 0
            
            for alert in active_alerts:
                # Check if alert has expired
                if alert.is_expired():
                    alert.status = AlertStatus.EXPIRED
                    continue
                
                # Send reminder if needed
                result = notification_service.send_reminder(alert)
                
                if result.get("status") != "skipped":
                    successful = result.get("successful_deliveries", 0)
                    if successful > 0:
                        reminders_sent += successful
                        print(f"📬 Sent {successful} reminders for alert: {alert.title}")
            
            if reminders_sent > 0:
                print(f"✅ Processed reminders: {reminders_sent} notifications sent")
    
    def send_immediate_reminder(self, alert_id: int) -> dict:
        """Send immediate reminder for a specific alert (for testing/admin use)."""
        with get_db_session() as db:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return {"error": "Alert not found"}
            
            if not alert.is_active():
                return {"error": "Alert is not active"}
            
            return notification_service.send_reminder(alert)
    
    def get_reminder_stats(self) -> dict:
        """Get statistics about reminders."""
        with get_db_session() as db:
            from src.models.notification_delivery import NotificationDelivery
            from src.models.user_alert_preference import UserAlertPreference, AlertPreferenceState
            
            # Count active alerts with reminders
            active_alerts_count = db.query(Alert).filter(
                Alert.status == AlertStatus.ACTIVE,
                Alert.reminders_enabled == True
            ).count()
            
            # Count total deliveries today
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time())
            
            deliveries_today = db.query(NotificationDelivery).filter(
                NotificationDelivery.created_at >= today_start
            ).count()
            
            # Count snoozed alerts
            snoozed_count = db.query(UserAlertPreference).filter(
                UserAlertPreference.state == AlertPreferenceState.SNOOZED
            ).count()
            
            # Count unread alerts
            unread_count = db.query(UserAlertPreference).filter(
                UserAlertPreference.state == AlertPreferenceState.UNREAD
            ).count()
            
            return {
                "active_alerts_with_reminders": active_alerts_count,
                "deliveries_today": deliveries_today,
                "snoozed_alerts": snoozed_count,
                "unread_alerts": unread_count,
                "service_running": self._running,
                "check_interval_seconds": self._check_interval
            }


# Singleton instance
reminder_service = ReminderService()