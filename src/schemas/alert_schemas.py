"""
Pydantic schemas for alert-related API requests and responses.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from src.models.alert import AlertSeverity, DeliveryType, VisibilityType, AlertStatus


class AlertCreateRequest(BaseModel):
    """Schema for creating a new alert."""
    
    title: str = Field(..., min_length=1, max_length=200, description="Alert title")
    message: str = Field(..., min_length=1, description="Alert message body")
    severity: AlertSeverity = Field(default=AlertSeverity.INFO, description="Alert severity level")
    delivery_type: DeliveryType = Field(default=DeliveryType.IN_APP, description="Delivery channel")
    visibility_type: VisibilityType = Field(..., description="Visibility scope")
    visibility_targets: Optional[List[int]] = Field(default=None, description="Target team/user IDs")
    start_time: Optional[datetime] = Field(default=None, description="Alert start time")
    expiry_time: Optional[datetime] = Field(default=None, description="Alert expiry time")
    reminder_interval_hours: int = Field(default=2, ge=1, le=24, description="Reminder interval in hours")
    reminders_enabled: bool = Field(default=True, description="Enable reminders")
    
    @validator('visibility_targets')
    def validate_visibility_targets(cls, v, values):
        """Validate visibility targets based on visibility type."""
        visibility_type = values.get('visibility_type')
        
        if visibility_type == VisibilityType.ORGANIZATION:
            if v is not None and len(v) > 0:
                raise ValueError("Organization visibility should not have targets")
        elif visibility_type in [VisibilityType.TEAM, VisibilityType.USER]:
            if not v or len(v) == 0:
                raise ValueError(f"{visibility_type.value} visibility requires targets")
        
        return v
    
    @validator('expiry_time')
    def validate_expiry_time(cls, v, values):
        """Validate expiry time is after start time."""
        start_time = values.get('start_time')
        if v and start_time and v <= start_time:
            raise ValueError("Expiry time must be after start time")
        return v


class AlertUpdateRequest(BaseModel):
    """Schema for updating an existing alert."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    message: Optional[str] = Field(None, min_length=1)
    severity: Optional[AlertSeverity] = None
    expiry_time: Optional[datetime] = None
    reminder_interval_hours: Optional[int] = Field(None, ge=1, le=24)
    reminders_enabled: Optional[bool] = None
    status: Optional[AlertStatus] = None


class AlertResponse(BaseModel):
    """Schema for alert response."""
    
    id: int
    title: str
    message: str
    severity: str
    delivery_type: str
    visibility_type: str
    visibility_targets: Optional[List[int]]
    start_time: Optional[str]
    expiry_time: Optional[str]
    reminder_interval_hours: int
    reminders_enabled: bool
    status: str
    created_by: int
    created_by_name: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Schema for alert list response."""
    
    alerts: List[AlertResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class AlertFilterParams(BaseModel):
    """Schema for alert filtering parameters."""
    
    severity: Optional[AlertSeverity] = None
    status: Optional[AlertStatus] = None
    visibility_type: Optional[VisibilityType] = None
    created_by: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=100)


class NotificationResult(BaseModel):
    """Schema for notification delivery result."""
    
    total_users: int
    successful_deliveries: int
    failed_deliveries: int
    delivery_details: List[Dict[str, Any]]


class AlertPerformanceResponse(BaseModel):
    """Schema for alert performance metrics."""
    
    alert: AlertResponse
    delivery_metrics: Dict[str, Any]
    engagement_metrics: Dict[str, Any]