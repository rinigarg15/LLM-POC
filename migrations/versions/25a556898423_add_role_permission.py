"""Add Role, Permission

Revision ID: 25a556898423
Revises: 0f6b5f48dfeb
Create Date: 2024-04-04 13:45:57.726297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime

from ORM.auto_grader_orms import Permission, Role
from ORM.role_constants import Roles, permission_names

# revision identifiers, used by Alembic.
revision: str = '25a556898423'
down_revision: Union[str, None] = '0f6b5f48dfeb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    # Example: Inserting seed data using the ORM model
    roles = [
        Role(
            name=Roles.STUDENT.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Role(
            name=Roles.ADMIN.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    ]

    permissions = []
    for permission_name in permission_names[Roles.ADMIN.value]:
        permissions.append(
            Permission(
                name=permission_name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )
        
    
    session.add_all(roles)
    session.add_all(permissions)
    session.commit()


def downgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)
    # Example downgrade logic (if specific)
    session.query(Role).delete()
    session.query(Permission).delete()
    session.commit()
