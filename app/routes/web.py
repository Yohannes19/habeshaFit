"""
HabeshaFit web routes — serves Jinja2 templates.
In-memory demo data for now; swap for DB queries once models exist.
"""
import uuid
from datetime import date, timedelta
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ── Demo data ────────────────────────────────────────────────────────────

EVENTS = [
    {"slug": "wedding", "icon": "💍", "name": "Wedding", "sub": "Bride, groom & guests"},
    {"slug": "church", "icon": "✝️", "name": "Church holiday", "sub": "Timkat, Meskel, Enkutatash"},
    {"slug": "graduation", "icon": "🎓", "name": "Graduation", "sub": "Celebrate milestones"},
    {"slug": "cultural", "icon": "🎉", "name": "Cultural event", "sub": "Family, community, holidays"},
]

EVENTS_BY_SLUG = {e["slug"]: e for e in EVENTS}

# In-memory request store for demo purposes (replace with DB)
_requests: dict[str, dict] = {}
_orders: dict[str, dict] = {}


def _demo_offers(request_data: dict) -> list[dict]:
    """Generate demo designer offers based on the request. Replace with real matching engine."""
    budget_low = int(request_data.get("budget", "150-300").split("-")[0].replace("+", ""))
    base = max(budget_low + 40, 150)

    return [
        {
            "id": "off_1",
            "designer_id": "des_selam",
            "designer_name": "Selam Abrham",
            "initials": "SA",
            "avatar_bg": "#E6F5F0",
            "avatar_color": "#043D2D",
            "location": "Addis Ababa · ships worldwide",
            "rating": "4.9",
            "order_count": 38,
            "price": base,
            "shipping_note": "+ €35 shipping",
            "description": (
                "Traditional Habesha kemis in hand-woven Tibeb fabric with gold and ivory "
                "embroidery at the neckline, sleeves and hem. Available in soft blue, white "
                "or ivory. Includes matching netela."
            ),
            "tags": ["Hand-woven Tibeb", "Gold embroidery", "Includes netela", "Custom measurements"],
            "production_days": 18,
            "shipping_time": "7–10 days",
            "deposit": round(base * 0.4),
        },
        {
            "id": "off_2",
            "designer_id": "des_mekdes",
            "designer_name": "Mekdes Tadesse",
            "initials": "MT",
            "avatar_bg": "#E6F5F0",
            "avatar_color": "#065C44",
            "location": "Gondar · ships worldwide",
            "rating": "4.8",
            "order_count": 21,
            "price": base - 30,
            "shipping_note": "+ €35 shipping",
            "description": (
                "Classic white Habesha kemis with hand-stitched Gondar-style Tibeb border "
                "and minimal collar embroidery. Lightweight cotton blend, breathable for "
                "European summer weddings."
            ),
            "tags": ["Cotton blend", "Gondar style", "Lightweight"],
            "production_days": 14,
            "shipping_time": "7–10 days",
            "deposit": round((base - 30) * 0.4),
        },
        {
            "id": "off_3",
            "designer_id": "des_hiwot",
            "designer_name": "Hiwot Girma",
            "initials": "HG",
            "avatar_bg": "#E6F1FB",
            "avatar_color": "#185FA5",
            "location": f"{request_data.get('city', 'Frankfurt')}, {request_data.get('country', 'Germany')} · local tailor",
            "rating": "4.7",
            "order_count": 12,
            "price": base + 65,
            "shipping_note": "no shipping",
            "description": (
                "Local tailor — in-person fitting available. Uses imported Tibeb fabric "
                "from Addis. Premium finish, fastest option. Can accommodate last-minute "
                "size changes."
            ),
            "tags": ["Local fitting", "No shipping wait", "Premium finish", "Last-minute friendly"],
            "production_days": 10,
            "shipping_time": "Pickup / local",
            "deposit": round((base + 65) * 0.4),
        },
    ]


# ── Routes ───────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(request, "pages/landing.html", {
        "active_page": "home",
        "events": EVENTS,
        "flash": None,
    })


@router.get("/request/new", response_class=HTMLResponse)
async def request_form(request: Request, event: str = "wedding"):
    selected_event = EVENTS_BY_SLUG.get(event, EVENTS[0])
    return templates.TemplateResponse(request, "pages/request_form.html", {
        "active_page": "request",
        "event": selected_event,
        "flash": None,
    })


