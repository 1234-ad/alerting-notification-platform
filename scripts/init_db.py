#!/usr/bin/env python3
"""
Database initialization script.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.database import init_db

def main():
    """Initialize the database."""
    print("🔧 Initializing database...")
    
    try:
        init_db()
        print("✅ Database initialized successfully!")
        print("📊 Tables created:")
        print("   - users")
        print("   - teams") 
        print("   - alerts")
        print("   - notification_deliveries")
        print("   - user_alert_preferences")
        
    except Exception as e:
        print(f"❌ Error initializing database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()