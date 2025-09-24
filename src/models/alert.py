"""
Alert model and related functionality.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from src.database.database import Base


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DeliveryType(str, Enum):
    """Delivery channel types."""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"


class VisibilityType(str, Enum):
    """Alert visibility types."""
    ORGANIZATION = "organization"
    TEAM = "team"
    USER = "user"


class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class Alert(Base):
    """Alert model representing system alerts."""
    
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, default=AlertSeverity.INFO)
    delivery_type = Column(String(20), nullable=False, default=DeliveryType.IN_APP)
    visibility_type = Column(String(20), nullable=False)
    visibility_targets = Column(JSON, nullable=True)  # List of team/user IDs
    
    # Timing
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    expiry_time = Column(DateTime, nullable=True)
    reminder_interval_hours = Column(Integer, default=2)
    reminders_enabled = Column(Boolean, default=True)
    
    # Status and metadata
    status = Column(String(20), default=AlertStatus.ACTIVE)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by_user = relationship("User", back_populates="created_alerts")
    notification_deliveries = relationship("NotificationDelivery", back_populates="alert")
    user_preferences = relationship("UserAlertPreference", back_populates="alert")
    
    def __repr__(self):
        return f"<Alert(id={self.id}, title='{self.title}', severity='{self.severity}')>"
    
    def to_dict(self) -> dict:
        """Convert alert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "delivery_type": self.delivery_type,
            "visibility_type": self.visibility_type,
            "visibility_targets": self.visibility_targets,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "expiry_time": self.expiry_time.isoformat() if self.expiry_time else None,
            "reminder_interval_hours": self.reminder_interval_hours,
            "reminders_enabled": self.reminders_enabled,
            "status": self.status,
            "created_by": self.created_by,
            "created_by_name": self.created_by_user.name if self.created_by_user else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_active(self) -> bool:
        """Check if alert is currently active."""
        now = datetime.utcnow()
        return (
            self.status == AlertStatus.ACTIVE and
            self.start_time <= now and
            (self.expiry_time is None or self.expiry_time > now)
        )
    
    def is_expired(self) -> bool:
        """Check if alert has expired."""
        if self.expiry_time is None:
            return False
        return datetime.utcnow() > self.expiry_time
    
    def get_target_user_ids(self, db_session) -> List[int]:
        """Get list of user IDs that should receive this alert."""
        from src.models.user import User
        from src.models.team import Team
        
        if self.visibility_type == VisibilityType.ORGANIZATION:
            # All users in organization
            users = db_session.query(User).all()
            return [user.id for user in users]
        
        elif self.visibility_type == VisibilityType.TEAM:
            # Users in specific teams
            if not self.visibility_targets:
                return []
            
            user_ids = []
            for team_id in self.visibility_targets:
                team = db_session.query(Team).filter(Team.id == team_id).first()
                if team:
                    user_ids.extend(team.get_member_ids())
            return list(set(user_ids))  # Remove duplicates
        
        elif self.visibility_type == VisibilityType.USER:
            # Specific users
            return self.visibility_targets or []
        
        return []