"""
Team model and related functionality.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List

from src.database.database import Base


class Team(Base):
    """Team model representing organizational teams."""
    
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = relationship("User", back_populates="team")
    
    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}')>"
    
    def to_dict(self) -> dict:
        """Convert team to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "member_count": len(self.members) if self.members else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_member_ids(self) -> List[int]:
        """Get list of member IDs."""
        return [member.id for member in self.members] if self.members else []