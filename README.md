# DDL Command Center

DDL Command Center is a Python desktop application for managing course schedules, deadlines, reminders, and study planning for PKU students.

## Project Goals

- Manage tasks and course deadlines in a unified interface
- Auto-sync DDL, schedule, and exams from PKU Blackboard via IAAA authentication
- Provide deadline alerts and overload warnings
- Visualize progress and workload
- Recommend available time slots based on schedule

## Tech Stack

- Python 3.11+
- PySide6 (GUI)
- SQLite (local storage)
- requests + BeautifulSoup4 (PKU Blackboard scraping)
- matplotlib (statistics charts)
- pycryptodome (RSA password encryption for IAAA)

## Repository Structure

```text
DDL-Center/
├─ app/
│  ├─ main.py           application entry point
│  ├─ config.py         constants and paths
│  │
│  ├─ gui/              PySide6 windows and widgets
│  │  └─ widgets/       reusable widget components
│  │
│  ├─ models/           domain model classes (Task, Course, Exam, …)
│  ├─ managers/         business logic; AppFacade is the GUI-facing API
│  ├─ repositories/     database CRUD per entity
│  ├─ database/         DatabaseManager + schema.sql
│  ├─ network/          IAAA auth, Blackboard HTTP client
│  ├─ parsers/          HTML/JSON parsers for DDL, schedule, exams
│  └─ utils/            time helpers, validators, logger, CSV/JSON utils
│
├─ tests/               pytest test files
├─ data/                SQLite DB file (runtime) + mock HTML samples
├─ docs/                project documents
├─ scripts/             standalone utility scripts (e.g. probe_teaching_site.py)
├─ requirements.txt
├─ .env.example         environment variable template
└─ README.md
```

## PKU Authentication

Authentication uses the PKU IAAA OAuth flow:

1. Fetch RSA public key from `https://iaaa.pku.edu.cn/iaaa/getPublicKey.do`
2. RSA-encrypt the password (PKCS#1 v1.5)
3. POST credentials to `https://iaaa.pku.edu.cn/iaaa/oauthlogin.do` with `appid=blackboard`
4. Receive `token`, then visit the Blackboard campusLogin URL with `?token=<token>`

Copy `.env.example` to `.env` and fill in your student ID and password. **Never commit `.env`.**

## Branch Strategy

- `main`: stable, demo-ready
- `dev`: integration branch
- `feature/*`: individual feature branches

## Development Workflow

1. Pull latest `dev`
2. Create a `feature/*` branch
3. Develop and commit locally
4. Push branch and open a PR to `dev`
5. Merge into `main` only after stabilization

## Getting Started

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in your credentials
python -m app.main
```

## Team Division

| Role | Responsibility |
|---|---|
| A | `gui/` — PySide6 windows, widgets, user interaction |
| B | `models/` + `managers/` — business logic, AppFacade interface |
| C | `database/` + `repositories/` + `network/` + `parsers/` — data layer, PKU sync |
