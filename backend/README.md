# Current Django backend

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

The default database is SQLite. Set `DATABASE_URL=mysql://user:password@host:3306/current` for MySQL.

## Legacy import

Run a validation pass first:

```powershell
.\.venv\Scripts\python.exe manage.py migrate_legacy_current `
  --orion-db E:\00_Archived\Current\orion.db `
  --current-db E:\00_Archived\Current\current.db `
  --uploads-root E:\00_Archived\Current\uploads `
  --dry-run `
  --report legacy-report.json
```

Remove `--dry-run` only after the report has no errors and the target database has been backed up.

The new application has no sudo-token authentication. Legacy `sessions` and `sudo` tables are intentionally ignored during import because they are short-lived credentials. All administration is handled by Django Admin at `/admin/`.
