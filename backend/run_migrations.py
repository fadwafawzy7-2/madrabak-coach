"""Apply migrations and seed dev data. Usage: python run_migrations.py [--seed]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.db import get_engine, run_migrations

applied = run_migrations(get_engine(), Path(__file__).parent / "migrations")
print(f"Applied migrations: {applied or 'none (up to date)'}")
if "--seed" in sys.argv:
    from seeds.dev_foods_seed import seed_foods
    n = seed_foods(get_engine())
    print(f"Seeded {n} dev foods")
