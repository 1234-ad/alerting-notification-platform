"""
Notification delivery model for tracking alert deliveries.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from src.database.database import Base


class DeliveryStatus(str, Enum):
    """Delivery status options."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class NotificationDelivery(Base):
    """Model for tracking notification deliveries to users."""
    
    __tablename__ = "notification_deliveries"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Delivery details
    delivery_type = Column(String(20), nullable=False)  # in_app, email, sms
    status = Column(String(20), default=DeliveryStatus.PENDING)
    attempt_count = Column(Integer, default=0)
    
    # Timing
    scheduled_at = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    alert = relationship("Alert", back_populates="notification_deliveries")
    user = relationship("User", back_populates="notification_deliveries")
    
    def __repr__(self):
        return f"<NotificationDelivery(id={self.id}, alert_id={self.alert_id}, user_id={self.user_id}, status='{self.status}')>"
    
    def to_dict(self) -> dict:
        """Convert delivery to dictionary."""
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "user_id": self.user_id,
            "delivery_type": self.delivery_type,
            "status": self.status,
            "attempt_count": self.attempt_count,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def mark_as_sent(self):
        """Mark delivery as sent."""
        self.status = DeliveryStatus.SENT
        self.sent_at = datetime.utcnow()
        self.attempt_count += 1
    
    def mark_as_delivered(self):
        """Mark delivery as delivered."""
        self.status = DeliveryStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
    
    def mark_as_failed(self, error_message: str = None):
        """Mark delivery as failed."""
        self.status = DeliveryStatus.FAILED
        self.error_message = error_message
        self.attempt_count += 1