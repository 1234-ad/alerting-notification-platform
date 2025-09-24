"""
Pydantic schemas for user-related API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.models.user_alert_preference import AlertPreferenceState


class UserResponse(BaseModel):
    """Schema for user response."""
    
    id: int
    name: str
    email: str
    team_id: Optional[int]
    team_name: Optional[str]
    is_admin: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class TeamResponse(BaseModel):
    """Schema for team response."""
    
    id: int
    name: str
    description: Optional[str]
    member_count: int
    created_at: Optional[str]
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class UserAlertResponse(BaseModel):
    """Schema for user alert with preference state."""
    
    alert_id: int
    title: str
    message: str
    severity: str
    start_time: Optional[str]
    expiry_time: Optional[str]
    created_by_name: Optional[str]
    state: str
    first_delivered_at: Optional[str]
    last_reminded_at: Optional[str]
    read_at: Optional[str]
    snoozed_at: Optional[str]
    snoozed_until: Optional[str]
    
    class Config:
        from_attributes = True


class UserDashboardResponse(BaseModel):
    """Schema for user dashboard data."""
    
    user: UserResponse
    active_alerts: List[UserAlertResponse]
    unread_count: int
    snoozed_count: int
    read_count: int
    total_alerts: int


class AlertActionRequest(BaseModel):
    """Schema for alert actions (read/snooze)."""
    
    action: str = Field(..., regex="^(read|unread|snooze)$")


class AlertActionResponse(BaseModel):
    """Schema for alert action response."""
    
    success: bool
    message: str
    alert_id: int
    new_state: str
    action_timestamp: str


class UserPreferenceResponse(BaseModel):
    """Schema for user alert preference."""
    
    id: int
    user_id: int
    alert_id: int
    state: str
    first_delivered_at: Optional[str]
    last_reminded_at: Optional[str]
    read_at: Optional[str]
    snoozed_at: Optional[str]
    snoozed_until: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class UserAlertListResponse(BaseModel):
    """Schema for user alert list response."""
    
    alerts: List[UserAlertResponse]
    total: int
    unread_count: int
    snoozed_count: int
    read_count: int


class UserAlertFilterParams(BaseModel):
    """Schema for user alert filtering parameters."""
    
    state: Optional[AlertPreferenceState] = None
    severity: Optional[str] = None
    include_expired: bool = Field(default=False)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=100)