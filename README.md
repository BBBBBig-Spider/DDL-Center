# DDL Command Center

DDL Command Center is a Python desktop application for managing course schedules, deadlines, reminders, and study planning.

## Project Goals

- Manage tasks and course deadlines in a unified interface
- Support manual task editing and filtering
- Provide deadline alerts and overload warnings
- Visualize progress and workload
- Recommend available time slots based on schedule

## Tech Stack

- Python
- PySide6
- SQLite
- GitHub for collaboration

## Repository Structure

```text
app/
  ui/             GUI components
  models/         domain models
  services/       business logic
  repositories/   data access
  database/       database-related code
  utils/          helper functions
  main.py         application entry

docs/             project documents
tests/            test files
resources/        icons / assets / sample data
```

## Branch Strategy

- `main`: stable and demo-ready branch
- `dev`: integration branch for development
- `feature/*`: individual feature branches

## Development Workflow

1. Pull latest dev
2. Create a new feature/* branch
3. Develop and commit locally
4. Push branch and open a PR to dev
5. Merge into main only after stabilization

## Getting Started

```bash
pip install -r requirements.txt
python app/main.py
```
