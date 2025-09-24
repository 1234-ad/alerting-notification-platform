# Alerting & Notification Platform

A lightweight, extensible alerting and notification system built with clean OOP design principles. This platform allows admins to create and manage alerts with configurable visibility, while providing users with persistent reminders and snooze functionality.

## Features

### Admin Features
- **Alert Management**: Create, update, and archive alerts with title, message, severity levels
- **Visibility Control**: Target entire organization, specific teams, or individual users
- **Reminder Configuration**: Set recurring reminders (default: every 2 hours)
- **Analytics Dashboard**: Track alert metrics and user engagement

### User Features
- **Smart Notifications**: Receive alerts based on visibility settings
- **Snooze Control**: Snooze alerts for the day (resets next day)
- **Alert Dashboard**: View active alerts, mark as read/unread
- **History Tracking**: Check snoozed and read alert history

### Technical Highlights
- **Clean OOP Design**: Strategy, Observer, and State patterns
- **Extensible Architecture**: Easy to add new delivery channels
- **Modular Structure**: Separation of concerns across components
- **Future-Ready**: Built for Email/SMS integration

## Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/1234-ad/alerting-notification-platform.git
cd alerting-notification-platform
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python scripts/init_db.py
```

4. Load seed data:
```bash
python scripts/seed_data.py
```

5. Start the application:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Documentation

### Admin Endpoints

#### Create Alert
```http
POST /admin/alerts
Content-Type: application/json

{
    "title": "System Maintenance",
    "message": "Scheduled maintenance tonight 10 PM - 2 AM",
    "severity": "warning",
    "delivery_type": "in_app",
    "visibility_type": "organization",
    "visibility_targets": [],
    "start_time": "2024-01-15T10:00:00Z",
    "expiry_time": "2024-01-16T02:00:00Z"
}
```

#### Update Alert
```http
PUT /admin/alerts/{alert_id}
```

#### List Alerts
```http
GET /admin/alerts?severity=warning&status=active
```

#### Get Analytics
```http
GET /admin/analytics
```

### User Endpoints

#### Get User Alerts
```http
GET /user/alerts
```

#### Mark Alert as Read
```http
POST /user/alerts/{alert_id}/read
```

#### Snooze Alert
```http
POST /user/alerts/{alert_id}/snooze
```

#### Get User Dashboard
```http
GET /user/dashboard
```

## Architecture

### Core Components

1. **Alert Management** (`src/models/alert.py`)
   - Alert creation and lifecycle management
   - Visibility and targeting logic

2. **Notification System** (`src/services/notification_service.py`)
   - Strategy pattern for delivery channels
   - Reminder scheduling and management

3. **User Preferences** (`src/models/user_alert_preference.py`)
   - State pattern for read/unread/snooze states
   - User-specific alert settings

4. **Analytics Engine** (`src/services/analytics_service.py`)
   - Metrics collection and reporting
   - Performance tracking

### Design Patterns Used

- **Strategy Pattern**: Pluggable notification channels (In-App, Email, SMS)
- **Observer Pattern**: User subscription to alerts
- **State Pattern**: Alert preference states (Read, Unread, Snoozed)
- **Factory Pattern**: Alert and notification creation

## Database Schema

### Core Tables
- `alerts`: Alert definitions and metadata
- `users`: User information and team assignments
- `teams`: Team definitions
- `notification_deliveries`: Delivery logs
- `user_alert_preferences`: User-specific alert states

## Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

Run with coverage:
```bash
python -m pytest tests/ --cov=src --cov-report=html
```

## Configuration

Environment variables (create `.env` file):
```env
DATABASE_URL=sqlite:///alerts.db
API_HOST=0.0.0.0
API_PORT=8000
REMINDER_INTERVAL_HOURS=2
LOG_LEVEL=INFO
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Future Enhancements

- Email and SMS delivery channels
- Customizable reminder frequencies
- Scheduled alerts with cron expressions
- Escalation workflows
- Role-based access control
- Push notification integration
- Mobile app support