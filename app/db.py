"""
HabeshaFit Database Module - Lightweight SQLite with async support
Minimal, scalable, no ORM bloat. Just raw SQL with Pydantic models.
"""
import sqlite3
from datetime import datetime
from typing import Optional, Any
from contextlib import contextmanager
import aiosqlite

DB_PATH = "habeshafit.db"


# ── Pydantic Models (Lightweight Data Schemas) ───────────────────────────

class RequestModel:
    """Schema for outfit requests"""
    def __init__(self, id: str, event_type: str, gender: str, size: str,
                 budget: str, country: str, city: str, event_date: str,
                 notes: str, email: str, created_at: str):
        self.id = id
        self.event_type = event_type
        self.gender = gender
        self.size = size
        self.budget = budget
        self.country = country
        self.city = city
        self.event_date = event_date
        self.notes = notes
        self.email = email
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "gender": self.gender,
            "size": self.size,
            "budget": self.budget,
            "country": self.country,
            "city": self.city,
            "event_date": self.event_date,
            "notes": self.notes,
            "email": self.email,
            "created_at": self.created_at,
        }


class OrderModel:
    """Schema for orders"""
    def __init__(self, id: str, request_id: str, offer_id: str, designer_id: str,
                 designer_name: str, total_price: float, deposit_paid: float,
                 status: str, ship_to: str, eta: str, created_at: str):
        self.id = id
        self.request_id = request_id
        self.offer_id = offer_id
        self.designer_id = designer_id
        self.designer_name = designer_name
        self.total_price = total_price
        self.deposit_paid = deposit_paid
        self.status = status
        self.ship_to = ship_to
        self.eta = eta
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "offer_id": self.offer_id,
            "designer_id": self.designer_id,
            "designer_name": self.designer_name,
            "total_price": self.total_price,
            "deposit_paid": self.deposit_paid,
            "balance_due": self.total_price - self.deposit_paid,
            "status": self.status,
            "ship_to": self.ship_to,
            "eta": self.eta,
            "created_at": self.created_at,
        }


class DesignerModel:
    """Schema for designers"""
    def __init__(self, id: str, name: str, location: str, rating: float,
                 order_count: int, specialty: str, bio: str, avatar_color: str):
        self.id = id
        self.name = name
        self.location = location
        self.rating = rating
        self.order_count = order_count
        self.specialty = specialty
        self.bio = bio
        self.avatar_color = avatar_color

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "rating": self.rating,
            "order_count": self.order_count,
            "specialty": self.specialty,
            "bio": self.bio,
            "avatar_color": self.avatar_color,
        }


# ── Database Initialization ──────────────────────────────────────────────

INIT_SQL = """
-- Requests table
CREATE TABLE IF NOT EXISTS requests (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    gender TEXT NOT NULL,
    size TEXT NOT NULL,
    budget TEXT NOT NULL,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    event_date TEXT NOT NULL,
    notes TEXT DEFAULT '',
    email TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Designers table
CREATE TABLE IF NOT EXISTS designers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    rating REAL NOT NULL,
    order_count INTEGER DEFAULT 0,
    specialty TEXT NOT NULL,
    bio TEXT NOT NULL,
    avatar_color TEXT NOT NULL
);

-- Offers table
CREATE TABLE IF NOT EXISTS offers (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    designer_id TEXT NOT NULL,
    price REAL NOT NULL,
    shipping_cost REAL DEFAULT 0,
    production_days INTEGER NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    FOREIGN KEY (request_id) REFERENCES requests(id),
    FOREIGN KEY (designer_id) REFERENCES designers(id)
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    offer_id TEXT NOT NULL,
    designer_id TEXT NOT NULL,
    designer_name TEXT NOT NULL,
    total_price REAL NOT NULL,
    deposit_paid REAL NOT NULL,
    status TEXT DEFAULT 'in_production',
    ship_to TEXT NOT NULL,
    eta TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (request_id) REFERENCES requests(id),
    FOREIGN KEY (offer_id) REFERENCES offers(id),
    FOREIGN KEY (designer_id) REFERENCES designers(id)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_requests_event_date ON requests(event_date);
CREATE INDEX IF NOT EXISTS idx_offers_request_id ON offers(request_id);
CREATE INDEX IF NOT EXISTS idx_orders_request_id ON orders(request_id);
CREATE INDEX IF NOT EXISTS idx_designers_rating ON designers(rating DESC);
"""


