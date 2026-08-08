"""Database module initialization with full business logic."""
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.database import async_session_maker
from app.db.models import (
    User, DesignerProfile, OutfitRequest, Offer, Order,
    UserRole, RequestStatus, OfferStatus, OrderStatus
)


async def create_request(data: dict) -> OutfitRequest:
    """Create a new outfit request in the database."""
    async with async_session_maker() as session:
        # Create anonymous client user if not provided
        client_email = data.get("email", f"anon_{uuid.uuid4().hex[:8]}@habeshafit.com")
        
        # Check if user exists
        result = await session.execute(select(User).where(User.email == client_email))
        user = result.scalar_one_or_none()
        
        if not user:
            # Create anonymous user
            user = User(
                id=str(uuid.uuid4()),
                email=client_email,
                hashed_password="",  # No password for anonymous users
                full_name=data.get("full_name", "Anonymous Client"),
                role=UserRole.CLIENT,
                is_verified=False,
            )
            session.add(user)
            await session.flush()
        
        # Parse event date
        try:
            deadline = datetime.fromisoformat(data["event_date"])
        except (KeyError, ValueError):
            deadline = datetime.now() + timedelta(days=30)
        
        # Parse budget
        try:
            budget_min = float(data["budget"])
            budget_max = budget_min * 1.5
        except (KeyError, ValueError):
            budget_min = 100.0
            budget_max = 300.0
        
        # Create outfit request
        request_id = data.get("id", str(uuid.uuid4())[:8])
        outfit_request = OutfitRequest(
            id=request_id,
            client_id=user.id,
            event_type=data["event_type"],
            description=f"{data.get('gender', '')} {data.get('size', '')}, {data.get('notes', '')}",
            budget_min=budget_min,
            budget_max=budget_max,
            deadline=deadline,
            status=RequestStatus.PENDING,
        )
        session.add(outfit_request)
        await session.commit()
        await session.refresh(outfit_request)
        return outfit_request


async def get_request(request_id: str) -> OutfitRequest | None:
    """Get an outfit request by ID."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(OutfitRequest).where(OutfitRequest.id == request_id)
        )
        return result.scalar_one_or_none()


async def generate_offers_for_request(request_data: dict) -> list[dict]:
    """Generate matching designer offers for a request."""
    async with async_session_maker() as session:
        # Get all available designers
        result = await session.execute(
            select(DesignerProfile).where(DesignerProfile.is_available == True)
        )
        designers = result.scalars().all()
        
        # If no designers in DB, use demo data
        if not designers:
            return _get_demo_offers(request_data)
        
        # Match designers based on specialty and location
        offers = []
        event_type = request_data.get("event_type", "").lower()
        budget = float(request_data.get("budget", 200))
        
        for designer in designers:
            # Calculate match score
            score = 0.8  # Base score
            
            # Specialty match
            if designer.specialty and any(
                keyword in designer.specialty.lower() 
                for keyword in ["habesha", "traditional", "kemis", "cultural"]
            ):
                score += 0.1
            
            # Price within budget
            base_price = budget * 0.9
            if base_price <= budget <= base_price * 1.3:
                score += 0.1
            
            # Rating boost
            rating_boost = min(designer.rating / 5.0, 1.0) * 0.1
            score += rating_boost
            
            # Create offer
            price = round(base_price * (1 + rating_boost), 0)
            timeline = 21 + int(uuid.uuid4().int % 10)
            
            offers.append({
                "id": f"off_{designer.user_id}",
                "designer_id": designer.user_id,
                "designer_name": designer.business_name or f"Designer {designer.id[:4]}",
                "price": price,
                "timeline_days": timeline,
                "rating": designer.rating or 4.5,
                "reviews": designer.total_reviews or 12,
                "specialty": designer.specialty or "Traditional Attire",
                "location": designer.location or "Addis Ababa",
                "portfolio_url": designer.portfolio_url,
                "message": f"I'd love to create your {event_type} outfit! Specializing in traditional designs.",
            })
        
        # Sort by score (simulated by rating)
        offers.sort(key=lambda x: x["rating"], reverse=True)
        return offers[:5]  # Return top 5


def _get_demo_offers(request_data: dict) -> list[dict]:
    """Return demo offers when no designers exist in DB."""
    event_type = request_data.get("event_type", "Wedding")
    budget = float(request_data.get("budget", 200))
    
    demo_designers = [
        {"name": "Selam Abrham", "base_price": 220, "rating": 4.9, "reviews": 47, "specialty": "Habesha Kemis & Tibeb"},
        {"name": "Mekdes Tadesse", "base_price": 190, "rating": 4.7, "reviews": 32, "specialty": "Traditional Embroidery"},
        {"name": "Hiwot Girma", "base_price": 285, "rating": 5.0, "reviews": 68, "specialty": "Luxury Cultural Attire"},
        {"name": "Yonas Kebede", "base_price": 310, "rating": 4.8, "reviews": 54, "specialty": "Modern Habesha Designs"},
        {"name": "Lily Haile", "base_price": 265, "rating": 4.9, "reviews": 41, "specialty": "Wedding & Church Attire"},
    ]
    
    offers = []
    for i, des in enumerate(demo_designers):
        price = round(des["base_price"] * (budget / 200), 0)
        offers.append({
            "id": f"off_des_{i}",
            "designer_id": f"des_{i}",
            "designer_name": des["name"],
            "price": price,
            "timeline_days": 18 + (i * 3),
            "rating": des["rating"],
            "reviews": des["reviews"],
            "specialty": des["specialty"],
            "location": "Addis Ababa, Ethiopia",
            "portfolio_url": None,
            "message": f"I specialize in {event_type} outfits and would love to work with you!",
        })
    
    return offers


async def create_order(data: dict) -> Order:
    """Create a new order from an accepted offer."""
    async with async_session_maker() as session:
        # Get the request to find client_id
        client_id = data.get("client_id", "")
        if not client_id and data.get("request_id"):
            req_result = await session.execute(
                select(OutfitRequest).where(OutfitRequest.id == data["request_id"])
            )
            request = req_result.scalar_one_or_none()
            if request:
                client_id = request.client_id
        
        # Create offer from data if not exists
        offer = Offer(
            id=data["offer_id"],
            request_id=data.get("request_id", ""),
            designer_id=data["designer_id"],
            price=data["total_price"],
            timeline_days=25,
            message="",
            status=OfferStatus.ACCEPTED,
        )
        session.add(offer)
        await session.flush()
        
        # Update request status if exists
        if data.get("request_id"):
            req_result = await session.execute(
                select(OutfitRequest).where(OutfitRequest.id == data["request_id"])
            )
            request = req_result.scalar_one_or_none()
            if request:
                request.status = RequestStatus.COMPLETED
        
        # Create order
        order = Order(
            id=data["id"],
            offer_id=offer.id,
            client_id=client_id,
            designer_id=data["designer_id"],
            total_amount=data["total_price"],
            deposit_amount=data["deposit_paid"],
            status=OrderStatus.DEPOSIT_PAID,
            notes=data.get("notes", ""),
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order


async def get_order(order_id: str) -> Order | None:
    """Get an order by ID with relationships loaded."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if order:
            # Load relationships
            await session.refresh(order, attribute_names=["designer", "client"])
        
        return order


