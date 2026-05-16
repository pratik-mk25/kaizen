# Contributing to MISSION AVINYA

We are pleased that you are interested in contributing to AVINYA. Whether you are fixing a bug, improving the UI, or adding a major new feature, your help is valued.

## Getting Started

1. **Fork the Repository**: Create your own copy of the project on GitHub.
2. **Clone Locally**:
   ```bash
   git clone https://github.com/VihangDroneClub/mission-tracker.git
   cd mission-tracker
   ```
3. **Setup Environment**:
   Run the setup script (recommended):
   ```bash
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```
   Or perform the steps manually:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```
4. **Configure Database**: You will need a Supabase project. Use the provided `MIGRATION.sql` file to set up your database schema.

## Development Workflow

- **Branching**: Create a feature branch for your changes: `git checkout -b feat/your-feature-name`.
- **Coding Standards**:
  - Use clear, descriptive variable names.
  - Adhere to PEP 8 for Python code.
  - Keep templates modular using `macros.html` for repetitive elements.
- **Testing**: Run existing tests before submitting a Pull Request:
  ```bash
  pytest
  ```

## Architectural Overview

- **main.py**: Entry point and FastAPI application configuration.
- **routers/**: Contains API endpoints grouped by functionality.
- **crud.py**: Centralized database operations using the Supabase Python client.
- **templates/**: Jinja2 templates for the frontend.
- **templates_utils.py**: Helpers for rendering templates with project context.

## Submitting a Pull Request

1. **Push to your fork**: `git push origin feat/your-feature-name`.
2. **Create a Pull Request**: Provide a detailed description of what you have changed and the rationale behind it.
3. **Review**: Your PR will be reviewed and feedback provided as soon as possible.

## Future Development Ideas

- Implementation of a native password reset flow.
- Fine-tuning of role-based permissions (Member vs. Lead).
- Data export functionality (PDF/CSV).
- Integration with additional communication platforms.

---
Maintained by the AVINYA community.