def init_db():
    """Initialize database schema and seed demo data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(INIT_SQL)

    # Seed demo designers if empty
    cursor.execute("SELECT COUNT(*) FROM designers")
    if cursor.fetchone()[0] == 0:
        designers = [
            ("des_selam", "Selam Abrham", "Addis Ababa · ships worldwide", 4.9, 38,
             "Hand-woven Tibeb", "Specializes in traditional Gondar-style kemis with intricate gold embroidery.", "#043D2D"),
            ("des_mekdes", "Mekdes Tadesse", "Gondar · ships worldwide", 4.8, 21,
             "Cotton blend", "Expert in lightweight Habesha dresses perfect for European summers.", "#065C44"),
            ("des_hiwot", "Hiwot Girma", "Frankfurt, Germany · local", 4.7, 12,
             "Local fittings", "Diaspora tailor offering in-person measurements and quick turnarounds.", "#185FA5"),
            ("des_yonas", "Yonas Kebede", "Addis Ababa · ships worldwide", 4.9, 45,
             "Men's traditional", "Master of Habesha suits and ceremonial wear for grooms.", "#2D4A7C"),
            ("des_lily", "Lily Haile", "Bahir Dar · ships worldwide", 4.8, 29,
             "Modern fusion", "Blends traditional Tibeb with contemporary silhouettes.", "#8B3A6B"),
        ]
        cursor.executemany(
            "INSERT INTO designers VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            designers
        )

    conn.commit()
    conn.close()


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ── Async Database Operations ────────────────────────────────────────────

async def db_init_async():
    """Async version of database initialization"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(INIT_SQL)
        
        # Check if designers exist
        cursor = await db.execute("SELECT COUNT(*) FROM designers")
        count = await cursor.fetchone()
        
        if count[0] == 0:
            designers = [
                ("des_selam", "Selam Abrham", "Addis Ababa · ships worldwide", 4.9, 38,
                 "Hand-woven Tibeb", "Specializes in traditional Gondar-style kemis with intricate gold embroidery.", "#043D2D"),
                ("des_mekdes", "Mekdes Tadesse", "Gondar · ships worldwide", 4.8, 21,
                 "Cotton blend", "Expert in lightweight Habesha dresses perfect for European summers.", "#065C44"),
                ("des_hiwot", "Hiwot Girma", "Frankfurt, Germany · local", 4.7, 12,
                 "Local fittings", "Diaspora tailor offering in-person measurements and quick turnarounds.", "#185FA5"),
                ("des_yonas", "Yonas Kebede", "Addis Ababa · ships worldwide", 4.9, 45,
                 "Men's traditional", "Master of Habesha suits and ceremonial wear for grooms.", "#2D4A7C"),
                ("des_lily", "Lily Haile", "Bahir Dar · ships worldwide", 4.8, 29,
                 "Modern fusion", "Blends traditional Tibeb with contemporary silhouettes.", "#8B3A6B"),
            ]
            await db.executemany(
                "INSERT INTO designers VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                designers
            )
            await db.commit()


