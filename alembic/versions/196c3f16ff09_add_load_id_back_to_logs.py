"""Add load_id back to logs

Revision ID: 196c3f16ff09
Revises: a7e997cbe30c
Create Date: 2025-07-01 20:21:45.708778
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '196c3f16ff09'
down_revision: Union[str, Sequence[str], None] = 'a7e997cbe30c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Agregar la columna como nullable
    op.add_column('logs', sa.Column('load_id', sa.Uuid(), nullable=True))

    # 2. Rellenar con UUIDs únicos
    op.execute("UPDATE logs SET load_id = gen_random_uuid()")

    # 3. Alterar a NOT NULL
    op.alter_column('logs', 'load_id', nullable=False)

    # 4. Crear índice
    op.create_index(op.f('ix_logs_load_id'), 'logs', ['load_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_logs_load_id'), table_name='logs')
    op.drop_column('logs', 'load_id')
