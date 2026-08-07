"""
SQLAlchemy models for HabeshaFit.
Minimal, clean schema with proper relationships.
"""
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.database import Base


class UserRole(str, enum.Enum):
    """User roles in the system."""
    CLIENT = "client"
    DESIGNER = "designer"
    ADMIN = "admin"


class RequestStatus(str, enum.Enum):
    """Outfit request statuses."""
    PENDING = "pending"
    MATCHING = "matching"
    OFFERS_RECEIVED = "offers_received"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OfferStatus(str, enum.Enum):
    """Offer statuses."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderStatus(str, enum.Enum):
    """Order lifecycle statuses."""
    PENDING_DEPOSIT = "pending_deposit"
    DEPOSIT_PAID = "deposit_paid"
    IN_PROGRESS = "in_progress"
    MEASUREMENTS_SUBMITTED = "measurements_submitted"
    READY_FOR_PICKUP = "ready_for_pickup"
    COMPLETED = "completed"
    DISPUTED = "disputed"


class User(Base):
    """Users table - both clients and designers."""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.CLIENT)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    requests = relationship("OutfitRequest", back_populates="client", cascade="all, delete-orphan")
    offers = relationship("Offer", back_populates="designer", cascade="all, delete-orphan")
    orders_as_client = relationship("Order", foreign_keys="Order.client_id", back_populates="client")
    orders_as_designer = relationship("Order", foreign_keys="Order.designer_id", back_populates="designer")


class DesignerProfile(Base):
    """Extended profile data for designers."""
    __tablename__ = "designer_profiles"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    business_name = Column(String(255))
    bio = Column(Text)
    specialty = Column(String(255))  # e.g., "Habesha Kemis", "Embroidery"
    location = Column(String(255))
    years_experience = Column(Integer)
    rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    portfolio_url = Column(String(500))
    
    # Relationship
    user = relationship("User", backref="designer_profile")


class OutfitRequest(Base):
    """Client outfit requests."""
    __tablename__ = "outfit_requests"
    
    id = Column(String(36), primary_key=True)
    client_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)
    description = Column(Text)
    budget_min = Column(Float)
    budget_max = Column(Float)
    deadline = Column(DateTime)
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    client = relationship("User", back_populates="requests")
    offers = relationship("Offer", back_populates="request", cascade="all, delete-orphan")


class Offer(Base):
    """Designer proposals for requests."""
    __tablename__ = "offers"
    
    id = Column(String(36), primary_key=True)
    request_id = Column(String(36), ForeignKey("outfit_requests.id", ondelete="CASCADE"), nullable=False)
    designer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    price = Column(Float, nullable=False)
    timeline_days = Column(Integer, nullable=False)
    message = Column(Text)
    status = Column(SQLEnum(OfferStatus), default=OfferStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    request = relationship("OutfitRequest", back_populates="offers")
    designer = relationship("User", back_populates="offers")


class Order(Base):
    """Confirmed orders from accepted offers."""
    __tablename__ = "orders"
    
    id = Column(String(36), primary_key=True)
    offer_id = Column(String(36), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    designer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_amount = Column(Float, nullable=False)
    deposit_amount = Column(Float, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING_DEPOSIT)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    client = relationship("User", foreign_keys=[client_id], back_populates="orders_as_client")
    designer = relationship("User", foreign_keys=[designer_id], back_populates="orders_as_designer")
