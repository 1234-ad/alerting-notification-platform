"""
Tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from main import app
from src.database.database import Base, get_db
from src.models.user import User
from src.models.team import Team
from src.models.alert import Alert, AlertSeverity, DeliveryType, VisibilityType


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Override the get_db dependency
    def override_get_db():
        try:
            yield session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield session
    
    session.close()
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


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
        visibility_type=VisibilityType.ORGANIZATION,
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


class TestRootEndpoints:
    """Test root endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["version"] == "1.0.0"
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAdminEndpoints:
    """Test admin endpoints."""
    
    def test_create_alert(self, client, sample_data):
        """Test creating an alert."""
        alert_data = {
            "title": "New Test Alert",
            "message": "This is a new test alert",
            "severity": "warning",
            "delivery_type": "in_app",
            "visibility_type": "organization",
            "visibility_targets": None
        }
        
        response = client.post(
            f"/admin/alerts?created_by={sample_data['admin'].id}",
            json=alert_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == alert_data["title"]
        assert data["message"] == alert_data["message"]
        assert data["severity"] == alert_data["severity"]
    
    def test_create_alert_non_admin(self, client, sample_data):
        """Test creating alert with non-admin user."""
        alert_data = {
            "title": "New Test Alert",
            "message": "This is a new test alert",
            "severity": "info",
            "delivery_type": "in_app",
            "visibility_type": "organization"
        }
        
        response = client.post(
            f"/admin/alerts?created_by={sample_data['user1'].id}",
            json=alert_data
        )
        
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]
    
    def test_list_alerts(self, client, sample_data):
        """Test listing alerts."""
        response = client.get(f"/admin/alerts?admin_id={sample_data['admin'].id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert len(data["alerts"]) >= 1
    
    def test_get_alert(self, client, sample_data):
        """Test getting a specific alert."""
        response = client.get(
            f"/admin/alerts/{sample_data['alert'].id}?admin_id={sample_data['admin'].id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_data['alert'].id
        assert data["title"] == sample_data['alert'].title
    
    def test_update_alert(self, client, sample_data):
        """Test updating an alert."""
        update_data = {
            "title": "Updated Alert Title",
            "severity": "critical"
        }
        
        response = client.put(
            f"/admin/alerts/{sample_data['alert'].id}?admin_id={sample_data['admin'].id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["severity"] == update_data["severity"]
    
    def test_archive_alert(self, client, sample_data):
        """Test archiving an alert."""
        response = client.delete(
            f"/admin/alerts/{sample_data['alert'].id}?admin_id={sample_data['admin'].id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "archived successfully" in data["message"]
        assert data["alert_id"] == sample_data['alert'].id
    
    def test_get_analytics_overview(self, client, sample_data):
        """Test getting analytics overview."""
        response = client.get(f"/admin/analytics/overview?admin_id={sample_data['admin'].id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "system_metrics" in data
        assert "delivery_metrics" in data
        assert "engagement_metrics" in data
    
    def test_get_alert_analytics(self, client, sample_data):
        """Test getting alert analytics."""
        response = client.get(
            f"/admin/analytics/alerts?admin_id={sample_data['admin'].id}&days=30"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "severity_breakdown" in data
        assert "status_breakdown" in data
        assert "daily_trend" in data
        assert data["period_days"] == 30
    
    def test_list_users(self, client, sample_data):
        """Test listing users."""
        response = client.get(f"/admin/users?admin_id={sample_data['admin'].id}")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # admin, user1, user2
    
    def test_list_teams(self, client, sample_data):
        """Test listing teams."""
        response = client.get(f"/admin/teams?admin_id={sample_data['admin'].id}")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the engineering team


class TestUserEndpoints:
    """Test user endpoints."""
    
    def test_get_user_dashboard(self, client, sample_data):
        """Test getting user dashboard."""
        response = client.get(f"/user/dashboard?user_id={sample_data['user1'].id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "active_alerts" in data
        assert "unread_count" in data
        assert "snoozed_count" in data
        assert "read_count" in data
        assert "total_alerts" in data
    
    def test_get_user_alerts(self, client, sample_data):
        """Test getting user alerts."""
        response = client.get(f"/user/alerts?user_id={sample_data['user1'].id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "total" in data
        assert "unread_count" in data
        assert "snoozed_count" in data
        assert "read_count" in data
    
    def test_get_user_profile(self, client, sample_data):
        """Test getting user profile."""
        response = client.get(f"/user/profile?user_id={sample_data['user1'].id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_data['user1'].id
        assert data["name"] == sample_data['user1'].name
        assert data["email"] == sample_data['user1'].email
    
    def test_get_user_stats(self, client, sample_data):
        """Test getting user statistics."""
        response = client.get(f"/user/stats?user_id={sample_data['user1'].id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "total_alerts" in data
        assert "read_alerts" in data
        assert "snoozed_alerts" in data
        assert "unread_alerts" in data
        assert "engagement_rate" in data
    
    def test_user_not_found(self, client):
        """Test user not found error."""
        response = client.get("/user/profile?user_id=999")
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


class TestAlertActions:
    """Test alert action endpoints."""
    
    def test_mark_alert_as_read_not_assigned(self, client, sample_data):
        """Test marking alert as read when not assigned to user."""
        response = client.post(
            f"/user/alerts/{sample_data['alert'].id}/read?user_id={sample_data['user1'].id}"
        )
        
        # Should fail because alert is not assigned to user yet
        assert response.status_code == 404
        assert "not assigned to user" in response.json()["detail"]
    
    def test_snooze_alert_not_assigned(self, client, sample_data):
        """Test snoozing alert when not assigned to user."""
        response = client.post(
            f"/user/alerts/{sample_data['alert'].id}/snooze?user_id={sample_data['user1'].id}"
        )
        
        # Should fail because alert is not assigned to user yet
        assert response.status_code == 404
        assert "not assigned to user" in response.json()["detail"]
    
    def test_get_alert_not_assigned(self, client, sample_data):
        """Test getting alert when not assigned to user."""
        response = client.get(
            f"/user/alerts/{sample_data['alert'].id}?user_id={sample_data['user1'].id}"
        )
        
        # Should fail because alert is not assigned to user yet
        assert response.status_code == 404
        assert "not found or not assigned to user" in response.json()["detail"]


class TestValidation:
    """Test input validation."""
    
    def test_create_alert_invalid_visibility(self, client, sample_data):
        """Test creating alert with invalid visibility configuration."""
        alert_data = {
            "title": "Test Alert",
            "message": "Test message",
            "severity": "info",
            "delivery_type": "in_app",
            "visibility_type": "team",
            "visibility_targets": []  # Empty targets for team visibility
        }
        
        response = client.post(
            f"/admin/alerts?created_by={sample_data['admin'].id}",
            json=alert_data
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_alert_invalid_team(self, client, sample_data):
        """Test creating alert with non-existent team."""
        alert_data = {
            "title": "Test Alert",
            "message": "Test message",
            "severity": "info",
            "delivery_type": "in_app",
            "visibility_type": "team",
            "visibility_targets": [999]  # Non-existent team
        }
        
        response = client.post(
            f"/admin/alerts?created_by={sample_data['admin'].id}",
            json=alert_data
        )
        
        assert response.status_code == 400
        assert "Team 999 not found" in response.json()["detail"]
    
    def test_pagination_validation(self, client, sample_data):
        """Test pagination parameter validation."""
        # Test invalid page number
        response = client.get(f"/admin/alerts?admin_id={sample_data['admin'].id}&page=0")
        assert response.status_code == 422
        
        # Test invalid per_page
        response = client.get(f"/admin/alerts?admin_id={sample_data['admin'].id}&per_page=101")
        assert response.status_code == 422