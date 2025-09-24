"""
User API routes for alert consumption and management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import math

from src.database.database import get_db
from src.models.alert import Alert, AlertStatus
from src.models.user import User
from src.models.user_alert_preference import UserAlertPreference, AlertStateManager, AlertPreferenceState
from src.schemas.user_schemas import (
    UserResponse, UserAlertResponse, UserDashboardResponse,
    AlertActionRequest, AlertActionResponse, UserAlertListResponse,
    UserAlertFilterParams
)

user_router = APIRouter()


@user_router.get("/dashboard", response_model=UserDashboardResponse)
async def get_user_dashboard(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Get user dashboard with alert summary."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's active alerts with preferences
    active_alerts_query = db.query(Alert, UserAlertPreference).join(
        UserAlertPreference, Alert.id == UserAlertPreference.alert_id
    ).filter(
        UserAlertPreference.user_id == user_id,
        Alert.status == AlertStatus.ACTIVE
    )
    
    active_alerts_data = active_alerts_query.all()
    
    # Process alerts
    active_alerts = []
    unread_count = 0
    snoozed_count = 0
    read_count = 0
    
    for alert, preference in active_alerts_data:
        # Reset snooze if new day
        preference.reset_snooze_if_new_day()
        
        alert_response = UserAlertResponse(
            alert_id=alert.id,
            title=alert.title,
            message=alert.message,
            severity=alert.severity,
            start_time=alert.start_time.isoformat() if alert.start_time else None,
            expiry_time=alert.expiry_time.isoformat() if alert.expiry_time else None,
            created_by_name=alert.created_by_user.name if alert.created_by_user else None,
            state=preference.state,
            first_delivered_at=preference.first_delivered_at.isoformat() if preference.first_delivered_at else None,
            last_reminded_at=preference.last_reminded_at.isoformat() if preference.last_reminded_at else None,
            read_at=preference.read_at.isoformat() if preference.read_at else None,
            snoozed_at=preference.snoozed_at.isoformat() if preference.snoozed_at else None,
            snoozed_until=preference.snoozed_until.isoformat() if preference.snoozed_until else None
        )
        
        active_alerts.append(alert_response)
        
        # Count by state
        if preference.state == AlertPreferenceState.UNREAD:
            unread_count += 1
        elif preference.state == AlertPreferenceState.SNOOZED:
            snoozed_count += 1
        elif preference.state == AlertPreferenceState.READ:
            read_count += 1
    
    db.commit()  # Commit any snooze resets
    
    return UserDashboardResponse(
        user=UserResponse.model_validate(user.to_dict()),
        active_alerts=active_alerts,
        unread_count=unread_count,
        snoozed_count=snoozed_count,
        read_count=read_count,
        total_alerts=len(active_alerts)
    )


@user_router.get("/alerts", response_model=UserAlertListResponse)
async def get_user_alerts(
    user_id: int = Query(..., description="User ID"),
    state: Optional[str] = Query(None, description="Filter by state"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    include_expired: bool = Query(False, description="Include expired alerts"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get user's alerts with filtering and pagination."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build query
    query = db.query(Alert, UserAlertPreference).join(
        UserAlertPreference, Alert.id == UserAlertPreference.alert_id
    ).filter(UserAlertPreference.user_id == user_id)
    
    # Apply filters
    if not include_expired:
        query = query.filter(Alert.status == AlertStatus.ACTIVE)
    
    if state:
        query = query.filter(UserAlertPreference.state == state)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    alerts_data = query.offset(offset).limit(per_page).all()
    
    # Process alerts and count states
    alerts = []
    unread_count = 0
    snoozed_count = 0
    read_count = 0
    
    for alert, preference in alerts_data:
        # Reset snooze if new day
        preference.reset_snooze_if_new_day()
        
        alert_response = UserAlertResponse(
            alert_id=alert.id,
            title=alert.title,
            message=alert.message,
            severity=alert.severity,
            start_time=alert.start_time.isoformat() if alert.start_time else None,
            expiry_time=alert.expiry_time.isoformat() if alert.expiry_time else None,
            created_by_name=alert.created_by_user.name if alert.created_by_user else None,
            state=preference.state,
            first_delivered_at=preference.first_delivered_at.isoformat() if preference.first_delivered_at else None,
            last_reminded_at=preference.last_reminded_at.isoformat() if preference.last_reminded_at else None,
            read_at=preference.read_at.isoformat() if preference.read_at else None,
            snoozed_at=preference.snoozed_at.isoformat() if preference.snoozed_at else None,
            snoozed_until=preference.snoozed_until.isoformat() if preference.snoozed_until else None
        )
        
        alerts.append(alert_response)
        
        # Count by state (for all user's alerts, not just filtered)
        if preference.state == AlertPreferenceState.UNREAD:
            unread_count += 1
        elif preference.state == AlertPreferenceState.SNOOZED:
            snoozed_count += 1
        elif preference.state == AlertPreferenceState.READ:
            read_count += 1
    
    db.commit()  # Commit any snooze resets
    
    return UserAlertListResponse(
        alerts=alerts,
        total=total,
        unread_count=unread_count,
        snoozed_count=snoozed_count,
        read_count=read_count
    )


@user_router.post("/alerts/{alert_id}/read", response_model=AlertActionResponse)
async def mark_alert_as_read(
    alert_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Mark an alert as read."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get alert
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Get or create user preference
    preference = db.query(UserAlertPreference).filter(
        UserAlertPreference.user_id == user_id,
        UserAlertPreference.alert_id == alert_id
    ).first()
    
    if not preference:
        raise HTTPException(status_code=404, detail="Alert not assigned to user")
    
    # Use state manager to handle read action
    AlertStateManager.handle_read(preference)
    preference.updated_at = datetime.utcnow()
    
    db.commit()
    
    return AlertActionResponse(
        success=True,
        message="Alert marked as read",
        alert_id=alert_id,
        new_state=preference.state,
        action_timestamp=datetime.utcnow().isoformat()
    )


@user_router.post("/alerts/{alert_id}/unread", response_model=AlertActionResponse)
async def mark_alert_as_unread(
    alert_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Mark an alert as unread."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get alert
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Get user preference
    preference = db.query(UserAlertPreference).filter(
        UserAlertPreference.user_id == user_id,
        UserAlertPreference.alert_id == alert_id
    ).first()
    
    if not preference:
        raise HTTPException(status_code=404, detail="Alert not assigned to user")
    
    # Mark as unread
    preference.mark_as_unread()
    preference.updated_at = datetime.utcnow()
    
    db.commit()
    
    return AlertActionResponse(
        success=True,
        message="Alert marked as unread",
        alert_id=alert_id,
        new_state=preference.state,
        action_timestamp=datetime.utcnow().isoformat()
    )


@user_router.post("/alerts/{alert_id}/snooze", response_model=AlertActionResponse)
async def snooze_alert(
    alert_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Snooze an alert for the day."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get alert
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Get user preference
    preference = db.query(UserAlertPreference).filter(
        UserAlertPreference.user_id == user_id,
        UserAlertPreference.alert_id == alert_id
    ).first()
    
    if not preference:
        raise HTTPException(status_code=404, detail="Alert not assigned to user")
    
    # Use state manager to handle snooze action
    AlertStateManager.handle_snooze(preference)
    preference.updated_at = datetime.utcnow()
    
    db.commit()
    
    return AlertActionResponse(
        success=True,
        message=f"Alert snoozed until end of day ({preference.snoozed_until.strftime('%Y-%m-%d %H:%M:%S')} UTC)",
        alert_id=alert_id,
        new_state=preference.state,
        action_timestamp=datetime.utcnow().isoformat()
    )


@user_router.get("/alerts/{alert_id}", response_model=UserAlertResponse)
async def get_user_alert(
    alert_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Get a specific alert for the user."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get alert with preference
    result = db.query(Alert, UserAlertPreference).join(
        UserAlertPreference, Alert.id == UserAlertPreference.alert_id
    ).filter(
        Alert.id == alert_id,
        UserAlertPreference.user_id == user_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found or not assigned to user")
    
    alert, preference = result
    
    # Reset snooze if new day
    preference.reset_snooze_if_new_day()
    db.commit()
    
    return UserAlertResponse(
        alert_id=alert.id,
        title=alert.title,
        message=alert.message,
        severity=alert.severity,
        start_time=alert.start_time.isoformat() if alert.start_time else None,
        expiry_time=alert.expiry_time.isoformat() if alert.expiry_time else None,
        created_by_name=alert.created_by_user.name if alert.created_by_user else None,
        state=preference.state,
        first_delivered_at=preference.first_delivered_at.isoformat() if preference.first_delivered_at else None,
        last_reminded_at=preference.last_reminded_at.isoformat() if preference.last_reminded_at else None,
        read_at=preference.read_at.isoformat() if preference.read_at else None,
        snoozed_at=preference.snoozed_at.isoformat() if preference.snoozed_at else None,
        snoozed_until=preference.snoozed_until.isoformat() if preference.snoozed_until else None
    )


@user_router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Get user profile information."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse.model_validate(user.to_dict())


@user_router.get("/stats")
async def get_user_stats(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Get user-specific statistics."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's alert statistics
    total_alerts = db.query(UserAlertPreference).filter(
        UserAlertPreference.user_id == user_id
    ).count()
    
    read_alerts = db.query(UserAlertPreference).filter(
        UserAlertPreference.user_id == user_id,
        UserAlertPreference.state == AlertPreferenceState.READ
    ).count()
    
    snoozed_alerts = db.query(UserAlertPreference).filter(
        UserAlertPreference.user_id == user_id,
        UserAlertPreference.state == AlertPreferenceState.SNOOZED
    ).count()
    
    unread_alerts = db.query(UserAlertPreference).filter(
        UserAlertPreference.user_id == user_id,
        UserAlertPreference.state == AlertPreferenceState.UNREAD
    ).count()
    
    # Calculate engagement rate
    engagement_rate = (read_alerts / total_alerts * 100) if total_alerts > 0 else 0
    
    return {
        "user_id": user_id,
        "total_alerts": total_alerts,
        "read_alerts": read_alerts,
        "snoozed_alerts": snoozed_alerts,
        "unread_alerts": unread_alerts,
        "engagement_rate": round(engagement_rate, 2)
    }