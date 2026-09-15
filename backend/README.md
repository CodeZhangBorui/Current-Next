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

## Permissions

New users are active by default and automatically receive only `current.create_entry`. Staff and superuser status remain disabled unless an administrator explicitly enables them. Assign all other global permissions directly to individual users in Django Admin; the legacy `Current Users`, `Current Editors`, `Current Chief Editors`, and `Current Administrators` groups are no longer used.

Issue roles remain scoped and do not require global permissions:

- Users selected in an issue's `Editors` field can review entries in that issue.
- The issue `Leader` and `Responsible editor` can make chief-editor decisions and manage that issue's PDF.

Permission names are localized in Chinese after migrations so Django Admin does not expose English permission labels.

For local development, the default CSRF trusted origins include `http://localhost:3000` and `http://127.0.0.1:3000`. In production, set `CSRF_TRUSTED_ORIGINS` to the public HTTPS origin used by the browser, separated by commas.
