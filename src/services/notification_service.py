"""
Notification service implementing Strategy pattern for different delivery channels.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.alert import Alert, DeliveryType
from src.models.user import User
from src.models.notification_delivery import NotificationDelivery, DeliveryStatus
from src.models.user_alert_preference import UserAlertPreference, AlertStateManager
from src.database.database import get_db_session


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""
    
    @abstractmethod
    def send_notification(self, user: User, alert: Alert, delivery: NotificationDelivery) -> bool:
        """Send notification through this channel."""
        pass
    
    @abstractmethod
    def get_channel_type(self) -> str:
        """Get the channel type identifier."""
        pass


class InAppNotificationChannel(NotificationChannel):
    """In-app notification channel."""
    
    def send_notification(self, user: User, alert: Alert, delivery: NotificationDelivery) -> bool:
        """Send in-app notification."""
        try:
            # For MVP, we just mark as sent since it's in-app
            # In a real implementation, this might push to a WebSocket or queue
            print(f"📱 In-App Notification sent to {user.name} ({user.email})")
            print(f"   Alert: {alert.title}")
            print(f"   Message: {alert.message}")
            print(f"   Severity: {alert.severity.upper()}")
            return True
        except Exception as e:
            print(f"❌ Failed to send in-app notification: {str(e)}")
            return False
    
    def get_channel_type(self) -> str:
        return DeliveryType.IN_APP


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel (future implementation)."""
    
    def send_notification(self, user: User, alert: Alert, delivery: NotificationDelivery) -> bool:
        """Send email notification."""
        try:
            # Placeholder for email implementation
            print(f"📧 Email notification would be sent to {user.email}")
            print(f"   Subject: [{alert.severity.upper()}] {alert.title}")
            print(f"   Body: {alert.message}")
            return True
        except Exception as e:
            print(f"❌ Failed to send email notification: {str(e)}")
            return False
    
    def get_channel_type(self) -> str:
        return DeliveryType.EMAIL


class SMSNotificationChannel(NotificationChannel):
    """SMS notification channel (future implementation)."""
    
    def send_notification(self, user: User, alert: Alert, delivery: NotificationDelivery) -> bool:
        """Send SMS notification."""
        try:
            # Placeholder for SMS implementation
            print(f"📱 SMS notification would be sent to user {user.name}")
            print(f"   Message: [{alert.severity.upper()}] {alert.title}: {alert.message[:100]}...")
            return True
        except Exception as e:
            print(f"❌ Failed to send SMS notification: {str(e)}")
            return False
    
    def get_channel_type(self) -> str:
        return DeliveryType.SMS