async def create_request(data: dict) -> RequestModel:
    """Create a new outfit request"""
    now = datetime.utcnow().isoformat()
    request_id = data.get("id", f"req_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO requests 
               (id, event_type, gender, size, budget, country, city, event_date, notes, email, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (request_id, data["event_type"], data["gender"], data["size"],
             data["budget"], data["country"], data["city"], data["event_date"],
             data.get("notes", ""), data["email"], now)
        )
        await db.commit()
    
    return RequestModel(
        id=request_id, event_type=data["event_type"], gender=data["gender"],
        size=data["size"], budget=data["budget"], country=data["country"],
        city=data["city"], event_date=data["event_date"],
        notes=data.get("notes", ""), email=data["email"], created_at=now
    )


async def get_request(request_id: str) -> Optional[RequestModel]:
    """Get a request by ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM requests WHERE id = ?", (request_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return RequestModel(
                id=row["id"], event_type=row["event_type"], gender=row["gender"],
                size=row["size"], budget=row["budget"], country=row["country"],
                city=row["city"], event_date=row["event_date"],
                notes=row["notes"] or "", email=row["email"], created_at=row["created_at"]
            )
    return None


async def create_offer(request_id: str, designer_id: str, price: float,
                       production_days: int, description: str,
                       shipping_cost: float = 0) -> str:
    """Create an offer for a request"""
    offer_id = f"off_{request_id}_{designer_id}"
    now = datetime.utcnow().isoformat()
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO offers 
               (id, request_id, designer_id, price, shipping_cost, production_days, description, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (offer_id, request_id, designer_id, price, shipping_cost,
             production_days, description, now)
        )
        await db.commit()
    
    return offer_id


async def get_offers_for_request(request_id: str) -> list[dict]:
    """Get all offers for a request with designer info"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT o.*, d.name as designer_name, d.location, d.rating, 
                      d.order_count, d.avatar_color
               FROM offers o
               JOIN designers d ON o.designer_id = d.id
               WHERE o.request_id = ? AND o.status = 'pending'
               ORDER BY o.price ASC""",
            (request_id,)
        )
        rows = await cursor.fetchall()
        
        return [
            {
                "id": row["id"],
                "designer_id": row["designer_id"],
                "designer_name": row["designer_name"],
                "location": row["location"],
                "rating": row["rating"],
                "order_count": row["order_count"],
                "avatar_color": row["avatar_color"],
                "price": row["price"],
                "shipping_cost": row["shipping_cost"],
                "production_days": row["production_days"],
                "description": row["description"],
                "deposit": round(row["price"] * 0.4),
            }
            for row in rows
        ]


async def create_order(data: dict) -> OrderModel:
    """Create an order from an accepted offer"""
    now = datetime.utcnow().isoformat()
    order_id = data.get("id", f"ord_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO orders 
               (id, request_id, offer_id, designer_id, designer_name, total_price, 
                deposit_paid, status, ship_to, eta, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_id, data["request_id"], data["offer_id"], data["designer_id"],
             data["designer_name"], data["total_price"], data["deposit_paid"],
             data.get("status", "in_production"), data["ship_to"], data["eta"], now)
        )
        
        # Update offer status
        await db.execute(
            "UPDATE offers SET status = 'accepted' WHERE id = ?",
            (data["offer_id"],)
        )
        await db.commit()
    
    return OrderModel(
        id=order_id, request_id=data["request_id"], offer_id=data["offer_id"],
        designer_id=data["designer_id"], designer_name=data["designer_name"],
        total_price=data["total_price"], deposit_paid=data["deposit_paid"],
        status=data.get("status", "in_production"), ship_to=data["ship_to"],
        eta=data["eta"], created_at=now
    )


async def get_order(order_id: str) -> Optional[OrderModel]:
    """Get an order by ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return OrderModel(
                id=row["id"], request_id=row["request_id"], offer_id=row["offer_id"],
                designer_id=row["designer_id"], designer_name=row["designer_name"],
                total_price=row["total_price"], deposit_paid=row["deposit_paid"],
                status=row["status"], ship_to=row["ship_to"], eta=row["eta"],
                created_at=row["created_at"]
            )
    return None


async def get_designer(designer_id: str) -> Optional[DesignerModel]:
    """Get a designer by ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM designers WHERE id = ?", (designer_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return DesignerModel(
                id=row["id"], name=row["name"], location=row["location"],
                rating=row["rating"], order_count=row["order_count"],
                specialty=row["specialty"], bio=row["bio"],
                avatar_color=row["avatar_color"]
            )
    return None


async def get_all_designers() -> list[DesignerModel]:
    """Get all designers ordered by rating"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM designers ORDER BY rating DESC, order_count DESC"
        )
        rows = await cursor.fetchall()
        
        return [
            DesignerModel(
                id=row["id"], name=row["name"], location=row["location"],
                rating=row["rating"], order_count=row["order_count"],
                specialty=row["specialty"], bio=row["bio"],
                avatar_color=row["avatar_color"]
            )
            for row in rows
        ]


async def generate_offers_for_request(request_data: dict) -> list[dict]:
    """Generate offers based on request using matching algorithm"""
    budget_str = request_data.get("budget", "150-300")
    try:
        budget_low = int(budget_str.split("-")[0].replace("+", ""))
    except (ValueError, IndexError):
        budget_low = 150
    
    base_price = max(budget_low + 40, 150)
    city = request_data.get("city", "Frankfurt")
    country = request_data.get("country", "Germany")
    
    # Get designers from DB
    designers = await get_all_designers()
    offers = []
    
    for i, designer in enumerate(designers[:3]):  # Top 3 matches
        # Adjust price based on designer rating and location
        rating_factor = 1 + (designer.rating - 4.5) * 0.2
        is_local = "local" in designer.location.lower() or country.lower() in designer.location.lower()
        
        price = round(base_price * rating_factor)
        shipping_cost = 0 if is_local else 35
        production_days = 10 if is_local else 18
        
        offers.append({
            "id": f"off_{designer.id}",
            "designer_id": designer.id,
            "designer_name": designer.name,
            "location": designer.location,
            "rating": str(designer.rating),
            "order_count": designer.order_count,
            "avatar_color": designer.avatar_color,
            "price": price,
            "shipping_cost": shipping_cost,
            "production_days": production_days,
            "description": designer.bio,
            "tags": [designer.specialty],
            "deposit": round(price * 0.4),
        })
    
    return offers
