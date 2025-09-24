#!/usr/bin/env python3
"""
Seed data script for testing and demonstration.
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.database import get_db_session
from src.models.user import User
from src.models.team import Team
from src.models.alert import Alert, AlertSeverity, DeliveryType, VisibilityType
from src.services.notification_service import alert_subject

def create_teams():
    """Create sample teams."""
    teams_data = [
        {
            "name": "Engineering",
            "description": "Software development and technical operations team"
        },
        {
            "name": "Marketing", 
            "description": "Marketing and growth team"
        },
        {
            "name": "Sales",
            "description": "Sales and business development team"
        },
        {
            "name": "Support",
            "description": "Customer support and success team"
        },
        {
            "name": "Operations",
            "description": "Business operations and administration team"
        }
    ]
    
    teams = []
    with get_db_session() as db:
        for team_data in teams_data:
            # Check if team already exists
            existing_team = db.query(Team).filter(Team.name == team_data["name"]).first()
            if existing_team:
                teams.append(existing_team)
                continue
                
            team = Team(**team_data)
            db.add(team)
            db.flush()
            teams.append(team)
            print(f"📁 Created team: {team.name}")
    
    return teams

def create_users(teams):
    """Create sample users."""
    users_data = [
        # Admin users
        {
            "name": "Alice Admin",
            "email": "alice@company.com",
            "team_id": teams[0].id,  # Engineering
            "is_admin": True
        },
        {
            "name": "Bob Manager",
            "email": "bob@company.com", 
            "team_id": teams[1].id,  # Marketing
            "is_admin": True
        },
        
        # Engineering team
        {
            "name": "Charlie Developer",
            "email": "charlie@company.com",
            "team_id": teams[0].id,
            "is_admin": False
        },
        {
            "name": "Diana Engineer",
            "email": "diana@company.com",
            "team_id": teams[0].id,
            "is_admin": False
        },
        {
            "name": "Eve DevOps",
            "email": "eve@company.com",
            "team_id": teams[0].id,
            "is_admin": False
        },
        
        # Marketing team
        {
            "name": "Frank Marketer",
            "email": "frank@company.com",
            "team_id": teams[1].id,
            "is_admin": False
        },
        {
            "name": "Grace Designer",
            "email": "grace@company.com",
            "team_id": teams[1].id,
            "is_admin": False
        },
        
        # Sales team
        {
            "name": "Henry Sales",
            "email": "henry@company.com",
            "team_id": teams[2].id,
            "is_admin": False
        },
        {
            "name": "Ivy Account",
            "email": "ivy@company.com",
            "team_id": teams[2].id,
            "is_admin": False
        },
        
        # Support team
        {
            "name": "Jack Support",
            "email": "jack@company.com",
            "team_id": teams[3].id,
            "is_admin": False
        },
        {
            "name": "Kate Success",
            "email": "kate@company.com",
            "team_id": teams[3].id,
            "is_admin": False
        },
        
        # Operations team
        {
            "name": "Leo Operations",
            "email": "leo@company.com",
            "team_id": teams[4].id,
            "is_admin": False
        }
    ]
    
    users = []
    with get_db_session() as db:
        for user_data in users_data:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            if existing_user:
                users.append(existing_user)
                continue
                
            user = User(**user_data)
            db.add(user)
            db.flush()
            users.append(user)
            print(f"👤 Created user: {user.name} ({user.email}) - {'Admin' if user.is_admin else 'User'}")
    
    return users

def create_sample_alerts(users, teams):
    """Create sample alerts for demonstration."""
    now = datetime.utcnow()
    
    alerts_data = [
        # Organization-wide alerts
        {
            "title": "System Maintenance Scheduled",
            "message": "Scheduled maintenance will occur tonight from 10 PM to 2 AM EST. Some services may be temporarily unavailable.",
            "severity": AlertSeverity.WARNING,
            "delivery_type": DeliveryType.IN_APP,
            "visibility_type": VisibilityType.ORGANIZATION,
            "visibility_targets": None,
            "start_time": now,
            "expiry_time": now + timedelta(days=1),
            "created_by": users[0].id  # Alice Admin
        },
        {
            "title": "New Security Policy",
            "message": "Please review the updated security policy in the company handbook. All employees must acknowledge by end of week.",
            "severity": AlertSeverity.INFO,
            "delivery_type": DeliveryType.IN_APP,
            "visibility_type": VisibilityType.ORGANIZATION,
            "visibility_targets": None,
            "start_time": now,
            "expiry_time": now + timedelta(days=7),
            "created_by": users[1].id  # Bob Manager
        },
        
        # Team-specific alerts
        {
            "title": "Code Review Required",
            "message": "Several pull requests are pending review. Please prioritize code reviews to maintain development velocity.",
            "severity": AlertSeverity.WARNING,
            "delivery_type": DeliveryType.IN_APP,
            "visibility_type": VisibilityType.TEAM,
            "visibility_targets": [teams[0].id],  # Engineering
            "start_time": now,
            "expiry_time": now + timedelta(days=2),
            "created_by": users[0].id  # Alice Admin
        },
        {
            "title": "Marketing Campaign Launch",
            "message": "Q4 marketing campaign launches tomorrow. All marketing materials should be finalized today.",
            "severity": AlertSeverity.CRITICAL,
            "delivery_type": DeliveryType.IN_APP,
            "visibility_type": VisibilityType.TEAM,
            "visibility_targets": [teams[1].id],  # Marketing
            "start_time": now,
            "expiry_time": now + timedelta(days=1),
            "created_by": users[1].id  # Bob Manager
        },
        {
            "title": "Sales Target Update",
            "message": "Monthly sales targets have been updated. Please check your individual goals in the sales dashboard.",
            "severity": AlertSeverity.INFO,
            "delivery_type": DeliveryType.IN_APP,
            "visibility_type": VisibilityType.TEAM,
            "visibility_targets": [teams[2].id],  # Sales
            "start_time": now,
            "expiry_time": now + timedelta(days=5),
            "created_by": users[0].id  # Alice Admin
        },
        
        # Multi-team alerts
        {
            "title": "Customer Support Escalation",
            "message": "High-priority customer issue requires immediate attention from both Support and Engineering teams.",
            "severity": AlertSeverity.CRITICAL,
            "delivery_type": DeliveryType.IN_APP,
            "visibility_type": VisibilityType.TEAM,
            "visibility_targets": [teams[0].id, teams[3].id],  # Engineering + Support
            "start_time": now,
            "expiry_time": now + timedelta(hours=8),
            "created_by": users[1].id  # Bob Manager
        },
        
        # User-specific alerts
        {
            "title": "Performance Review Reminder",
            "message": "Your quarterly performance review is scheduled for next week. Please complete your self-assessment.",
            "severity": AlertSeverity.INFO,
            "delivery_type": DeliveryType.IN_APP,
            "visibility_type": VisibilityType.USER,
            "visibility_targets": [users[2].id, users[3].id, users[4].id],  # Some engineering users
            "start_time": now,
            "expiry_time": now + timedelta(days=10),
            "created_by": users[0].id  # Alice Admin
        },
        
        # Expired alert (for testing)
        {
            "title": "Expired Test Alert",
            "message": "This alert has already expired and should not send reminders.",
            "severity": AlertSeverity.INFO,
            "delivery_type": DeliveryType.IN_APP,
            "visibility_type": VisibilityType.ORGANIZATION,
            "visibility_targets": None,
            "start_time": now - timedelta(days=2),
            "expiry_time": now - timedelta(hours=1),  # Expired 1 hour ago
            "created_by": users[0].id  # Alice Admin
        }
    ]
    
    alerts = []
    with get_db_session() as db:
        for alert_data in alerts_data:
            # Check if similar alert already exists
            existing_alert = db.query(Alert).filter(Alert.title == alert_data["title"]).first()
            if existing_alert:
                alerts.append(existing_alert)
                continue
                
            alert = Alert(**alert_data)
            db.add(alert)
            db.flush()
            alerts.append(alert)
            print(f"🚨 Created alert: {alert.title} ({alert.severity}) - {alert.visibility_type}")
            
            # Trigger notifications for the alert
            alert_subject.notify_alert_created(alert)
    
    return alerts

def main():
    """Main seeding function."""
    print("🌱 Seeding database with sample data...")
    
    try:
        # Create teams first
        print("\n📁 Creating teams...")
        teams = create_teams()
        
        # Create users
        print("\n👥 Creating users...")
        users = create_users(teams)
        
        # Create sample alerts
        print("\n🚨 Creating sample alerts...")
        alerts = create_sample_alerts(users, teams)
        
        print(f"\n✅ Seeding completed successfully!")
        print(f"📊 Created:")
        print(f"   - {len(teams)} teams")
        print(f"   - {len(users)} users ({len([u for u in users if u.is_admin])} admins)")
        print(f"   - {len(alerts)} alerts")
        
        print(f"\n🔑 Admin users for testing:")
        for user in users:
            if user.is_admin:
                print(f"   - {user.name} (ID: {user.id}, Email: {user.email})")
        
        print(f"\n💡 You can now:")
        print(f"   - Start the API server: python main.py")
        print(f"   - Access API docs: http://localhost:8000/docs")
        print(f"   - Test admin endpoints with admin user IDs")
        print(f"   - Test user endpoints with any user ID")
        
    except Exception as e:
        print(f"❌ Error seeding database: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()