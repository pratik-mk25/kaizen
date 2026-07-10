# KAIZEN: Drone Club OS

Kaizen is a single-club operating system for drone clubs — member management, equipment/inventory tracking, budget/treasury, knowledge base, and attendance kiosk.

## Features

- **Equipment & Inventory** — Track drones, parts, and consumables with maintenance logs and transaction history
- **Member Management** — Profiles, skills, certifications, attendance tracking with role-based access (admin/lead/member)
- **Budget & Treasury** — Categories, income/expense tracking, dues management
- **Knowledge Base** — Document storage and versioning for club resources
- **Attendance Kiosk** — One-click check-in/out (localhost-only for club PC)

## Technical Stack

- **Backend**: Python 3.12 + FastAPI
- **Database**: Supabase (PostgreSQL)
- **Frontend**: TailwindCSS + Alpine.js + HTMX

## Getting Started

```bash
git clone https://github.com/pratik-mk25/kaizen.git
cd kaizen
```

Create `.env` with your Supabase credentials:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SECRET_KEY=your_session_secret
```

Then run:

```bash
source venv/bin/activate
uvicorn main:app --reload
```