async def get_all_designers() -> list[DesignerProfile]:
    """Get all designer profiles."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(DesignerProfile).where(DesignerProfile.is_available == True)
        )
        designers = result.scalars().all()
        
        # If no designers in DB, return demo data as mock objects
        if not designers:
            return _get_demo_designer_profiles()
        
        return list(designers)


def _get_demo_designer_profiles() -> list[DesignerProfile]:
    """Return demo designer profiles when DB is empty."""
    demo_data = [
        {
            "id": "des_selam",
            "user_id": "user_selam",
            "business_name": "Selam's Traditional Designs",
            "bio": "Master tailor with 15+ years creating authentic Habesha kemis for weddings and cultural events.",
            "specialty": "Habesha Kemis & Tibeb",
            "location": "Addis Ababa, Ethiopia",
            "years_experience": 15,
            "rating": 4.9,
            "total_reviews": 47,
            "is_available": True,
            "portfolio_url": None,
        },
        {
            "id": "des_mekdes",
            "user_id": "user_mekdes",
            "business_name": "Mekdes Embroidery Studio",
            "bio": "Specializing in intricate hand-embroidered details that honor our heritage.",
            "specialty": "Traditional Embroidery",
            "location": "Dire Dawa, Ethiopia",
            "years_experience": 10,
            "rating": 4.7,
            "total_reviews": 32,
            "is_available": True,
            "portfolio_url": None,
        },
        {
            "id": "des_hiwot",
            "user_id": "user_hiwot",
            "business_name": "Hiwot Luxury Attire",
            "bio": "Premium custom designs for discerning clients who want the finest traditional wear.",
            "specialty": "Luxury Cultural Attire",
            "location": "Addis Ababa, Ethiopia",
            "years_experience": 20,
            "rating": 5.0,
            "total_reviews": 68,
            "is_available": True,
            "portfolio_url": None,
        },
        {
            "id": "des_yonas",
            "user_id": "user_yonas",
            "business_name": "Yonas Modern Habesha",
            "bio": "Blending traditional craftsmanship with contemporary silhouettes for the modern Ethiopian.",
            "specialty": "Modern Habesha Designs",
            "location": "Bahir Dar, Ethiopia",
            "years_experience": 8,
            "rating": 4.8,
            "total_reviews": 54,
            "is_available": True,
            "portfolio_url": None,
        },
        {
            "id": "des_lily",
            "user_id": "user_lily",
            "business_name": "Lily's Bridal Collection",
            "bio": "Creating unforgettable wedding and church holiday outfits with attention to every detail.",
            "specialty": "Wedding & Church Attire",
            "location": "Hawassa, Ethiopia",
            "years_experience": 12,
            "rating": 4.9,
            "total_reviews": 41,
            "is_available": True,
            "portfolio_url": None,
        },
    ]
    
    profiles = []
    for data in demo_data:
        profile = DesignerProfile(**data)
        profiles.append(profile)
    
    return profiles


async def submit_designer_application(data: dict) -> DesignerProfile:
    """Submit a new designer application."""
    async with async_session_maker() as session:
        # Create user account
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=data["email"],
            hashed_password="",  # Will set password later
            full_name=data["full_name"],
            role=UserRole.DESIGNER,
            is_verified=False,
        )
        session.add(user)
        await session.flush()
        
        # Create designer profile
        profile = DesignerProfile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            business_name=data.get("business_name", data["full_name"]),
            bio=data.get("bio", ""),
            specialty=data.get("specialty", "Traditional Attire"),
            location=data.get("location", ""),
            years_experience=data.get("years_experience", 0),
            rating=0.0,
            total_reviews=0,
            is_available=False,  # Pending approval
            portfolio_url=data.get("portfolio_url", ""),
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile


__all__ = [
    "create_request",
    "get_request",
    "generate_offers_for_request",
    "create_order",
    "get_order",
    "get_all_designers",
    "submit_designer_application",
]
