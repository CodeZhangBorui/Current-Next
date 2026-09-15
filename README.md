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

The canonical Django Admin URL is `/admin/`. Next.js does not add an Admin redirect; it uses an explicit `/admin/:path(.*)` rewrite so Django owns the Admin response and nested URLs are not normalized twice. In production, Nginx handles only the bare `/admin` redirect.

Django static assets use `/dj-static/`. Run `python manage.py collectstatic --noinput` after installing dependencies; production Nginx serves that directory directly, while Next.js proxies it to Django during local development.
