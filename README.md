# 🛸 Mission Tracker: The Operating System for Elite Drone Clubs

[![Deploy to Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FVihangDroneClub%2Fmission-tracker)

**Mission Tracker** is a precision-engineered SaaS platform designed for high-stakes drone coordination, pilot management, and mission transparency. Built for clubs that demand excellence, it moves your operations from messy spreadsheets to a unified, auditable, and visual command center.

## 🚀 Why Mission Tracker?

Drone missions are complex. Between hardware failures, pilot availability, and shifting deadlines, things get lost. Mission Tracker provides:
- **Zero Friction Coordination**: Kanban-style mission intelligence.
- **Full Accountability**: Secure audit logs with 1-click **Undo** for every mutation.
- **Pilot Empowerment**: Clear roles, task assignments, and discussion threads.
- **Deployment Ready**: Designed to scale with multi-tenancy and high-performance serverless architecture.

## ⚡ Core Features

- **Kanban Mission Intel**: Visual tracking of tasks from `AWAIT` to `DONE`.
- **Pilot Assignment**: Multi-pilot task allocation with specialized roles (Admin, Lead, Member).
- **Secure Audit Log**: Full transparency of who did what, when.
- **Data Vault**: Secure task attachments (images, logs, manifests) and real-time HTMX discussion threads.
- **Auto-Provisioning**: Automated member ID generation (`vhng_0000` format).

## 🛠 The TAAH Stack

We prioritize speed, reliability, and modern aesthetics:
- **Backend**: Python 3.12 + FastAPI (Serverless optimized)
- **Database**: Supabase (PostgreSQL) + Row Level Security
- **Frontend**: 
    - **T**ailwindCSS: Utility-first styling for a sleek HUD.
    - **A**lpine.js: Lightweight reactivity for interactive elements.
    - **A**ny-CSS: Vanilla CSS for custom high-tech HUD components.
    - **H**TMX: Seamless, partial page updates without full reloads.

## 🏁 Quick Start

1. **Clone & Enter**:
   ```bash
   git clone https://github.com/VihangDroneClub/mission-tracker.git
   cd mission-tracker
   ```

2. **Environment Configuration**:
   Create a `.env` file:
   ```env
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   JWT_SECRET=your_jwt_secret
   ```

3. **Install & Run**:
   ```bash
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

## 🗺 Roadmap

- [x] **v2.0**: Core Kanban + Audit Logs + Undo
- [ ] **v2.1**: **Multi-Tenancy** (Organization isolation for SaaS scaling)
- [ ] **v2.2**: **Discord Webhooks** & Email Notifications
- [ ] **v2.3**: **Analytics HUD** (ApexCharts integration)
- [ ] **v2.4**: **Mobile-Native** HUD Interface

---
*Maintained by Vihang Drone Club. Deploy Excellence.*
