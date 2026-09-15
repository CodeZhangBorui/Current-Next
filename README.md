# Current

Current is being migrated from the archived Flask application to a Next.js + Django stack.

## Development

Backend (venv):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Frontend (Bun):

```powershell
cd frontend
bun install
bun run dev
```

Set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1` in `frontend/.env.local` for local development.

The canonical Django Admin URL is `/admin/`. The bare `/admin` path is redirected once to `/admin/`; Next.js is configured with `skipTrailingSlashRedirect` and an explicit `/admin/:path(.*)` rewrite so nested Admin URLs are not normalized twice.
