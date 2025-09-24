"""
User alert preference model implementing State pattern for alert states.
"""

from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, String
from sqlalchemy.orm import relationship
from datetime import datetime, date
from enum import Enum
from abc import ABC, abstractmethod

from src.database.database import Base


class AlertPreferenceState(str, Enum):
    """Alert preference states."""
    UNREAD = "unread"
    READ = "read"
    SNOOZED = "snoozed"


class UserAlertPreference(Base):
    """Model for user-specific alert preferences and states."""
    
    __tablename__ = "user_alert_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    
    # State management
    state = Column(String(20), default=AlertPreferenceState.UNREAD)
    
    # Timing
    first_delivered_at = Column(DateTime, nullable=True)
    last_reminded_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    snoozed_at = Column(DateTime, nullable=True)
    snoozed_until = Column(DateTime, nullable=True)  # End of current day when snoozed
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="alert_preferences")
    alert = relationship("Alert", back_populates="user_preferences")
    
    def __repr__(self):
        return f"<UserAlertPreference(user_id={self.user_id}, alert_id={self.alert_id}, state='{self.state}')>"
    
    def to_dict(self) -> dict:
        """Convert preference to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "alert_id": self.alert_id,
            "state": self.state,
            "first_delivered_at": self.first_delivered_at.isoformat() if self.first_delivered_at else None,
            "last_reminded_at": self.last_reminded_at.isoformat() if self.last_reminded_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "snoozed_at": self.snoozed_at.isoformat() if self.snoozed_at else None,
            "snoozed_until": self.snoozed_until.isoformat() if self.snoozed_until else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def mark_as_read(self):
        """Mark alert as read."""
        self.state = AlertPreferenceState.READ
        self.read_at = datetime.utcnow()
    
    def mark_as_unread(self):
        """Mark alert as unread."""
        self.state = AlertPreferenceState.UNREAD
        self.read_at = None
    
    def snooze_for_day(self):
        """Snooze alert for the rest of the current day."""
        now = datetime.utcnow()
        # Set snooze until end of current day
        end_of_day = datetime.combine(now.date(), datetime.max.time())
        
        self.state = AlertPreferenceState.SNOOZED
        self.snoozed_at = now
        self.snoozed_until = end_of_day
    
    def is_snoozed(self) -> bool:
        """Check if alert is currently snoozed."""
        if self.state != AlertPreferenceState.SNOOZED:
            return False
        
        if self.snoozed_until is None:
            return False
        
        return datetime.utcnow() < self.snoozed_until
    
    def should_send_reminder(self, reminder_interval_hours: int = 2) -> bool:
        """Check if a reminder should be sent."""
        # Don't send if snoozed
        if self.is_snoozed():
            return False
        
        # Don't send if already read
        if self.state == AlertPreferenceState.READ:
            return False
        
        now = datetime.utcnow()
        
        # If never reminded, check against first delivery
        if self.last_reminded_at is None:
            if self.first_delivered_at is None:
                return True  # First delivery
            
            # Check if enough time has passed since first delivery
            time_since_first = now - self.first_delivered_at
            return time_since_first.total_seconds() >= (reminder_interval_hours * 3600)
        
        # Check if enough time has passed since last reminder
        time_since_last = now - self.last_reminded_at
        return time_since_last.total_seconds() >= (reminder_interval_hours * 3600)
    
    def update_reminder_time(self):
        """Update the last reminded time."""
        self.last_reminded_at = datetime.utcnow()
        if self.first_delivered_at is None:
            self.first_delivered_at = datetime.utcnow()
    
    def reset_snooze_if_new_day(self):
        """Reset snooze if it's a new day."""
        if self.is_snoozed() and self.snoozed_until:
            if datetime.utcnow() >= self.snoozed_until:
                self.state = AlertPreferenceState.UNREAD
                self.snoozed_at = None
                self.snoozed_until = None


# State Pattern Implementation for Alert Preferences

class AlertState(ABC):
    """Abstract base class for alert states."""
    
    @abstractmethod
    def handle_read(self, preference: UserAlertPreference):
        """Handle read action."""
        pass
    
    @abstractmethod
    def handle_snooze(self, preference: UserAlertPreference):
        """Handle snooze action."""
        pass
    
    @abstractmethod
    def can_send_reminder(self, preference: UserAlertPreference) -> bool:
        """Check if reminder can be sent."""
        pass


class UnreadState(AlertState):
    """State for unread alerts."""
    
    def handle_read(self, preference: UserAlertPreference):
        preference.mark_as_read()
    
    def handle_snooze(self, preference: UserAlertPreference):
        preference.snooze_for_day()
    
    def can_send_reminder(self, preference: UserAlertPreference) -> bool:
        return preference.should_send_reminder()


class ReadState(AlertState):
    """State for read alerts."""
    
    def handle_read(self, preference: UserAlertPreference):
        # Already read, no action needed
        pass
    
    def handle_snooze(self, preference: UserAlertPreference):
        preference.snooze_for_day()
    
    def can_send_reminder(self, preference: UserAlertPreference) -> bool:
        return False  # Don't send reminders for read alerts


class SnoozedState(AlertState):
    """State for snoozed alerts."""
    
    def handle_read(self, preference: UserAlertPreference):
        preference.mark_as_read()
    
    def handle_snooze(self, preference: UserAlertPreference):
        # Extend snooze for another day
        preference.snooze_for_day()
    
    def can_send_reminder(self, preference: UserAlertPreference) -> bool:
        return not preference.is_snoozed()


class AlertStateManager:
    """Manager for alert state transitions."""
    
    _states = {
        AlertPreferenceState.UNREAD: UnreadState(),
        AlertPreferenceState.READ: ReadState(),
        AlertPreferenceState.SNOOZED: SnoozedState()
    }
    
    @classmethod
    def get_state(cls, state_type: AlertPreferenceState) -> AlertState:
        """Get state instance by type."""
        return cls._states.get(state_type, cls._states[AlertPreferenceState.UNREAD])
    
    @classmethod
    def handle_read(cls, preference: UserAlertPreference):
        """Handle read action using current state."""
        state = cls.get_state(AlertPreferenceState(preference.state))
        state.handle_read(preference)
    
    @classmethod
    def handle_snooze(cls, preference: UserAlertPreference):
        """Handle snooze action using current state."""
        state = cls.get_state(AlertPreferenceState(preference.state))
        state.handle_snooze(preference)
    
    @classmethod
    def can_send_reminder(cls, preference: UserAlertPreference) -> bool:
        """Check if reminder can be sent using current state."""
        # Reset snooze if new day
        preference.reset_snooze_if_new_day()
        
        state = cls.get_state(AlertPreferenceState(preference.state))
        return state.can_send_reminder(preference)