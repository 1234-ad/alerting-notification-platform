"""
Admin API routes for alert management and analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import math

from src.database.database import get_db
from src.models.alert import Alert, AlertStatus
from src.models.user import User
from src.models.team import Team
from src.schemas.alert_schemas import (
    AlertCreateRequest, AlertUpdateRequest, AlertResponse, 
    AlertListResponse, AlertFilterParams, NotificationResult,
    AlertPerformanceResponse
)
from src.services.notification_service import alert_subject
from src.services.analytics_service import analytics_service
from src.services.reminder_service import reminder_service

admin_router = APIRouter()


@admin_router.post("/alerts", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertCreateRequest,
    created_by: int = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """Create a new alert."""
    # Verify admin user exists
    admin_user = db.query(User).filter(User.id == created_by, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate visibility targets
    if alert_data.visibility_type == "team" and alert_data.visibility_targets:
        for team_id in alert_data.visibility_targets:
            team = db.query(Team).filter(Team.id == team_id).first()
            if not team:
                raise HTTPException(status_code=400, detail=f"Team {team_id} not found")
    
    elif alert_data.visibility_type == "user" and alert_data.visibility_targets:
        for user_id in alert_data.visibility_targets:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=400, detail=f"User {user_id} not found")
    
    # Create alert
    alert = Alert(
        title=alert_data.title,
        message=alert_data.message,
        severity=alert_data.severity,
        delivery_type=alert_data.delivery_type,
        visibility_type=alert_data.visibility_type,
        visibility_targets=alert_data.visibility_targets,
        start_time=alert_data.start_time or datetime.utcnow(),
        expiry_time=alert_data.expiry_time,
        reminder_interval_hours=alert_data.reminder_interval_hours,
        reminders_enabled=alert_data.reminders_enabled,
        created_by=created_by
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    # Notify observers (triggers initial notifications)
    alert_subject.notify_alert_created(alert)
    
    return AlertResponse.model_validate(alert.to_dict())


@admin_router.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_data: AlertUpdateRequest,
    admin_id: int = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """Update an existing alert."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get alert
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Update fields
    update_data = alert_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)
    
    alert.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    
    # Notify observers
    alert_subject.notify_alert_updated(alert)
    
    return AlertResponse.model_validate(alert.to_dict())


@admin_router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    admin_id: int = Query(..., description="Admin user ID"),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    visibility_type: Optional[str] = Query(None),
    created_by: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List alerts with filtering."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Build query
    query = db.query(Alert)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    if status:
        query = query.filter(Alert.status == status)
    if visibility_type:
        query = query.filter(Alert.visibility_type == visibility_type)
    if created_by:
        query = query.filter(Alert.created_by == created_by)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    alerts = query.offset(offset).limit(per_page).all()
    
    # Convert to response format
    alert_responses = [AlertResponse.model_validate(alert.to_dict()) for alert in alerts]
    
    return AlertListResponse(
        alerts=alert_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page)
    )


@admin_router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    admin_id: int = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """Get a specific alert."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertResponse.model_validate(alert.to_dict())


@admin_router.delete("/alerts/{alert_id}")
async def archive_alert(
    alert_id: int,
    admin_id: int = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """Archive an alert."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = AlertStatus.ARCHIVED
    alert.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Alert archived successfully", "alert_id": alert_id}


@admin_router.post("/alerts/{alert_id}/send-reminder", response_model=NotificationResult)
async def send_immediate_reminder(
    alert_id: int,
    admin_id: int = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """Send immediate reminder for an alert (for testing/admin use)."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = reminder_service.send_immediate_reminder(alert_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return NotificationResult.model_validate(result)


@admin_router.get("/analytics/overview")
async def get_analytics_overview(
    admin_id: int = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """Get system-wide analytics overview."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return analytics_service.get_system_overview()


@admin_router.get("/analytics/alerts")
async def get_alert_analytics(
    admin_id: int = Query(..., description="Admin user ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get alert-specific analytics."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return analytics_service.get_alert_metrics(days)


@admin_router.get("/analytics/engagement")
async def get_engagement_analytics(
    admin_id: int = Query(..., description="Admin user ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get user engagement analytics."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return analytics_service.get_user_engagement_metrics(days)


@admin_router.get("/analytics/delivery")
async def get_delivery_analytics(
    admin_id: int = Query(..., description="Admin user ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get delivery performance analytics."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return analytics_service.get_delivery_metrics(days)


@admin_router.get("/analytics/alerts/{alert_id}/performance", response_model=AlertPerformanceResponse)
async def get_alert_performance(
    alert_id: int,
    admin_id: int = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """Get performance metrics for a specific alert."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = analytics_service.get_alert_performance(alert_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return AlertPerformanceResponse.model_validate(result)


@admin_router.get("/analytics/teams")
async def get_team_analytics(
    admin_id: int = Query(..., description="Admin user ID"),
    team_id: Optional[int] = Query(None, description="Specific team ID"),
    db: Session = Depends(get_db)
):
    """Get team-specific analytics."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = analytics_service.get_team_metrics(team_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@admin_router.get("/reminder-service/stats")
async def get_reminder_service_stats(
    admin_id: int = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """Get reminder service statistics."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return reminder_service.get_reminder_stats()


@admin_router.get("/users", response_model=List[dict])
async def list_users(
    admin_id: int = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """List all users (for admin reference)."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = db.query(User).all()
    return [user.to_dict() for user in users]


@admin_router.get("/teams", response_model=List[dict])
async def list_teams(
    admin_id: int = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """List all teams (for admin reference)."""
    # Verify admin user
    admin_user = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    teams = db.query(Team).all()
    return [team.to_dict() for team in teams]