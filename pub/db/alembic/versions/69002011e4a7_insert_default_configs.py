"""insert default configs

Revision ID: 69002011e4a7
Revises: aaf6bbd973c5
Create Date: 2025-07-14 14:02:43.284171

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer
from db.model.message_info_config import MessageInfoConfig

# revision identifiers, used by Alembic.
revision: str = '69002011e4a7'
down_revision: Union[str, Sequence[str], None] = 'aaf6bbd973c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.bulk_insert(MessageInfoConfig.__table__, [
        {
            'mac': '74:fe:48:6c:20:df',
            'data_field_index': 0,
            'ip': '192.168.0.14',
            'source_name': 'Ironer 1',
            'zone': 'finishing',
            'machine': 'Ironer 1',
            'machine_stage': 'stacker',
        },
        {
            'mac': '74:fe:48:6c:20:df',
            'data_field_index': 1,
            'ip': '192.168.0.14',
            'source_name': 'Ironer 1',
            'zone': 'finishing',
            'machine': 'Ironer 1',
            'machine_stage': 'folder',
        },
        {
            'mac': '74:fe:48:49:99:86',
            'data_field_index': 0,
            'ip': '192.168.0.185',
            'source_name': 'Ironer 3',
            'zone': 'finishing',
            'machine': 'Ironer 3',
            'machine_stage': 'stacker',
        },
    ])


def downgrade() -> None:
    op.execute("""
    DELETE FROM message_info_config
    WHERE (mac, data_field_index) IN (
        ('74:fe:48:6c:20:df', 0),
        ('74:fe:48:6c:20:df', 1),
        ('74:fe:48:49:99:86', 0)
    )
""")

