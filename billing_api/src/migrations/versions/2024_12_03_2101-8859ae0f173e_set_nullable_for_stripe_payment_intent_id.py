"""set_nullable_for_stripe_payment_intent_id

Revision ID: 8859ae0f173e
Revises: 6c8b90e219a8
Create Date: 2024-12-03 21:01:50.113913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8859ae0f173e'
down_revision: Union[str, None] = '6c8b90e219a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('transactions', 'stripe_payment_intent_id',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('transactions', 'stripe_payment_intent_id',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###
