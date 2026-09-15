# Production processes

Run Django with Gunicorn from `backend/.venv`:

```bash
cd backend
.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000
```

Run the frontend with Bun:

```bash
cd frontend
bun run build
bun run start -- -p 3000
```

Load `nginx.conf` as the public reverse proxy. Keep `/media/` on a persistent volume and do not expose the Django development server publicly.

Administration is provided only by Django Admin at `/admin/`; the archived Flask sudo-token flow is not part of the new runtime.

Before deployment, collect Django static assets:

```bash
cd backend
.venv/bin/python manage.py collectstatic --noinput
```

The Nginx `/dj-static/` location must point to the same `backend/staticfiles/` directory used by `STATIC_ROOT`.