@router.post("/request/submit")
async def submit_request(
    event_type: str = Form(...),
    gender: str = Form(...),
    size: str = Form(...),
    budget: str = Form(...),
    country: str = Form(...),
    city: str = Form(...),
    event_date: str = Form(...),
    notes: str = Form(""),
    email: str = Form(...),
):
    request_id = str(uuid.uuid4())[:8]
    event_name = EVENTS_BY_SLUG.get(event_type, EVENTS[0])["name"]

    _requests[request_id] = {
        "id": request_id,
        "event_type": event_name,
        "gender": gender,
        "size": size,
        "budget": budget,
        "country": country,
        "city": city,
        "event_date": event_date,
        "notes": notes,
        "email": email,
    }
    return RedirectResponse(url=f"/offers/{request_id}", status_code=303)


@router.get("/offers/{request_id}", response_class=HTMLResponse)
async def offers(request: Request, request_id: str):
    request_data = _requests.get(request_id)
    if not request_data:
        # Fallback demo data if request_id not found (e.g. direct visit)
        request_data = {
            "id": request_id, "event_type": "Wedding", "gender": "woman", "size": "M",
            "budget": "150-300", "country": "Germany", "city": "Frankfurt",
            "event_date": "2025-09-20", "notes": "", "email": "demo@example.com",
        }

    offers_list = _demo_offers(request_data)

    # Pretty-format event date
    try:
        d = date.fromisoformat(request_data["event_date"])
        request_data["event_date"] = d.strftime("%d %b %Y")
    except (ValueError, KeyError):
        pass

    return templates.TemplateResponse(request, "pages/offers.html", {
        "active_page": "offers",
        "order_request": request_data,
        "offers": offers_list,
        "flash": None,
    })


@router.post("/offers/{offer_id}/choose")
async def choose_offer(offer_id: str):
    order_id = str(uuid.uuid4())[:8]

    designer_map = {
        "off_1": ("Selam Abrham", "des_selam", 220),
        "off_2": ("Mekdes Tadesse", "des_mekdes", 190),
        "off_3": ("Hiwot Girma", "des_hiwot", 285),
    }
    designer_name, designer_id, price = designer_map.get(offer_id, ("Selam Abrham", "des_selam", 220))
    deposit = round(price * 0.4)

    _orders[order_id] = {
        "ref": f"HF-{order_id.upper()}",
        "designer_name": designer_name,
        "designer_id": designer_id,
        "event_type": "Wedding",
        "status_label": "In production",
        "outfit_summary": "Habesha kemis, hand-woven Tibeb, size M",
        "total_price": price,
        "deposit_paid": deposit,
        "balance_due": price - deposit,
        "ship_to": "Frankfurt, Germany",
        "eta": (date.today() + timedelta(days=25)).strftime("%d %b %Y"),
        "timeline": [
            {"state": "done", "title": "Order confirmed", "sub": "Deposit received", "time": "Today"},
            {"state": "now", "title": "In production", "sub": f"{designer_name} is preparing your outfit", "time": "Est. 18 days"},
            {"state": "upcoming", "title": "Shipped", "sub": None, "time": None},
            {"state": "upcoming", "title": "Delivered", "sub": None, "time": None},
        ],
    }
    return RedirectResponse(url=f"/orders/{order_id}", status_code=303)


@router.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_tracking(request: Request, order_id: str):
    order = _orders.get(order_id)
    if not order:
        order = {
            "ref": f"HF-{order_id.upper()}", "designer_name": "Selam Abrham", "designer_id": "des_selam",
            "event_type": "Wedding", "status_label": "In production",
            "outfit_summary": "Habesha kemis, hand-woven Tibeb, size M",
            "total_price": 220, "deposit_paid": 88, "balance_due": 132,
            "ship_to": "Frankfurt, Germany", "eta": "25 Jul 2026",
            "timeline": [
                {"state": "done", "title": "Order confirmed", "sub": "Deposit received", "time": "Today"},
                {"state": "now", "title": "In production", "sub": "Selam Abrham is preparing your outfit", "time": "Est. 18 days"},
                {"state": "upcoming", "title": "Shipped", "sub": None, "time": None},
                {"state": "upcoming", "title": "Delivered", "sub": None, "time": None},
            ],
        }
    return templates.TemplateResponse(request, "pages/order_tracking.html", {
        "active_page": "orders",
        "order": order,
        "flash": {"type": "ok", "message": "Order confirmed! We've notified your designer."},
    })


@router.get("/how-it-works", response_class=HTMLResponse)
async def how_it_works(request: Request):
    return templates.TemplateResponse(request, "pages/landing.html", {
        "active_page": "how",
        "events": EVENTS,
        "flash": None,
    })


@router.get("/designers", response_class=HTMLResponse)
async def designers_list(request: Request):
    return templates.TemplateResponse(request, "pages/landing.html", {
        "active_page": "designers",
        "events": EVENTS,
        "flash": None,
    })
