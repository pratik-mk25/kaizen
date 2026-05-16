# MISSION AVINYA: The Operating System for Team Excellence

AVINYA is a precision-engineered SaaS platform designed for high-stakes coordination, project management, and operational transparency. Built for organizations that demand excellence, it moves your operations from disparate spreadsheets to a unified, auditable, and visual command center.

## Project Vision

AVINYA focuses on three core pillars:
- **Zero Friction Coordination**: Kanban-style intelligence for tracking work.
- **Full Accountability**: Secure audit logs with 1-click Undo for every change.
- **Multi-Tenancy**: Built-in support for multiple organizations to run on a single deployment with strict data isolation.

## Core Features

- **Kanban Mission Intel**: Visual tracking of tasks from Queued to Complete.
- **Role-Based Access**: Specialized roles (Admin, Lead, Member) to manage permissions.
- **Secure Audit Log**: Full transparency of system actions and mutations.
- **Data Vault**: Secure task attachments and real-time discussion threads.
- **Automated Provisioning**: System-generated identifiers for members.

## Technical Stack

- **Backend**: Python 3.12 + FastAPI
- **Database**: Supabase (PostgreSQL) + Row Level Security (RLS)
- **Frontend**: 
    - TailwindCSS: Utility-first styling for a sleek, responsive interface.
    - Alpine.js: Lightweight reactivity for interactive UI components.
    - HTMX: Partial page updates for a seamless user experience.

## Getting Started

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/VihangDroneClub/mission-tracker.git
   cd mission-tracker
   ```

2. **Run Setup**:
   ```bash
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

3. **Configure Environment**:
   Update the `.env` file with your Supabase credentials:
   ```env
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   SECRET_KEY=your_session_secret
   ```

4. **Launch Application**:
   ```bash
   source venv/bin/activate
   uvicorn main:app --reload
   ```

## Contributing

We welcome contributions to AVINYA. Please see `CONTRIBUTING.md` for guidelines on how to get started.

---
Maintained by the MISSION AVINYA.
