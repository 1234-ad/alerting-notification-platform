"""
Tests for service classes.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.database import Base
from src.models.user import User
from src.models.team import Team
from src.models.alert import Alert, AlertSeverity, DeliveryType, VisibilityType
from src.models.user_alert_preference import UserAlertPreference, AlertPreferenceState
from src.models.notification_delivery import NotificationDelivery, DeliveryStatus
from src.services.notification_service import (
    NotificationService, InAppNotificationChannel, 
    UserNotificationObserver, AlertSubject
)
from src.services.analytics_service import AnalyticsService


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
def sample_data(db_session):
    """Create sample data for testing."""
    # Create team
    team = Team(name="Engineering", description="Test team")
    db_session.add(team)
    db_session.flush()
    
    # Create users
    admin = User(name="Admin", email="admin@test.com", team_id=team.id, is_admin=True)
    user1 = User(name="User 1", email="user1@test.com", team_id=team.id)
    user2 = User(name="User 2", email="user2@test.com", team_id=team.id)
    db_session.add_all([admin, user1, user2])
    db_session.flush()
    
    # Create alert
    alert = Alert(
        title="Test Alert",
        message="Test message",
        severity=AlertSeverity.INFO,
        delivery_type=DeliveryType.IN_APP,
        visibility_type=VisibilityType.TEAM,
        visibility_targets=[team.id],
        created_by=admin.id
    )
    db_session.add(alert)
    db_session.commit()
    
    return {
        'team': team,
        'admin': admin,
        'user1': user1,
        'user2': user2,
        'alert': alert
    }


class TestNotificationService:
    """Test NotificationService."""
    
    def test_notification_service_initialization(self):
        """Test notification service initialization."""
        service = NotificationService()
        
        channels = service.get_available_channels()
        assert DeliveryType.IN_APP in channels
        assert DeliveryType.EMAIL in channels
        assert DeliveryType.SMS in channels
    
    @patch('src.services.notification_service.get_db_session')
    def test_send_alert_to_users(self, mock_db_session, sample_data):
        """Test sending alert to users."""
        # Mock database session
        mock_db_session.return_value.__enter__.return_value = Mock()
        mock_session = mock_db_session.return_value.__enter__.return_value
        
        # Mock user query
        mock_session.query.return_value.filter.return_value.first.return_value = sample_data['user1']
        mock_session.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        
        service = NotificationService()
        
        # Mock the _send_notification method to return True
        service._send_notification = Mock(return_value=True)
        
        result = service.send_alert_to_users(sample_data['alert'], [sample_data['user1'].id])
        
        assert result['total_users'] == 1
        assert result['successful_deliveries'] == 1
        assert result['failed_deliveries'] == 0
    
    def test_in_app_notification_channel(self, sample_data):
        """Test in-app notification channel."""
        channel = InAppNotificationChannel()
        
        assert channel.get_channel_type() == DeliveryType.IN_APP
        
        # Create a mock delivery
        delivery = NotificationDelivery(
            alert_id=sample_data['alert'].id,
            user_id=sample_data['user1'].id,
            delivery_type=DeliveryType.IN_APP,
            scheduled_at=datetime.utcnow()
        )
        
        # Test sending notification
        result = channel.send_notification(sample_data['user1'], sample_data['alert'], delivery)
        assert result is True


class TestAlertSubject:
    """Test AlertSubject (Observer pattern)."""
    
    def test_observer_attachment(self):
        """Test observer attachment and detachment."""
        subject = AlertSubject()
        observer = Mock()
        
        subject.attach(observer)
        assert observer in subject._observers
        
        subject.detach(observer)
        assert observer not in subject._observers
    
    def test_notify_alert_created(self, sample_data):
        """Test alert creation notification."""
        subject = AlertSubject()
        observer = Mock()
        subject.attach(observer)
        
        subject.notify_alert_created(sample_data['alert'])
        
        observer.on_alert_created.assert_called_once_with(sample_data['alert'])
    
    def test_notify_alert_updated(self, sample_data):
        """Test alert update notification."""
        subject = AlertSubject()
        observer = Mock()
        subject.attach(observer)
        
        subject.notify_alert_updated(sample_data['alert'])
        
        observer.on_alert_updated.assert_called_once_with(sample_data['alert'])


class TestUserNotificationObserver:
    """Test UserNotificationObserver."""
    
    def test_on_alert_created(self, sample_data):
        """Test alert creation handling."""
        mock_service = Mock()
        observer = UserNotificationObserver(mock_service)
        
        with patch('src.services.notification_service.get_db_session') as mock_db_session:
            mock_session = Mock()
            mock_db_session.return_value.__enter__.return_value = mock_session
            
            # Mock get_target_user_ids
            sample_data['alert'].get_target_user_ids = Mock(return_value=[1, 2, 3])
            
            observer.on_alert_created(sample_data['alert'])
            
            mock_service.send_alert_to_users.assert_called_once_with(sample_data['alert'], [1, 2, 3])


class TestAnalyticsService:
    """Test AnalyticsService."""
    
    @patch('src.services.analytics_service.get_db_session')
    def test_get_system_overview(self, mock_db_session, sample_data):
        """Test system overview analytics."""
        # Mock database session and queries
        mock_session = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock query results
        mock_session.query.return_value.count.return_value = 5
        mock_session.query.return_value.filter.return_value.count.return_value = 3
        
        service = AnalyticsService()
        result = service.get_system_overview()
        
        assert 'system_metrics' in result
        assert 'delivery_metrics' in result
        assert 'engagement_metrics' in result
        assert result['system_metrics']['total_alerts'] == 5
    
    @patch('src.services.analytics_service.get_db_session')
    def test_get_alert_metrics(self, mock_db_session):
        """Test alert metrics."""
        mock_session = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock severity counts
        mock_session.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
            (AlertSeverity.INFO, 10),
            (AlertSeverity.WARNING, 5),
            (AlertSeverity.CRITICAL, 2)
        ]
        
        # Mock status counts
        mock_session.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
            ('active', 15),
            ('expired', 2)
        ]
        
        # Mock daily trend
        mock_session.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = [
            (datetime.now().date(), 5)
        ]
        
        service = AnalyticsService()
        result = service.get_alert_metrics(30)
        
        assert 'severity_breakdown' in result
        assert 'status_breakdown' in result
        assert 'daily_trend' in result
        assert result['period_days'] == 30
    
    @patch('src.services.analytics_service.get_db_session')
    def test_get_alert_performance(self, mock_db_session, sample_data):
        """Test alert performance metrics."""
        mock_session = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock alert query
        mock_session.query.return_value.filter.return_value.first.return_value = sample_data['alert']
        
        # Mock delivery and preference counts
        mock_session.query.return_value.filter.return_value.count.return_value = 10
        
        service = AnalyticsService()
        result = service.get_alert_performance(sample_data['alert'].id)
        
        assert 'alert' in result
        assert 'delivery_metrics' in result
        assert 'engagement_metrics' in result
        assert result['alert']['id'] == sample_data['alert'].id
    
    @patch('src.services.analytics_service.get_db_session')
    def test_get_alert_performance_not_found(self, mock_db_session):
        """Test alert performance for non-existent alert."""
        mock_session = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock alert not found
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        service = AnalyticsService()
        result = service.get_alert_performance(999)
        
        assert 'error' in result
        assert result['error'] == 'Alert not found'


class TestReminderLogic:
    """Test reminder-related functionality."""
    
    def test_should_send_reminder_timing(self, db_session, sample_data):
        """Test reminder timing logic."""
        # Create preference
        preference = UserAlertPreference(
            user_id=sample_data['user1'].id,
            alert_id=sample_data['alert'].id
        )
        db_session.add(preference)
        db_session.commit()
        
        # Should send reminder for new alert
        assert preference.should_send_reminder() is True
        
        # Update reminder time
        preference.update_reminder_time()
        
        # Should not send reminder immediately after
        assert preference.should_send_reminder() is False
        
        # Should send reminder after interval
        preference.last_reminded_at = datetime.utcnow() - timedelta(hours=3)
        assert preference.should_send_reminder() is True
    
    def test_snooze_behavior(self, db_session, sample_data):
        """Test snooze behavior."""
        preference = UserAlertPreference(
            user_id=sample_data['user1'].id,
            alert_id=sample_data['alert'].id
        )
        db_session.add(preference)
        db_session.commit()
        
        # Snooze the alert
        preference.snooze_for_day()
        
        # Should not send reminder when snoozed
        assert preference.should_send_reminder() is False
        assert preference.is_snoozed() is True
        
        # Test snooze reset (simulate next day)
        preference.snoozed_until = datetime.utcnow() - timedelta(hours=1)
        preference.reset_snooze_if_new_day()
        
        assert preference.state == AlertPreferenceState.UNREAD
        assert preference.is_snoozed() is False