"""
HabeshaFit web routes — serves Jinja2 templates.
Now backed by SQLite database for persistence and scalability.
"""
import uuid
from datetime import date, timedelta
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import (
    create_request, get_request, generate_offers_for_request,
    create_order, get_order, get_all_designers, submit_designer_application
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ── Demo data (for landing page only) ────────────────────────────────────

EVENTS = [
    {"slug": "wedding", "icon": "💍", "name": "Wedding", "sub": "Bride, groom & guests"},
    {"slug": "church", "icon": "✝️", "name": "Church holiday", "sub": "Timkat, Meskel, Enkutatash"},
    {"slug": "graduation", "icon": "🎓", "name": "Graduation", "sub": "Celebrate milestones"},
    {"slug": "cultural", "icon": "🎉", "name": "Cultural event", "sub": "Family, community, holidays"},
]

EVENTS_BY_SLUG = {e["slug"]: e for e in EVENTS}


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
    # Generate short request ID
    request_id = str(uuid.uuid4())[:8]
    
    # Save to database
    await create_request({
        "id": request_id,
        "event_type": EVENTS_BY_SLUG.get(event_type, EVENTS[0])["name"],
        "gender": gender,
        "size": size,
        "budget": budget,
        "country": country,
        "city": city,
        "event_date": event_date,
        "notes": notes,
        "email": email,
    })
    
    return RedirectResponse(url=f"/offers/{request_id}", status_code=303)


@router.get("/offers/{request_id}", response_class=HTMLResponse)
async def offers(request: Request, request_id: str):
    # Get request from database
    request_data = await get_request(request_id)
    
    if not request_data:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Convert to dict manually
    req_dict = {
        "id": request_data.id,
        "event_type": request_data.event_type,
        "description": request_data.description,
        "budget_min": request_data.budget_min,
        "budget_max": request_data.budget_max,
        "budget": str(request_data.budget_min),  # For template compatibility
        "deadline": request_data.deadline.isoformat() if request_data.deadline else None,
        "status": request_data.status.value if request_data.status else "pending",
    }
    
    # Generate offers using matching algorithm
    offers_list = await generate_offers_for_request(req_dict)
    
    # Pretty-format event date
    try:
        d = request_data.deadline
        if d:
            req_dict["event_date"] = d.strftime("%d %b %Y")
    except (ValueError, KeyError, AttributeError):
        pass

    return templates.TemplateResponse(request, "pages/offers.html", {
        "active_page": "offers",
        "order_request": req_dict,
        "offers": offers_list,
        "flash": None,
    })


@router.post("/offers/{offer_id}/choose")
async def choose_offer(offer_id: str, request: Request):
    # Parse offer data from form or use defaults
    # In production, this would come from the selected offer
    request_id = request.query_params.get("request_id", "demo")
    
    # Get request data to build order
    req = await get_request(request_id)
    if not req:
        # Fallback for demo
        req_dict = {
            "city": "Frankfurt", "country": "Germany", "event_type": "Wedding"
        }
        client_id = ""
    else:
        req_dict = {
            "city": "Unknown", 
            "country": "Unknown", 
            "event_type": req.event_type
        }
        client_id = req.client_id
    
    # Designer mapping based on offer_id
    designer_map = {
        f"off_des_{i}": (name, f"des_{i}", price) 
        for i, (name, price) in enumerate([
            ("Selam Abrham", 220),
            ("Mekdes Tadesse", 190),
            ("Hiwot Girma", 285),
            ("Yonas Kebede", 310),
            ("Lily Haile", 265),
        ])
    }
    
    designer_name, designer_id, price = designer_map.get(
        offer_id, ("Selam Abrham", "des_selam", 220)
    )
    deposit = round(price * 0.4)
    order_id = str(uuid.uuid4())[:8]
    
    # Calculate ETA
    eta_date = date.today() + timedelta(days=25)
    
    # Create order in database
    await create_order({
        "id": order_id,
        "request_id": request_id,
        "offer_id": offer_id,
        "designer_id": designer_id,
        "designer_name": designer_name,
        "total_price": price,
        "deposit_paid": deposit,
        "status": "in_production",
        "ship_to": f"{req_dict.get('city', 'Frankfurt')}, {req_dict.get('country', 'Germany')}",
        "eta": eta_date.strftime("%d %b %Y"),
        "notes": "",
    })
    
    return RedirectResponse(url=f"/orders/{order_id}", status_code=303)


@router.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_tracking(request: Request, order_id: str):
    order = await get_order(order_id)
    
    if not order:
        # Fallback demo data
        order_dict = {
            "ref": f"HF-{order_id.upper()}",
            "designer_name": "Selam Abrham",
            "designer_id": "des_selam",
            "event_type": "Wedding",
            "status_label": "In production",
            "outfit_summary": "Habesha kemis, hand-woven Tibeb, size M",
            "total_price": 220,
            "deposit_paid": 88,
            "balance_due": 132,
            "ship_to": "Frankfurt, Germany",
            "eta": "25 Jul 2026",
            "timeline": [
                {"state": "done", "title": "Order confirmed", "sub": "Deposit received", "time": "Today"},
                {"state": "now", "title": "In production", "sub": "Selam Abrham is preparing your outfit", "time": "Est. 18 days"},
                {"state": "upcoming", "title": "Shipped", "sub": None, "time": None},
                {"state": "upcoming", "title": "Delivered", "sub": None, "time": None},
            ],
        }
    else:
        order_dict = order.to_dict()
        order_dict["ref"] = f"HF-{order_id.upper()}"
        order_dict["status_label"] = order.status.replace("_", " ").title()
        order_dict["outfit_summary"] = f"Custom {order_dict.get('event_type', 'Outfit')}"
        order_dict["timeline"] = [
            {"state": "done", "title": "Order confirmed", "sub": "Deposit received", "time": "Today"},
            {"state": "now", "title": "In production", "sub": f"{order.designer_name} is preparing your outfit", "time": "Est. 18 days"},
            {"state": "upcoming", "title": "Shipped", "sub": None, "time": None},
            {"state": "upcoming", "title": "Delivered", "sub": None, "time": None},
        ]
    
    return templates.TemplateResponse(request, "pages/order_tracking.html", {
        "active_page": "orders",
        "order": order_dict,
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
    # Get all designers from database
    designers = await get_all_designers()
    
    # Convert to dict format for templates
    designers_data = []
    for d in designers:
        designers_data.append({
            "id": d.id,
            "business_name": d.business_name or f"Designer {d.id[:6]}",
            "bio": d.bio or "",
            "specialty": d.specialty or "Traditional Attire",
            "location": d.location or "Ethiopia",
            "years_experience": d.years_experience or 0,
            "rating": d.rating or 4.5,
            "total_reviews": d.total_reviews or 10,
            "is_available": d.is_available,
            "portfolio_url": d.portfolio_url,
        })
    
    return templates.TemplateResponse(request, "pages/designers.html", {
        "active_page": "designers",
        "events": EVENTS,
        "designers": designers_data,
        "flash": None,
    })


@router.get("/designers/apply", response_class=HTMLResponse)
async def designer_apply(request: Request):
    return templates.TemplateResponse(request, "pages/designer_apply.html", {
        "active_page": "designers",
        "flash": None,
    })


@router.post("/designers/apply/submit")
async def submit_designer_application_form(
    full_name: str = Form(...),
    email: str = Form(...),
    business_name: str = Form(""),
    specialty: str = Form(...),
    location: str = Form(...),
    years_experience: int = Form(0),
    bio: str = Form(""),
    portfolio_url: str = Form(""),
):
    """Handle designer application submission."""
    try:
        await submit_designer_application({
            "full_name": full_name,
            "email": email,
            "business_name": business_name or full_name,
            "specialty": specialty,
            "location": location,
            "years_experience": years_experience,
            "bio": bio,
            "portfolio_url": portfolio_url,
        })
        
        # Redirect to landing page with success message
        return RedirectResponse(url="/?status=application_submitted", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Application failed: {str(e)}")
