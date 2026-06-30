# HabeshaFit — Event-based outfit ordering for the diaspora

## Quick start

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000

## Pages

- `/` — Landing page with event selection
- `/request/new?event=wedding` — 3-step outfit request form
- `/offers/{request_id}` — Designer offer comparison (after form submit)
- `/orders/{order_id}` — Order confirmation + tracking timeline

## Structure

```
app/
├── main.py                — FastAPI app, mounts static + routes
├── routes/web.py          — All page routes (in-memory demo data)
├── templates/
│   ├── layouts/base.html  — Shared nav, footer, flash messages
│   └── pages/              — landing, request_form, offers, order_tracking
└── static/css/habeshafit.css — Full design system (emerald palette)
```

## Design system

Primary color `#0A7B5C` emerald. Display font Bricolage Grotesque, body font
Inter. All interactive form controls (gender/size/budget toggles, multi-step
progress bar) are vanilla JS with no framework dependency.

## Next steps

Replace the `_requests` / `_orders` in-memory dicts in `app/routes/web.py`
with real SQLAlchemy models once the backend (designer matching, payments,
auth) is ready. Route signatures are already structured for that swap —
each route currently builds a plain dict that maps directly onto a future
ORM model.
