# FermentLog

**FermentLog** is a full-stack Django web application for home fermentation schedule and jar management. This repository implements **Phase 1 (Project Setup & Account Feature)**, establishing the PostgreSQL/Supabase configuration, authentication, role-based dashboards, and user profile management.

## Phase 1 Implemented Features

- **Account Registration (`/accounts/signup/`)**
  - Validates required fields, valid email format, case-insensitive unique email, unique username, optional contact number format, and matching password confirmation.
  - Hashes all passwords using Django's built-in password hashers.
  - Displays clear validation errors and flash confirmation messages.
- **Session Login & Logout (`/accounts/login/`, `/accounts/logout/`)**
  - Authenticates registered users with explicit error feedback on invalid credentials.
  - Ends user sessions cleanly on logout and redirects unauthenticated visitors from protected routes to login.
- **Role-Based Dashboards (`/`, `/dashboard/fermenter/`, `/dashboard/admin/`)**
  - Supports **Home Fermenter** (`FERMENTER`) and **Administrator** (`ADMIN`) roles enforced at the model (`CheckConstraint`) and view (`RoleRequiredMixin`) levels.
  - Automatically routes each user to their role-specific dashboard on login and returns `403 Forbidden` if a user manually visits another role's dashboard URL.
- **User Profile (`/accounts/profile/`)**
  - Allows logged-in users to view and edit their own details (`first_name`, `last_name`, `email`, `contact_number`, `preferred_ferment`, `bio`, and optional `profile_photo`).
  - Enforces server-side ownership so users can view and update only their own profile.

## Tech Stack

- **Backend & Templates:** Python, Django 6, Django Templates, Bootstrap 5.3.3
- **Database:** PostgreSQL / Supabase PostgreSQL (`psycopg[binary]`)
- **Media / Config:** Pillow, `python-dotenv`

## Local Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # macOS / Linux:
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables by copying `.env.example` to `.env` and filling in your PostgreSQL or Supabase credentials:
   ```bash
   cp .env.example .env
   ```
4. Apply database migrations and start the development server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
5. Run automated tests:
   ```bash
   python manage.py test
   ```
