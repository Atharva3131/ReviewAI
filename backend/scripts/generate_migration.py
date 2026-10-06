import os
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import alembic.autogenerate
from alembic.migration import MigrationContext
from alembic.autogenerate import render_python_code
from sqlalchemy import create_engine
import app.models
from app.core.database import Base

def generate() -> None:
    engine = create_engine('sqlite:///:memory:')
    mc = MigrationContext.configure(engine.connect())
    diff = alembic.autogenerate.compare_metadata(mc, Base.metadata)
    upgrade_code = render_python_code(diff)

    content = f'''"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-06 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
{upgrade_code}

def downgrade() -> None:
    pass
'''

    out_path = Path(__file__).parent.parent / "alembic" / "versions" / "0001_initial_schema.py"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Successfully generated migration file: {out_path}")

if __name__ == "__main__":
    generate()
