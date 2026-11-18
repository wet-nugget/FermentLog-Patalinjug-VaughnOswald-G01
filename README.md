# FermentLog

**FermentLog** is a full-stack Django web application for home fermentation schedule and jar management. It enables home fermentation hobbyists to organize their fermentation jars, calculate brine salt and sugar ratios, monitor batch progress, and manage standard culture baselines backed by PostgreSQL / Supabase or SQLite for local testing.

## Core & Standard Features

### Batch & Jar Logger (`batches`)
- **Batch & Jar Entry Management (`/batches/`, `/batches/new/`, `/batches/<id>/`)**
  - Create, view, edit, archive/restore, and delete fermentation batches (`JarBatch`) linked to standard `FermentType` categories and `RatioTemplate` presets.
  - Enforces unique jar labels per user (`unique_user_jar_id`), positive jar capacity (`> 0` mL), non-negative target duration, lifecycle status (`FERMENTING`, `COLD STORAGE`, `COMPLETED`), and completion-date rules (`BR-09`).
  - Tracks elapsed fermentation days, remaining target days, progress percentages, and recipe ingredient notes.
- **Recipe & Ratio Calculator (`/batches/calculator/`)**
  - Computes working vessel volume after headspace allowance (default 15%), brine salt weights, produce + brine salt totals, and sugar weights in grams.
  - Supports loading standard ratio presets and launching a new jar batch pre-filled with the calculated values.
- **Culture & Ratio Reference Library (`/batches/categories/`)**
  - Seeded with standard fermentation baselines (`Sauerkraut`, `Kimchi`, `Hot Sauce`, `Kombucha`) and default ratio templates.
  - Administrator-only creation and editing of ferment categories and ratio presets (`BR-12`).

### Account, Role Dashboards & Profile (`accounts`, `dashboard`)
- **Account Registration (`/accounts/signup/`)**: Validates required fields, valid email format, case-insensitive unique email, unique username, optional contact number format, and matching password confirmation with Django password hashing.
- **Session Login & Logout (`/accounts/login/`, `/accounts/logout/`)**: Authenticates users with explicit invalid-credential feedback and protects private routes from anonymous access.
- **Role-Based Dashboards (`/`, `/dashboard/fermenter/`, `/dashboard/admin/`)**: Separates **Home Fermenter** (`FERMENTER`) and **Administrator** (`ADMIN`) workspaces with `RoleRequiredMixin` (`403 Forbidden` on cross-role access).
- **User Profile (`/accounts/profile/`)**: Allows logged-in users to view and edit only their own profile details (`first_name`, `last_name`, `email`, `contact_number`, `preferred_ferment`, `bio`, and `profile_photo`).

## Tech Stack

- **Backend & Templates:** Python, Django 6.1.3, Django Templates, Bootstrap 5.3.3
- **Database:** PostgreSQL / Supabase (`psycopg[binary]`) or SQLite (local testing)
- **Media / Config:** Pillow, `python-dotenv`

## Local Setup

### 1. Create a Virtual Environment & Install Dependencies
```bash
python -m venv venv
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Database Environment

#### Option A: PostgreSQL / Supabase (Production / Primary Setup)
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Fill in your PostgreSQL or Supabase credentials (`DB_ENGINE=django.db.backends.postgresql`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_SSLMODE`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`).

#### Option B: SQLite Setup (For Local Testing Without Supabase)
If you want to run or test FermentLog locally without connecting to Supabase/PostgreSQL:
1. Copy `.env.example` to `.env` (or edit your existing `.env`).
2. Comment out the PostgreSQL `DB_*` variables and enable the SQLite variables at the bottom of `.env`:
   ```env
   DB_ENGINE=django.db.backends.sqlite3
   DB_NAME=db.sqlite3
   ```
   *(Alternatively, on Windows PowerShell you can set it for the current terminal session only: `$env:DB_ENGINE="django.db.backends.sqlite3"`, or on macOS/Linux prefix commands with `DB_ENGINE=django.db.backends.sqlite3`.)*
3. Note: `*.sqlite3` and `db.sqlite3` are listed in `.gitignore` so local test databases are never committed.

### 3. Apply Migrations, Seed Demo Data & Run Server
```bash
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```
The `seed_demo_data` command creates sample batches and two test accounts:
- **Administrator:** `benchadmin` / `BrineAdmin!2026`
- **Home Fermenter:** `krautkeeper` / `BrineBatch!2026`

### 4. Run Automated Tests
```bash
python manage.py test
```
*(Or using SQLite without modifying `.env`:)*
```powershell
$env:DB_ENGINE="django.db.backends.sqlite3"; python manage.py test
```
