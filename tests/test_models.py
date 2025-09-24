"""
Tests for data models.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.database import Base
from src.models.user import User
from src.models.team import Team
from src.models.alert import Alert, AlertSeverity, DeliveryType, VisibilityType, AlertStatus
from src.models.user_alert_preference import UserAlertPreference, AlertStateManager, AlertPreferenceState
from src.models.notification_delivery import NotificationDelivery, DeliveryStatus


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_team(db_session):
    """Create a sample team."""
    team = Team(name="Engineering", description="Test team")
    db_session.add(team)
    db_session.commit()
    return team


@pytest.fixture
def sample_user(db_session, sample_team):
    """Create a sample user."""
    user = User(
        name="Test User",
        email="test@example.com",
        team_id=sample_team.id,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_user(db_session, sample_team):
    """Create an admin user."""
    user = User(
        name="Admin User",
        email="admin@example.com",
        team_id=sample_team.id,
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_alert(db_session, admin_user):
    """Create a sample alert."""
    alert = Alert(
        title="Test Alert",
        message="This is a test alert",
        severity=AlertSeverity.INFO,
        delivery_type=DeliveryType.IN_APP,
        visibility_type=VisibilityType.ORGANIZATION,
        created_by=admin_user.id
    )
    db_session.add(alert)
    db_session.commit()
    return alert


class TestUser:
    """Test User model."""
    
    def test_user_creation(self, db_session, sample_team):
        """Test user creation."""
        user = User(
            name="John Doe",
            email="john@example.com",
            team_id=sample_team.id
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.team_id == sample_team.id
        assert user.is_admin is False
        assert user.created_at is not None
    
    def test_user_to_dict(self, sample_user):
        """Test user to_dict method."""
        user_dict = sample_user.to_dict()
        
        assert user_dict["id"] == sample_user.id
        assert user_dict["name"] == sample_user.name
        assert user_dict["email"] == sample_user.email
        assert user_dict["team_id"] == sample_user.team_id
        assert user_dict["is_admin"] == sample_user.is_admin


class TestTeam:
    """Test Team model."""
    
    def test_team_creation(self, db_session):
        """Test team creation."""
        team = Team(name="Marketing", description="Marketing team")
        db_session.add(team)
        db_session.commit()
        
        assert team.id is not None
        assert team.name == "Marketing"
        assert team.description == "Marketing team"
        assert team.created_at is not None
    
    def test_team_to_dict(self, sample_team):
        """Test team to_dict method."""
        team_dict = sample_team.to_dict()
        
        assert team_dict["id"] == sample_team.id
        assert team_dict["name"] == sample_team.name
        assert team_dict["description"] == sample_team.description
    
    def test_get_member_ids(self, db_session, sample_team):
        """Test get_member_ids method."""
        # Create users in the team
        user1 = User(name="User 1", email="user1@example.com", team_id=sample_team.id)
        user2 = User(name="User 2", email="user2@example.com", team_id=sample_team.id)
        db_session.add_all([user1, user2])
        db_session.commit()
        
        # Refresh team to load members
        db_session.refresh(sample_team)
        
        member_ids = sample_team.get_member_ids()
        assert len(member_ids) == 2
        assert user1.id in member_ids
        assert user2.id in member_ids


class TestAlert:
    """Test Alert model."""
    
    def test_alert_creation(self, db_session, admin_user):
        """Test alert creation."""
        alert = Alert(
            title="System Maintenance",
            message="Maintenance scheduled for tonight",
            severity=AlertSeverity.WARNING,
            delivery_type=DeliveryType.IN_APP,
            visibility_type=VisibilityType.ORGANIZATION,
            created_by=admin_user.id
        )
        db_session.add(alert)
        db_session.commit()
        
        assert alert.id is not None
        assert alert.title == "System Maintenance"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.status == AlertStatus.ACTIVE
        assert alert.reminders_enabled is True
        assert alert.reminder_interval_hours == 2
    
    def test_alert_is_active(self, sample_alert):
        """Test alert is_active method."""
        assert sample_alert.is_active() is True
        
        # Test expired alert
        sample_alert.expiry_time = datetime.utcnow() - timedelta(hours=1)
        assert sample_alert.is_active() is False
        
        # Test archived alert
        sample_alert.expiry_time = None
        sample_alert.status = AlertStatus.ARCHIVED
        assert sample_alert.is_active() is False
    
    def test_alert_is_expired(self, sample_alert):
        """Test alert is_expired method."""
        assert sample_alert.is_expired() is False
        
        sample_alert.expiry_time = datetime.utcnow() - timedelta(hours=1)
        assert sample_alert.is_expired() is True
    
    def test_get_target_user_ids_organization(self, db_session, sample_alert, sample_user, admin_user):
        """Test get_target_user_ids for organization visibility."""
        sample_alert.visibility_type = VisibilityType.ORGANIZATION
        
        user_ids = sample_alert.get_target_user_ids(db_session)
        
        assert len(user_ids) >= 2  # At least sample_user and admin_user
        assert sample_user.id in user_ids
        assert admin_user.id in user_ids
    
    def test_get_target_user_ids_team(self, db_session, sample_alert, sample_user, sample_team):
        """Test get_target_user_ids for team visibility."""
        sample_alert.visibility_type = VisibilityType.TEAM
        sample_alert.visibility_targets = [sample_team.id]
        
        user_ids = sample_alert.get_target_user_ids(db_session)
        
        assert sample_user.id in user_ids
    
    def test_get_target_user_ids_user(self, db_session, sample_alert, sample_user):
        """Test get_target_user_ids for user visibility."""
        sample_alert.visibility_type = VisibilityType.USER
        sample_alert.visibility_targets = [sample_user.id]
        
        user_ids = sample_alert.get_target_user_ids(db_session)
        
        assert user_ids == [sample_user.id]


class TestUserAlertPreference:
    """Test UserAlertPreference model."""
    
    def test_preference_creation(self, db_session, sample_user, sample_alert):
        """Test preference creation."""
        preference = UserAlertPreference(
            user_id=sample_user.id,
            alert_id=sample_alert.id
        )
        db_session.add(preference)
        db_session.commit()
        
        assert preference.id is not None
        assert preference.state == AlertPreferenceState.UNREAD
        assert preference.created_at is not None
    
    def test_mark_as_read(self, db_session, sample_user, sample_alert):
        """Test mark_as_read method."""
        preference = UserAlertPreference(
            user_id=sample_user.id,
            alert_id=sample_alert.id
        )
        db_session.add(preference)
        db_session.commit()
        
        preference.mark_as_read()
        
        assert preference.state == AlertPreferenceState.READ
        assert preference.read_at is not None
    
    def test_snooze_for_day(self, db_session, sample_user, sample_alert):
        """Test snooze_for_day method."""
        preference = UserAlertPreference(
            user_id=sample_user.id,
            alert_id=sample_alert.id
        )
        db_session.add(preference)
        db_session.commit()
        
        preference.snooze_for_day()
        
        assert preference.state == AlertPreferenceState.SNOOZED
        assert preference.snoozed_at is not None
        assert preference.snoozed_until is not None
        assert preference.is_snoozed() is True
    
    def test_should_send_reminder(self, db_session, sample_user, sample_alert):
        """Test should_send_reminder method."""
        preference = UserAlertPreference(
            user_id=sample_user.id,
            alert_id=sample_alert.id
        )
        db_session.add(preference)
        db_session.commit()
        
        # Should send reminder for new unread alert
        assert preference.should_send_reminder() is True
        
        # Should not send reminder for read alert
        preference.mark_as_read()
        assert preference.should_send_reminder() is False
        
        # Should not send reminder for snoozed alert
        preference.mark_as_unread()
        preference.snooze_for_day()
        assert preference.should_send_reminder() is False


class TestAlertStateManager:
    """Test AlertStateManager."""
    
    def test_handle_read(self, db_session, sample_user, sample_alert):
        """Test handle_read method."""
        preference = UserAlertPreference(
            user_id=sample_user.id,
            alert_id=sample_alert.id
        )
        db_session.add(preference)
        db_session.commit()
        
        AlertStateManager.handle_read(preference)
        
        assert preference.state == AlertPreferenceState.READ
        assert preference.read_at is not None
    
    def test_handle_snooze(self, db_session, sample_user, sample_alert):
        """Test handle_snooze method."""
        preference = UserAlertPreference(
            user_id=sample_user.id,
            alert_id=sample_alert.id
        )
        db_session.add(preference)
        db_session.commit()
        
        AlertStateManager.handle_snooze(preference)
        
        assert preference.state == AlertPreferenceState.SNOOZED
        assert preference.snoozed_at is not None
        assert preference.snoozed_until is not None
    
    def test_can_send_reminder(self, db_session, sample_user, sample_alert):
        """Test can_send_reminder method."""
        preference = UserAlertPreference(
            user_id=sample_user.id,
            alert_id=sample_alert.id
        )
        db_session.add(preference)
        db_session.commit()
        
        # Should be able to send reminder for unread alert
        assert AlertStateManager.can_send_reminder(preference) is True
        
        # Should not send reminder for read alert
        preference.mark_as_read()
        assert AlertStateManager.can_send_reminder(preference) is False
        
        # Should not send reminder for snoozed alert
        preference.mark_as_unread()
        preference.snooze_for_day()
        assert AlertStateManager.can_send_reminder(preference) is False


class TestNotificationDelivery:
    """Test NotificationDelivery model."""
    
    def test_delivery_creation(self, db_session, sample_user, sample_alert):
        """Test delivery creation."""
        delivery = NotificationDelivery(
            alert_id=sample_alert.id,
            user_id=sample_user.id,
            delivery_type=DeliveryType.IN_APP,
            scheduled_at=datetime.utcnow()
        )
        db_session.add(delivery)
        db_session.commit()
        
        assert delivery.id is not None
        assert delivery.status == DeliveryStatus.PENDING
        assert delivery.attempt_count == 0
    
    def test_mark_as_sent(self, db_session, sample_user, sample_alert):
        """Test mark_as_sent method."""
        delivery = NotificationDelivery(
            alert_id=sample_alert.id,
            user_id=sample_user.id,
            delivery_type=DeliveryType.IN_APP,
            scheduled_at=datetime.utcnow()
        )
        db_session.add(delivery)
        db_session.commit()
        
        delivery.mark_as_sent()
        
        assert delivery.status == DeliveryStatus.SENT
        assert delivery.sent_at is not None
        assert delivery.attempt_count == 1
    
    def test_mark_as_failed(self, db_session, sample_user, sample_alert):
        """Test mark_as_failed method."""
        delivery = NotificationDelivery(
            alert_id=sample_alert.id,
            user_id=sample_user.id,
            delivery_type=DeliveryType.IN_APP,
            scheduled_at=datetime.utcnow()
        )
        db_session.add(delivery)
        db_session.commit()
        
        error_msg = "Network error"
        delivery.mark_as_failed(error_msg)
        
        assert delivery.status == DeliveryStatus.FAILED
        assert delivery.error_message == error_msg
        assert delivery.attempt_count == 1