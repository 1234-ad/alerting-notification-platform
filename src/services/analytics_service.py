"""
Analytics service for tracking alert metrics and user engagement.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from src.models.alert import Alert, AlertSeverity, AlertStatus
from src.models.user import User
from src.models.team import Team
from src.models.notification_delivery import NotificationDelivery, DeliveryStatus
from src.models.user_alert_preference import UserAlertPreference, AlertPreferenceState
from src.database.database import get_db_session


class AnalyticsService:
    """Service for generating analytics and metrics."""
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide overview metrics."""
        with get_db_session() as db:
            # Basic counts
            total_alerts = db.query(Alert).count()
            active_alerts = db.query(Alert).filter(Alert.status == AlertStatus.ACTIVE).count()
            total_users = db.query(User).count()
            total_teams = db.query(Team).count()
            
            # Delivery metrics
            total_deliveries = db.query(NotificationDelivery).count()
            successful_deliveries = db.query(NotificationDelivery).filter(
                NotificationDelivery.status == DeliveryStatus.DELIVERED
            ).count()
            
            # User engagement
            read_alerts = db.query(UserAlertPreference).filter(
                UserAlertPreference.state == AlertPreferenceState.READ
            ).count()
            snoozed_alerts = db.query(UserAlertPreference).filter(
                UserAlertPreference.state == AlertPreferenceState.SNOOZED
            ).count()
            
            return {
                "system_metrics": {
                    "total_alerts": total_alerts,
                    "active_alerts": active_alerts,
                    "total_users": total_users,
                    "total_teams": total_teams
                },
                "delivery_metrics": {
                    "total_deliveries": total_deliveries,
                    "successful_deliveries": successful_deliveries,
                    "delivery_success_rate": (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
                },
                "engagement_metrics": {
                    "read_alerts": read_alerts,
                    "snoozed_alerts": snoozed_alerts,
                    "total_preferences": read_alerts + snoozed_alerts
                }
            }
    
    def get_alert_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get alert-specific metrics for the last N days."""
        with get_db_session() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Alerts by severity
            severity_counts = db.query(
                Alert.severity,
                func.count(Alert.id).label('count')
            ).filter(
                Alert.created_at >= cutoff_date
            ).group_by(Alert.severity).all()
            
            severity_breakdown = {
                AlertSeverity.INFO: 0,
                AlertSeverity.WARNING: 0,
                AlertSeverity.CRITICAL: 0
            }
            
            for severity, count in severity_counts:
                severity_breakdown[severity] = count
            
            # Alerts by status
            status_counts = db.query(
                Alert.status,
                func.count(Alert.id).label('count')
            ).filter(
                Alert.created_at >= cutoff_date
            ).group_by(Alert.status).all()
            
            status_breakdown = {status: count for status, count in status_counts}
            
            # Daily alert creation trend
            daily_alerts = db.query(
                func.date(Alert.created_at).label('date'),
                func.count(Alert.id).label('count')
            ).filter(
                Alert.created_at >= cutoff_date
            ).group_by(func.date(Alert.created_at)).order_by('date').all()
            
            daily_trend = [
                {
                    "date": date.isoformat(),
                    "count": count
                }
                for date, count in daily_alerts
            ]
            
            return {
                "period_days": days,
                "severity_breakdown": severity_breakdown,
                "status_breakdown": status_breakdown,
                "daily_trend": daily_trend
            }
    
    def get_user_engagement_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get user engagement metrics."""
        with get_db_session() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # User preference states
            preference_states = db.query(
                UserAlertPreference.state,
                func.count(UserAlertPreference.id).label('count')
            ).join(Alert).filter(
                Alert.created_at >= cutoff_date
            ).group_by(UserAlertPreference.state).all()
            
            state_breakdown = {
                AlertPreferenceState.UNREAD: 0,
                AlertPreferenceState.READ: 0,
                AlertPreferenceState.SNOOZED: 0
            }
            
            for state, count in preference_states:
                state_breakdown[state] = count
            
            # Most engaged users (by read alerts)
            top_users = db.query(
                User.name,
                User.email,
                func.count(UserAlertPreference.id).label('read_count')
            ).join(UserAlertPreference).join(Alert).filter(
                UserAlertPreference.state == AlertPreferenceState.READ,
                Alert.created_at >= cutoff_date
            ).group_by(User.id, User.name, User.email).order_by(
                func.count(UserAlertPreference.id).desc()
            ).limit(10).all()
            
            # Users with most snoozed alerts
            top_snoozers = db.query(
                User.name,
                User.email,
                func.count(UserAlertPreference.id).label('snooze_count')
            ).join(UserAlertPreference).join(Alert).filter(
                UserAlertPreference.state == AlertPreferenceState.SNOOZED,
                Alert.created_at >= cutoff_date
            ).group_by(User.id, User.name, User.email).order_by(
                func.count(UserAlertPreference.id).desc()
            ).limit(10).all()
            
            return {
                "period_days": days,
                "state_breakdown": state_breakdown,
                "top_engaged_users": [
                    {
                        "name": name,
                        "email": email,
                        "read_count": count
                    }
                    for name, email, count in top_users
                ],
                "top_snoozing_users": [
                    {
                        "name": name,
                        "email": email,
                        "snooze_count": count
                    }
                    for name, email, count in top_snoozers
                ]
            }
    
    def get_delivery_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get delivery performance metrics."""
        with get_db_session() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Delivery status breakdown
            delivery_statuses = db.query(
                NotificationDelivery.status,
                func.count(NotificationDelivery.id).label('count')
            ).filter(
                NotificationDelivery.created_at >= cutoff_date
            ).group_by(NotificationDelivery.status).all()
            
            status_breakdown = {status: count for status, count in delivery_statuses}
            
            # Delivery type breakdown
            delivery_types = db.query(
                NotificationDelivery.delivery_type,
                func.count(NotificationDelivery.id).label('count')
            ).filter(
                NotificationDelivery.created_at >= cutoff_date
            ).group_by(NotificationDelivery.delivery_type).all()
            
            type_breakdown = {delivery_type: count for delivery_type, count in delivery_types}
            
            # Daily delivery volume
            daily_deliveries = db.query(
                func.date(NotificationDelivery.created_at).label('date'),
                func.count(NotificationDelivery.id).label('count')
            ).filter(
                NotificationDelivery.created_at >= cutoff_date
            ).group_by(func.date(NotificationDelivery.created_at)).order_by('date').all()
            
            daily_volume = [
                {
                    "date": date.isoformat(),
                    "count": count
                }
                for date, count in daily_deliveries
            ]
            
            # Average delivery attempts
            avg_attempts = db.query(
                func.avg(NotificationDelivery.attempt_count)
            ).filter(
                NotificationDelivery.created_at >= cutoff_date
            ).scalar() or 0
            
            return {
                "period_days": days,
                "status_breakdown": status_breakdown,
                "type_breakdown": type_breakdown,
                "daily_volume": daily_volume,
                "average_attempts": round(avg_attempts, 2)
            }
    
    def get_alert_performance(self, alert_id: int) -> Dict[str, Any]:
        """Get performance metrics for a specific alert."""
        with get_db_session() as db:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return {"error": "Alert not found"}
            
            # Basic alert info
            alert_info = alert.to_dict()
            
            # Delivery stats
            total_deliveries = db.query(NotificationDelivery).filter(
                NotificationDelivery.alert_id == alert_id
            ).count()
            
            successful_deliveries = db.query(NotificationDelivery).filter(
                NotificationDelivery.alert_id == alert_id,
                NotificationDelivery.status == DeliveryStatus.DELIVERED
            ).count()
            
            # User engagement stats
            total_preferences = db.query(UserAlertPreference).filter(
                UserAlertPreference.alert_id == alert_id
            ).count()
            
            read_count = db.query(UserAlertPreference).filter(
                UserAlertPreference.alert_id == alert_id,
                UserAlertPreference.state == AlertPreferenceState.READ
            ).count()
            
            snoozed_count = db.query(UserAlertPreference).filter(
                UserAlertPreference.alert_id == alert_id,
                UserAlertPreference.state == AlertPreferenceState.SNOOZED
            ).count()
            
            # Calculate rates
            delivery_rate = (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
            read_rate = (read_count / total_preferences * 100) if total_preferences > 0 else 0
            snooze_rate = (snoozed_count / total_preferences * 100) if total_preferences > 0 else 0
            
            return {
                "alert": alert_info,
                "delivery_metrics": {
                    "total_deliveries": total_deliveries,
                    "successful_deliveries": successful_deliveries,
                    "delivery_rate": round(delivery_rate, 2)
                },
                "engagement_metrics": {
                    "total_users_targeted": total_preferences,
                    "read_count": read_count,
                    "snoozed_count": snoozed_count,
                    "read_rate": round(read_rate, 2),
                    "snooze_rate": round(snooze_rate, 2)
                }
            }
    
    def get_team_metrics(self, team_id: Optional[int] = None) -> Dict[str, Any]:
        """Get metrics by team."""
        with get_db_session() as db:
            if team_id:
                teams = [db.query(Team).filter(Team.id == team_id).first()]
                if not teams[0]:
                    return {"error": "Team not found"}
            else:
                teams = db.query(Team).all()
            
            team_metrics = []
            
            for team in teams:
                if not team:
                    continue
                
                # Get team member IDs
                member_ids = team.get_member_ids()
                
                if not member_ids:
                    team_metrics.append({
                        "team": team.to_dict(),
                        "alerts_received": 0,
                        "alerts_read": 0,
                        "alerts_snoozed": 0,
                        "engagement_rate": 0
                    })
                    continue
                
                # Count alerts received by team members
                alerts_received = db.query(UserAlertPreference).filter(
                    UserAlertPreference.user_id.in_(member_ids)
                ).count()
                
                alerts_read = db.query(UserAlertPreference).filter(
                    UserAlertPreference.user_id.in_(member_ids),
                    UserAlertPreference.state == AlertPreferenceState.READ
                ).count()
                
                alerts_snoozed = db.query(UserAlertPreference).filter(
                    UserAlertPreference.user_id.in_(member_ids),
                    UserAlertPreference.state == AlertPreferenceState.SNOOZED
                ).count()
                
                engagement_rate = (alerts_read / alerts_received * 100) if alerts_received > 0 else 0
                
                team_metrics.append({
                    "team": team.to_dict(),
                    "alerts_received": alerts_received,
                    "alerts_read": alerts_read,
                    "alerts_snoozed": alerts_snoozed,
                    "engagement_rate": round(engagement_rate, 2)
                })
            
            return {
                "team_metrics": team_metrics
            }


# Singleton instance
analytics_service = AnalyticsService()