class NotificationService:
    """Service for managing notifications using Strategy pattern."""
    
    def __init__(self):
        self._channels: Dict[str, NotificationChannel] = {
            DeliveryType.IN_APP: InAppNotificationChannel(),
            DeliveryType.EMAIL: EmailNotificationChannel(),
            DeliveryType.SMS: SMSNotificationChannel()
        }
    
    def register_channel(self, channel: NotificationChannel):
        """Register a new notification channel."""
        self._channels[channel.get_channel_type()] = channel
    
    def send_alert_to_users(self, alert: Alert, user_ids: List[int]) -> Dict[str, Any]:
        """Send alert to specified users."""
        results = {
            "total_users": len(user_ids),
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "delivery_details": []
        }
        
        with get_db_session() as db:
            for user_id in user_ids:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    results["failed_deliveries"] += 1
                    results["delivery_details"].append({
                        "user_id": user_id,
                        "status": "failed",
                        "error": "User not found"
                    })
                    continue
                
                # Create or get user preference
                preference = db.query(UserAlertPreference).filter(
                    UserAlertPreference.user_id == user_id,
                    UserAlertPreference.alert_id == alert.id
                ).first()
                
                if not preference:
                    preference = UserAlertPreference(
                        user_id=user_id,
                        alert_id=alert.id
                    )
                    db.add(preference)
                    db.flush()
                
                # Check if we should send (considering snooze state)
                if not AlertStateManager.can_send_reminder(preference):
                    results["delivery_details"].append({
                        "user_id": user_id,
                        "status": "skipped",
                        "reason": f"Alert is {preference.state}"
                    })
                    continue
                
                # Create delivery record
                delivery = NotificationDelivery(
                    alert_id=alert.id,
                    user_id=user_id,
                    delivery_type=alert.delivery_type,
                    scheduled_at=datetime.utcnow()
                )
                db.add(delivery)
                db.flush()
                
                # Send notification
                success = self._send_notification(user, alert, delivery)
                
                if success:
                    delivery.mark_as_sent()
                    delivery.mark_as_delivered()
                    preference.update_reminder_time()
                    results["successful_deliveries"] += 1
                    results["delivery_details"].append({
                        "user_id": user_id,
                        "status": "delivered",
                        "delivery_id": delivery.id
                    })
                else:
                    delivery.mark_as_failed("Channel delivery failed")
                    results["failed_deliveries"] += 1
                    results["delivery_details"].append({
                        "user_id": user_id,
                        "status": "failed",
                        "delivery_id": delivery.id,
                        "error": "Channel delivery failed"
                    })
        
        return results
    
    def _send_notification(self, user: User, alert: Alert, delivery: NotificationDelivery) -> bool:
        """Send notification using appropriate channel."""
        channel = self._channels.get(alert.delivery_type)
        if not channel:
            print(f"❌ No channel found for delivery type: {alert.delivery_type}")
            return False
        
        return channel.send_notification(user, alert, delivery)
    
    def send_reminder(self, alert: Alert) -> Dict[str, Any]:
        """Send reminder for an alert to all eligible users."""
        if not alert.is_active() or not alert.reminders_enabled:
            return {
                "status": "skipped",
                "reason": "Alert not active or reminders disabled"
            }
        
        with get_db_session() as db:
            # Get all users who should receive this alert
            target_user_ids = alert.get_target_user_ids(db)
            
            # Filter users who need reminders
            eligible_users = []
            for user_id in target_user_ids:
                preference = db.query(UserAlertPreference).filter(
                    UserAlertPreference.user_id == user_id,
                    UserAlertPreference.alert_id == alert.id
                ).first()
                
                if preference and AlertStateManager.can_send_reminder(preference):
                    eligible_users.append(user_id)
            
            if not eligible_users:
                return {
                    "status": "skipped",
                    "reason": "No eligible users for reminder"
                }
            
            # Send reminders
            return self.send_alert_to_users(alert, eligible_users)
    
    def get_available_channels(self) -> List[str]:
        """Get list of available notification channels."""
        return list(self._channels.keys())


# Observer Pattern Implementation for User Subscriptions

class AlertObserver(ABC):
    """Abstract observer for alert events."""
    
    @abstractmethod
    def on_alert_created(self, alert: Alert):
        """Handle alert creation event."""
        pass
    
    @abstractmethod
    def on_alert_updated(self, alert: Alert):
        """Handle alert update event."""
        pass


class UserNotificationObserver(AlertObserver):
    """Observer that handles user notifications for alert events."""
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
    
    def on_alert_created(self, alert: Alert):
        """Send initial notifications when alert is created."""
        with get_db_session() as db:
            target_user_ids = alert.get_target_user_ids(db)
            if target_user_ids:
                self.notification_service.send_alert_to_users(alert, target_user_ids)
    
    def on_alert_updated(self, alert: Alert):
        """Handle alert updates (could trigger re-notifications)."""
        # For now, we don't re-send on updates
        # This could be extended to handle specific update scenarios
        pass


class AlertSubject:
    """Subject that notifies observers about alert events."""
    
    def __init__(self):
        self._observers: List[AlertObserver] = []
    
    def attach(self, observer: AlertObserver):
        """Attach an observer."""
        self._observers.append(observer)
    
    def detach(self, observer: AlertObserver):
        """Detach an observer."""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify_alert_created(self, alert: Alert):
        """Notify all observers about alert creation."""
        for observer in self._observers:
            observer.on_alert_created(alert)
    
    def notify_alert_updated(self, alert: Alert):
        """Notify all observers about alert updates."""
        for observer in self._observers:
            observer.on_alert_updated(alert)


# Global instances
notification_service = NotificationService()
alert_subject = AlertSubject()

# Set up observer
user_notification_observer = UserNotificationObserver(notification_service)
alert_subject.attach(user_notification_observer)