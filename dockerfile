FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ✅ Required folders
RUN mkdir -p instance
RUN mkdir -p uploads

# ✅ AUTO DB MIGRATION (VERY IMPORTANT)
RUN python - <<'EOF'
from backend.app import app, db
from sqlalchemy import inspect, text

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if 'user' in tables:
        columns = [c['name'] for c in inspector.get_columns('user')]

        with db.engine.begin() as conn:
            if 'bio' not in columns:
                conn.execute(text("ALTER TABLE user ADD COLUMN bio TEXT"))

            if 'profile_pic' not in columns:
                conn.execute(text("ALTER TABLE user ADD COLUMN profile_pic TEXT"))
    else:
        db.create_all()
EOF

EXPOSE 8000

CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:8000", "backend.app:app"]
